'''
    数据库的连接 关闭工具
'''

import pymysql
# 连接数据库

def get_conn():
    return pymysql.connect(host="localhost",
                            user="root", 
                            port=3306,
                            password="root", 
                            database="aiyolo",  #数据库名称
                            charset="utf8"
                        )

# 关闭数据库连接
def close_conn(cursor,conn):
    cursor.close()
    conn.close()

if __name__ == '__main__':
    conn = get_conn()
    print(conn)