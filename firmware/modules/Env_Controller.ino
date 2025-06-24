#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

/**
 * ESP32 온도 제어 시스템
 * 세 개의 구역(A, B, C)의 온도를 감지하고 제어하는 프로그램 
 **/

// ───── Wi-Fi 설정 ─────
const char* SSID = "Galaxy Z Fold42488";
const char* PASSWORD = "623623623";
const char* HOST = "192.168.2.2";
const uint16_t PORT = 9000;
WiFiClient client;

IPAddress local_IP(192, 168, 2, 4);
IPAddress gateway(192, 168, 2, 1);
IPAddress subnet(255, 255, 255, 0);

// ───── OLED 설정 ─────
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_SDA   22
#define OLED_SCL   23
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ───── 핀 정의 ─────
// 구역 A 핀 설정
const int A_BLUE_LED   = 2;
const int A_YELLOW_LED = 4;
const int A_SENSOR     = 36;
const int A_BUZZER     = 5;
const int A_MOTOR_IA   = 15;
const int A_MOTOR_IB   = 13;

// 구역 B 핀 설정
const int B_BLUE_LED   = 16;
const int B_YELLOW_LED = 17;
const int B_SENSOR     = 34;
const int B_BUZZER     = 18;
const int B_MOTOR_IA   = 19;
const int B_MOTOR_IB   = 21;

// 구역 C 핀 설정 
const int C_RED_LED     = 25; // C만 난방 기능 포함
const int C_BLUE_LED    = 26;
const int C_YELLOW_LED  = 27;
const int C_SENSOR      = 35;
const int C_BUZZER      = 14;
const int C_MOTOR_IA    = 33;
const int C_MOTOR_IB    = 32;

// ───── 온도 제어 관련 상수 ─────
const float MIN_TEMPS[3] = { -25.0,  0.0, 15.0 };  // 최소 허용 온도
const float MAX_TEMPS[3] = { -15.0, 10.0, 25.0 };  // 최대 허용 온도
float base_temps[3]      = { -20.0, 5.0, 20.0 };   // 기준 온도 (조절 가능)
const float cal = -1.0;
const float CALIBRATION[3] = { -30.0 + cal, -5.0 + cal, 10.0 + cal };  // 센서 보정값

const float HEATING_START = -2.0;  // C 구역: 이보다 낮으면 가열 시작
const float HEATING_THRESHOLDS[2] = { -4.0, -6.0 }; // 가열: [1단계, 2단계] 기준
const float COOLING_START =  2.0;  // 전체 구역: 이보다 높으면 냉각 시작
const float COOLING_THRESHOLDS[2] = { 4.0, 6.0 };  // 냉각: [1단계, 2단계] 기준

const int SPEED_VALS[4] = { 0, 52, 64, 75 };      // 팬 속도 조절 PWM 0~255


// ───── 상태 및 타이머 변수 ─────
unsigned long last_sensor_read_time = 0;
unsigned long last_display_time = 0;
unsigned long last_action_time = 0;
unsigned long last_reconnect_time = 0;

const unsigned long SENSOR_READ_INTERVAL = 1000;   // 센서 읽기 간격
const unsigned long DISPLAY_INTERVAL = 1000;       // 디스플레이 업데이트 간격
const unsigned long ACTION_INTERVAL = 5000;        // 액션 실행 간격
const unsigned long RECONNECT_INTERVAL = 10000;    // 재연결 시도 간격

// 상태 저장 변수
bool warning_states[3] = { false, false, false };  // 각 구역 경고 상태
int last_speeds[3]     = { -1, -1, -1 };           // 마지막으로 설정된 모터 속도
float current_temps[3] = { 0.0, 0.0, 0.0 };        // 현재 측정된 온도

// 함수 선언
void setup_pins();
void setup_display();
void connect_wifi();
void connect_to_server();

void handle_command(String cmd);

void read_sensor_values();
void update_display();
void use_data_and_send_events();


/** 초기 설정 함수 **/
void setup()
{
    Serial.begin(115200);
    setup_pins();
    setup_display();

    connect_wifi();
    connect_to_server();
}

/** 메인 루프 함수 **/
void loop()
{
    unsigned long now = millis();

    // WiFi 연결이 끊어졌으면 재시도
    if (WiFi.status() != WL_CONNECTED) 
    {
        connect_wifi(); // 재시도
        return;
    }

    // 서버에서 명령 수신 처리
    if (client.connected() && client.available()) 
    {
        String cmd = client.readStringUntil('\n');
        Serial.println("📻 [명령 수신] " + cmd);
        handle_command(cmd);
    }

    // 일정 간격으로 센서값 읽기
    if (now - last_sensor_read_time > SENSOR_READ_INTERVAL) 
    {
        read_sensor_values();
        last_sensor_read_time = millis();
    }

    // 일정 간격으로 디스플레이 업데이트
    if (now - last_display_time > DISPLAY_INTERVAL) 
    {
        update_display();
        last_display_time = millis();
    }

    // 일정 간격으로 센서 데이터 전송 및 액션 실행
    if (now - last_action_time > ACTION_INTERVAL) 
    {
        use_data_and_send_events();
        last_action_time = millis();
    }

    // 서버 연결이 끊어진 경우 재연결 시도
    if (!client.connected() && millis() - last_reconnect_time > RECONNECT_INTERVAL) 
    {
        connect_to_server();
        last_reconnect_time = millis();
    }
}

// ───── 초기화 및 연결 함수 ─────
/** GPIO 핀 설정 함수 **/
void setup_pins()
{
    // 구역 A 핀 설정
    pinMode(A_BLUE_LED, OUTPUT); 
    pinMode(A_YELLOW_LED, OUTPUT); 
    pinMode(A_BUZZER, OUTPUT);
    pinMode(A_MOTOR_IA, OUTPUT); 
    pinMode(A_MOTOR_IB, OUTPUT);

    // 구역 B 핀 설정
    pinMode(B_BLUE_LED, OUTPUT); 
    pinMode(B_YELLOW_LED, OUTPUT); 
    pinMode(B_BUZZER, OUTPUT);
    pinMode(B_MOTOR_IA, OUTPUT); 
    pinMode(B_MOTOR_IB, OUTPUT);

    // 구역 C 핀 설정
    pinMode(C_BLUE_LED, OUTPUT); 
    pinMode(C_YELLOW_LED, OUTPUT); 
    pinMode(C_RED_LED, OUTPUT);
    pinMode(C_BUZZER, OUTPUT); 
    pinMode(C_MOTOR_IA, OUTPUT); 
    pinMode(C_MOTOR_IB, OUTPUT);

    // OLED 통신 핀 설정
    Wire.begin(OLED_SDA, OLED_SCL);
}

/** OLED 디스플레이 초기화 함수 **/
void setup_display()
{
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) 
    {
        Serial.println("❌ OLED 처리 실패");
        while (true);  // OLED 초기화 실패시 진행 불가
    }
    
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("OLED 처리 완료");
    display.display();
}

/** WiFi 연결 함수 **/
void connect_wifi()
{
    // OLED 연결 중 메시지 표시
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("WiFi connecting...");
    display.display();

    WiFi.mode(WIFI_STA);
    WiFi.config(local_IP, gateway, subnet);
    WiFi.begin(SSID, PASSWORD);
    
    // 최대 10초 동안 연결 시도
    for (int i = 0; i < 10 && WiFi.status() != WL_CONNECTED; i++) 
    {
        delay(1000);
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.print("\u2705 WiFi 연결함: ");
        Serial.println(WiFi.localIP());
    }
    else 
    {
        Serial.println("\u274c WiFi 연결 실패");
    }
}

/** 서버 연결 함수 **/
void connect_to_server()
{
    if (WiFi.status() == WL_CONNECTED && client.connect(HOST, PORT))
    {
        Serial.println("\u2705 서버 연결 성공");
    }
    else 
    {
        Serial.println("\u274c 서버 연결 실패");
    }
}


// ───── 명령어 수신 함수 ─────
/** 서버 명령 처리 함수 **/
void handle_command(String cmd)
{
    cmd.trim();
    
    // 온도 기준점 설정 명령 처리 (HCpX##.#)
    if (cmd.startsWith("HCp") && cmd.length() >= 5) 
    {
        char zone_char = cmd.charAt(3);  // 구역 문자 (A/B/C)
        float new_base = cmd.substring(4).toFloat();  // 새 기준 온도
        int zone_index = zone_char - 'A';  // 구역 인덱스 (0/1/2)

        if (zone_index >= 0 && zone_index < 3) 
        {
            // 유효한 구역인 경우 기준점 변경
            base_temps[zone_index] = new_base;
            Serial.printf("\u2699️ 기준치 변경: %c → %.1f\n", zone_char, new_base);
            
            if (client.connected()) 
            {
                client.println("HRok");  // 성공 응답
            }
        } 
        else 
        {
            // 유효하지 않은 구역인 경우 오류
            Serial.println("\u274c 기준치 변경 실패: 구역 오류");
            
            if (client.connected()) 
            {
                client.println("HXe1");  // 오류 응답
            }
        }
    }
}


// ───── 센서 input, output 함수 ─────
/** 센서값 읽기 함수 **/
void read_sensor_values()
{
    const int sensor_pins[3] = { A_SENSOR, B_SENSOR, C_SENSOR };
    
    // 각 센서 값 읽기
    for (int i = 0; i < 3; i++) 
    {
        // 아날로그 값을 전압으로 변환 (0-4095 → 0-3.3V)
        float voltage = analogRead(sensor_pins[i]) * (3.3 / 4095.0);
        
        // 전압을 온도로 변환 (센서 특성 + 보정값 적용)
        current_temps[i] = voltage * 100.0 + CALIBRATION[i];
    }
}

/** OLED 디스플레이 업데이트 함수 **/
void update_display()
{
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);

    // 각 구역별 정보 표시
    for (int i = 0; i < 3; i++) 
    {
        String zone = String(char('A' + i));
        String mode;
        
        // 모드 결정 (냉각/가열/정상)
        if (last_speeds[i] > 0) 
        {
            if (i == 2 && digitalRead(C_RED_LED)) 
            {
                mode = "Heat";  // 가열 모드 (C 구역만 가능)
            } 
            else 
            {
                mode = "Cool";  // 냉각 모드
            }
        } 
        else 
        {
            mode = "Normal";    // 정상 모드
        }

        // 구역, 온도, 모드, 속도 표시
        display.printf("%s: %.1fC %s S%d\n",
            zone.c_str(),
            current_temps[i],
            mode.c_str(),
            last_speeds[i]);
    }

    display.display();
}


// ───── 이벤트 처리 및 송신 함수 ─────
/** 센서 데이터 전송 및 제어 액션 수행 함수 **/
void use_data_and_send_events()
{
    // 각 구역별 핀 배열 정의
    const int motors_ia[3] = { A_MOTOR_IA, B_MOTOR_IA, C_MOTOR_IA };
    const int motors_ib[3] = { A_MOTOR_IB, B_MOTOR_IB, C_MOTOR_IB };
    const int blue_leds[3] = { A_BLUE_LED, B_BLUE_LED, C_BLUE_LED };
    const int yellow_leds[3] = { A_YELLOW_LED, B_YELLOW_LED, C_YELLOW_LED };
    const int buzzers[3] = { A_BUZZER, B_BUZZER, C_BUZZER };

    // 각 구역별 처리
    for (int i = 0; i < 3; i++) 
    {
        float temp = current_temps[i];
        String zone = String(char('A' + i));
        float diff = temp - base_temps[i];  // 기준점과의 온도차
        int speed = 0;
        bool cooling = false, heating = false;

        // 경고 상태 확인 (온도가 허용 범위 밖인 경우)
        bool in_warning = (temp < MIN_TEMPS[i] || temp > MAX_TEMPS[i]);
        
        // 경고 상태가 변경된 경우 처리
        if (in_warning != warning_states[i]) 
        {
            String msg = "HEw" + zone + (in_warning ? "1" : "0");
            Serial.println((in_warning ? "🚨 경고 발생 → " : "✅ 경고 해제 → ") + msg);
            
            if (client.connected()) 
            {
                client.println(msg);
            }
            
            digitalWrite(yellow_leds[i], in_warning);  // 경고등 제어
            digitalWrite(buzzers[i], in_warning);      // 버저 제어
            warning_states[i] = in_warning;            // 상태 저장
        }

        // 온도에 따른 모드 및 속도 결정
        if (i == 2 && diff < HEATING_START)  // C 구역만 가열 가능
        {
            heating = true;
            if (diff >= HEATING_THRESHOLDS[0])        speed = 1;
            else if (diff >= HEATING_THRESHOLDS[1])   speed = 2;
            else                                       speed = 3;
        } 
        else if (diff > COOLING_START)  // 모든 구역 냉각 가능
        {
            cooling = true;
            if (diff <= COOLING_THRESHOLDS[0])        speed = 1;
            else if (diff <= COOLING_THRESHOLDS[1])   speed = 2;
            else                                       speed = 3;
        }

        // LED 및 모터 제어
        digitalWrite(blue_leds[i], cooling);  // 냉각 모드 표시
        if (i == 2) 
        {
            digitalWrite(C_RED_LED, heating);  // C 구역 가열 모드 표시
        }
        
        // 모터 속도 제어 (PWM)
        analogWrite(motors_ia[i], SPEED_VALS[speed]);
        analogWrite(motors_ib[i], 0);

        // 모터 속도가 변경된 경우 서버에 알림
        if (speed != last_speeds[i]) 
        {
            last_speeds[i] = speed;
            char mode = cooling ? 'C' : (heating ? 'H' : '0');
            String msg = "HE" + zone + mode + String(speed);
            Serial.println("\u2699️ 속도 변경 → " + msg);
            
            if (client.connected()) 
            {
                client.println(msg);
            }
        }
    }

    // 모든 구역의 현재 온도를 서버로 전송
    String msg = "HEtp" + String(current_temps[0], 1) + ";" + 
                         String(current_temps[1], 1) + ";" + 
                         String(current_temps[2], 1);
    Serial.println("🌡️ 센서 전송 → " + msg);
    
    if (client.connected()) 
    {
        client.println(msg);
    }
}
