#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <SoftwareSerial.h>

// ───── 상수 및 핀 설정 ─────
// RFID 관련 핀
#define SS_PIN 10
#define RST_PIN 9

#define DATA_BLOCK 4

// 출력 제어 핀
#define SERVO_PIN A0
#define GREEN_LED_PIN 7
#define RED_LED_PIN 6
#define YELLOW_LED_PIN 5

// ESP8266 통신 핀
#define ESP_RX_PIN 2
#define ESP_TX_PIN 3

// 서보 모터 각도
#define SERVO_IDLE_ANGLE 90
#define SERVO_UNLOCK_ANGLE 180

// 시간 관련 상수
#define READ_TIMEOUT 3000
#define LED_TIMEOUT 2000
#define WIFI_CHECK_INTERVAL 10000
#define AT_TIMEOUT 3000

// ───── 객체 초기화 ─────
MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
Servo access_servo;
SoftwareSerial esp_serial(ESP_RX_PIN, ESP_TX_PIN);

// ───── 상태 변수 ─────
// RFID 카드 관련 상태
bool is_register_mode = false;
bool is_card_writable = false;
bool is_card_present = false;
String current_uid = "";
String write_emp_id = "";
String last_processed_uid = "";
unsigned long last_read_time = 0;

// WiFi 상태 변수
bool is_wifi_connected = false;
unsigned long last_wifi_check_time = 0;

// LED 및 액세스 제어 상태
bool is_access_led_active = false;
unsigned long access_led_start_time = 0;
int access_led_pin = -1;

void setup()
{
    Serial.begin(9600);
    esp_serial.begin(9600);
    
    // 하드웨어 초기화
    init_hardware();
    
    // WiFi 설정
    setup_wifi();

    Serial.println("🟢 게이트 제어 시작됨");
}

void loop()
{
    handle_wifi_command();
    handle_rfid();
    update_access_led();
    check_wifi_status();
}

// ───── 초기화 함수 ─────

void init_hardware()
{
    // RFID 초기화
    SPI.begin();
    mfrc522.PCD_Init();
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    // LED 핀 초기화
    pinMode(GREEN_LED_PIN, OUTPUT);
    pinMode(RED_LED_PIN, OUTPUT);
    pinMode(YELLOW_LED_PIN, OUTPUT);
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(YELLOW_LED_PIN, LOW);

    // 서보 모터 초기화
    access_servo.attach(SERVO_PIN);
    access_servo.write(SERVO_IDLE_ANGLE);
    delay(100);
}

void setup_wifi()
{
    send_at("AT");
    send_at("AT+CWMODE=1");
    send_at("AT+CIPSTA=\"192.168.0.20\"");
    send_at("AT+CWJAP=\"addinedu_class_2 (2.4G)\",\"addinedu1\"");
    delay(3000);
    send_at("AT+CIPMUX=0");
    // send_at("AT+CIPSTART=\"TCP\",\"192.168.0.3\",9000");
    send_at("AT+CIPSTART=\"TCP\",\"192.168.0.227\",9100");
}

// ───── WiFi 통신 관련 함수 ─────

void send_at(const String& cmd)
{
    access_servo.detach();  // AT 명령 전송 중 서보 간섭 방지
    Serial.println("📤 AT 전송: " + cmd);
    esp_serial.println(cmd);

    unsigned long timeout = millis() + AT_TIMEOUT;
    while (millis() < timeout)
    {
        if (esp_serial.available())
        {
            char c = esp_serial.read();
            Serial.write(c);
        }
    }
    access_servo.attach(SERVO_PIN);
}

void send_tcp_message(String msg)
{
    String cip_send_cmd = "AT+CIPSEND=" + String(msg.length());
    Serial.println("📤 TCP 전송 준비: " + cip_send_cmd);
    esp_serial.println(cip_send_cmd);

    // '>' 프롬프트 대기
    unsigned long timeout = millis() + AT_TIMEOUT;
    bool prompt_received = false;

    while (millis() < timeout)
    {
        if (esp_serial.available())
        {
            String resp = esp_serial.readStringUntil('\n');
            resp.trim();
            Serial.println("🟢 ESP 응답: " + resp);
            if (resp.endsWith(">"))
            {
                prompt_received = true;
                break;
            }
        }
    }

    if (!prompt_received)
    {
        Serial.println("🔴 전송 실패: '>' 미수신");
        return;
    }

    esp_serial.print(msg);
    Serial.println("📤 TCP 데이터 전송: " + msg);
}

String extract_ipd_data(String input)
{
    int ipd_index = input.indexOf("+IPD");
    int colon_index = input.indexOf(':');

    if (ipd_index == -1 || colon_index == -1 || colon_index + 1 >= input.length())
    {
        return "";
    }

    String data = input.substring(colon_index + 1);
    data.trim();
    return data;
}

void check_wifi_status()
{
    if (millis() - last_wifi_check_time >= WIFI_CHECK_INTERVAL)
    {
        last_wifi_check_time = millis();

        access_servo.detach();
        esp_serial.println("AT+CWJAP?");
        unsigned long timeout = millis() + 2000;
        bool found_ssid = false;

        while (millis() < timeout)
        {
            if (esp_serial.available())
            {
                String line = esp_serial.readStringUntil('\n');
                line.trim();
                if (line.indexOf("addinedu_class_2") != -1)
                {
                    found_ssid = true;
                }
                if (line == "OK") break;
            }
        }

        access_servo.attach(SERVO_PIN);
        if (found_ssid)
        {
            if (!is_wifi_connected)
            {
                is_wifi_connected = true;
                Serial.println("✅ WiFi 연결 유지 중");
            }
        }
        else
        {
            if (is_wifi_connected)
            {
                is_wifi_connected = false;
                Serial.println("🔴 WiFi 연결 끊김!");
                setup_wifi();
            }
        }
    }
}

// ───── 명령 처리 함수 ─────

void handle_wifi_command()
{
    if (esp_serial.available())
    {
        String raw = esp_serial.readStringUntil('\n');
        raw.trim();

        if (raw.startsWith("+IPD"))
        {
            String cmd = extract_ipd_data(raw);
            process_command(cmd);
        }
    }
}

void process_command(String cmd)
{
    // 등록 모드 진입
    if (cmd == "GCmd1")
    {
        enter_register_mode();
    }
    // 일반 모드 복귀
    else if (cmd == "GCmd0")
    {
        exit_register_mode();
    }
    // 카드 정보 쓰기
    else if (cmd.startsWith("GCwr"))
    {
        write_card_data(cmd.substring(4));
    }
    // 출입 허용
    else if (cmd == "GCac1")
    {
        handle_access_result("ALLOW");
        Serial.println("GRok: 출입 허용 → GREEN ON");
        send_tcp_message("GRok\n");
    }
    // 출입 거부
    else if (cmd == "GCac0")
    {
        handle_access_result("DENY");
        Serial.println("GRok: 출입 거부 → RED ON");
        send_tcp_message("GRok\n");
    }
    // 알 수 없는 명령
    else
    {
        Serial.println("GXe4: 알 수 없는 명령");
        send_tcp_message("GXe4\n");
    }
}

void enter_register_mode()
{
    is_register_mode = true;
    is_card_writable = false;
    current_uid = "";
    last_processed_uid = "";
    digitalWrite(YELLOW_LED_PIN, HIGH);
    Serial.println("GRok: 등록 모드 진입");
    send_tcp_message("GRok\n");
}

void exit_register_mode()
{
    is_register_mode = false;
    is_card_writable = false;
    write_emp_id = "";
    current_uid = "";
    digitalWrite(YELLOW_LED_PIN, LOW);
    Serial.println("GRok: 출입 모드 복귀");
    send_tcp_message("GRok\n");
}

void write_card_data(String emp_id)
{
    write_emp_id = emp_id;

    // 카드 존재 여부 확인
    if (!is_card_writable || current_uid == "")
    {
        Serial.println("GXe0: 카드 없음");
        send_tcp_message("GXe0\n");
        return;
    }

    // 카드 재검증
    mfrc522.PCD_Init();
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial())
    {
        Serial.println("GXe0: 카드 없음 (쓰기 시)");
        send_tcp_message("GXe0\n");
        return;
    }

    // UID 일치 여부 확인
    String uid_str = get_uid_string();
    if (uid_str != current_uid)
    {
        Serial.println("GXe1: 다른 카드가 감지됨");
        send_tcp_message("GXe1\n");
        return;
    }

    // 카드 인증
    byte trailer_block = (DATA_BLOCK / 4) * 4 + 3;
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailer_block, &key, &(mfrc522.uid));

    if (status != MFRC522::STATUS_OK)
    {
        Serial.println("GXe1: 인증 실패");
        send_tcp_message("GXe1\n");
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    // 데이터 쓰기
    byte buffer[16] = {0};
    write_emp_id.getBytes(buffer, 16);

    bool write_success = false;
    for (int attempt = 0; attempt < 3; attempt++)
    {
        status = mfrc522.MIFARE_Write(DATA_BLOCK, buffer, 16);
        if (status == MFRC522::STATUS_OK)
        {
            write_success = true;
            break;
        }
    }

    // 결과 처리
    if (write_success)
    {
        Serial.print("GRok: 카드 쓰기 완료 → ");
        Serial.print(current_uid);
        Serial.print(" ← ");
        Serial.println(write_emp_id);
        send_tcp_message("GRok\n");
    }
    else
    {
        Serial.println("GXe2: 카드 쓰기 실패");
        send_tcp_message("GXe2\n");
    }

    // 리소스 해제 및 상태 초기화
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    is_card_writable = false;
    current_uid = "";
    write_emp_id = "";
    last_processed_uid = uid_str;
    last_read_time = millis();
}

// ───── RFID 처리 함수 ─────

void handle_rfid()
{
    mfrc522.PCD_Init();

    // 카드 감지 확인
    if (!mfrc522.PICC_IsNewCardPresent())
    {
        if (is_card_present) is_card_present = false;
        return;
    }

    // 카드 시리얼 번호 읽기
    if (!mfrc522.PICC_ReadCardSerial()) return;

    String uid_str = get_uid_string();
    unsigned long current_time = millis();

    // 중복 읽기 방지
    if (uid_str == last_processed_uid && current_time - last_read_time < READ_TIMEOUT)
    {
        if (!is_register_mode || (is_register_mode && is_card_writable))
        {
            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
            return;
        }
    }

    is_card_present = true;

    // 카드 인증
    if (!authenticate_card())
    {
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    // 카드 데이터 읽기
    byte buffer[18];
    byte size = sizeof(buffer);
    MFRC522::StatusCode status = mfrc522.MIFARE_Read(DATA_BLOCK, buffer, &size);

    if (status != MFRC522::STATUS_OK)
    {
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    // 사원 ID 추출
    char emp_id[17] = {0};
    memcpy(emp_id, buffer, 16);

    // 모드에 따른 처리
    process_card_data(uid_str, String(emp_id), current_time);

    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
}

bool authenticate_card()
{
    byte trailer_block = (DATA_BLOCK / 4) * 4 + 3;
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailer_block, &key, &(mfrc522.uid));

    return (status == MFRC522::STATUS_OK);
}

void process_card_data(String uid_str, String emp_id, unsigned long current_time)
{
    if (is_register_mode)
    {
        if (!is_card_writable)
        {
            String msg = "GEwr" + uid_str + ";" + emp_id + "\n";
            send_tcp_message(msg);
            current_uid = uid_str;
            is_card_writable = true;
            last_processed_uid = uid_str;
            last_read_time = current_time;
        }
    }
    else
    {
        // 출입 모드: 카드 UID와 사원 ID 전송
        String msg = "GEid" + uid_str + ";" + emp_id + "\n";
        send_tcp_message(msg);
        last_processed_uid = uid_str;
        last_read_time = current_time;
    }
}

String get_uid_string()
{
    String uid_str = "";
    for (byte i = 0; i < mfrc522.uid.size; i++)
    {
        uid_str += String(mfrc522.uid.uidByte[i], HEX);
        if (i < mfrc522.uid.size - 1) uid_str += ":";
    }
    return uid_str;
}

// ───── 액세스 제어 함수 ─────

void handle_access_result(String type)
{
    if (type == "ALLOW")
    {
        access_led_pin = GREEN_LED_PIN;
        access_servo.attach(SERVO_PIN);
        access_servo.write(SERVO_UNLOCK_ANGLE);
        delay(100);
    }
    else if (type == "DENY")
    {
        access_led_pin = RED_LED_PIN;
    }
    else
    {
        return;
    }

    digitalWrite(access_led_pin, HIGH);
    access_led_start_time = millis();
    is_access_led_active = true;
}

void update_access_led()
{
    if (is_access_led_active && millis() - access_led_start_time >= LED_TIMEOUT)
    {
        digitalWrite(access_led_pin, LOW);
        is_access_led_active = false;
        
        // 서보 모터를 원래 위치로 복귀 (GREEN LED가 꺼질 때만)
        if (access_led_pin == GREEN_LED_PIN)
        {
            access_servo.attach(SERVO_PIN);
            access_servo.write(SERVO_IDLE_ANGLE);
        }
        
        access_led_pin = -1;
    }
}
