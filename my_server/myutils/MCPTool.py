import json
import os
from django.db import connection
from langchain_core.tools import tool
import requests
from myutils.MySQLUtil import get_conn, close_conn
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
    



