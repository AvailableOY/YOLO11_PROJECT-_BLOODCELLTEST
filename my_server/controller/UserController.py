# 导入包
import json
import os
import time
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from my_server.settings import BASE_DIR
from service import UserService as us

# login
def login(request):
    dict_data = json.loads(request.body)
    return JsonResponse(us.login(dict_data))

'''
    HttpResponse, JsonResponse 返回json数据给客户端
    1、json数据格式:本质是字符串，只是说满足key:value的格式
    JSON 数据和py中的dict可以相互转化，API
        json.dumps(dict)  dict --> json
        json.loads(json_str)  json --> dict
    JSON数据格式常用于客户端和服务器间进行交换
    2、HttpResponse, JsonResponse区别
        HttpResponse:默认返回文本内容 可以设置content_type为"application/json"来返回json数据
        返回json数据需要手动将dict转换为json字符串
        JsonResponse:专门返回json数据 参数就给一个字典，自动转化为json字符串
'''

# 测试返回Jsonn数据
def re_json(request):
    dict_data = {
        "status":200,
        "msg":"返回json数据成功",
        "data":[
            {
                "name":"张三",
                "age":18
            },
            {
                "name":"亮剑",
                "age":27
            }
        ]
    }
    return JsonResponse(dict_data)


# 迭代器
def gennerator_data():
    for i in range(10):
        time.sleep(1)
        yield "第%s个数据\n" % i
# 测试流式输出
def re_stream(request):
    '''
        StreamingHttpResponse用来做流式输出
         streaming_content:一个可迭代对象，迭代对象返回的字符串会作为响应内容输出
         content_type:响应内容类型,不同业务设置不同的类型
    '''
    return StreamingHttpResponse(streaming_content=gennerator_data(), content_type="text/plain;charset=utf-8")  #返回流式响应


'''
    get请求 客户端传给服务器一个参数加msg，内容为因为你
'''

def get_params(request):
    msg = request.GET.get("msg")
    print(msg)
    return JsonResponse({
        "status":200, 
        "msg":"GET请求成功",
        "data":msg
        })

'''
    post请求 客户端传给服务器求账号内容，分别为uername和password
    格式：通过请求体得到数据（bytes类型）
    dict_data = json.loads(request.body)
'''

def post_params(request):
    dict_data = json.loads(request.body)
    print(dict_data)
    return JsonResponse({
        "status":200, 
        "msg":"POST请求成功",
        "data":dict_data
        })

'''
    post请求 客户端传给服务器一个图片 key名为file
    格式：
        file_data = request.FILES.get("file")
'''
def post_file(request):
    file_data = request.FILES.get("file")
    # file_data.name 文件名
    save_path = os.path.join(BASE_DIR, "static", "upload",file_data.name)  #保存文件路径
    with open(save_path, "wb") as f:  #保存文件
        for chunk in file_data.chunks():  #分块写入文件
            f.write(chunk)
    print(file_data)
    print(type(file_data))
    return JsonResponse({
        "status":200, 
        "msg":"POST请求成功",
        })