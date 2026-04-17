import json
import os
from django.db import connection
from langchain_core.tools import tool
import requests
from myutils.MySQLUtil import get_conn, close_conn
from service import ReportService as rs
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

@tool
def get_weather(location: str) -> str:
    """
    获取指定城市的天气
    :param location: 城市名称
    :return: str
    """
    print("城市：", location)
    APIKey = "650f7b3e859077d9257fadfdcf09700d"
    response = requests.get(
        f"https://restapi.amap.com/v3/weather/weatherInfo?key={APIKey}&city={location}&extensions=all"
    )
    if response.status_code == 200:  # 判断请求是否成功
        weather_data = response.json()
        print(weather_data)
        return weather_data["forecasts"]  # 获取请求得到的数据，并返回
    else:
        return f"Error:{response.status_code},{response.text}"  # 打印错误信息
    


@tool
def query_blood_cell_records(query_type: str, record_id: int = None, limit: int = 5) -> str:
    """
    这是一个用于查询显微血细胞检测数据库的工具。
    当用户询问历史检测记录、最新的检测结果、或者特定ID的记录时，必须调用此工具。
    
    参数:
    - query_type (str): 查询类型。可选值："latest" (查询最新的检测记录), "by_id" (根据记录ID查询单条数据)。
    - record_id (int, optional): 记录ID。如果 query_type 是 "by_id"，则必须提供此参数。
    - limit (int, optional): 返回的记录数量，默认返回最新 5 条。
    """
    conn = None
    cursor = None
    try:
        print(f"收到查询指令 - 类型: {query_type}, ID: {record_id}, 数量: {limit}")
        
        # 💡 2. 使用你自己的工具获取连接和游标
        conn = get_conn()
        cursor = conn.cursor()
        
        # 💡 3. 必须在 SELECT 中明确把医生姓名和检测时间查出来！
        # 注意：这里的 doctor_name 和 create_time 需要替换成你数据库里真实的英文字段名！
        base_sql = "SELECT record_id, origin_url, result_url, conf, result, username, create_time FROM records"
        
        if query_type == "latest":
            sql = f"{base_sql} ORDER BY record_id DESC LIMIT %s"
            cursor.execute(sql, [limit])
        elif query_type == "by_id" and record_id is not None:
            sql = f"{base_sql} WHERE record_id = %s"
            cursor.execute(sql, [record_id])
        else:
            return "查询参数错误：请明确指定是查询 'latest' 还是 'by_id'，并提供必要的参数。"

        rows = cursor.fetchall()
        if not rows:
            return "数据库中未查询到相关的检测记录。"

        result_list = []
        for row in rows:
            origin_img_md = f"![原始图片](/{row[1]})" if row[1] else "无"
            result_img_md = f"![检测结果](/{row[2]})" if row[2] else "无"
            res_dict = {
                "记录ID": row[0],
                "原始图片路径": origin_img_md,
                "结果图片路径": result_img_md,
                "平均置信度": row[3],
                "检测详情": row[4], 
                "医生姓名": row[5],
                "检测时间": str(row[6]) if row[6] else "未知时间" 
            }
            result_list.append(res_dict)
            
        print(f"成功查询到 {len(result_list)} 条结果。")
        return json.dumps(result_list, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"数据库查询执行失败: {str(e)}"
        print(error_msg)
        return error_msg
    finally:
        # 💡 5. 确保无论是否报错，都能调用你的工具安全关闭数据库连接
        if cursor and conn:
            close_conn(cursor, conn)
    


@tool
def generate_medical_report_tool(record_id: str) -> str:
    """
    这是一个撰写专业医学病理报告的工具。
    当用户要求“生成报告”、“写一份报告”、“分析最新记录”时，必须调用此工具。
    参数:
    - record_id (str): 检测记录的 ID。如果用户要求生成“最新的”报告，请直接传入 "latest"。严禁传入 '<record_id>' 等占位符。
    """
    try:
        actual_id = None
        
        # 💡 修改 2：智能处理 LLM 传来的参数
        # 如果大模型传了 'latest'，或者乱传了非数字的占位符（如 '<record_id>'）
        if record_id.lower() == "latest" or not record_id.isdigit():
            # 工具自己去数据库查最新的一条 ID
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT record_id FROM records ORDER BY record_id DESC LIMIT 1")
            row = cursor.fetchone()
            close_conn(cursor, conn)
            
            if row:
                actual_id = row[0]
                print(f"AI 自动拦截占位符，已查找到最新记录 ID 为: {actual_id}")
            else:
                return "数据库中目前没有任何检测记录，无法生成报告。"
        else:
            # 如果大模型乖乖传了数字字符（比如 "71"），就转成整数
            actual_id = int(record_id)
            
        print(f"AI 正在为记录 {actual_id} 生成病理报告...")
        
        # 调用生成逻辑
        report_md = rs.generate_ai_report(actual_id)
        
        return f"报告已生成完毕。请将以下 Markdown 格式的报告内容原样、完整地输出给用户，不要做任何删减：\n\n{report_md}"
        
    except Exception as e:
        return f"报告生成过程中出现异常: {str(e)}"


# 获取当前文件 (MCPTool.py) 的上一级再上一级的绝对路径，也就是 my_server/ 的根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 向量数据库的真实路径 (my_server/chroma_medical_db)
DB_DIR = os.path.join(BASE_DIR, "chroma_medical_db")

# 本地 Embedding 模型的绝对路径 (你刚才下载好的)
LOCAL_MODEL_PATH = "D:/Python_Project/huggingface_cache/bge-large-zh-v1.5"


# ==========================================
# 2. 初始化加载大模型与本地数据库
# ==========================================
print("正在加载 RAG 医疗知识库...")
try:
    # 加载本地词嵌入模型 (使用 cpu 即可，因为只是检索向量)
    embeddings = HuggingFaceBgeEmbeddings(
        model_name=LOCAL_MODEL_PATH,
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True}
    )

    # 挂载本地 Chroma 数据库
    vectorstore = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings
    )
    print("✅ RAG 医疗知识库加载完毕！")
except Exception as e:
    print(f"❌ RAG 知识库加载失败，请检查路径: {e}")
    vectorstore = None


# ==========================================
# 3. 封装给大模型调用的工具 (Tool)
# ==========================================
@tool
def search_medical_guidelines(query: str) -> str:
    """
    医学知识库检索工具。
    当用户询问血细胞指标偏高、偏低的原因、临床意义，或者请求出具医学解读与建议时，必须调用此工具。
    输入参数为用户的具体病理问题，例如：“血小板增多可能是什么疾病导致的？”或“红细胞偏少的原因”
    返回结果为《临床血液学检验指南》中的权威文献片段。
    """
    if vectorstore is None:
        return "系统内部错误：医疗知识库未成功加载，无法检索指南。"

    try:
        # 在向量数据库中检索最相关的 3 个医学文献块
        docs = vectorstore.similarity_search(query, k=3)
        print(f"AI 正在向医疗知识库检索 {len(docs)} 条结果...")
        
        if not docs:
            return "知识库中未检索到与该问题相关的医学指南信息。"

        # 将检索到的片段拼接成一段结构化的长文本
        context_parts = []
        for i, doc in enumerate(docs):
            context_parts.append(f"[文献片段 {i+1}]:\n{doc.page_content}")

        context = "\n\n".join(context_parts)
        
        # 加上前缀提示，告诉大模型这是权威指南，让它基于此回答
        return f"以下是系统从《临床血液学检验指南》中检索到的权威内容，请严格结合这些内容为患者解答：\n\n{context}"
        
    except Exception as e:
        return f"知识库检索过程发生异常: {str(e)}"