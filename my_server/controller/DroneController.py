import json
import os
from django.http import FileResponse, JsonResponse, StreamingHttpResponse
from my_server.settings import BASE_DIR
from service import DroneService as ds
from service import ChatService as cs
from service import ReportService as rs

def detect_img(request):
    file = request.FILES.get("file")
    username = request.POST.get("username")
    print(file, username)
    return JsonResponse(
        ds.detect_img(file, username)
        )

# 检测结果展示
def find_data(request):
    # 获取的是字符串类型 要转成int类型
    page = int(request.GET.get("page"))
    size = int(request.GET.get("size"))
    return JsonResponse(
        ds.find_data(page, size)
        )


# 实时监测
def camera_detect(request):
    # isOpen是客户端传过来的参数控制摄像头的变量
    is_open = request.GET.get("isOpen")
    return StreamingHttpResponse(
        streaming_content=ds.camera_detect(is_open),
        content_type="multipart/x-mixed-replace;boundary=frame"
        )

# 视频检测
def detect_Video(request):
    data = json.loads(request.body)
    task_id = data.get("task_id")
    print("任务ID为：", task_id)
    return JsonResponse(
        ds.detect_video(task_id)
        )


# 可视化 --柱状图
'''
    检测记录中的置信度前五的数据
    x轴为时间
    y轴为置信度
'''
def load_bar(request):
    return JsonResponse(ds.load_bar())

def load_current_bar(request):
    return JsonResponse(ds.load_current_bar())

def get_realtime_data(request):
    task_id = request.GET.get("task_id")
    return JsonResponse(ds.get_realtime_data(task_id))

# 可视化 --饼状图
def load_pie(request):
    return JsonResponse(ds.load_pie())

# 聊天
def chat(request):
    return cs.chat(request)
# 获取今天检测的数量
def get_dashboard_stats(request):
    return ds.get_dashboard_stats(request)
# 生成报告
def generate_report(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            record_id = data.get("record_id")
            
            # 1. 调用 Service 生成报告，获取生成的绝对路径
            file_path = rs.generate_report(record_id)
            
            if file_path and os.path.exists(file_path):
                # 2. 以二进制读取模式打开文件
                file_obj = open(file_path, 'rb')
                
                # 3. 使用 FileResponse 将文件流返回给前端下载
                response = FileResponse(file_obj)
                
                # 设置 MIME 类型，告诉浏览器这是一个 Word 文档
                response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                # 允许前端读取跨域的文件名 (如果在前端 axios 需要读 header 的话)
                response['Access-Control-Expose-Headers'] = 'Content-Disposition'
                
                return response
            else:
                return JsonResponse({"error": "后端生成报告失败，请检查日志。"}, status=500)
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST allowed"}, status=405)