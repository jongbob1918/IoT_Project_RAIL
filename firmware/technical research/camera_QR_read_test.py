import cv2
import numpy as np

ESP32_CAM_IP = "192.168.2.2"
PORT = 81
STREAM_URL = f"http://{ESP32_CAM_IP}:{PORT}/stream"

def scan_qrcode(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)

    if data:
        print(f"[QR] {data}")
        if points is not None:
            points = points.reshape(-1, 2).astype(int)
            cv2.polylines(frame, [points], True, (0, 255, 0), 2)
            x, y = points[0]
            cv2.putText(frame, data, (int(x), int(y - 10)),
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

if __name__ == "__main__":
    main()
