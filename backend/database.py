from datetime import datetime  
from mongodb import mongodb  
  
def save_content(user_id, topic, content_type, content_data):  
    """保存内容到 MongoDB"""  
    return mongodb.save_content(user_id, topic, content_type, content_data)  
  
def get_content(user_id, topic, content_type):  
    """从 MongoDB 获取内容"""  
    return mongodb.get_content(user_id, topic, content_type)  
  
def get_or_create_user(user_id=None):  
    """获取或创建用户"""  
    return mongodb.get_or_create_user(user_id)  
  
def update_quiz_score(user_id, topic, score):  
    """更新测验成绩"""  
    return mongodb.update_quiz_score(user_id, topic, score)  

def save_quiz_record(user_id, course, week, subtopic, record):
    """保存测验完整记录"""
    return mongodb.save_quiz_record(user_id, course, week, subtopic, record)
  
def get_user_contents(user_id):  
    """获取用户的所有内容"""  
    return mongodb.get_user_contents(user_id)

def get_quiz_records(user_id, course=None, week=None, subtopic=None):
    """根据条件获取测验记录（可按 course/week/subtopic 过滤）"""
    return mongodb.get_quiz_records(user_id, course, week, subtopic)

def delete_quiz_records(user_id, course=None, week=None, subtopic=None):
    """按条件删除测验记录"""
    return mongodb.delete_quiz_records(user_id, course, week, subtopic)

def cancel_course(user_id, topic):
    """取消学习某课程，删除与该课程相关的所有数据库数据"""
    return mongodb.delete_course_data(user_id, topic)