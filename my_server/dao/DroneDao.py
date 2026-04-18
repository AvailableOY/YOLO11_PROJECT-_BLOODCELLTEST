import ast
import sys
import os

import torch
# 获取当前脚本所在目录的父级目录（即 YOLO11_PROJECT 根目录）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(project_root))
# 存储图片检测结果
from myutils import MySQLUtil


def save_result(data):
    
    '''
        存入数据库
        这里是数据库的存储操作，我们需要手动的管理事物
        1、如果操作的数据库代码没有问题 就提交
        2、如果操作的代码有问题 就回滚
    '''
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    '''
        定义SQL 插入语句的SQL格式
        insert into 表名 values
    '''
    try:
        sql = """
            INSERT INTO `records` 
            (origin_url, result_url, conf, result, infer_time, username, create_time) 
            VALUES (%s, %s, %s, %s, %s, %s, now())
        """
        cur.execute(sql, data)
    except Exception as e:
        print(e)
    finally:
        MySQLUtil.close_conn(cur, conn)



#统计数据库中一共多少条数据   使用查询语句结合mysql中的函数count实现
def get_total():
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    #计算一共有多少数据
    sql = "select count(*) from `records`;"
    cur.execute(sql)
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    return result[0][0]


#获取数据库中的指定页数据 使用到查询语句结合mysql中的limit关键字实现
'''
    page:当前页码  
    size:每页显示多少条数据
'''
def find_data(page,size):
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    start = (page - 1) * size
    #计算一共有多少数据
    sql = "select * from `records` order by record_id desc limit %s,%s;"
    cur.execute(sql,[start,size])
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    return result

# 可视化 ---柱状图
def load_bar():
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    #计算一共有多少数据
    sql = "SELECT `create_time`,`conf` FROM `records` ORDER BY `conf` DESC LIMIT 5;"
    cur.execute(sql)
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    return result
# 可视化 ---当前柱状图
def load_current_bar():
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    #计算一共有多少数据
    sql = "SELECT `result` FROM `records` ORDER BY `create_time` DESC LIMIT 1;"
    cur.execute(sql)
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    return result

# 可视化 ---饼状图
def load_pie():
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    #计算一共有多少数据
    sql = "SELECT `create_time`,`conf` FROM `records` ORDER BY `conf` DESC LIMIT 5;"
    cur.execute(sql)
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    return result

# 获取今日的血细胞总数
def get_today_count():
    # 血细胞类型统计字典（使用中文名称作为 key，与数据库一致）
    total_counts = {
        "红细胞": 0,
        "嗜碱性粒细胞": 0,
        "杆状核中性粒细胞": 0,
        "嗜酸性粒细胞": 0,
        "有核红细胞": 0,
        "淋巴细胞": 0,
        "晚幼粒细胞": 0,
        "单核细胞": 0,
        "中幼粒细胞": 0,
        "血小板": 0,
        "早幼粒细胞": 0,
        "分叶核中性粒细胞": 0,
    }
    
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    
    # 查询今天的所有检测结果
    sql = "SELECT `result` FROM `records` WHERE TO_DAYS(create_time) = TO_DAYS(NOW());"
    cur.execute(sql)
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    
    # 提取 result 字段
    result = [res[0] for res in result]
    
    # 对 result 的每一行进行转换并累加
    try:
        for res in result:
            # 如果 result 是字符串格式的字典，需要转换
            if isinstance(res, str):
                res = ast.literal_eval(res)
            # 遍历字典，累加到 total_counts
            for key, value in res.items():
                if key in total_counts:  # 🔥 只统计我们关注的血细胞类型
                    total_counts[key] += value
                # 如果遇到未知类型，可选择忽略或记录日志
                # else:
                #     print(f"⚠️ 未知血细胞类型: {key}")
    except Exception as e:
        print(f"⚠️ 血细胞统计解析错误：{e}")
    
    # 🔥 计算今天检测的血细胞总数（所有类型相加）
    total_num = sum(total_counts.values())
    
    
    return total_num

# 获取今天检测的异常血细胞数量
def get_today_pathological_count():
    #  病症细胞列表（健康成人外周血不应出现）
    pathological_cells = [
        "有核红细胞",      # 出现=骨髓代偿/应激/浸润
        "晚幼粒细胞",      # 出现=感染/血液病
        "中幼粒细胞",      # 出现=高度怀疑白血病等
        "早幼粒细胞",      # 出现=急性白血病高危信号
    ]
    
    # 异常细胞统计字典
    pathological_counts = {cell: 0 for cell in pathological_cells}
    
    conn = MySQLUtil.get_conn()
    cur = conn.cursor()
    
    # 查询今天的所有检测结果
    sql = "SELECT `result` FROM `records` WHERE TO_DAYS(create_time) = TO_DAYS(NOW());"
    cur.execute(sql)
    result = cur.fetchall()
    MySQLUtil.close_conn(cur, conn)
    
    # 提取 result 字段
    result = [res[0] for res in result]
    
    # 对 result 的每一行进行转换并累加
    try:
        for res in result:
            # 如果 result 是字符串格式的字典，需要转换
            if isinstance(res, str):
                res = ast.literal_eval(res)
            # 遍历字典，只统计异常细胞
            for key, value in res.items():
                if key in pathological_counts:
                    pathological_counts[key] += value
    except Exception as e:
        print(f"⚠️ 异常细胞统计解析错误：{e}")
    
    total_pathological = sum(pathological_counts.values())
    
    
    return total_pathological

# 获取GPU状态
def get_gpu_status():
    if torch.cuda.is_available():
        gpu_usage_percent = 0.0
        # 2. 获取第 0 块显卡的总显存 (单位：Byte)
        total_memory = torch.cuda.get_device_properties(0).total_memory
        
        # 3. 获取当前 PyTorch 引擎已经占用（保留）的显存
        reserved_memory = torch.cuda.memory_reserved(0)
        
        # 4. 计算占比百分比，并保留一位小数
        if total_memory > 0:
            gpu_usage_percent = round((reserved_memory / total_memory) * 100, 1)
        
        engine_status = "GPU 推理就绪"
    else:
        # 如果没检测到显卡，说明当前 YOLO 是在用 CPU 强跑
        engine_status = "CPU 推理中"
    return gpu_usage_percent,engine_status


if __name__ == '__main__':
    print(load_bar())