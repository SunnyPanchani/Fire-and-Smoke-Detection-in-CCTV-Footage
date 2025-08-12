# from ultralytics import YOLO

# model = YOLO("best.pt")
# model.export(format="onnx")

from ultralytics import YOLO
import cv2


model = YOLO("best.pt")  

video_path = "data/fire.mp4"  
cap = cv2.VideoCapture(video_path)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("output_detected.mp4", fourcc, int(cap.get(cv2.CAP_PROP_FPS)),
                      (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))

while True:
    ret, frame = cap.read()
    if not ret:
        break

   
    results = model(frame)

    
    annotated_frame = results[0].plot()

    
    out.write(annotated_frame)

    
    cv2.imshow("Fire & Smoke Detection", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()

