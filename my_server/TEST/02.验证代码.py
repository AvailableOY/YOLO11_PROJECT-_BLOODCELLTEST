from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO("yolov8s.pt")  

    model.val(
        data="",
        batch=8,
        imgsz=640,
        workers=8,
        device="0",
    )