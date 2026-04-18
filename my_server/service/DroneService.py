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


def detect_img(files, username):
    # 1. 确保核心文件夹存在（防止 FileNotFoundError）
    # 既然你要用 runs/detect，我们把它放在 static 下，这样前端才能直接访问
    upload_dir = os.path.join(BASE_DIR, "static", "upload")
    # 💡 关键：这就是你要的路径，放在 static 下是为了让网页能看到图
    project_path = os.path.join(BASE_DIR, "static", "runs", "detect")
    
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(project_path, exist_ok=True)

    # 模型加载
    model_path = os.path.join(BASE_DIR, "weights", "best.pt")
    model = YOLO(model_path)
    
    detailed_results = []

    # 2. 循环处理每一张图片
    for index, file in enumerate(files):
        class_names = {}
        filename = f"{int(time.time())}_{index}.jpg"
        
        # --- A. 保存原图到 static/upload ---
        save_path = os.path.join(upload_dir, filename)
        with open(save_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        # 这里是推理时间的测试
        start_time = time.time()

        # --- B. 执行预测 ---
        # 💡 project 参数设为你想要的路径
        # name 设为 "predict"，YOLO 会自动生成 predict, predict2, predict3...
        results = model.predict(
            source=save_path, 
            save=True, 
            project=project_path, 
            name="predict"
        )
        # 💡 2. 记录推理结束时间，并计算耗时（转换为毫秒 ms，保留两位小数）
        end_time = time.time()
        infer_time_ms = round((end_time - start_time) * 1000, 2)
        
        # 💡 3. 在后台打印出来，方便你直接抄进论文的数据表里
        print(f"🚀 图片 {filename} 纯推理耗时: {infer_time_ms} ms")
        
        if len(results) == 0:
            continue

        # --- C. 处理检测结果 ---
        for result in results:
            # 💡 关键：获取 YOLO 刚刚自动创建的文件夹名字（如 predict85）
            yolo_folder = os.path.basename(result.save_dir)
            
            names = result.names
            boxes = result.boxes
            length = len(boxes)
            
            if length == 0:
                continue

            conf_sum = 0
            for box in boxes:
                cls_id = int(box.cls.item())
                class_name = names[cls_id]
                class_names[class_name] = class_names.get(class_name, 0) + 1
                conf_sum += box.conf.item()

            # --- D. 封装路径与存库 ---
            # 数据库里的原始图路径
            origin_url = f"static/upload/{filename}"
            
            # 💡 核心修正：按照你要求的格式拼接结果图路径
            # 存入数据库的应该是：static/runs/detect/predictXX/文件名.jpg
            formatted_res_url = f"static/runs/detect/{yolo_folder}/{filename}"

            conf_avg = round(conf_sum / length, 2)
            translated_results = translate_result(class_names)

            # --- 封装当前图片的完整数据 ---
            current_item_data = {
                "origin_url": "/" + origin_url,
                "result_url": "/" + formatted_res_url,
                "conf": conf_avg,
                "details": translated_results, # 这里是 {'红细胞': 10, '血小板': 2}
                "filename": file.name,           # 保留原始文件名，前端好展示
                "infer_time": infer_time_ms,
            }

            # 准备数据并存入数据库
            save_data = [origin_url, formatted_res_url, conf_avg, str(translated_results), infer_time_ms,username]
            
            try:
                dd.save_result(save_data)
                detailed_results.append(current_item_data)
            except Exception as e:
                print(f"图片 {filename} 存入数据库失败: {e}")
                continue

    # --- E. 响应 ---
    if len(detailed_results) > 0:
        return {
            "status": 200,
            "msg": f"批量检测成功，处理了{len(detailed_results)}张图",
            "data": { "all_data": detailed_results }
        }
    else:
        return { "status": 500, "msg": "检测失败", "data": {} }


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
            "createTime":item[6],
            "inferTime":item[7],
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