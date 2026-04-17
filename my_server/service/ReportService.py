import os
import ast
import json
from myutils.MySQLUtil import get_conn, close_conn
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

# 加载环境变量中的 API_KEY
load_dotenv()
API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 初始化大模型 (使用你在聊天系统里配置的模型)
model = ChatOpenAI(
    model="qwen-max-2025-01-25",
    api_key=API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def generate_ai_report(record_id):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        # 1. 从数据库查出当前记录的所有信息
        sql = "SELECT record_id, conf, result, username, create_time FROM records WHERE record_id = %s"
        cursor.execute(sql, [record_id])
        row = cursor.fetchone()
        
        if not row:
            raise Exception("未找到对应的检测记录")

        rec_id = row[0]
        conf = row[1]
        result_str = row[2]
        username = row[3] if row[3] else "未知医生"
        create_time = row[4]

        # 2. 解析细胞数据
        try:
            result_dict = ast.literal_eval(result_str)
        except Exception:
            result_dict = {}

        # 3. 构造给大模型的 Prompt (提示词)
        # 把枯燥的数据变成大模型能理解的上下文
        data_context = f"""
        【患者样本信息】
        - 记录编号：{rec_id}
        - 检验医师：{username}
        - 检测时间：{create_time}
        - AI模型平均置信度：{conf}

        【各类细胞检测数量】
        {json.dumps(result_dict, ensure_ascii=False, indent=2)}
        """

        system_prompt = """你是一位经验丰富的临床血液病理学专家。
你的任务是根据提供的显微血细胞AI检测数据，撰写一份结构化、专业的检验报告。
请直接使用 Markdown 格式输出，报告必须包含以下结构：
1. 📝 **基本信息** (直接使用提供的数据)
2. 📊 **数据汇总** (以清晰的无边框列表展示各细胞数量)
3. 🩺 **形态学初步分析** (根据细胞数量分布，分析是否存在异常，例如早幼/中幼粒细胞过多通常提示病理异常)
4. ⚠️ **临床建议与免责声明** (必须强调本报告为AI辅助生成，不可替代执业医师诊断)
"""

        # 4. 调用大模型生成报告
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请根据以下数据生成诊断报告：\n{data_context}")
        ]
        
        # 获取大模型的回答文本
        ai_response = model.invoke(messages)
        report_markdown = ai_response.content
        
        # 将生成的 Markdown 文本返回
        return report_markdown

    except Exception as e:
        print(f"AI报告生成失败: {e}")
        return f"生成报告时发生错误：{str(e)}"
    finally:
        close_conn(cursor, conn)