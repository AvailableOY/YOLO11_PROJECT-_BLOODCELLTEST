"""my_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
# 引入SystemController模块
from controller import SystemController as sc
from controller import UserController as uc
from controller import DroneController as dc
from service import DroneService as ds
from service import ChatService as cs

urlpatterns = [
    path('admin/', admin.site.urls),
    path('goTest/', sc.go_test),  #配置访问test.html的路由
    path('reJson/', uc.re_json),
    path('reStream/', uc.re_stream),
    path('getParams/', uc.get_params),
    path('postParams/', uc.post_params),
    path('postFile/', uc.post_file),
    path('', sc.go_login),  #配置访问login.html的路由  直接通过8777访问
    path('login/', uc.login),  #配置登录接口
    path('goIndex/', sc.go_index),  #配置访问index.html的路由

    path("goDetectRecords/", sc.go_detect_records),
    path('goCameraDetect/', sc.go_camera_detect),  #配置访问camera_detect.html的
    path("goVideoDetect/", sc.go_video_detect),  #配置访问video_record.html的路由
    path("goLogin/", sc.go_login),  #配置访问login.html的路由
    path("goWelcome/", sc.go_welcome),  #配置访问welcome.html的路由
    path("detectImg/", dc.detect_img),  #配置访问detect_img.html的路由
    path("goDetectImg/", sc.go_detect_img),
    path("findData/", dc.find_data),  #配置访问find_data.html的路由
    path("cameraDetect/", dc.camera_detect),  #配置访问camera_detect.html的路由
    path("detectVideo/", dc.detect_Video),  #配置访问detect_img.html的路由
    path('uploadVideo/', ds.upload_video),
    # path('streamDetection/<str:task_id>/', ds.stream_detection),
    path('loadBar/', dc.load_bar),
    path('loadPie/', dc.load_pie),
    path("goEcharts/", sc.go_echarts),  #配置访问echarts.html的路由")
    path("goChat/", sc.go_chat),
    path('aichat/', include('aichat.urls')),
    path("LoadCurrentBar/", dc.load_current_bar),  #配置访问load_current_bar.html的路由
    path("get_realtime_data/",dc.get_realtime_data),
    # path("get_today_count/",dc.get_today_count),
    path("get_dashboard_stats/",dc.get_dashboard_stats),
    # 生成报告
    path("generate_report/",dc.generate_report),
    # 获取历史聊天记录
    path("get_chat_history/", cs.get_chat_history),
    # 获取会话列表
    path("get_session_list/", cs.get_session_list),
]
