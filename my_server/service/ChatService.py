import json
import os
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from django.views.decorators.csrf import csrf_exempt
from myutils.MCPTool import get_weather,query_blood_cell_records, generate_medical_report_tool,search_medical_guidelines
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage,SystemMessage
from dotenv import load_dotenv
load_dotenv()
from myutils.MySQLUtil import get_conn, close_conn
import uuid



TOOL_CN_NAMES = {
    "search_medical_guidelines": "本地医疗知识库 (RAG)",
    "query_blood_cell_records": "血细胞记录查库",
    "generate_medical_report_tool": "医学报告生成",
    "get_weather": "实时天气查询"
}


# 💡 新增 1：保存单条聊天记录到数据库
def save_chat_message(session_id, role, content):
    if not content: # 如果内容为空就不保存
        return
    conn = get_conn()
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)"
        cursor.execute(sql, [session_id, role, content])
        conn.commit()
    except Exception as e:
        print(f"保存聊天记录失败: {e}")
    finally:
        close_conn(cursor, conn)

# 💡 新增 2：根据 session_id 获取历史记录给前端展示
def get_chat_history(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return JsonResponse({"status": 400, "error": "缺少 session_id"})
        
    conn = get_conn()
    cursor = conn.cursor()
    try:
        sql = "SELECT role, content, create_time FROM chat_messages WHERE session_id = %s ORDER BY id ASC"
        cursor.execute(sql, [session_id])
        rows = cursor.fetchall()
        
        history_list = []
        for row in rows:
            history_list.append({
                "role": row[0],
                "content": row[1],
                "time": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else ""
            })
            
        return JsonResponse({"status": 200, "data": history_list})
    except Exception as e:
        return JsonResponse({"status": 500, "error": str(e)})
    finally:
        close_conn(cursor, conn)

# 💡 获取所有历史会话的列表
def get_session_list(request):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        # 使用 GROUP BY 按 session_id 分组，取每组的最早时间，以及对应的第一句话作为标题
        sql = """
            SELECT session_id, MIN(content) as title, MAX(create_time) as last_time 
            FROM chat_messages 
            WHERE role = 'user' 
            GROUP BY session_id 
            ORDER BY last_time DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        session_list = []
        for row in rows:
            title = row[1]
            # 如果标题太长，截取前 15 个字符加上省略号
            if len(title) > 15:
                title = title[:15] + "..."
                
            session_list.append({
                "session_id": row[0],
                "title": title,
                "time": row[2].strftime("%m-%d %H:%M") if row[2] else ""
            })
            
        return JsonResponse({"status": 200, "data": session_list})
    except Exception as e:
        return JsonResponse({"status": 500, "error": str(e)})
    finally:
        close_conn(cursor, conn)

# 2. 读取具体的 API Key
API_KEY = os.getenv("DASHSCOPE_API_KEY")
# 调用模型
model = ChatOpenAI(
    model="qwen-max-2025-01-25",
    api_key=API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
tools = [get_weather,query_blood_cell_records, generate_medical_report_tool,search_medical_guidelines]
model_with_tools = model.bind_tools(tools=tools)
@csrf_exempt
def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        user_input = data.get("question", "")
        # 传入一个 session_id
        session_id = data.get("session_id", str(uuid.uuid4()))
        
        # 💡 第一步：用户的提问在此处进行唯一一次入库处理
        save_chat_message(session_id, "user", user_input)
    except Exception as e:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 定义系统提示词 (System Prompt)
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

        ai_msg_accumulator = None
        # 💡 准备一个变量，用来“吸星大法”般地收集 AI 吐出的每一个碎片字符
        final_ai_text = ""  

        try:
            # 1. 第一次调用：使用 stream()
            for chunk in model_with_tools.stream(messages):
                if ai_msg_accumulator is None:
                    ai_msg_accumulator = chunk
                else:
                    ai_msg_accumulator += chunk
                
                if chunk.content:
                    final_ai_text += chunk.content # 收集文字碎片
                    yield f"data: {json.dumps({'content': chunk.content})}\n\n"

            messages.append(ai_msg_accumulator)

            # 2. 拦截并处理工具调用
            if hasattr(ai_msg_accumulator, 'tool_calls') and ai_msg_accumulator.tool_calls:
                available_tools = {t.name.lower(): t for t in tools}
                
                for tool_call in ai_msg_accumulator.tool_calls:
                    tool_name = tool_call["name"].lower()

                    # 把工具名称和检索词提取出来
                    # 解析参数，让它变成干净的字符串，比如把 {'query': '红细胞偏低'} 变成 '红细胞偏低'
                    args_dict = tool_call.get("args", {})
                    args_str = ", ".join([str(v) for v in args_dict.values()]) if args_dict else "无参数"
                    
                    # 实时推送到前端告诉用户：“我正在用工具查东西！”
                    readable_name = TOOL_CN_NAMES.get(tool_name, tool_name)
                    yield f"data: {json.dumps({'tool_name': tool_name, 'readable_name':readable_name,'tool_args': args_str})}\n\n"
                    
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
                    print(messages)
                    if chunk.content:
                        final_ai_text += chunk.content # 收集工具分析后的文字碎片
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"
                        
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"流式输出中断异常: {e}")
            error_msg = "\n\n(⚠️ AI 生成意外中断)"
            final_ai_text += error_msg
            yield f"data: {json.dumps({'content': error_msg})}\n\n"
            
        finally:
            # 💡 最终步：不管中间发没发生报错、用没用工具，只要 AI 说过话，就在这里统一入库！
            # 注意角色要和数据库/前端约定好，如果前端写的是 'ai'，这里也要传 'ai'
            if final_ai_text.strip():
                save_chat_message(session_id, "ai", final_ai_text)

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response