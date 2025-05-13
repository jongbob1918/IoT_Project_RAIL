#include <WiFi.h>

// ───── Wi-Fi 설정 ─────
const char* SSID = "addinedu_class_1(2.4G)";
const char* PASSWORD = "addinedu1";
const char* HOST = "192.168.2.6";
const uint16_t PORT = 9000;
WiFiClient client;

// ───── 핀 정의 ─────
const int A_BLUE_LED   = 2;
const int A_YELLOW_LED = 4;
const int A_SENSOR     = 36;
const int A_BUZZER     = 5;
const int A_MOTOR_IA   = 15;
const int A_MOTOR_IB   = 13;

const int B_BLUE_LED   = 16;
const int B_YELLOW_LED = 17;
const int B_SENSOR     = 34;
const int B_BUZZER     = 19;
const int B_MOTOR_IA   = 21;
const int B_MOTOR_IB   = 22;

const int C_RED_LED     = 25;
const int C_BLUE_LED    = 26;
const int C_YELLOW_LED  = 27;
const int C_SENSOR      = 35;
const int C_BUZZER      = 14;
const int C_MOTOR_IA    = 33;
const int C_MOTOR_IB    = 32;

// ───── 온도 제어 관련 상수 ─────
const float MIN_TEMPS[3] = { -25.0,  0.0, 15.0 }; // 경고 하한
const float MAX_TEMPS[3] = { -15.0, 10.0, 25.0 }; // 경고 상한
float base_temps[3] = { -20.0, 5.0, 20.0 };       // 서버 명령으로 조정됨
const float CALIBRATION[3] = { -30.0, -5.0, 10.0 }; // 센서 보정값

// ───── 상태 변수 ─────
bool warning_states[3] = { false, false, false }; // 경고 상태 유지
int last_speeds[3] = { -1, -1, -1 };              // 마지막 속도 상태
unsigned long last_sensor_time = 0;               // 센서 전송 타이머
unsigned long last_reconnect_time = 0;            // 서버 재연결 타이머


void setup()
{
    Serial.begin(115200);
    setup_pins();
    connect_wifi();
    connect_to_server();
}

void loop()
{
    // Wi-Fi 연결 확인
    if (WiFi.status() != WL_CONNECTED)
    {
        return;
    }

    // 클라이언트 명령 수신 처리
    if (client.connected() && client.available())
    {
        String cmd = client.readStringUntil('\n');
        Serial.println("\U0001F4BB [명령 수신] " + cmd);
        handle_command(cmd);
    }

    // 주기적으로 센서 데이터 전송
    if (millis() - last_sensor_time > 5000)
    {
        send_sensor_data();
        last_sensor_time = millis();
    }

    // 서버 재연결 시도
    if (!client.connected() && millis() - last_reconnect_time > 10000)
    {
        last_reconnect_time = millis();
        connect_to_server();
    }
}


// ───── 각 핀의 모드 설정 ─────
void setup_pins()
{
    pinMode(A_BLUE_LED, OUTPUT);
    pinMode(A_YELLOW_LED, OUTPUT);
    pinMode(A_BUZZER, OUTPUT);
    pinMode(A_MOTOR_IA, OUTPUT);
    pinMode(A_MOTOR_IB, OUTPUT);

    pinMode(B_BLUE_LED, OUTPUT);
    pinMode(B_YELLOW_LED, OUTPUT);
    pinMode(B_BUZZER, OUTPUT);
    pinMode(B_MOTOR_IA, OUTPUT);
    pinMode(B_MOTOR_IB, OUTPUT);

    pinMode(C_BLUE_LED, OUTPUT);
    pinMode(C_YELLOW_LED, OUTPUT);
    pinMode(C_RED_LED, OUTPUT);
    pinMode(C_BUZZER, OUTPUT);
    pinMode(C_MOTOR_IA, OUTPUT);
    pinMode(C_MOTOR_IB, OUTPUT);
}

// ───── Wi-Fi 연결 함수 ─────
void connect_wifi()
{
    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASSWORD);

    for (int i = 0; i < 10 && WiFi.status() != WL_CONNECTED; i++)
    {
        delay(1000);
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.print("✅ WiFi 연결됨: ");
        Serial.println(WiFi.localIP());
    }
    else
    {
        Serial.println("❌ WiFi 연결 실패");
    }
}

// ───── 서버 연결 함수 ─────
void connect_to_server()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        if (client.connect(HOST, PORT))
        {
            Serial.println("✅ 서버 연결 성공");
        }
        else
        {
            Serial.println("❌ 서버 연결 실패");
        }
    }
}

// ───── 기준 온도 변경 명령 처리 ─────
void handle_command(String cmd)
{
    cmd.trim();

    if (cmd.startsWith("HCp") && cmd.length() >= 5)
    {
        char zone_char = cmd.charAt(3);
        float new_base = cmd.substring(4).toFloat();
        int zone_index = zone_char - 'A';

        if (zone_index >= 0 && zone_index < 3)
        {
            base_temps[zone_index] = new_base;
            Serial.printf("⚙️ 기준치 변경: %c → %.1f\n", zone_char, new_base);
            if (client.connected())
            {
                client.println("HRok");
            }
        }
        else
        {
            Serial.println("❌ 기준치 변경 실패: 구역 오류");
            if (client.connected())
            {
                client.println("HXe1");
            }
        }
    }
}

// ───── 센서 측정 및 제어 판단 + 전송 ─────
void send_sensor_data()
{
    const int sensor_pins[3] = { A_SENSOR, B_SENSOR, C_SENSOR };
    const int motors_ia[3]   = { A_MOTOR_IA, B_MOTOR_IA, C_MOTOR_IA };
    const int motors_ib[3]   = { A_MOTOR_IB, B_MOTOR_IB, C_MOTOR_IB };
    const int blue_leds[3]   = { A_BLUE_LED, B_BLUE_LED, C_BLUE_LED };
    const int yellow_leds[3] = { A_YELLOW_LED, B_YELLOW_LED, C_YELLOW_LED };
    const int buzzers[3]     = { A_BUZZER, B_BUZZER, C_BUZZER };
    const int red_led_c      = C_RED_LED;

    float temps[3];

    for (int i = 0; i < 3; i++)
    {
        float voltage = analogRead(sensor_pins[i]) * (3.3 / 4095.0);
        float temp = voltage * 100.0 + CALIBRATION[i];
        temps[i] = temp;

        String zone = String(char('A' + i));
        float diff = temp - base_temps[i];
        int speed = 0;
        bool cooling = false, heating = false;

        // 경고 상태 판단 및 알림
        bool in_warning = (temp < MIN_TEMPS[i] || temp > MAX_TEMPS[i]);
        if (in_warning != warning_states[i])
        {
            String msg = "HEw" + zone + (in_warning ? "1" : "0");
            Serial.println((in_warning ? "\U0001F6A8 경고 발생 → " : "✅ 경고 해제 → ") + msg);
            if (client.connected())
            {
                client.println(msg);
            }
            digitalWrite(yellow_leds[i], in_warning);
            digitalWrite(buzzers[i], in_warning);
            warning_states[i] = in_warning;
        }

        // 냉난방 판단 로직
        if (i == 2 && diff < -2.0)
        {
            heating = true;
            speed = (diff >= -4.0) ? 1 : (diff >= -6.0) ? 2 : 3;
        }
        else if (diff > 2.0)
        {
            cooling = true;
            speed = (diff <= 4.0) ? 1 : (diff <= 6.0) ? 2 : 3;
        }

        // 출력 제어
        digitalWrite(blue_leds[i], cooling);
        if (i == 2)
        {
            digitalWrite(red_led_c, heating);
        }

        analogWrite(motors_ia[i], speed == 0 ? 0 : speed * 85);
        analogWrite(motors_ib[i], 0);

        // 속도 변경 이벤트 전송
        if (speed != last_speeds[i])
        {
            last_speeds[i] = speed;
            String msg = "HCf" + zone + String(speed);
            Serial.println("⚙️ 속도 변경 → " + msg);
            if (client.connected())
            {
                client.println(msg);
            }
        }
    }

    // 센서 값 전송 메시지
    String msg = "HEtp" + String(temps[0], 1) + ";" + String(temps[1], 1) + ";" + String(temps[2], 1);
    Serial.println("\U0001F321️ 센서 전송 → " + msg);
    if (client.connected())
    {
        client.println(msg);
    }
}
