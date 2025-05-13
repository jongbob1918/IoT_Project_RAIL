import socket
import cv2
import numpy as np

# === UDP 수신 설정 ===
UDP_IP = "0.0.0.0"
UDP_PORT = 8888
PACKET_SIZE = 1024

# === TCP 서버 설정 (ESP32가 클라이언트로 연결)
SERVER_IP = "0.0.0.0"
SERVER_PORT = 9100

# 창고 ID → MV 코드 매핑
mv_mapping = {
    'A': 'MV0',
    'B': 'MV1',
    'C': 'MV2',
    'D': 'MV3',
    'E': 'MV4'
}

# === TCP 서버 시작 ===
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind((SERVER_IP, SERVER_PORT))
server_sock.listen(1)

print(f"[📡] TCP 서버 시작됨. ESP32 접속 대기 중 {SERVER_PORT}...")
conn, addr = server_sock.accept()
print(f"[✅] ESP32 연결됨: {addr}")

# === UDP 수신 소켓 설정 ===
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind((UDP_IP, UDP_PORT))
udp_sock.settimeout(5)

buffer = bytearray()
receiving = False
expected_size = 0
last_sent_data = ""  # 중복 전송 방지
qr_detector = cv2.QRCodeDetector()

print(f"[📷] UDP 수신 대기 중 {UDP_PORT}...")

# === 메인 루프 ===
while True:
    try:
        data, _ = udp_sock.recvfrom(PACKET_SIZE + 50)

        if data.startswith(b'FRAME_START'):
            buffer.clear()
            parts = data.decode().strip().split(':')
            if len(parts) == 2:
                expected_size = int(parts[1])
                receiving = True
                print(f"[▶] 수신 시작: {expected_size} bytes")

        elif data.startswith(b'FRAME_END'):
            print(f"[■] 수신 완료: {len(buffer)} bytes")

            if len(buffer) == expected_size:
                # jpg = np.frombuffer(buffer, dtype=np.uint8)
                jpg = np.frombuffer(bytes(buffer), dtype=np.uint8)
                img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)

                if img is not None:
                    qr_data, points, _ = qr_detector.detectAndDecode(img)
                    if qr_data:
                        print(f"[QR] 인식됨: {qr_data}")
                        if points is not None and points.size >= 4:
                            # points = points.astype(int).reshape(-1, 2)
                            # cv2.polylines(img, [points], True, (0, 255, 0), 2)
                            # x, y = points[0]
                            # cv2.putText(img, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            try:
                                points = points.astype(int).reshape(-1, 2)
                                cv2.polylines(img, [points], True, (0, 255, 0), 2)
                                x, y = points[0]
                                cv2.putText(img, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            except Exception as e:
                                print(f"[⚠️] QR 시각화 실패: {e}")

                        # QR → 명령 → ESP32 전송
                        if len(qr_data) >= 1:
                            warehouse_id = qr_data[0].upper()
                            mv_cmd = mv_mapping.get(warehouse_id, "MVX")
                            if qr_data != last_sent_data and mv_cmd.startswith("MV"):
                                try:
                                    # conn.sendall((mv_cmd + '\n').encode())
                                    conn.sendall((qr_data + '\n').encode())
                                    print(f"[📤] ESP32로 전송됨: {mv_cmd}")
                                    last_sent_data = qr_data
                                except Exception as e:
                                    print(f"[X] TCP 전송 오류: {e}")
                                    break
                else:
                    print("[!] 이미지 디코딩 실패")

                cv2.imshow("QR UDP Stream", img)
                if cv2.waitKey(1) == 27:
                    break
            else:
                print(f"[!] 불완전한 프레임: {len(buffer)} / {expected_size}")

            receiving = False
            buffer.clear()

        elif receiving:
            buffer.extend(data)

    except socket.timeout:
        print("[!] UDP 타임아웃")
    except Exception as e:
        print(f"[X] 오류 발생: {e}")
        break

# === 종료 처리 ===
conn.close()
udp_sock.close()
server_sock.close()
cv2.destroyAllWindows()
print("[🛑] 프로그램 종료")
