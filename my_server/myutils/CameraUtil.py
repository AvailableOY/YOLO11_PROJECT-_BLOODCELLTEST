'''
    1 打开摄像头
    2 关闭摄像头
    3 检测 流式输出 做到实时的效果
'''

import os
import threading
from my_server.settings import BASE_DIR
import cv2
from ultralytics import YOLO


class CameraUtil:
    # 定义三个变量 锁、摄像头读取对象、摄像头激活变量
    _lock = threading.Lock()     #拿到锁之后可以打开关闭摄像头
    _cap = None          #cv2.VideoCapture() 拿到摄像头
    _activate = False    #摄像头是否激活  cap.isOpened() 拿到摄像头是否打开的状态
    _model = YOLO(os.path.join(BASE_DIR, "weights","yolo11s.engine"))   #加载模型
    _class_names = {
        "person" : 0,
        "car" : 0,
        "pedestrian" : 0,

    }
    # 打开摄像头类方法
    @classmethod
    def open(cls):
        with cls._lock:
            # 打开摄像头：如果已经打开就不需要再打开了
            if cls._activate: return
            # 打开摄像头
            cls._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if cls._cap.isOpened():
                cls._activate = True
            else:
                cls._cap.release()
                raise RuntimeError("摄像头打开失败")
    
    
    # 关闭摄像头类方法
    @classmethod
    def close(cls):
        with cls._lock:
            # 关闭摄像头：如果已经关闭就不需要再关闭了
            if not cls._activate: return
            # 关闭摄像头
            cls._cap.release()
            cls._activate = False 

    # 检测摄像头类方法
    @classmethod
    def detect(cls):
        # 读取内容
        while True:
            ret, frame = cls._cap.read()
            if not ret:
                continue
            # 重置计数器（否则会无限累加）
            current_counts = {"person": 0, "car": 0, "pedestrian": 0}
            results = cls._model.predict(source=frame)
            for result in results:
                name = result.names
                for box in result.boxes:
                    # 类别
                    class_name = name[int(box.cls.item())]
                    if class_name in current_counts:
                        current_counts[class_name] += 1
                    # 置信度
                    conf = round(box.conf.item(), 2)
                    # 边界框信息
                    x_min, y_min, x_max, y_max = map(int, box.xyxy[0].tolist())
                    '''
                        完善统计到的物体的内容和数量
                    '''
                    cv2.putText(frame,f"{current_counts}",(0,0 + 10),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),2)
                    # 绘制检测结果信息到frame上
                    cv2.putText(frame,f"{class_name} {conf}",(x_min,y_min-10),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),2)
                    # 绘制边界框
                    cv2.rectangle(frame,(x_min,y_min),(x_max,y_max),(0,255,177),2)
            # 把frame转化为jpg格式
            # ret是布尔值 buffer转化为返回前端的内容
            ret,buffer = cv2.imencode('.jpg',frame)
            # 把buffer转化为字节流，返回给前端
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')