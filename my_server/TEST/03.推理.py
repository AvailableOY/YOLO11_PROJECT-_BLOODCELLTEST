import os
from ultralytics import YOLO
from my_server.settings import BASE_DIR

if __name__ == "__main__":
    # 加载模型
    model = YOLO(os.path.join(BASE_DIR, 'weights', 'visdrone.pt'))
    # 推理
    results = model.predict(source="car.png" ,save=False)
    # model.export(format="engine")   #转成tensorrt会快很多
    '''
        获取检结果中的部分内容
         置信度
         类别
    '''
for result in results:
    name = result.names
    for box in result.boxes:
        # 类别
        class_name = name[int(box.cls.item())]
        # 置信度
        conf = round(box.conf.item(), 2)
        # print(class_name, conf)
        # print(box.xyxy.tolist())
        x_min, y_min, x_max, y_max = map(int, box.xyxy[0].tolist())