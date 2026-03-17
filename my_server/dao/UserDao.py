'''
    操作数据库
'''
from myutils import MySQLUtil
def login(username):
    #通过账号查询数据库数据 如果数据不存在 表示账号不存在
    conn = MySQLUtil.get_conn()
    '''
        获取游标对象
    '''
    cur = conn.cursor()
    sql = "SELECT * FROM `user` WHERE `username` = %s;"
    '''
        游标对象.execute方法 表示执行SQL语句 execute方法参数
        1. SQL语句
        2. SQL语句的参数 如果有%s占位符 就按照占位符的顺序依次赋值
         这些参数必须放在列表字典元组中
    '''
    cur.execute(sql, [username])
    # 获取结果
    '''
        fetchall() 获取所有结果
    '''
    result = cur.fetchall()

    # 关闭资源
    MySQLUtil.close_conn(cur,conn)

    # 返回结果
    return result

if __name__ == '__main__':
    print(login("陶喆"))