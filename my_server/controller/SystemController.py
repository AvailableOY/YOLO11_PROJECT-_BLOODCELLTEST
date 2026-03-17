'''
    用于配置html文件的访问
    使用Django中的render函数
    1.导包
    2.直接return render(request, template_name)
    3、返回给页面的数据，键值对格式，页面可以通过[ey}}取出来
    4.返回数据格式
'''
# 导包
from django.shortcuts import render
#访问test.html文件
def go_test(request):
    return render(request = request, 
                  template_name ='test.html',
                  context = {"name" : "陶吉吉"},
                  content_type = "text/html;charset=utf-8",
                  )  #第一个参数必须是request对象，第二个参数是模板文件名

# 访问登录界面
def go_login(request):
    return render(request = request, 
                  template_name ='login.html',
                  content_type = "text/html;charset=utf-8",
                  )

# index.html
def go_index(request):
    return render(request = request, 
                  template_name ='index.html',
                )

# camera_detect.html
def go_camera_detect(request):
    return render(request = request, 
                  template_name ='camera_detect.html',
                )

# detect_records.html
def go_detect_records(request):
    return render(request, "detect_records.html")

# 跳转到视频监测界面
def go_video_detect(request):
    return render(request = request, 
                  template_name ='video_detect.html',
                )
# 跳转到欢迎界面
def go_welcome(request):
    return render(request = request, 
                  template_name ='welcome.html',
                )

# detect_img.html
def go_detect_img(request):
    return render(request, "detect_img.html")

def go_echarts(request):
    return render(request, "echarts.html")

#跳转聊天界面
def go_chat(request):
    return render(request, "chat.html")