from functools import wraps
import time

'''
时间戳装饰器
'''

def time_counter(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        start_time = time.perf_counter()
        result = func(*args,**kwargs)
        end_time = time.perf_counter()
        cost_t = end_time - start_time
        return result,cost_t
    return wrapper