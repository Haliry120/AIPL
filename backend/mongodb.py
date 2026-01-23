from pymongo import MongoClient  
from datetime import datetime  
import os  
from dotenv import load_dotenv  
  
load_dotenv()  
  
class MongoDB:  
    def __init__(self):  
        self.client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))  
        self.db = self.client['aipl_database']  
        self.users = self.db['users']  
        self.contents = self.db['learning_contents']  
        self.stats = self.db['learning_stats']  
        self.quiz_records = self.db['quiz_records']
      
    def get_or_create_user(self, user_id=None):  
        """获取或创建用户"""  
        if not user_id:  
            user_id = f"temp_{datetime.now().timestamp()}"  
          
        user = self.users.find_one({"user_id": user_id})  
        if not user:  
            user = {  
                "user_id": user_id,  
                "created_at": datetime.utcnow(),  
                "updated_at": datetime.utcnow(),  
                "is_temporary": True  
            }  
            self.users.insert_one(user)  
          
        return user  
    
    def save_content(self, user_id, topic, content_type, content_data, version=1):  
        """保存学习内容"""  
        # 检查是否已存在相同内容  
        existing = self.contents.find_one({  
            "user_id": user_id,  
            "topic": topic,  
            "content_type": content_type  
        })  
          
        content = {  
            "user_id": user_id,  
            "topic": topic,  
            "content_type": content_type,  
            "content_data": content_data,  
            "version": version,  
            "updated_at": datetime.utcnow()  
        }  
          
        if existing:  
            self.contents.update_one(  
                {"_id": existing["_id"]},  
                {"$set": content}  
            )  
        else:  
            content["created_at"] = datetime.utcnow()  
            self.contents.insert_one(content)  
      
    def get_content(self, user_id, topic, content_type):  
        """获取学习内容"""  
        return self.contents.find_one({  
            "user_id": user_id,  
            "topic": topic,  
            "content_type": content_type  
        })  
    
    def update_quiz_score(self, user_id, topic, score):  
        """更新测验成绩"""  
        stats = self.stats.find_one({"user_id": user_id, "topic": topic})  
        if stats:  
            self.stats.update_one(  
                {"_id": stats["_id"]},  
                {  
                    "$push": {"quiz_scores": score},  
                    "$set": {"last_activity": datetime.utcnow()}  
                }  
            )  
        else:  
            stats = {  
                "user_id": user_id,  
                "topic": topic,  
                "quiz_scores": [score],  
                "completion_rate": 0,  
                "last_activity": datetime.utcnow()  
            }  
            self.stats.insert_one(stats)  

    def save_quiz_record(self, user_id, course, week, subtopic, record):
        """保存单次测验记录到 quiz_records 集合"""
        doc = {
            "user_id": user_id,
            "course": course,
            "week": week,
            "subtopic": subtopic,
            "record": record,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        self.quiz_records.insert_one(doc)
        return str(doc.get('_id'))

    def get_quiz_records(self, user_id, course=None, week=None, subtopic=None):
        """根据筛选条件返回测验记录列表（序列化日期和 _id）"""
        query = {"user_id": user_id}
        if course:
            query["course"] = course
        if week:
            query["week"] = week
        if subtopic:
            query["subtopic"] = subtopic

        docs = list(self.quiz_records.find(query).sort([("created_at", -1)]))
        # 序列化
        for d in docs:
            d['id'] = str(d.get('_id'))
            if 'created_at' in d:
                d['created_at'] = d['created_at'].isoformat()
            if 'updated_at' in d:
                d['updated_at'] = d['updated_at'].isoformat()
        return docs

    def delete_quiz_records(self, user_id, course=None, week=None, subtopic=None):
        """按条件删除测验记录，默认仅删除当前用户的数据"""
        query = {"user_id": user_id}
        if course:
            query["course"] = course
        if week:
            query["week"] = week
        if subtopic:
            query["subtopic"] = subtopic

        result = self.quiz_records.delete_many(query)
        return {"deleted_count": result.deleted_count}

    def get_user_contents(self, user_id):
        """获取用户的所有学习内容（返回可序列化的列表）"""
        docs = list(self.contents.find({"user_id": user_id}))
        # 将 ObjectId 和 datetime 等不可序列化字段转换为字符串
        for d in docs:
            d['id'] = str(d.get('_id'))
            if 'created_at' in d:
                d['created_at'] = d['created_at'].isoformat()
            if 'updated_at' in d:
                d['updated_at'] = d['updated_at'].isoformat()
        return docs

    def delete_course_data(self, user_id, topic):
        """删除用户与某课程相关的所有数据（contents 与 stats）"""
        # 删除 learning_contents 中与 user_id 和 topic 匹配的文档
        contents_result = self.contents.delete_many({"user_id": user_id, "topic": topic})
        # 删除 learning_stats 中与 user_id 和 topic 匹配的文档
        stats_result = self.stats.delete_many({"user_id": user_id, "topic": topic})
        # 删除 quiz_records 中与 user_id 和 course 匹配的文档
        quiz_result = self.quiz_records.delete_many({"user_id": user_id, "course": topic})

        return {
            "deleted_contents_count": contents_result.deleted_count,
            "deleted_stats_count": stats_result.deleted_count,
            "deleted_quiz_count": quiz_result.deleted_count
        }
  
# 全局实例  
mongodb = MongoDB()