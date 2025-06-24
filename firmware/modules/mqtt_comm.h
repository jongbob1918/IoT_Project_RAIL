#ifndef MQTT_COMM_H
#define MQTT_COMM_H

#include <WiFiEsp.h>
#include <WiFiEspClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

class MqttComm {
private:
    WiFiEspClient espClient;
    PubSubClient client;
    SoftwareSerial* espSerial;
    const char* ssid;
    const char* pass;
    const char* mqttServer;
    int mqttPort;

public:
    MqttComm(SoftwareSerial* serial, const char* ssid, const char* pass, const char* mqttServer, int mqttPort)
        : client(espClient), espSerial(serial), ssid(ssid), pass(pass), mqttServer(mqttServer), mqttPort(mqttPort) {}

    // void setup() {
    //     espSerial->begin(9600);
    //     WiFi.init(espSerial);

    //     if (WiFi.status() == WL_NO_SHIELD) {
    //         Serial.println("WiFi shield not present");
    //         while (true);
    //     }

    //     while (WiFi.status() != WL_CONNECTED) {
    //         Serial.print("Connecting to WiFi...");
    //         WiFi.begin(ssid, pass);
    //         delay(3000);
    //     }

    //     Serial.println("WiFi connected");
    //     Serial.print("IP Address: ");
    //     Serial.println(WiFi.localIP());

    //     client.setServer(mqttServer, mqttPort);
    // }
    bool setup() {
        espSerial->begin(9600);
        WiFi.init(espSerial);
    
        if (WiFi.status() == WL_NO_SHIELD) {
            Serial.println("WiFi shield not present");
            return false;  // 실패 반환
        }
    
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 10) {
            Serial.print("Connecting to WiFi...");
            WiFi.begin(ssid, pass);
            delay(3000);
            attempts++;
        }
    
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("WiFi connection failed.");
            return false;  // 실패 반환
        }
    
        Serial.println("WiFi connected");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    
        client.setServer(mqttServer, mqttPort);
        return true;  // 성공
    }

    void reconnect() {
        while (!client.connected()) {
            Serial.print("Attempting MQTT connection...");
            if (client.connect("esp8266Client")) {
                Serial.println("connected");
            } else {
                Serial.print("failed, rc=");
                Serial.print(client.state());
                Serial.println(" try again in 5 seconds");
                delay(5000);
            }
        }
    }

    void loop() {
        if (!client.connected()) {
            reconnect();
        }
        client.loop();
    }

    void publishSensorData(const char* warehouseId, float temp, float hum) {
        StaticJsonDocument<200> doc;
        doc["temp"] = temp;
        doc["hum"] = hum;
        doc["ts"] = millis() / 1000; // 또는 time() 사용

        char topic[64];
        snprintf(topic, sizeof(topic), "v1/env/tmp/%s/data", warehouseId);

        char payload[128];
        serializeJson(doc, payload);
        client.publish(topic, payload);
    }
};

#endif
