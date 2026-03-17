import ast
import os
import sys
import cv2
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from ultralytics import YOLO
# 获取项目根目录：my_server 的父目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from my_server.settings import BASE_DIR
import time
from dao import DroneDao as dd
from myutils.CameraUtil import CameraUtil
from threading import Lock
FINAL_RESULTS = {} 
result_lock = Lock()


# 将检测的结果映射为中文
def translate_result(result):
    result_map = {
    "BA": "嗜碱性粒细胞",
    "BNE": "杆状核中性粒细胞",
    "EO": "嗜酸性粒细胞",
    "ERB": "有核红细胞",
    "LY": "淋巴细胞",
    "MMY": "晚幼粒细胞",
    "MO": "单核细胞",
    "MY": "中幼粒细胞",
    "PLT": "血小板",
    "PMY": "早幼粒细胞",
    "RBC": "红细胞",
    "SNE": "分叶核中性粒细胞",
    }
    return {result_map.get(k, k): v for k, v in result.items()}
#图片检测
def detect_img(file, username):
    # 定义一个字典 里面的key就是类型信息 value是类别数量
    class_names = {}
    filename = str(int(time.time())) + ".jpg"
    # 存储的路径
    save_path = os.path.join(BASE_DIR, 'static',"upload", filename)
    # print(save_path) 
    # 保存
    with open(save_path, 'wb') as f:
        # 一行一行写入
        for chunk in file.chunks(): 
            f.write(chunk)
    '''
        图片检测
    '''
    # 统计全部的置信度
    conf_sum = 0
    length = 0
    result_url = ''
    model = YOLO(os.path.join(BASE_DIR, "weights","best.pt"))
    project = os.path.join(BASE_DIR, 'runs',"detect")
    results = model.predict(source=save_path,save = True,project=project)
    if len(results) == 0:
        return{
            "status": 200,
            "msg": "未检测到任何目标"
        }
    # 检测结果处理
    for result in results:
        names = result.names
        boxes = result.boxes
        length = len(boxes)
        result_url = result.save_dir
        for box in boxes:
            # 类别
            class_name = names[int(box.cls.item())]
            # print("class_name:", class_name)
            # 对于应的类别数量+1
            class_names[class_name] = class_names.get(class_name, 0) + 1
            # 置信度
            conf = round(box.conf.item(), 2)
            conf_sum += conf
            '''
                每一次数据存入数据库的内容为：
                原始图片访问路径 检测结果图片访问地址 检测的置信度平均值 类别数量统计 检测的人 检测时间
            '''
        # 封装数据
        origin_rul = os.path.join("static","upload", filename).replace("\\","/")
        result_url = os.path.join("static",result_url.split("runs")[1]).replace("\\","/")
        result_url = "static" + result_url + "/" + filename

        conf = round(conf_sum/length,2)
        # 映射为中文
        class_names = translate_result(class_names)
        result = class_names
        save_data = [origin_rul,result_url,conf,str(result),username]
        print(save_data)
        '''
            存入数据库
            这里是数据库的存储操作，我们需要手动的管理事物
            1、如果操作的数据库代码没有问题 就提交
            2、如果操作的代码有问题 就回滚
        '''
        try:
            dd.save_result(save_data)
            return{
            "status": 200,
            "msg": "检测成功",
            "data": {
                "result_url": result_url,
                "result": result,
            }
        }
        except Exception as e:
            print(e)
            '''
            返回检测结果
            '''
            return{
                "status": 200,
                "msg": "检测失败",
                "data": e
            }



#检测结果展示
def find_data(page,size):
    total = dd.get_total()
    result = dd.find_data(page,size)
    #循环遍历result 把result中的每一个数据变成key value的形式 统一存放在list里面
    #定义存储数据的list
    data_list = []
    for item in result:
        #向 data_list 中添加数据 每一个数据都是字典 字典的key最好和列名对应
        data_list.append({
            "recordId":item[0],
            "orginUrl":item[1],
            "resultUrl":item[2],
            "conf":item[3],
            "result":item[4],
            "username":item[5],
            "createTime":item[6]
        })
    return {
        'status': 200,
        'msg': '数据获取成功',
        'data': {
            'total': total,
            'dataList': data_list
        }
    }


# 实时监测
def camera_detect(is_open):
    if is_open == "true":
        CameraUtil.open()
        #调用检测方法 返回一个生成器
        return CameraUtil.detect()
    else:
        CameraUtil.close()
        return{
            "status": 200,
            "msg": "关闭成功"
        }


# 用于上传视频（只保存，不检测）
def upload_video(request):
    if request.method == 'POST':
        file = request.FILES['file']
        username = request.POST.get('username', 'default')
        filename = str(int(time.time())) + ".mp4"
        save_path = os.path.join(BASE_DIR, "static", "upload", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        return JsonResponse({"status": 200, "task_id": filename})  # 返回文件名作为 task_id
    return JsonResponse({"status": 405})


# 可视化柱状图
def load_bar():
    result = dd.load_bar()
    '''
        封装数据
        x 字符串列表 createtime
        y 列表 conf
    '''
    x_data = []
    y_data = []
    for item in result:
        x_data.append(item[0].strftime("%Y-%m-%d %H:%M:%S"))
        y_data.append(item[1])
    return{
        "status": 200,
        "msg": "数据获取成功",
        "data": {
            "xData": x_data,
            "yData": y_data
        }
    }
CATEGORY_MAP = {
    'pedestrian': '行人',
    'person': '人',
    'bicycle': '自行车',
    'car': '小汽车',
    'van': '厢式货车',
    'truck': '卡车',
    'tricycle': '三轮车',
    'awning-tricycle': '带棚三轮车',
    'bus': '公交车',
    'motor cycle': '摩托车',
    'other': '其他'
}
def load_current_bar():
    result = dd.load_current_bar()
    '''
        封装数据
        x 字符串列表 createtime
        y 列表 conf
    '''
    print("=============",result[0][0])
    x_data = []
    y_data = []
    # 将结果转换为字典
    data_dict = ast.literal_eval(result[0][0])
    
    for key, value in data_dict.items():
        chinese_name = CATEGORY_MAP.get(key, key)  # 无映射则用原名
        x_data.append(chinese_name)
        y_data.append(value)

    return{
        "status": 200,
        "msg": "数据获取成功",
        "data": {
            "xData": x_data,
            "yData": y_data
        }
    }

# 可视化饼状图
def load_pie():
    result = dd.load_pie()
    '''
        封装数据
        [
            {"name": "分类名称", "value": 10}
            ...
        ]
    '''
    data = []
    for item in result:
        data.append({
            "name": item[0].strftime("%Y-%m-%d %H:%M:%S"),
            "value": item[1]
        })
    print(data)
    return{
        "status": 200,
        "msg": "数据获取成功",
        "data": data
    }
 

def detect_video(file):

    initial_state = {
        "status": 200,
        "msg": "",
        "counts": "",
        "output_video": "",
        "task_id": file,
        "isDetecting":True,
    }
    with result_lock:
        FINAL_RESULTS[file] = initial_state.copy()
    frame_count = 0
    last_update_time = time.time()
    UPDATE_INTERVAL = 3.0
    input_path = os.path.join(BASE_DIR, "static", "upload", file)
    output_filename = f"detected_{file}"
    output_path = os.path.join(BASE_DIR, "static", "output", f"detected_{file}")
    model_path = os.path.join(BASE_DIR, "weights", "yolo11s.engine")
    if os.path.exists(input_path):
        model = YOLO(model_path)
    # 处理视频
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 使用 mp4v 编码（兼容性好）
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 5. 初始化计数器（基于 track_id 去重）
    track_ids_seen = set()
    counts = {"person": 0, "car": 0, "truck": 0, "bus": 0}
    # YOLO COCO 类别映射（确保模型是 COCO 预训练）
    TARGET_CLASSES = {
        0: "person",
        2: "car",
        7: "truck",
        5: "bus"
    }

    frame_count = 0
    print(f"📌 视频总帧数: {total_frames}, 分辨率: {width}x{height}, FPS: {fps:.2f}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % 30 == 0:  # 每 30 帧打印一次进度
            print(f"  → 处理中... {frame_count}/{total_frames} ({frame_count/total_frames:.1%})")

        # ✅ 逐帧检测 + 跟踪（显存安全！）
        # persist=True 保持跟踪器状态；half=True 启用 FP16 加速（需 GPU）
        results = model.track(
            source=frame,
            persist=True,
            conf=0.25,          # 置信度阈值
            iou=0.6,           # NMS IOU 阈值
            tracker="bytetrack.yaml",  # 轻量级跟踪器
            verbose=False,
            half=True          # ✅ 关键：FP16，显存减半，速度↑（RTX 30+/40 系列支持）
        )

        # 6. 解析结果 & 计数
        if results and len(results[0].boxes) > 0:
            r = results[0]
            if r.boxes.id is not None:
                track_ids = r.boxes.id.cpu().numpy().astype(int)
                cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                confs = r.boxes.conf.cpu().numpy()
                xyxy = r.boxes.xyxy.cpu().numpy()

                for i, (tid, cls, conf, bbox) in enumerate(zip(track_ids, cls_ids, confs, xyxy)):
                    # 只处理目标类别
                    if cls not in TARGET_CLASSES:
                        continue
                    class_name = TARGET_CLASSES[cls]

                    # ✅ 去重：仅首次出现时计数
                    if tid not in track_ids_seen:
                        track_ids_seen.add(tid)
                        counts[class_name] += 1

                    # 绘制检测框（可选优化：只画关注类别）
                    x1, y1, x2, y2 = map(int, bbox)
                    color = (0, 255, 0) if class_name == "person" else (255, 177, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame,
                        f"{class_name} {tid} {conf:.2f}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

        current_time = time.time()
        if current_time - last_update_time >= UPDATE_INTERVAL:
            with result_lock:
                # 注意：FINAL_RESULTS[file] 是字典，不是 None
                FINAL_RESULTS[file]["counts"] = counts.copy()
                FINAL_RESULTS[file]["status"] = "running"
            last_update_time = current_time
            get_realtime_data(file)
        # 写入帧（保持原时间轴）
        out.write(frame)
    # 7. 释放资源
    cap.release()
    out.release()
    print(f"✅ 视频处理完成！共检测到: {counts}")

    # 8. 返回结果
    final_result = {
        "status": 200,
        "msg": "视频检测完成",
        "counts": counts,
        "output_video": f"/static/output/{output_filename}",
        "task_id": file,
        "isDetecting": False,
    }

    # 缓存最终结果
    with result_lock:
        FINAL_RESULTS[file] = final_result

    # 返回 final_result
    return final_result

def get_realtime_data(task_id):
    with result_lock:
        result = FINAL_RESULTS.get(task_id)
    if result is None:
        return {
            "status": 200,
            "msg": "视频检测完成",
            "counts": "",
            "output_video": "",
            "task_id": task_id,
            "isDetecting": True,
        }
    return result

# 获取当天检测的车辆
def get_today_count():
    counts = dd.get_today_count()
    return {
        "satus": 200,
        "counts" : counts
    }


# 统一获取首页大屏统计数据
def get_dashboard_stats(request):
    try:
        # 1. 今日样本分析 (调用你原有的方法)
        today_counts = dd.get_today_count()
        
        # 2. 异常细胞检出 (建议你在 Dao 层新增一个方法，比如统计 result 中 WBC>某阈值的数量)
        # abnormal_counts = dd.get_abnormal_count() 
        abnormal_counts = dd.get_today_pathological_count()
        
        # 3. 接入显微设备数 (可以查设备表，或者暂时写死)
        device_counts = 4

        # 获取 AI 引擎的真实 GPU 显存占用率
        gpu_usage_percent = 0
        engine_status = "引擎初始化中"

        gpu_usage_percent, engine_status = dd.get_gpu_status()

        return JsonResponse({
            "status": 200,
            "data": {
                "today_count": today_counts,
                "abnormal_count": abnormal_counts,
                "device_count": device_counts,
                "gpu_usage": gpu_usage_percent,
                "engine_status": engine_status
            }
        })
    except Exception as e:
        return JsonResponse({"status": 500, "error": str(e)})