#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// WiFi 정보
// const char* ssid = "Galaxy Z Fold42488";
// const char* password = "623623623";

const char *ssid = "addinedu_class_1(2.4G)";
const char *password = "addinedu1";

// UDP 설정
WiFiUDP udp;
// const char* udp_address = "192.168.232.32"; // PC 수신기 주소
const char* udp_address = "192.168.2.198"; // PC 수신기 주소
const int udp_port = 8888;
const int packet_size = 1024; // UDP 패킷 크기

void setup() {
  Serial.begin(115200);

  // 카메라 설정
  camera_config_t config = {
    .pin_pwdn = PWDN_GPIO_NUM,
    .pin_reset = RESET_GPIO_NUM,
    .pin_xclk = XCLK_GPIO_NUM,
    .pin_sscb_sda = SIOD_GPIO_NUM,
    .pin_sscb_scl = SIOC_GPIO_NUM,
    .pin_d7 = Y9_GPIO_NUM,
    .pin_d6 = Y8_GPIO_NUM,
    .pin_d5 = Y7_GPIO_NUM,
    .pin_d4 = Y6_GPIO_NUM,
    .pin_d3 = Y5_GPIO_NUM,
    .pin_d2 = Y4_GPIO_NUM,
    .pin_d1 = Y3_GPIO_NUM,
    .pin_d0 = Y2_GPIO_NUM,
    .pin_vsync = VSYNC_GPIO_NUM,
    .pin_href = HREF_GPIO_NUM,
    .pin_pclk = PCLK_GPIO_NUM,
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = PIXFORMAT_JPEG,
    .frame_size = FRAMESIZE_QVGA,
    .jpeg_quality = 10,
    .fb_count = 1
  };

  esp_camera_init(&config);

  // WiFi 연결
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("WiFi connected");
  Serial.print("ESP32 CAM IP address : ");
  Serial.println(WiFi.localIP());
}

void loop() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  int total_len = fb->len;
  int packet_index = 0;

  // 시작 신호 (헤더)
  udp.beginPacket(udp_address, udp_port);
  udp.printf("FRAME_START:%d", total_len);
  udp.endPacket();
  delay(5);

  // UDP로 프레임 전송 (1024 바이트 단위)
  for (int i = 0; i < total_len; i += packet_size) {
    int len = (i + packet_size < total_len) ? packet_size : total_len - i;
    udp.beginPacket(udp_address, udp_port);
    udp.write(&fb->buf[i], len);
    udp.endPacket();
    delay(1); // 너무 빠르면 패킷 손실 발생 가능
  }

  // 종료 신호
  udp.beginPacket(udp_address, udp_port);
  udp.print("FRAME_END");
  udp.endPacket();

  esp_camera_fb_return(fb);
  delay(10); // 다음 프레임 간 간격
}
