import argparse
from src import train_model, predict, video_inference, alert_system
from utils.preprocessing import prepare_data
import os

def download_yolo_model():
    from ultralytics import YOLO
    print("[INFO] Downloading YOLOv8 model...")
    YOLO('yolov8n.pt')  # Downloads and caches model
    print("[INFO] YOLOv8 base model downloaded.")

def main(args):
    if args.task == "download":
        download_yolo_model()

    elif args.task == "prepare-data":
        prepare_data(args.data_path)

    elif args.task == "train":
        train_model.train(params_file=args.params)

    elif args.task == "predict":
        predict.run(image_path=args.image)

    elif args.task == "video":
        video_inference.run(video_path=args.video)

    elif args.task == "alert":
        alert_system.send_alert()

    else:
        print("❌ Invalid task. Use one of: download, prepare-data, train, predict, video, alert")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fire and Smoke Detection - Main Controller")
    parser.add_argument("--task", type=str, required=True,
                        help="Task to perform: download | prepare-data | train | predict | video | alert")
    parser.add_argument("--params", type=str, default="params.yaml", help="Path to params.yaml")
    parser.add_argument("--data_path", type=str, default="data/", help="Path to dataset")
    parser.add_argument("--image", type=str, help="Path to image for prediction")
    parser.add_argument("--video", type=str, help="Path to video for inference")
    
    args = parser.parse_args()
    main(args)
