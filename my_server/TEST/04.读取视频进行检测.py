'''
    读取视频进行检测的步骤 opencv
    1 读取视频 得到视频帧
    2 在视频帧上进行检测
    3 自己提取检测结果信息 使用opencv计算把内别 置信度 边界框绘制在这一帧上
'''
import cv2
from ultralytics import YOLO

VIDEO_PATH = "test.mp4"
# 加载模型
MODEL_PATH = "weights/visdrone.pt"
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(VIDEO_PATH)
# ✅ 先创建窗口
cv2.namedWindow("frame", cv2.WINDOW_NORMAL)  # WINDOW_NORMAL 允许调整大小
# 再设置窗口大小
cv2.resizeWindow("frame", 640, 480)
# 通过循环不断读取视频内容
while True:
    '''
        read 方法返回两个值
        第一个值 ret 表示是否成功读取
        第二个值 frame 表示当前帧
    '''
    ret, frame = cap.read()
    if not ret:
        break

    #使用模型进行检测
    results = model.predict(source=frame)
    for result in results:
        name = result.names
        for box in result.boxes:
            # 类别
            class_name = name[int(box.cls.item())]
            # 置信度
            conf = round(box.conf.item(), 2)
            # 边界框信息
            x_min, y_min, x_max, y_max = map(int, box.xyxy[0].tolist())
            # 绘制检测结果信息到frame上
            cv2.putText(frame,f"{class_name} {conf}",(x_min,y_min-10),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),2)
            # 绘制边界框
            cv2.rectangle(frame,(x_min,y_min),(x_max,y_max),(0,255,177),2)
    #显示当前帧
    cv2.imshow("frame",frame)
    if cv2.waitKey(1) == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()