#include <WiFi.h>
#include <ESP32Servo.h>
#include <queue>
#include <Arduino.h>

// ───────────── 상수 및 설정 ─────────────
// 디버깅 출력 간격
const unsigned long QUEUE_PRINT_INTERVAL = 3000;
const unsigned long STATUS_PRINT_INTERVAL = 5000;

// 핀 번호 정리
// 컨베이어 모터 핀 (L9110)
const int CONVEYOR_PIN_1A = 14;
const int CONVEYOR_PIN_1B = 13;

// 서보 모터 핀
const int SERVO_A_PIN = 21;
const int SERVO_B_PIN = 18;
const int SERVO_C_PIN = 19;

// 입구 IR 센서
const int IR_SENSOR_TRIGGER_PIN = 23;

// Zone 감지용 IR 센서
const int IR_SENSOR_ZONE_A = 17;
const int IR_SENSOR_ZONE_B = 16;
const int IR_SENSOR_ZONE_C = 4;
const int IR_SENSOR_PINS[] = { IR_SENSOR_ZONE_A, IR_SENSOR_ZONE_B, IR_SENSOR_ZONE_C };

// 도착 엣지 트리거 IR 센서 (정밀 감지)
const int ARRIVAL_IR_PIN_A = 34;
const int ARRIVAL_IR_PIN_B = 35;
const int ARRIVAL_IR_PIN_C = 32;
const int ARRIVAL_IR_PIN_E = 33;
const int ARRIVAL_IR[] = { ARRIVAL_IR_PIN_A, ARRIVAL_IR_PIN_B, ARRIVAL_IR_PIN_C, ARRIVAL_IR_PIN_E };
const int ARRIVAL_IR_NUM = 4;
const char zoneLabels[] = { 'A', 'B', 'C', 'E' };

// WiFi 설정
// const char* ssid = "Galaxy Z Fold42488";
// const char* password = "623623623";
const char* ssid = "jongmyung";
const char* password = "12345678";
const char* host = "192.168.2.198";
const uint16_t port = 9100;
const char* SORT_HOST = "192.168.2.2";
const uint16_t SORT_PORT = 9000;

// 네트워크 연결 설정
const unsigned long RECONNECT_INTERVAL_MS = 5000;
const unsigned long CONNECTION_TIMEOUT_MS = 10000;
const int MAX_CONNECTION_ATTEMPTS = 3;

// 컨베이어 설정
const int CONVEYOR_SPEED_FAST = 200;
const int CONVEYOR_SPEED_SLOW = 110;
const int CONVEYOR_SPEED_STOP = 0;
const unsigned long CONVEYOR_FAST_DURATION_MS = 4000;
const unsigned long CONVEYOR_SAFETY_TIMEOUT_MS = 300000; // 5분 안전 타임아웃

// 서보 설정
const int NUM_SERVOS = 3;
const int BASE_ANGLE = 90;
const int OPEN_ANGLE = 10;
const unsigned long SERVO_RETRY_INTERVAL_MS = 100;
const int MAX_SERVO_RETRIES = 3;

// ───────────── 전역 변수 ─────────────
WiFiClient client;
WiFiClient sortSocket;

// 네트워크 상태 변수
unsigned long lastReconnectAttempt = 0;
unsigned long lastSortReconnect = 0;
unsigned long lastStatusPrint = 0;
bool isWifiConnected = false;
int connectionAttempts = 0;

// 컨베이어 상태 변수
bool isConveyorRunning = false;
bool isFastMode = false;
unsigned long conveyorStartTime = 0;
unsigned long conveyorSafetyTimer = 0;

// 큐 상태 관련 변수
std::queue<int> targetServoQueue;
unsigned long lastQueuePrint = 0;

// IR 센서 상태 변수
bool prevArrivalIrState[ARRIVAL_IR_NUM] = {true, true, true, true};
bool trigger_ir = false;

// 서보 모터 구조체 및 관련 변수
struct ServoUnit {
    Servo motor;
    int pin;
    float distance_cm;
    unsigned long active_duration_ms;
    bool isOpen = false;
    bool isActivated = false;
    bool isHandled = false;
    unsigned long startTime = 0;
    int retryCount = 0;
};

ServoUnit servos[NUM_SERVOS] = {
    {Servo(), SERVO_A_PIN, 1.0, 2000},
    {Servo(), SERVO_B_PIN, 12.0, 2000},
    {Servo(), SERVO_C_PIN, 20.0, 2000}
};

bool isArrived[NUM_SERVOS] = {false};
bool isObjectDetected = false;
unsigned long objectDetectedTime = 0;
int servoReturnCount = 0;

// ───────────── 함수 선언 ─────────────
void setupWiFi();
void setupHardware();
bool reconnectIfNeeded(WiFiClient& sock, const char* host, uint16_t port, unsigned long& lastAttempt);
void controlConveyor(int speed);
void startConveyor();
void stopConveyor();
void initializeServos();
void receiveWiFiCommand();
void handleSortSocket();
void checkZoneTriggerAndPopQueue();
void handleServoControl();
unsigned long computeArrivalDelay(float distance_cm);
void checkArrivalStatus();
void checkCompletion();
void checkIrSensor();
void printQueueState();
void printSystemStatus();
void handleSafetyTimeout();

// ───────────── 함수 정의 ─────────────
void setupWiFi() {
    Serial.println("📡 WiFi 연결 시작...");
    
    IPAddress local_IP(192, 168, 2, 3);
    IPAddress gateway(192, 168, 2, 1);
    IPAddress subnet(255, 255, 255, 0);
    
    if (!WiFi.config(local_IP, gateway, subnet)) {
        Serial.println("❌ WiFi 고정 IP 설정 실패");
    }
    
    WiFi.begin(ssid, password);
    
    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && 
           millis() - startAttemptTime < CONNECTION_TIMEOUT_MS) {
        delay(500);
        Serial.print(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        isWifiConnected = true;
        Serial.printf("\n✅ WiFi 연결됨: %s\n", WiFi.localIP().toString().c_str());
        
        // 서버 연결 시도
        Serial.println("🔌 메인 서버 연결 시도...");
        if (client.connect(host, port)) {
            Serial.println("✅ 메인 서버 연결 성공");
        } else {
            Serial.println("❌ 메인 서버 연결 실패");
        }
        
        Serial.println("🔌 분류 서버 연결 시도...");
        if (sortSocket.connect(SORT_HOST, SORT_PORT)) {
            Serial.println("✅ 분류 서버 연결 성공");
        } else {
            Serial.println("❌ 분류 서버 연결 실패");
        }
    } else {
        Serial.println("\n❌ WiFi 연결 실패 - 재시도 예정");
        isWifiConnected = false;
    }
}

void setupHardware() {
    // 핀 모드 설정
    pinMode(CONVEYOR_PIN_1A, OUTPUT);
    pinMode(CONVEYOR_PIN_1B, OUTPUT);
    pinMode(IR_SENSOR_TRIGGER_PIN, INPUT);
    
    for (int i = 0; i < NUM_SERVOS; i++) {
        pinMode(IR_SENSOR_PINS[i], INPUT);
    }
    
    for (int i = 0; i < ARRIVAL_IR_NUM; i++) {
        pinMode(ARRIVAL_IR[i], INPUT);
    }
    
    // 서보 모터 초기화
    initializeServos();
    
    // 모터 초기 상태
    controlConveyor(CONVEYOR_SPEED_STOP);
}

bool reconnectIfNeeded(WiFiClient& sock, const char* host, uint16_t port, unsigned long& lastAttempt) {
    if (WiFi.status() != WL_CONNECTED) {
        unsigned long now = millis();
        if (now - lastAttempt >= RECONNECT_INTERVAL_MS) {
            Serial.println("📡 WiFi 재연결 시도 중...");
            WiFi.reconnect();
            lastAttempt = now;
            return false;
        }
        return false;
    }
    
    if (!sock.connected()) {
        unsigned long now = millis();
        if (now - lastAttempt >= RECONNECT_INTERVAL_MS) {
            Serial.printf("🔁 [%s:%d] 서버 재접속 시도\n", host, port);
            sock.stop();
            bool success = sock.connect(host, port);
            lastAttempt = now;
            
            if (success) {
                Serial.printf("✅ [%s:%d] 서버 재접속 성공\n", host, port);
                return true;
            } else {
                Serial.printf("❌ [%s:%d] 서버 재접속 실패\n", host, port);
                return false;
            }
        }
        return false;
    }
    return true;
}

void controlConveyor(int speed) {
    if (speed > 0) {
        analogWrite(CONVEYOR_PIN_1A, speed);
        analogWrite(CONVEYOR_PIN_1B, 0);
        
        if (!isConveyorRunning) {
            Serial.printf("▶️ 컨베이어 시작 (속도: %d)\n", speed);
            isConveyorRunning = true;
            conveyorSafetyTimer = millis();
        }
        
        isFastMode = (speed == CONVEYOR_SPEED_FAST);
    } else {
        analogWrite(CONVEYOR_PIN_1A, 0);
        analogWrite(CONVEYOR_PIN_1B, 0);
        
        if (isConveyorRunning) {
            Serial.println("⏹️ 컨베이어 정지");
            isConveyorRunning = false;
        }
    }
}

void startConveyor() {
    // 빠른 속도로 시작
    controlConveyor(CONVEYOR_SPEED_FAST);
    conveyorStartTime = millis();
    
    // 타이머 이벤트로 속도 전환을 처리
    static bool speedChangeScheduled = false;
    if (!speedChangeScheduled) {
        speedChangeScheduled = true;
        
        // 정해진 시간 후 속도 변경 확인 태스크
        static TaskHandle_t speedChangeTask = NULL;
        if (speedChangeTask == NULL) {
            xTaskCreate(
                [](void* parameter) {
                    unsigned long fastModeEndTime = conveyorStartTime + CONVEYOR_FAST_DURATION_MS;
                    
                    // 빠른 모드 지속 시간 동안 대기
                    while (millis() < fastModeEndTime) {
                        vTaskDelay(100 / portTICK_PERIOD_MS);
                    }
                    
                    // 느린 속도로 변경
                    controlConveyor(CONVEYOR_SPEED_SLOW);
                    Serial.println("🔄 컨베이어 속도 전환: 빠름 → 느림");
                    
                    speedChangeScheduled = false;
                    vTaskDelete(NULL);
                },
                "SpeedChange",
                2048,
                NULL,
                1,
                &speedChangeTask
            );
        }
    }
}

void stopConveyor() {
    controlConveyor(CONVEYOR_SPEED_STOP);
}

void initializeServos() {
    for (int i = 0; i < NUM_SERVOS; i++) {
        servos[i].motor.setPeriodHertz(50); // 50Hz 표준 서보 주파수
        
        // 여러 번 시도하여 서보 부착 확인
        bool attached = false;
        for (int attempt = 0; attempt < MAX_SERVO_RETRIES && !attached; attempt++) {
            attached = servos[i].motor.attach(servos[i].pin, 500, 2400); // 0~180도 맵핑 범위
            
            if (!attached) {
                Serial.printf("⚠️ 서보 %c 핀 %d attach 시도 %d 실패\n", 
                              'A'+i, servos[i].pin, attempt+1);
                delay(SERVO_RETRY_INTERVAL_MS);
            }
        }
        
        Serial.printf("🧩 서보 %c 핀 %d attach %s\n", 
                     'A'+i, servos[i].pin, attached ? "성공" : "실패");
                     
        if (attached) {
            servos[i].motor.write(BASE_ANGLE);
        }
    }
}

void receiveWiFiCommand() {
    static String cmdBuffer = "";
    
    while (client.available()) {
        char c = client.read();
        
        // 명령 종료 처리
        if (c == '\n') {
            cmdBuffer.trim();
            
            if (cmdBuffer.length() > 0) {
                Serial.printf("📥 QR 수신: %s\n", cmdBuffer.c_str());
                
                // 명령 처리
                if (cmdBuffer.length() >= 1) {
                    char zone = cmdBuffer.charAt(0);
                    int idx = zone - 'A';
                    
                    if (idx >= 0 && idx < NUM_SERVOS) {
                        targetServoQueue.push(idx);
                        Serial.printf("✅ 큐 추가: %c (%d번)\n", zone, idx);
                        
                        // 큐 상태 즉시 출력
                        printQueueState();
                    } else {
                        Serial.printf("⚠️ 잘못된 구역 지정: %c\n", zone);
                    }
                }
                
                // 분류기 서버에 전달
                if (sortSocket.connected()) {
                    sortSocket.printf("SEbc%s\n", cmdBuffer.c_str());
                } else {
                    Serial.println("⚠️ 분류기 서버 연결 안됨 - 명령 전달 실패");
                }
            }
            
            // 버퍼 초기화
            cmdBuffer.clear();
        } else if (cmdBuffer.length() < 32) { // 버퍼 오버플로우 방지
            cmdBuffer += c;
        }
    }
}

void handleSortSocket() {
    static String buffer = "";
    
    while (sortSocket.available()) {
        char c = sortSocket.read();
        
        if (c == '\n') {
            buffer.trim();
            Serial.printf("📦 분류기 수신: %s\n", buffer.c_str());
            
            // 명령 처리
            if (buffer == "SCst") {
                startConveyor();
                sortSocket.print("SRok\n");
            } else if (buffer == "SCsp") {
                stopConveyor();
                sortSocket.print("SRok\n");
            } else if (buffer.startsWith("SCo") && buffer.length() == 4) {
                char zone = buffer.charAt(3);
                int idx = zone - 'A';
                
                if (idx >= 0 && idx < NUM_SERVOS) {
                    targetServoQueue.push(idx);
                    sortSocket.print("SRok\n");
                    Serial.printf("✅ 큐 추가: %c (%d번) [분류기 요청]\n", zone, idx);
                    
                    // 큐 상태 즉시 출력
                    printQueueState();
                } else {
                    sortSocket.print("SXe2\n");
                    Serial.printf("⚠️ 잘못된 구역 지정: %c [분류기 요청]\n", zone);
                }
            } else {
                sortSocket.print("SXe1\n");
                Serial.printf("⚠️ 알 수 없는 명령: %s\n", buffer.c_str());
            }
            
            // 버퍼 초기화
            buffer.clear();
        } else if (buffer.length() < 32) { // 버퍼 오버플로우 방지
            buffer += c;
        }
    }
}

void checkZoneTriggerAndPopQueue() {
    if (targetServoQueue.empty()) return;
    
    int target = targetServoQueue.front();
    
    // IR 센서에 의한 감지
    if (digitalRead(IR_SENSOR_PINS[target]) == LOW) {
        targetServoQueue.pop();
        objectDetectedTime = millis();
        
        // 서보 활성화
        servos[target].isActivated = true;
        servos[target].isOpen = false;
        servos[target].isHandled = false;
        isObjectDetected = true;
        
        Serial.printf("🟢 %c 구역 감지 → 서보 활성화\n", 'A' + target);
        
        // 큐 상태 즉시 출력
        printQueueState();
    }
}

void handleServoControl() {
    unsigned long now = millis();
    
    for (int i = 0; i < NUM_SERVOS; i++) {
        ServoUnit& s = servos[i];
        
        // 서보 열기
        if (s.isActivated && !s.isOpen && !s.isHandled) {
            // 서보 상태 확인
            if (!s.motor.attached()) {
                s.retryCount++;
                
                if (s.retryCount <= MAX_SERVO_RETRIES) {
                    Serial.printf("⚠️ 서보 %c 재연결 시도 %d/%d\n", 
                                 'A' + i, s.retryCount, MAX_SERVO_RETRIES);
                    s.motor.attach(s.pin, 500, 2400);
                } else {
                    Serial.printf("❌ 서보 %c 연결 실패, 작동 취소\n", 'A' + i);
                    s.isActivated = false;
                    continue;
                }
            }
            
            s.motor.write(OPEN_ANGLE);
            s.startTime = now;
            s.isOpen = true;
            s.isHandled = true;
            Serial.printf("🔧 서보 %c 작동 (각도: %d)\n", 'A' + i, OPEN_ANGLE);
        }
        
        // 서보 닫기
        if (s.isOpen && now - s.startTime >= s.active_duration_ms) {
            s.motor.write(BASE_ANGLE);
            s.isOpen = false;
            servoReturnCount++;
            Serial.printf("↩️ 서보 %c 복귀 (각도: %d)\n", 'A' + i, BASE_ANGLE);
        }
    }
}

unsigned long computeArrivalDelay(float distance_cm) {
    // 거리에 따른 도착 시간 계산
    float fast_s = CONVEYOR_FAST_DURATION_MS / 1000.0;
    float fast_d = fast_s * 25.0;  // 빠른 속도에서의 이동 거리
    
    if (distance_cm <= fast_d) {
        // 빠른 속도 구간 내에서의 시간
        return distance_cm / 25.0 * 1000;
    } else {
        // 빠른 속도 구간 + 느린 속도 구간
        float rem = distance_cm - fast_d;
        return (fast_s + rem / 15.0) * 1000;
    }
}

void checkArrivalStatus() {
    unsigned long now = millis();
    
    for (int i = 0; i < NUM_SERVOS; i++) {
        ServoUnit& s = servos[i];
        
        if (s.isHandled && !isArrived[i]) {
            // IR 센서로 도착 감지
            if (digitalRead(IR_SENSOR_PINS[i]) == LOW) {
                isArrived[i] = true;
                Serial.printf("✅ %c 구역 물체 도착 감지\n", 'A' + i);
            } else {
                // 시간 초과 기반 도착 판정
                unsigned long deadline = objectDetectedTime + computeArrivalDelay(s.distance_cm) + 1500;
                
                if (now > deadline) {
                    isArrived[i] = true;
                    Serial.printf("⏱️ %c 구역 물체 도착 시간 초과 처리\n", 'A' + i);
                }
            }
        }
    }
}

void checkCompletion() {
    if (!isObjectDetected) return;
    
    int active = 0;
    bool allArrived = true;
    
    // 모든 서보의 상태 확인
    for (int i = 0; i < NUM_SERVOS; i++) {
        if (servos[i].isHandled) {
            active++;
            if (!isArrived[i]) allArrived = false;
        }
    }
    
    // 모든 작업 완료 확인
    if (servoReturnCount >= active && active > 0 && allArrived) {
        isObjectDetected = false;
        servoReturnCount = 0;
        
        // 서보 상태 초기화
        for (int i = 0; i < NUM_SERVOS; i++) {
            servos[i].isActivated = false;
            servos[i].retryCount = 0;
            isArrived[i] = false;
        }
        
        Serial.println("✅ 모든 서보 동작 완료");
    }
}

void checkIrSensor() {
    // 입구 IR 센서 확인
    bool currentTriggerState = digitalRead(IR_SENSOR_TRIGGER_PIN) == LOW;
    
    if (currentTriggerState && !trigger_ir) {
        trigger_ir = true;
        
        // 메시지 전송
        if (sortSocket.connected()) {
            sortSocket.print("SEir1\n");
            Serial.println("📨 입구 IR 센서 감지 전송: SEir1");
        } else {
            Serial.println("⚠️ 분류기 서버 연결 안됨 - 입구 IR 감지 전송 실패");
        }
    } else if (!currentTriggerState) {
        trigger_ir = false;
    }
    
    // 도착 IR 센서 확인
    for (int i = 0; i < ARRIVAL_IR_NUM; i++) {
        bool currentState = digitalRead(ARRIVAL_IR[i]);
        
        // 하강 엣지 감지 (HIGH -> LOW)
        if (prevArrivalIrState[i] == HIGH && currentState == LOW) {
            // 메시지 전송
            if (sortSocket.connected()) {
                char msg[10];
                sprintf(msg, "SEss%c\n", zoneLabels[i]);
                sortSocket.print(msg);
                Serial.printf("%c 구역 📨 도착 IR 센서 감지 전송\n", zoneLabels[i]);
            } else {
                Serial.printf("⚠️ 분류기 서버 연결 안됨 - %c 구역 도착 감지 전송 실패\n", zoneLabels[i]);
            }
        }
        
        prevArrivalIrState[i] = currentState;
    }
}

void printQueueState() {
    Serial.print("📦 큐 상태: ");
    
    std::queue<int> temp = targetServoQueue;
    if (temp.empty()) {
        Serial.println("(비어 있음)");
        return;
    }
    
    while (!temp.empty()) {
        int val = temp.front();
        temp.pop();
        Serial.printf("%c ", 'A' + val);
    }
    Serial.println();
}

void printSystemStatus() {
    Serial.println("\n──────── 시스템 상태 ────────");
    Serial.printf("📡 WiFi: %s\n", WiFi.status() == WL_CONNECTED ? "연결됨" : "끊김");
    Serial.printf("🔌 메인 서버: %s\n", client.connected() ? "연결됨" : "끊김");
    Serial.printf("🔌 분류기 서버: %s\n", sortSocket.connected() ? "연결됨" : "끊김");
    Serial.printf("🛞 컨베이어: %s (%s)\n", 
                 isConveyorRunning ? "작동 중" : "정지", 
                 isFastMode ? "빠름" : "느림");
    
    Serial.println("🧩 서보 상태:");
    for (int i = 0; i < NUM_SERVOS; i++) {
        Serial.printf("  - %c: %s %s\n", 
                     'A' + i, 
                     servos[i].isActivated ? "활성화" : "비활성화",
                     servos[i].isOpen ? "(열림)" : "(닫힘)");
    }
    
    printQueueState();
    Serial.println("─────────────────────────");
}

void handleSafetyTimeout() {
    // 안전 타임아웃 처리
    if (isConveyorRunning && millis() - conveyorSafetyTimer > CONVEYOR_SAFETY_TIMEOUT_MS) {
        Serial.println("⚠️ 안전 타임아웃: 컨베이어 자동 정지");
        stopConveyor();
        
        // 분류기 서버에 알림
        if (sortSocket.connected()) {
            sortSocket.print("SEto1\n");
        }
    }
}

// ───────────── 메인 setup / loop ─────────────
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n\n──────── ESP32 컨베이어 시스템 초기화 ────────");
    
    setupHardware();
    setupWiFi();
    
    Serial.println("✅ 시스템 초기화 완료");
    startConveyor();
}

void loop() {
    // 네트워크 연결 관리
    if (WiFi.status() != WL_CONNECTED) {
        if (isWifiConnected) {
            Serial.println("❌ WiFi 연결 끊김");
            isWifiConnected = false;
        }
        
        // WiFi 재연결 시도
        unsigned long now = millis();
        if (now - lastReconnectAttempt >= RECONNECT_INTERVAL_MS) {
            Serial.println("📡 WiFi 재연결 시도...");
            WiFi.reconnect();
            lastReconnectAttempt = now;
        }
    } else {
        if (!isWifiConnected) {
            Serial.println("✅ WiFi 재연결 성공");
            isWifiConnected = true;
        }
        
        // 서버 연결 상태 확인 및 관리
        reconnectIfNeeded(client, host, port, lastReconnectAttempt);
        reconnectIfNeeded(sortSocket, SORT_HOST, SORT_PORT, lastSortReconnect);
        
        // 네트워크 통신 처리
        receiveWiFiCommand();
        handleSortSocket();
    }
    
    // 센서 및 액추에이터 처리
    checkZoneTriggerAndPopQueue();
    handleServoControl();
    checkArrivalStatus();
    checkCompletion();
    checkIrSensor();
    handleSafetyTimeout();
    
    // 주기적인 상태 출력
    unsigned long now = millis();
    if (now - lastQueuePrint >= QUEUE_PRINT_INTERVAL) {
        printQueueState();
        lastQueuePrint = now;
    }
    
    if (now - lastStatusPrint >= STATUS_PRINT_INTERVAL) {
        printSystemStatus();
        lastStatusPrint = now;
    }
    
    // 시스템 안정성을 위한 짧은 지연
    // 타이트 루프 방지 및 안정성 향상
    delay(10);
}
