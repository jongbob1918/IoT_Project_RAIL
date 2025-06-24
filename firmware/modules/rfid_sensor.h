#ifndef MY_RFID_H
#define MY_RFID_H

#include <MFRC522.h>

class MyRFID 
{
public:
    MFRC522 reader;

    MyRFID(byte ssPin, byte rstPin) : reader(ssPin, rstPin) 
    {
    
    }

    void begin() 
    {
        reader.PCD_Init();
    }

    bool checkCardAndPrint(const String& readerName) 
    {
        if (reader.PICC_IsNewCardPresent() && reader.PICC_ReadCardSerial())
        {
            Serial.print("[" + readerName + "] UID: ");
            printUID();
            reader.PICC_HaltA();
            return true;
        }
        return false;
    }

private:
    void printUID() 
    {
        for (byte i = 0; i < reader.uid.size; i++) 
        {
            Serial.print(reader.uid.uidByte[i] < 0x10 ? " 0" : " ");
            Serial.print(reader.uid.uidByte[i], HEX);
        }
        Serial.println();
    }
};

#endif
