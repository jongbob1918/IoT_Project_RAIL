#include <SPI.h>
#include <MFRC522.h>

// ───── 핀 설정 ─────
#define SS_PIN 10
#define RST_PIN 9
#define DATA_BLOCK 4
#define GREEN_LED_PIN 7
#define RED_LED_PIN   6

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

// ───── 상태 변수 ─────
bool registerMode = false;
bool cardReadyToWrite = false;
bool cardPresent = false;

String currentUid = "";
String writeEmpId = "";
String lastProcessedUid = "";
unsigned long lastReadTime = 0;
const unsigned long READ_TIMEOUT = 3000;

// ───── LED 제어 상태 ─────
bool accessLedActive = false;
unsigned long accessLedStartTime = 0;
int accessLedPin = -1;

// ───── 초기화 ─────
void setup()
{
    Serial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    pinMode(GREEN_LED_PIN, OUTPUT);
    pinMode(RED_LED_PIN, OUTPUT);
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);

    Serial.println("🟢 게이트 제어 시작됨");
}

// ───── 메인 루프 ─────
void loop()
{
    checkSerialCommand();
    handleRFID();
    updateAccessLed();
}

// ───── 명령 처리 ─────
void checkSerialCommand()
{
    if (Serial.available())
    {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        if (cmd == "GCmd1")
        {
            registerMode = true;
            cardReadyToWrite = false;
            currentUid = "";
            lastProcessedUid = "";
            Serial.println("GRok: 등록 모드 진입");
        }
        else if (cmd == "GCmd0")
        {
            registerMode = false;
            cardReadyToWrite = false;
            writeEmpId = "";
            currentUid = "";
            Serial.println("GRok: 출입 모드 복귀");
        }
        else if (cmd.startsWith("GCwr"))
        {
            writeEmpId = cmd.substring(4);

            if (!cardReadyToWrite || currentUid == "")
            {
                Serial.println("GXe0: 카드 없음");
                return;
            }

            mfrc522.PCD_Init();
            if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial())
            {
                Serial.println("GXe0: 카드 없음 (쓰기 시)");
                return;
            }

            String uidStr = getUidString();
            if (uidStr != currentUid) {
                Serial.println("GXe0: 다른 카드가 감지됨");
                return;
            }

            if (writeEmpId.length() > 16)
            {
                Serial.println("GXe2: 직원 ID 길이 초과");
                return;
            }

            byte trailerBlock = (DATA_BLOCK / 4) * 4 + 3;
            MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
                MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));

            if (status != MFRC522::STATUS_OK)
            {
                Serial.println("GXe1: 인증 실패");
                mfrc522.PICC_HaltA();
                mfrc522.PCD_StopCrypto1();
                return;
            }

            byte buffer[16] = {0};
            writeEmpId.getBytes(buffer, 16);

            bool writeSuccess = false;
            for (int attempt = 0; attempt < 3; attempt++) {
                status = mfrc522.MIFARE_Write(DATA_BLOCK, buffer, 16);
                if (status == MFRC522::STATUS_OK) {
                    writeSuccess = true;
                    break;
                }
                delay(50);
            }

            if (writeSuccess)
            {
                Serial.print("GRok: 카드 쓰기 완료 → ");
                Serial.print(currentUid);
                Serial.print(" ← ");
                Serial.println(writeEmpId);
            }
            else
            {
                Serial.println("GXe2: 카드 쓰기 실패");
            }

            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();

            cardReadyToWrite = false;
            currentUid = "";
            writeEmpId = "";

            lastProcessedUid = uidStr;
            lastReadTime = millis();
        }
        else if (cmd == "GCac1")
        {
            Serial.println("GRok: 출입 허용 → GREEN ON");
            handleAccessResult("ALLOW");
        }
        else if (cmd == "GCac0")
        {
            Serial.println("GRok: 출입 거부 → RED ON");
            handleAccessResult("DENY");
        }
        else
        {
            Serial.println("GXe4: 알 수 없는 명령");
        }
    }
}

// ───── RFID 처리 ─────
void handleRFID()
{
    mfrc522.PCD_Init();

    if (!mfrc522.PICC_IsNewCardPresent())
    {
        if (cardPresent) cardPresent = false;
        return;
    }

    if (!mfrc522.PICC_ReadCardSerial()) return;

    String uidStr = getUidString();
    unsigned long currentTime = millis();

    if (uidStr == lastProcessedUid && currentTime - lastReadTime < READ_TIMEOUT) {
        if (!registerMode || (registerMode && cardReadyToWrite)) {
            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
            return;
        }
    }

    cardPresent = true;

    byte trailerBlock = (DATA_BLOCK / 4) * 4 + 3;
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));

    if (status != MFRC522::STATUS_OK)
    {
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    byte buffer[18];
    byte size = sizeof(buffer);
    status = mfrc522.MIFARE_Read(DATA_BLOCK, buffer, &size);

    if (status != MFRC522::STATUS_OK)
    {
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        return;
    }

    char empId[17] = {0};
    memcpy(empId, buffer, 16);

    if (registerMode)
    {
        if (!cardReadyToWrite) {
            Serial.print("GEwr");
            Serial.print(uidStr);
            Serial.print(";");
            Serial.println(empId);
            currentUid = uidStr;
            cardReadyToWrite = true;
            lastProcessedUid = uidStr;
            lastReadTime = currentTime;
        }
    }
    else
    {
        Serial.print("GEid");
        Serial.print(uidStr);
        Serial.print(";");
        Serial.println(empId);
        lastProcessedUid = uidStr;
        lastReadTime = currentTime;
    }

    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
}

// ───── UID 문자열 생성 ─────
String getUidString()
{
    String uidStr = "";
    for (byte i = 0; i < mfrc522.uid.size; i++)
    {
        uidStr += String(mfrc522.uid.uidByte[i], HEX);
        if (i < mfrc522.uid.size - 1) uidStr += ":";
    }
    return uidStr;
}

// ───── 출입 결과 LED 제어 (비동기) ─────
void handleAccessResult(String type)
{
    if (type == "ALLOW")
        accessLedPin = GREEN_LED_PIN;
    else if (type == "DENY")
        accessLedPin = RED_LED_PIN;
    else
        return;

    digitalWrite(accessLedPin, HIGH);
    accessLedStartTime = millis();
    accessLedActive = true;
}

void updateAccessLed()
{
    if (accessLedActive && millis() - accessLedStartTime >= 2000)
    {
        digitalWrite(accessLedPin, LOW);
        accessLedActive = false;
        accessLedPin = -1;
    }
}
