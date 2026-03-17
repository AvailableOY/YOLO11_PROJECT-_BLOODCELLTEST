from ultralytics import YOLO
import os


if __name__ == "__main__":
    # 加载模型
    model = YOLO("weights/best.pt")
    model.export(format="engine")

