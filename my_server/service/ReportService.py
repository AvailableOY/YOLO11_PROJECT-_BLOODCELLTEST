import os
import ast
from datetime import datetime
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from myutils.MySQLUtil import get_conn, close_conn

# 获取 Django 项目的根目录 (my_server 文件夹)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_report(record_id):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        # 1. 查询数据库 (已将 doctor_name 修改为 user_name)
        sql = "SELECT record_id, origin_url, result_url, conf, result, user_name, create_time FROM records WHERE record_id = %s"
        cursor.execute(sql, [record_id])
        row = cursor.fetchone()
        
        if not row:
            raise Exception("未找到对应的检测记录")

        # 解包数据，让代码更易读
        rec_id = row[0]
        origin_url = row[1]
        result_url = row[2]
        conf = row[3]
        result_str = row[4]
        user_name = row[5] if row[5] else "未知用户"
        create_time = row[6]

        # 2. 解析类别数量字典
        try:
            # 将数据库中的 "{'红细胞': 18, '血小板': 1...}" 转换为真实的 Python 字典
            result_dict = ast.literal_eval(result_str)
        except Exception:
            result_dict = {}

        # 3. 配置文件路径
        # 💡 修改点 1：模板路径变更为 my_server/static/report_template/report_template.docx
        template_path = os.path.join(BASE_DIR, 'static', 'report_template', 'report_template.docx')
        
        # 确保输出目录存在
        output_dir = os.path.join(BASE_DIR, 'static', 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 💡 修改点 2：按 年月日时分_username 的格式生成文件名 (例如: 202603081430_admin.docx)
        # 注意：文件名尽量避免使用中文字符作为时间格式，以免前端下载时因编码问题导致乱码
        time_str = datetime.now().strftime("%Y%m%d%H%M") 
        file_name = f"{time_str}_{user_name}.docx"
        output_path = os.path.join(output_dir, file_name)
        
        # 4. 组装数据并渲染 Word
        doc = DocxTemplate(template_path)
        
        # 处理图片路径 (将相对路径转为绝对路径)
        img_local_path = os.path.join(BASE_DIR, str(result_url).replace('/', os.sep)) 
        
        if os.path.exists(img_local_path):
            img_obj = InlineImage(doc, img_local_path, width=Mm(120))
        else:
            img_obj = "【图片丢失或未生成】"

        # 💡 修改点 3：装配上下文数据
        context = {
            'record_id': rec_id,
            'create_time': str(create_time) if create_time else "未知",
            'user_name': user_name,
            'conf': conf,
            'result_image': img_obj,
            
            # 定义所有你可能用到的细胞种类，如果某次检测没有某种细胞，默认填 0
            '红细胞': result_dict.get('红细胞', 0),
            '嗜碱性粒细胞': result_dict.get('嗜碱性粒细胞', 0),
            '血小板': result_dict.get('血小板', 0),
            '有核红细胞': result_dict.get('有核红细胞', 0),
            '晚幼粒细胞': result_dict.get('晚幼粒细胞', 0),
            '中幼粒细胞': result_dict.get('中幼粒细胞', 0),
            '早幼粒细胞': result_dict.get('早幼粒细胞', 0),
            
            'ai_suggestion': "该样本分析完毕。注意：分析结果仅供辅助参考，临床确诊请结合患者实际体征及其他生理生化指标综合判定。"
        }

        # 渲染并保存
        doc.render(context)
        doc.save(output_path)
        
        return output_path

    except Exception as e:
        print(f"Word报告生成失败: {e}")
        return None
    finally:
        # 确保关闭数据库连接
        if cursor and conn:
            close_conn(cursor, conn)