#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT11

#define BLUE_LED_PIN 4
#define YELLOW_LED_PIN1 5
#define RED_LED_PIN 6
#define YELLOW_LED_PIN2 7

#define TEMP_BUZZER_PIN 8
#define HUM_BUZZER_PIN 9

#define MOTOR_PIN1 10
#define MOTOR_PIN2 11

const float TEMP_WARNING_LEVEL_2 = 3.0;   // 2단계: 기준보다 3도 차이
const float TEMP_WARNING_LEVEL_3 = 5.0;   // 3단계: 기준보다 5도 차이

const float HUM_WARNING_LEVEL_2 = 5.0;   // 2단계: 기준보다 5% 차이
const float HUM_WARNING_LEVEL_3 = 10.0;   // 3단계: 기준보다 10% 차이

const float TEMP_CORRECTION_VALUE = -45.0;            // 온도 보정치
const float MIN_TEMP = 24.0 + TEMP_CORRECTION_VALUE;
const float MAX_TEMP = 28.0 + TEMP_CORRECTION_VALUE;
const float HUM_CORRECTION_VALUE = 35.0;              // 습도 보정치
const float MIN_HUM = 40.0 + HUM_CORRECTION_VALUE;
const float MAX_HUM = 60.0 + HUM_CORRECTION_VALUE;

const int NOTE_C = 261;
const int NOTE_E = 329;
const int NOTE_G = 392;

const unsigned long SENSOR_INTERVAL = 2000;
const unsigned long MELODY_INTERVAL = 10000;
const unsigned long MELODY_DURATION = 1000;

enum AlarmType { NONE, COOLING, HEATING, DEHUMID, HUMIDIFY };

DHT dht(DHTPIN, DHTTYPE);

struct AlarmState {
  AlarmType type = NONE;
  bool active = false;
  unsigned long last_melody_time = 0;
  unsigned long melody_start_time = 0;
  int melody_step = 0;
  bool is_melody_playing = false;
};

AlarmState temp_alarm, hum_alarm;
unsigned long last_sensor_check = 0;

void setup() {
  Serial.begin(9600);
  dht.begin();

  pinMode(BLUE_LED_PIN, OUTPUT);
  pinMode(YELLOW_LED_PIN1, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(YELLOW_LED_PIN2, OUTPUT);

  pinMode(TEMP_BUZZER_PIN, OUTPUT);
  pinMode(HUM_BUZZER_PIN, OUTPUT);

  pinMode(MOTOR_PIN1, OUTPUT);
  pinMode(MOTOR_PIN2, OUTPUT);
}

bool alternate_flag = false;  // 부저 교대 상태
unsigned long last_switch_time = 0;
const unsigned long BUZZER_SWITCH_INTERVAL = 1000;

void loop() {
  unsigned long now = millis();

  if (now - last_sensor_check >= SENSOR_INTERVAL) {
    last_sensor_check = now;
    check_sensor_and_update_alarms();
  }

  if (temp_alarm.active && hum_alarm.active) {
    // 1초마다 부저 교대
    if (now - last_switch_time >= BUZZER_SWITCH_INTERVAL) {
      alternate_flag = !alternate_flag;
      last_switch_time = now;

      // 한 쪽 멜로디 리셋 (음 끊김 방지)
      temp_alarm.is_melody_playing = false;
      hum_alarm.is_melody_playing = false;
    }

    if (alternate_flag) {
      update_melody(temp_alarm, TEMP_BUZZER_PIN, NOTE_G); // 솔
      noTone(HUM_BUZZER_PIN);
    } else {
      update_melody(hum_alarm, HUM_BUZZER_PIN, NOTE_C); // 도
      noTone(TEMP_BUZZER_PIN);
    }
  } else {
    // 한 쪽만 활성화된 경우에는 평소대로
    update_melody(temp_alarm, TEMP_BUZZER_PIN, NOTE_G);
    update_melody(hum_alarm, HUM_BUZZER_PIN, NOTE_C);
  }
}

void check_sensor_and_update_alarms() {
  float temp = dht.readTemperature() + TEMP_CORRECTION_VALUE;
  float hum = dht.readHumidity() + HUM_CORRECTION_VALUE;
  if (hum < 100) {
    hum = 100;
  }

  if (isnan(temp) || isnan(hum)) {
    Serial.println("센서 에러!");
    return;
  }
  
  Serial.println("--------------------------------------------------------------");
  Serial.print("[정상 온도: "); Serial.print(MIN_TEMP), Serial.print("°C ~ "), Serial.print(MAX_TEMP), Serial.print("°C] 온도: "); Serial.print(temp); Serial.println(" °C, ");
  Serial.print("[정상 온도: "); Serial.print(MIN_HUM), Serial.print("% ~ "), Serial.print(MAX_HUM), Serial.print("%] 습도: "); Serial.print(hum); Serial.print(" %");

  
  // 온도 제어 LED
  if (temp > MAX_TEMP) {
    update_leds(BLUE_LED_PIN, RED_LED_PIN);
    update_alarm(temp_alarm, COOLING);
    Serial.print(" | 냉각 ON ");
  } else if (temp < MIN_TEMP) {
    update_leds(RED_LED_PIN, BLUE_LED_PIN);
    update_alarm(temp_alarm, HEATING);
    Serial.print(" | 온열 ON ");
  } else {
    clear_leds(BLUE_LED_PIN, RED_LED_PIN);
    reset_alarm(temp_alarm, TEMP_BUZZER_PIN);
    Serial.print(" | 온도 OFF ");
  }

  // 습도 제어 LED
  if (hum > MAX_HUM) {
    update_leds(YELLOW_LED_PIN1, YELLOW_LED_PIN2);
    update_alarm(hum_alarm, DEHUMID);
    Serial.print(" | 제습기 ON ");
  } else if (hum < MIN_HUM) {
    update_leds(YELLOW_LED_PIN2, YELLOW_LED_PIN1);
    update_alarm(hum_alarm, HUMIDIFY);
    Serial.print(" | 가습기 ON ");
  } else {
    clear_leds(YELLOW_LED_PIN1, YELLOW_LED_PIN2);
    reset_alarm(hum_alarm, HUM_BUZZER_PIN);
    Serial.print(" | 습도 OFF ");
  }
  Serial.println("");

  if (temp > MAX_HUM + HUM_WARNING_LEVEL_3 || temp < MIN_HUM - HUM_WARNING_LEVEL_3) {
    Serial.print("[경고 3단계] 습도를 조절하세요. | ");
  } else if (temp > MAX_HUM + HUM_WARNING_LEVEL_2 || temp < MIN_HUM - HUM_WARNING_LEVEL_2) {
    Serial.print("[경고 2단계] 습도를 조절하세요. | ");
  } else if (temp > MAX_HUM || temp < MIN_HUM ) {
    Serial.print("[경고 1단계] 습도를 조절하세요. | ");
  } else {

  }

  // 팬 제어
  if (temp > MAX_TEMP + TEMP_WARNING_LEVEL_3 || temp < MIN_TEMP - TEMP_WARNING_LEVEL_3) {
    analogWrite(MOTOR_PIN1, 200);
    digitalWrite(MOTOR_PIN2, 0);
    Serial.print("[경고 3단계] 온도를 조절하세요. ");
  } else if (temp > MAX_TEMP + TEMP_WARNING_LEVEL_2 || temp < MIN_TEMP - TEMP_WARNING_LEVEL_2) {
    analogWrite(MOTOR_PIN1, 100);
    digitalWrite(MOTOR_PIN2, 0);
    Serial.print("[경고 2단계] 온도를 조절하세요. ");
  } else if (temp > MAX_TEMP || temp < MIN_TEMP) {
    analogWrite(MOTOR_PIN1, 50);
    digitalWrite(MOTOR_PIN2, LOW);
    Serial.print("[경고 1단계] 온도를 조절하세요. ");
  } else {
    analogWrite(MOTOR_PIN1, 0);
    digitalWrite(MOTOR_PIN2, LOW);
  }

  Serial.println();
}

void update_leds(int on_pin, int off_pin) {
  digitalWrite(on_pin, HIGH);
  digitalWrite(off_pin, LOW);
}

void clear_leds(int pin1, int pin2) {
  digitalWrite(pin1, LOW);
  digitalWrite(pin2, LOW);
}

void update_alarm(AlarmState &alarm, AlarmType type) {
  alarm.type = type;
  alarm.active = true;
}

void reset_alarm(AlarmState &alarm, int buzzer_pin) {
  alarm.type = NONE;
  alarm.active = false;
  alarm.is_melody_playing = false;
  noTone(buzzer_pin);
}

void update_melody(AlarmState &alarm, int pin, int note) {
  unsigned long now = millis();

  if (alarm.type != NONE) {
    if (!alarm.is_melody_playing && now - alarm.last_melody_time >= MELODY_INTERVAL) {
      alarm.melody_start_time = now;
      alarm.is_melody_playing = true;
      alarm.melody_step = 0;
      alarm.last_melody_time = now;
    }

    if (alarm.is_melody_playing) {
      if (now - alarm.melody_start_time < MELODY_DURATION) {
        int tone_time = 200;     // 음 재생 시간
        int pause_time = 100;    // 쉼표 시간
        int cycle_time = tone_time + pause_time;

        unsigned long elapsed = now - alarm.melody_start_time;
        int current_step = elapsed / cycle_time;

        if (current_step < 3) {
          if (elapsed % cycle_time < tone_time) {
            tone(pin, note);
          } else {
            noTone(pin);
          }
        } else {
          noTone(pin);
          alarm.is_melody_playing = false;
        }
      } else {
        noTone(pin);
        alarm.is_melody_playing = false;
      }
    }
  } else {
    noTone(pin);
    alarm.is_melody_playing = false;
  }
}


void play_tone(int pin, int step, int note1, int note2, int note3) {
  switch (step) {
    case 0: tone(pin, note1); break;
    case 1: tone(pin, note2); break;
    case 2: tone(pin, note3); break;
    default: noTone(pin); break;
  }
}
