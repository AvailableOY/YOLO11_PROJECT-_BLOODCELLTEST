'''
    逻辑处理代码
'''
from dao import UserDao as ud

def login(dict_data):
    #获取账号密码
    username = dict_data.get("username")
    password = dict_data.get("password")
    #调用login方法 查询数据库
    result = ud.login(username)
    '''
        有数据账号存在
        无则反之
    '''

    if len(result) == 0:
        return {"status": 500,
                 "msg": "账号不存在"
            }
    
    '''
        判断密码
        传过来的密码和账号查询出来的密码账号对比
    '''
    if password != result[0][2]:
        return {"status": 500,
                 "msg": "密码错误"
            }
    return{
        "status": 200,
        "msg": "登录成功",
    }