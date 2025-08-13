from ultralytics import YOLO
import cv2

# Load your YOLO model
model = YOLO("best.pt")  # Path to your trained fire/smoke model

# Dahua RTSP URL (sub stream recommended for faster inference)
rtsp_url = "rtsp://admin:admin456@192.168.1.150:554/cam/realmonitor?channel=4&subtype=1"

cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("❌ Failed to connect to CCTV stream")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠ Failed to grab frame")
        break

    # Run detection
    results = model(frame, conf=0.5)
    annotated_frame = results[0].plot()

    # Display
    cv2.imshow("Dahua CCTV Fire/Smoke Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
