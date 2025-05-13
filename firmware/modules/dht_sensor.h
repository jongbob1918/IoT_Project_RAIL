#ifndef MY_DHT_H
#define MY_DHT_H

#include "DHT.h"

class MyDHT
{
public:
    DHT dht;

    MyDHT(byte DHTPIN, byte DHTTYPE) : dht(DHTPIN, DHTTYPE) 
    {
    
    }

    void begin() 
    {
        dht.begin();
    }

    int printTemp() 
    {   
        // 습도
        float humidity = dht.readHumidity();
        // 온도
        float temperature = dht.readTemperature();
        
        // 읽기 실패하지 않았는지 체크
        if (isnan(humidity) || isnan(temperature)) 
        {
            Serial.println("Failed to read from DHT sensor!"); // 읽기 실패 시 에러 메시지 출력
            return;
        }

        // 온도와 습도 출력
        // Serial.print("Temperature: ");
        // Serial.print((int)temperature);
        // Serial.print(" °C, ");
        // Serial.print("Humidity: ");
        // Serial.print((int)humidity);
        // Serial.print(" %, ");
        // Serial.println();
        //온도 리턴
        return (int)temperature;
    }

    int printHum() 
    {   
        // 습도
        float humidity = dht.readHumidity();
        // 온도
        float temperature = dht.readTemperature();
        
        // 읽기 실패하지 않았는지 체크
        if (isnan(humidity) || isnan(temperature)) 
        {
            Serial.println("Failed to read from DHT sensor!"); // 읽기 실패 시 에러 메시지 출력
            return;
        }

        // 온도와 습도 출력
        // Serial.print("Temperature: ");
        // Serial.print((int)temperature);
        // Serial.print(" °C, ");
        // Serial.print("Humidity: ");
        // Serial.print((int)humidity);
        // Serial.print(" %, ");
        // Serial.println();
        // 습도 리턴
        return (int)humidity;
    }
};

#endif
