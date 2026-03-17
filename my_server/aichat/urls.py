from django.contrib import admin
from django.urls import path
# 引入SystemController模块
from controller import DroneController as dc

urlpatterns = [
    path("chatModel/",dc.chat)
]