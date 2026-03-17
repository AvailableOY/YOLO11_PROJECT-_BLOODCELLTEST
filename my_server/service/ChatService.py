import json
import os
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from django.views.decorators.csrf import csrf_exempt
from myutils.MCPTool import get_weather,query_blood_cell_records
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage,SystemMessage
from dotenv import load_dotenv
load_dotenv()

# 2. 读取具体的 API Key
API_KEY = os.getenv("DASHSCOPE_API_KEY")
# 调用模型
model = ChatOpenAI(
    model="qwen-max-2025-01-25",
    api_key=API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
tools = [get_weather,query_blood_cell_records]
model_with_tools = model.bind_tools(tools=tools)
@csrf_exempt
def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        user_input = data.get("question", "")
    except Exception as e:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 💡 1. 定义系统提示词 (System Prompt)
    # 这段话决定了 AI 的语气、专业度和边界
    SYSTEM_PROMPT = """你是一个专门为【显微血细胞智能检测系统】服务的医学病理辅助AI助手。
                    你的主要职责是：
                    1. 根据系统提供的红细胞、白细胞、血小板等目标检测数量和形态数据，进行初步的生理指标解读。
                    2. 回答医生或检验员关于血液学、细胞学相关的专业问题。
                    3. 语气要严谨、客观、专业。
                    4. 必须在适当的时候提醒：你的分析仅供辅助参考，最终的临床诊断结果必须由具有执业资格的医生决定。
                    5. 【重要指令】：当调用数据库工具获取到“原始图片”或“结果图片”的 Markdown 链接（如 ![检测结果](/static/...)）时，你必须在回复中原样输出这些 Markdown 语法，以便在聊天界面中直接为用户渲染出图片！千万不要省略图片链接。
    """
    def event_stream():
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_input)
        ]
        
        # 1. 第一次调用：使用 stream() 替换 invoke()
        ai_msg_accumulator = None
        
        for chunk in model_with_tools.stream(messages):
            # 将流式碎片累加拼接，LangChain 会自动处理文本和工具参数的合并
            if ai_msg_accumulator is None:
                ai_msg_accumulator = chunk
            else:
                ai_msg_accumulator += chunk
            
            # 如果此时模型输出的是普通文本，直接实时发给前端
            if chunk.content:
                yield f"data: {json.dumps({'content': chunk.content})}\n\n"

        # 将第一轮完整的回答（包含可能的工具调用指令）存入历史记录
        messages.append(ai_msg_accumulator)

        # 2. 拦截并处理工具调用
        if ai_msg_accumulator.tool_calls:
            # 💡 终极优雅写法：直接遍历你定义的 tools 列表，自动生成映射字典
            # 这样以后你往 tools 列表里加 100 个工具，这里一行代码都不用改！
            available_tools = {t.name.lower(): t for t in tools}
            
            for tool_call in ai_msg_accumulator.tool_calls:
                tool_name = tool_call["name"].lower()
                
                if tool_name in available_tools:
                    selected_tool = available_tools[tool_name]
                    tool_output = selected_tool.invoke(tool_call["args"])
                    
                    messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))
                else:
                    messages.append(ToolMessage(
                        content=f"Error: Tool {tool_name} is not available.", 
                        tool_call_id=tool_call["id"]
                    ))
            # 3. 第二次调用：将工具结果传回给模型，并获取最终的流式分析结果
            for chunk in model_with_tools.stream(messages):
                if chunk.content:
                    yield f"data: {json.dumps({'content': chunk.content})}\n\n"

        yield "data: [DONE]\n\n"
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # 禁用 Nginx 缓冲，防止流式输出被卡住
    return response