# from ultralytics import YOLO

# model = YOLO("best.pt")
# model.export(format="onnx")

from ultralytics import YOLO
import cv2

# Load your trained YOLOv8 model
model = YOLO("best.pt")  # path to your trained weights

# Open the video file
video_path = "data/sample_video.mp4"  # change to your sample video path
cap = cv2.VideoCapture(video_path)

# Get video writer to save output
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("output_detected.mp4", fourcc, int(cap.get(cv2.CAP_PROP_FPS)),
                      (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLOv8 inference
    results = model(frame)

    # Plot results on the frame
    annotated_frame = results[0].plot()

    # Write to output file
    out.write(annotated_frame)

    # Show live detection window
    cv2.imshow("Fire & Smoke Detection", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()

