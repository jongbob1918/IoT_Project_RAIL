#include <WiFi.h>
#include <ESP32Servo.h>
#include <queue>

// ─────────────────────────────
// 📡 WiFi 설정
// ─────────────────────────────
const char* ssid = "addinedu_class_1(2.4G)";
const char* password = "addinedu1";
const char* host = "192.168.2.198";
const uint16_t port = 9100; // 서버 포트

// ─────────────────────────────
// 🔄 컨베이어 설정 (PWM 제어)
// ─────────────────────────────
const int CONVEYOR_PWM_PIN = 23;
const int PWM_CHANNEL = 0;
const int PWM_FREQ = 5000;
const int PWM_RESOLUTION = 8;

const int CONVEYOR_SPEED_FAST = 200;
const int CONVEYOR_SPEED_SLOW = 120;
const unsigned long CONVEYOR_FAST_DURATION_MS = 2000;     // 빠른 속도 유지 시간
const unsigned long CONVEYOR_IDLE_TIMEOUT_MS = 10000;     // 감지 없을 때 자동 정지 대기 시간

bool isConveyorRunning = false;
unsigned long conveyorStartTime = 0;
unsigned long lastDetectionTime = 0;

// ─────────────────────────────
// ⚙️ 서보 관련 설정
// ─────────────────────────────
struct ServoUnit {
    Servo motor;
    int pin;
    float distance_cm;                  // 감지 지점까지 거리
    unsigned long active_duration_ms;   // 서보 열린 상태 유지 시간
    bool isOpen = false;
    bool isActivated = false;
    bool isHandled = false;
    unsigned long startTime = 0;        // 열린 시간 기록
};

const int BASE_ANGLE = 90;
const int OPEN_ANGLE = 40;
const int NUM_SERVOS = 4;

ServoUnit servos[NUM_SERVOS] = {
    {Servo(), 18, 1.0, 500},
    {Servo(), 19, 12.0, 500},
    {Servo(), 21, 20.0, 500},
    {Servo(), 22, 28.0, 500}
};

// ─────────────────────────────
// 📍 IR 센서 설정
// ─────────────────────────────
const int IR_SENSOR_TRIGGER_PIN = 26;          // 입구 감지 센서
const int IR_SENSOR_PINS[] = {32, 33, 25, 27}; // 각 서보 위치 감지 센서

// ─────────────────────────────
// 📬 통신 및 큐 상태 변수
// ─────────────────────────────
WiFiClient client;
std::queue<int> targetServoQueue;

bool isObjectDetected = false;
bool wasSensorLowLast = true;
unsigned long objectDetectedTime = 0;
int servoReturnCount = 0;
bool isArrived[NUM_SERVOS] = {false};

// ─────────────────────────────
// 🟢 컨베이어 제어 함수
// ─────────────────────────────
void startConveyor() {
    if (!isConveyorRunning) {
        isConveyorRunning = true;
        conveyorStartTime = millis();
        ledcWrite(PWM_CHANNEL, CONVEYOR_SPEED_FAST);
        Serial.println("▶️ 컨베이어 시작 (PWM 200)");
    }
}

void stopConveyor() {
    if (isConveyorRunning) {
        isConveyorRunning = false;
        ledcWrite(PWM_CHANNEL, 0);
        Serial.println("⏹️ 컨베이어 정지");
    }
}

void updateConveyorSpeed() {
    // 일정 시간 후 속도 낮추기
    if (isConveyorRunning && millis() - conveyorStartTime > CONVEYOR_FAST_DURATION_MS) {
        ledcWrite(PWM_CHANNEL, CONVEYOR_SPEED_SLOW);
    }
}

// ─────────────────────────────
// 🛠️ 서보 초기화 함수
// ─────────────────────────────
void initializeServos() {
    for (int i = 0; i < NUM_SERVOS; i++) {
        servos[i].motor.attach(servos[i].pin);
        servos[i].motor.write(BASE_ANGLE);
    }
}

// 서버에 도착 메시지 전송
void sendArrivalMessage(int index) {
    if (client.connected()) {
        char msg[10];
        sprintf(msg, "IR/0%d\n", index);
        client.print(msg);
        Serial.printf("📨 서버로 전송: %s", msg);
    }
}

// 서버로부터 명령 수신
void receiveWiFiCommand() {
    if (!client.connected()) {
        client.stop();
        client.connect(host, port);
    }

    if (client.connected() && client.available()) {
        String cmd = client.readStringUntil('\n');
        cmd.trim();
        Serial.println(cmd);
        if (cmd.startsWith("MV")) {
            int index = cmd.substring(2).toInt();
            if (index >= 0 && index < NUM_SERVOS) {
                targetServoQueue.push(index);
                Serial.printf("🟢 큐에 명령 추가: %s (서보 %c)\n", cmd.c_str(), 'A' + index);
            }
        }
    }
}

// 도착 지점 거리 기반 예상 시간 계산
unsigned long computeArrivalDelay(float distance_cm) {
    float fast_duration_s = CONVEYOR_FAST_DURATION_MS / 1000.0;
    float fast_distance = fast_duration_s * 25.0;
    if (distance_cm <= fast_distance) {
        return distance_cm / 25.0 * 1000;
    } else {
        float remaining = distance_cm - fast_distance;
        return (fast_duration_s + (remaining / 15.0)) * 1000;
    }
}

// ─────────────────────────────
// 👀 입구 센서 감지 및 서보 명령 처리
// ─────────────────────────────
void checkObjectDetection() {
    int sensorState = digitalRead(IR_SENSOR_TRIGGER_PIN);

    if (sensorState == LOW) {
        lastDetectionTime = millis();
        startConveyor(); // 감지 시 컨베이어 작동
    } else if (isConveyorRunning && millis() - lastDetectionTime > CONVEYOR_IDLE_TIMEOUT_MS) {
        stopConveyor(); // 오래 감지 안되면 정지
    }

    updateConveyorSpeed();

    // 새로운 물체가 감지되었고 명령 큐에 있을 경우
    if (!isObjectDetected && sensorState == LOW && !wasSensorLowLast && !targetServoQueue.empty()) {
        isObjectDetected = true;
        objectDetectedTime = millis();
        servoReturnCount = 0;

        for (int i = 0; i < NUM_SERVOS; i++) {
            servos[i].isActivated = false;
            servos[i].isOpen = false;
            servos[i].isHandled = false;
            isArrived[i] = false;
        }

        int idx = targetServoQueue.front();
        targetServoQueue.pop();
        if (idx >= 0 && idx < NUM_SERVOS) {
            servos[idx].isActivated = true;
            Serial.printf("💡 명령 %c 서보 활성화 대기\n", 'A' + idx);
        }
    }

    wasSensorLowLast = (sensorState == LOW);
}

// 서보 개별 제어
void handleServoControl() {
    unsigned long now = millis();
    for (int i = 0; i < NUM_SERVOS; i++) {
        ServoUnit& s = servos[i];
        unsigned long delayToActivate = computeArrivalDelay(s.distance_cm);

        // 도달 예상 시간이 지났고 아직 작동 안한 경우
        if (isObjectDetected && s.isActivated && !s.isOpen && !s.isHandled && now - objectDetectedTime >= delayToActivate) {
            s.motor.write(OPEN_ANGLE);
            s.startTime = now;
            s.isOpen = true;
            s.isHandled = true;
            Serial.printf("→ 서보 %c 작동\n", 'A' + i);
        }

        // 작동 후 지정 시간 경과하면 서보 복귀
        if (s.isOpen && now - s.startTime >= s.active_duration_ms) {
            s.motor.write(BASE_ANGLE);
            s.isOpen = false;
            servoReturnCount++;
            Serial.printf("← 서보 %c 복귀\n", 'A' + i);
        }
    }
}

// IR 센서로 도착 감지
void checkArrivalStatus() {
    unsigned long now = millis();
    for (int i = 0; i < NUM_SERVOS; i++) {
        ServoUnit& s = servos[i];
        if (s.isHandled && !isArrived[i]) {
            int sensorState = digitalRead(IR_SENSOR_PINS[i]);
            if (sensorState == LOW) {
                isArrived[i] = true;
                Serial.printf("🟡 서보 %c 위치에서 물체 도착 확인\n", 'A' + i);
                sendArrivalMessage(i);
            } else {
                unsigned long delayToActivate = computeArrivalDelay(s.distance_cm);
                unsigned long deadline = objectDetectedTime + delayToActivate + 1500;
                if (now > deadline) {
                    isArrived[i] = true;
                    Serial.printf("⚠️ 서보 %c 위치 도착 타임아웃, 강제 도착 처리\n", 'A' + i);
                    sendArrivalMessage(i);
                }
            }
        }
    }
}

// 모든 도착 확인 및 서보 복귀 확인
void checkCompletion() {
    if (!isObjectDetected) return;

    int activeCount = 0;
    bool allArrived = true;
    for (int i = 0; i < NUM_SERVOS; i++) {
        if (servos[i].isHandled) {
            activeCount++;
            if (!isArrived[i]) allArrived = false;
        }
    }

    if (servoReturnCount >= activeCount && activeCount > 0 && allArrived) {
        isObjectDetected = false;
        servoReturnCount = 0;
        for (int i = 0; i < NUM_SERVOS; i++) {
            servos[i].isActivated = false;
            isArrived[i] = false;
        }
        Serial.println("✅ 동작 및 도착 확인 완료, 대기 상태");
    }
}

// ─────────────────────────────
// 🔁 메인 루프
// ─────────────────────────────
void setup() {
    Serial.begin(115200);
    pinMode(IR_SENSOR_TRIGGER_PIN, INPUT);
    for (int i = 0; i < NUM_SERVOS; i++) {
        pinMode(IR_SENSOR_PINS[i], INPUT);
    }

    initializeServos();

    // PWM 설정
    ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
    ledcAttachPin(CONVEYOR_PWM_PIN, PWM_CHANNEL);

    // WiFi 연결
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n📡 WiFi 연결 완료");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());

    client.connect(host, port);
}

void loop() {
    receiveWiFiCommand();     // 서버 명령 수신
    checkObjectDetection();   // 입구 IR 센서 확인
    handleServoControl();     // 서보 동작 처리
    checkArrivalStatus();     // IR로 도착 확인
    checkCompletion();        // 서보 복귀 및 완료 판단
}

