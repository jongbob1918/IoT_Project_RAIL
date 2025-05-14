#include <WiFi.h>
#include <ESP32Servo.h>
#include <queue>
#include <Arduino.h>

//----------큐 체크용
unsigned long lastQueuePrint = 0;
const unsigned long QUEUE_PRINT_INTERVAL = 2000;
// ───────────── WiFi 설정 ─────────────
const char* ssid = "Galaxy Z Fold42488";
const char* password = "623623623";
const char* host = "192.168.2.198";   // QR 서버 IP
const uint16_t port = 9100;

const char* SORT_HOST = "192.168.2.2"; // 분류기 서버 IP
const uint16_t SORT_PORT = 9000;

WiFiClient client;         // QR 서버
WiFiClient sortSocket;     // 분류기 서버
unsigned long lastReconnectAttempt = 0;
unsigned long lastSortReconnect = 0;
const unsigned long RECONNECT_INTERVAL_MS = 5000;

// ───────────── 컨베이어 설정 ─────────────
const int CONVEYOR_PWM_PIN = 23;
const int A_1A = 14;
const int A_1B = 13;
const int CONVEYOR_SPEED_FAST = 200;
const int CONVEYOR_SPEED_SLOW = 120;
const unsigned long CONVEYOR_FAST_DURATION_MS = 4000;
bool isConveyorRunning = false;
static bool isFastMode = true;
static unsigned long conveyorStartTime = 0;


// ───────────── 서보 설정 ─────────────
const int BASE_ANGLE = 90;
const int OPEN_ANGLE = 130;
const int NUM_SERVOS = 3;

struct ServoUnit {
    Servo motor;
    int pin;
    float distance_cm;
    unsigned long active_duration_ms;
    bool isOpen = false;
    bool isActivated = false;
    bool isHandled = false;
    unsigned long startTime = 0;
};

ServoUnit servos[NUM_SERVOS] = {
    {Servo(), 18, 1.0, 1000},
    {Servo(), 19, 12.0, 1000},
    {Servo(), 17, 20.0, 1000}
};

// ───────────── 센서 설정 ─────────────
const int IR_SENSOR_TRIGGER_PIN = 26;
const int IR_SENSOR_PINS[] = {32, 33, 25};
bool isArrived[NUM_SERVOS] = {false};

// ───────────── 상태 변수 ─────────────
std::queue<int> targetServoQueue;
bool isObjectDetected = false;
unsigned long objectDetectedTime = 0;
int servoReturnCount = 0;

// ───────────── 함수 정의 ─────────────
void reconnectIfNeeded(WiFiClient& sock, const char* host, uint16_t port, unsigned long& lastAttempt) 
{
    unsigned long now = millis();
    if (!sock.connected() && now - lastAttempt >= RECONNECT_INTERVAL_MS) 
    {
        Serial.printf("🔁 [%s:%d] 재접속 시도\n", host, port);
        sock.stop();
        sock.connect(host, port);
        lastAttempt = now;
    }
}

void startConveyor() 
{
    analogWrite(A_1A, CONVEYOR_SPEED_FAST);
    analogWrite(A_1B, 0);
    delay(CONVEYOR_FAST_DURATION_MS);
    analogWrite(A_1A, CONVEYOR_SPEED_SLOW);
    analogWrite(A_1B, 0);
    Serial.println("▶️ 컨베이어 시작");
}

void stopConveyor() 
{
    analogWrite(A_1A, 0);
    analogWrite(A_1B, 0);
    Serial.println("⏹️ 컨베이어 정지");
}

void initializeServos() 
{
    for (int i = 0; i < NUM_SERVOS; i++) 
    {
        servos[i].motor.attach(servos[i].pin);
        servos[i].motor.write(BASE_ANGLE);
    }
}

void sendArrivalMessage(int index) 
{
    if (sortSocket.connected()) 
    {
        char msg[10];
        sprintf(msg, "IR/0%d\n", index);
        sortSocket.print(msg);
        Serial.printf("📨 도착 메시지 전송: %s", msg);
    }
}

void receiveWiFiCommand() 
{
    static String cmdBuffer = "";
    while (client.available()) 
    {
        char c = client.read();
        if (c == '\n') {
            cmdBuffer.trim();
            Serial.printf("📥 QR 수신: %s\n", cmdBuffer.c_str());

            if (cmdBuffer.length() >= 1) 
            {
                char zone = cmdBuffer.charAt(0);
                int idx = zone - 'A';
                if (idx >= 0 && idx < NUM_SERVOS) 
                {
                    targetServoQueue.push(idx);
                    Serial.printf("✅ 큐 추가: %c (%d번)\n", zone, idx);
                }
            }

            sortSocket.printf("SEbc%s\n", cmdBuffer.c_str());
            cmdBuffer = "";
        } 
        else 
        {
            cmdBuffer += c;
        }
    }
}

void handleSortSocket() 
{
    static String buffer = "";
    while (sortSocket.available()) 
    {
        char c = sortSocket.read();
        if (c == '\n') 
        {
            buffer.trim();
            Serial.printf("📦 분류기 수신: %s\n", buffer.c_str());

            if (buffer == "SCst") 
            {
                startConveyor();
                sortSocket.print("SRok\n");
            }
            else if (buffer == "SCsp") 
            {
                stopConveyor();
                sortSocket.print("SRok\n");
            }
            else if (buffer.startsWith("SCo") && buffer.length() == 4) 
            {
                char zone = buffer.charAt(3);
                int idx = zone - 'A';
                if (idx >= 0 && idx < NUM_SERVOS) 
                {
                    targetServoQueue.push(idx);
                    sortSocket.print("SRok\n");
                } 
                else 
                {
                    sortSocket.print("SXe2\n");
                }
            } 
            else 
            {
                sortSocket.print("SXe1\n");
            }
            buffer = "";
        } 
        else 
        {
            buffer += c;
        }
    }
}

void checkZoneTriggerAndPopQueue() 
{
    if (targetServoQueue.empty()) return;
    int target = targetServoQueue.front();
    // Serial.printf("[DEBUG] 큐 대상: %d, IR 상태: %d, isHandled: %d\n", 
    //               target, digitalRead(IR_SENSOR_PINS[target]), servos[target].isHandled);

    if (digitalRead(IR_SENSOR_PINS[target]) == LOW) // <-- 여기 수정
    {
        targetServoQueue.pop();
        objectDetectedTime = millis();
        servos[target].isActivated = true;
        servos[target].isOpen = false;
        servos[target].isHandled = false; // 재설정
        isObjectDetected = true;
        Serial.printf("🟢 %c 구역 감지 → 서보 활성화\n", 'A' + target);
    }
}



void handleServoControl() 
{
    unsigned long now = millis();
    for (int i = 0; i < NUM_SERVOS; i++) 
    {
        ServoUnit& s = servos[i];
        if (s.isActivated && !s.isOpen && !s.isHandled) 
        {
            s.motor.write(OPEN_ANGLE);
            s.startTime = now;
            s.isOpen = true;
            s.isHandled = true;
            Serial.printf("🔧 서보 %c 작동\n", 'A' + i);
        }
        if (s.isOpen && now - s.startTime >= s.active_duration_ms) 
        {
            s.motor.write(BASE_ANGLE);
            s.isOpen = false;
            servoReturnCount++;
            Serial.printf("↩️ 서보 %c 복귀\n", 'A' + i);
        }
    }
}

unsigned long computeArrivalDelay(float distance_cm) 
{
    float fast_s = CONVEYOR_FAST_DURATION_MS / 1000.0;
    float fast_d = fast_s * 25.0;
    if (distance_cm <= fast_d) return distance_cm / 25.0 * 1000;
    float rem = distance_cm - fast_d;
    return (fast_s + rem / 15.0) * 1000;
}

void checkArrivalStatus() 
{
    unsigned long now = millis();
    for (int i = 0; i < NUM_SERVOS; i++) 
    {
        ServoUnit& s = servos[i];
        if (s.isHandled && !isArrived[i]) 
        {
            if (digitalRead(IR_SENSOR_PINS[i]) == LOW) 
            {
                isArrived[i] = true;
                sendArrivalMessage(i);
            } 
            else 
            {
                unsigned long deadline = objectDetectedTime + computeArrivalDelay(s.distance_cm) + 1500;
                if (now > deadline) 
                {
                    isArrived[i] = true;
                    sendArrivalMessage(i);
                }
            }
        }
    }
}

void checkCompletion() 
{
    if (!isObjectDetected) return;
    int active = 0;
    bool allArrived = true;
    for (int i = 0; i < NUM_SERVOS; i++) 
    {
        if (servos[i].isHandled) 
        {
            active++;
            if (!isArrived[i]) allArrived = false;
        }
    }
    if (servoReturnCount >= active && active > 0 && allArrived) 
    {
        isObjectDetected = false;
        servoReturnCount = 0;
        for (int i = 0; i < NUM_SERVOS; i++) 
        {
            servos[i].isActivated = false;
            isArrived[i] = false;
        }
        Serial.println("✅ 모든 서보 동작 완료");
    }
}


void printQueueStatus() 
{
    Serial.print("📦 현재 큐 상태: ");
    if (targetServoQueue.empty()) 
    {
        Serial.println("[비어 있음]");
        return;
    }

    // 큐는 순회가 어렵기 때문에 복사해서 출력
    std::queue<int> tempQueue = targetServoQueue;
    while (!tempQueue.empty()) {
        int index = tempQueue.front();
        tempQueue.pop();
        Serial.printf("%c ", 'A' + index); // 예: A, B, C
    }
    Serial.println();
}



// ───────────── 메인 setup / loop ─────────────
void setup() 
{
    Serial.begin(115200);
    pinMode(A_1A, OUTPUT);
    pinMode(A_1B, OUTPUT);
    pinMode(IR_SENSOR_TRIGGER_PIN, INPUT);
    for (int i = 0; i < NUM_SERVOS; i++) pinMode(IR_SENSOR_PINS[i], INPUT);

    initializeServos();

    IPAddress local_IP(192, 168, 2, 3);
    IPAddress gateway(192, 168, 2, 1);
    WiFi.config(local_IP, gateway, IPAddress(255, 255, 255, 0));
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) 
    {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n📡 WiFi 연결됨: %s\n", WiFi.localIP().toString().c_str());

    client.connect(host, port);
    sortSocket.connect(SORT_HOST, SORT_PORT);
}

void loop() 
{
    reconnectIfNeeded(client, host, port, lastReconnectAttempt);
    reconnectIfNeeded(sortSocket, SORT_HOST, SORT_PORT, lastSortReconnect);

    receiveWiFiCommand();
    handleSortSocket();
    checkZoneTriggerAndPopQueue();
    handleServoControl();
    checkArrivalStatus();
    checkCompletion();

    // 큐 상태 출력
    unsigned long now = millis();
    if (now - lastQueuePrint >= QUEUE_PRINT_INTERVAL) {
        printQueueStatus();
        lastQueuePrint = now;
    }
}
