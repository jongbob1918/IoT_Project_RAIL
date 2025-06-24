import cv2
import numpy as np
import socket

ESP32_CAM_IP = "192.168.232.147"
PORT = 81
STREAM_URL = f"http://{ESP32_CAM_IP}:{PORT}/stream"

# 전송할 ESP32 서버의 IP와 포트
ESP32_SERVER_IP = "192.168.232.100"  # 변경하세요
ESP32_SERVER_PORT = 9100

# TCP 소켓 설정
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.settimeout(5)
try:
    client_socket.connect((ESP32_SERVER_IP, ESP32_SERVER_PORT))
    print(f"✅ Connected to ESP32 server at {ESP32_SERVER_IP}:{ESP32_SERVER_PORT}")
except Exception as e:
    print(f"❌ Could not connect to ESP32: {e}")
    client_socket = None

def parse_qr_data(data):
    if len(data) >= 11:
        warehouse_id = data[0]
        product_id = data[1:3]
        company_code = data[3:5]
        expiry_date_raw = data[5:11]
        expiry_date = f"20{expiry_date_raw[:2]}-{expiry_date_raw[2:4]}-{expiry_date_raw[4:]}"
        return warehouse_id, product_id, company_code, expiry_date
    else:
        return None, None, None, None

def scan_qrcode(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)

    if data and points is not None and cv2.contourArea(points.astype(np.float32)) > 0:
        warehouse_id, product_id, company_code, expiry_date = parse_qr_data(data)
        print(f"[QR] 전체: {data}")
        print(f" - 창고번호 : {warehouse_id}")
        print(f" - 물품번호 : {product_id}")
        print(f" - 회사코드 : {company_code}")
        print(f" - 유통기한 : {expiry_date}")

        # 창고번호에 따라 전송 데이터 결정
        mv_mapping = {
            'A': 'MV0',
            'B': 'MV1',
            'C': 'MV2',
            'D': 'MV3',
            'E': 'MV4'
        }
        mv_code = mv_mapping.get(warehouse_id.upper(), 'MVX')  # 기본값 MVX

        # TCP로 전송
        if client_socket:
            try:
                client_socket.sendall((mv_code + "\n").encode())
                print(f"📤 Sent to ESP32: {mv_code}")
            except Exception as e:
                print(f"⚠️ Failed to send: {e}")

        # 시각화
        points = points.reshape(-1, 2).astype(int)
        cv2.polylines(frame, [points], True, (0, 255, 0), 2)
        x, y = points[0]
        cv2.putText(frame, mv_code, (int(x), int(y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        print("No QR code detected.")

    return frame


def main():
    print("Starting stream-based QR code scanner... (ESC to exit)")
    cap = cv2.VideoCapture(STREAM_URL)

    if not cap.isOpened():
        print("❌ Cannot open stream.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Failed to read frame.")
            continue

        frame = scan_qrcode(frame)
        cv2.imshow("QR Stream", frame)

        if cv2.waitKey(1) == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    if client_socket:
        client_socket.close()

if __name__ == "__main__":
    main()
