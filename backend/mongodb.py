from pymongo import MongoClient  
from datetime import datetime  
import os  
from dotenv import load_dotenv  
import hashlib
import uuid
import ast
import re
from bson import ObjectId

load_dotenv()

class MongoDB:
    def __init__(self):  
        uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        server_timeout = int(os.getenv('MONGO_SERVER_SELECTION_TIMEOUT_MS', '5000'))
        connect_timeout = int(os.getenv('MONGO_CONNECT_TIMEOUT_MS', '5000'))
        socket_timeout = int(os.getenv('MONGO_SOCKET_TIMEOUT_MS', '10000'))
        self.client = MongoClient(
            uri,
            serverSelectionTimeoutMS=server_timeout,
            connectTimeoutMS=connect_timeout,
            socketTimeoutMS=socket_timeout,
        )  
        self.db = self.client['aipl_database']
        self.users = self.db['users']
        self.contents = self.db['learning_contents']
        self.stats = self.db['learning_stats']
        self.quiz_records = self.db['quiz_records']
        self.wrong_questions = self.db['wrong_questions']
        self.redo_records = self.db['redo_records']
        self.user_profiles = self.db['user_profiles']  # 新增用户画像集合

        # 连接探测
        try:
            self.client.admin.command('ping')
        except Exception as e:
            print('[DBError] Mongo ping failed:', e)

        # 索引初始化（重复创建不会报错；unique 索引如遇历史重复数据将抛错，这里捕获并告警）
        try:
            self.users.create_index('user_id', unique=True)
        except Exception as e:
            print('[IndexWarning] users.user_id unique index creation failed:', e)
        try:
            self.users.create_index('username_lower', unique=True, sparse=True)
        except Exception as e:
            print('[IndexWarning] users.username_lower unique index creation failed:', e)
        try:
            self.users.create_index('email_lower', unique=True, sparse=True)
        except Exception as e:
            print('[IndexWarning] users.email_lower unique index creation failed:', e)
        try:
            self.contents.create_index([
                ('user_id', 1), ('topic', 1), ('content_type', 1)
            ], unique=True)
        except Exception as e:
            print('[IndexWarning] learning_contents unique index creation failed:', e)
        try:
            self.quiz_records.create_index([
                ('user_id', 1), ('course', 1), ('week', 1), ('subtopic', 1), ('created_at', -1)
            ])
        except Exception as e:
            print('[IndexWarning] quiz_records compound index creation failed:', e)
        try:
            self.wrong_questions.create_index([
                ('user_id', 1), ('question_key', 1)
            ], unique=True)
        except Exception as e:
            print('[IndexWarning] wrong_questions unique index creation failed:', e)
        try:
            self.wrong_questions.create_index([
                ('user_id', 1), ('course', 1), ('week', 1), ('subtopic', 1), ('difficulty', 1), ('updated_at', -1)
            ])
        except Exception as e:
            print('[IndexWarning] wrong_questions filter index creation failed:', e)
        try:
            self.redo_records.create_index([
                ('user_id', 1), ('course', 1), ('week', 1), ('subtopic', 1), ('created_at', -1)
            ])
        except Exception as e:
            print('[IndexWarning] redo_records index creation failed:', e)
        try:
            self.user_profiles.create_index('user_id', unique=True)
        except Exception as e:
            print(f'[IndexWarning] user_profiles index creation failed: {e}')

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

    def create_user(self, username, email, password_hash):
        """创建注册用户（返回 user_id）"""
        user_id = f"user_{uuid.uuid4().hex}"
        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "username": username,
            "username_lower": username.lower(),
            "email": email,
            "email_lower": email.lower(),
            "password_hash": password_hash,
            "avatar_url": "",
            "prompt_templates": [],
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "is_temporary": False
        }
        self.users.insert_one(doc)
        return user_id

    def get_user_by_id(self, user_id):
        return self.users.find_one({"user_id": user_id})

    def get_user_by_identifier(self, identifier):
        if not identifier:
            return None
        ident = identifier.strip()
        if "@" in ident:
            return self.users.find_one({"email_lower": ident.lower()})
        return self.users.find_one({"username_lower": ident.lower()})

    def update_last_login(self, user_id):
        return self.users.update_one({"user_id": user_id}, {"$set": {"last_login_at": datetime.utcnow()}})

    def get_user_settings(self, user_id):
        """返回用户设置（安全字段）"""
        user = self.users.find_one(
            {"user_id": user_id},
            {
                "_id": 0,
                "user_id": 1,
                "username": 1,
                "email": 1,
                "avatar_url": 1,
                "updated_at": 1,
            },
        )
        if not user:
            return None
        if isinstance(user.get("updated_at"), datetime):
            user["updated_at"] = user["updated_at"].isoformat()
        return user

    def update_user_settings(self, user_id, username=None, avatar_url=None):
        """更新用户可编辑设置（用户名、头像）"""
        update_doc = {"updated_at": datetime.utcnow()}
        if username is not None:
            update_doc["username"] = username
            update_doc["username_lower"] = username.lower()
        if avatar_url is not None:
            update_doc["avatar_url"] = avatar_url
        return self.users.update_one({"user_id": user_id}, {"$set": update_doc})

    def update_user_password_hash(self, user_id, password_hash):
        """更新用户密码 hash"""
        return self.users.update_one(
            {"user_id": user_id},
            {"$set": {"password_hash": password_hash, "updated_at": datetime.utcnow()}},
        )

    def list_prompt_templates(self, user_id):
        user = self.users.find_one({"user_id": user_id}, {"_id": 0, "prompt_templates": 1}) or {}
        prompts = user.get("prompt_templates") or []
        now = datetime.utcnow()
        changed = False
        out = []
        for p in prompts:
            item = dict(p)
            prompt_id = item.get("id") or item.get("prompt_id") or ""
            if not prompt_id:
                prompt_id = f"prompt_{uuid.uuid4().hex}"
                changed = True
            if item.get("id") != prompt_id:
                item["id"] = prompt_id
                changed = True

            if "favorite" not in item:
                item["favorite"] = False
                changed = True
            else:
                item["favorite"] = bool(item.get("favorite"))
            if not isinstance(item.get("tags"), list):
                item["tags"] = []
                changed = True
            if isinstance(item.get("created_at"), datetime):
                item["created_at"] = item["created_at"].isoformat()
            if isinstance(item.get("updated_at"), datetime):
                item["updated_at"] = item["updated_at"].isoformat()
            out.append(item)

        if changed:
            # Migrate legacy prompt records in place so subsequent edits/toggles always have ids.
            persist_prompts = []
            for item in out:
                saved = dict(item)
                if isinstance(saved.get("created_at"), str):
                    saved["created_at"] = now
                if isinstance(saved.get("updated_at"), str):
                    saved["updated_at"] = now
                persist_prompts.append(saved)
            self.users.update_one(
                {"user_id": user_id},
                {"$set": {"prompt_templates": persist_prompts, "updated_at": now}},
            )
        return out

    def upsert_prompt_template(self, user_id, prompt_id, title, content, enabled=True, description=None, favorite=False, tags=None):
        """新增或更新用户提示词模板"""
        now = datetime.utcnow()
        user = self.users.find_one({"user_id": user_id}, {"_id": 0, "prompt_templates": 1}) or {}
        prompts = user.get("prompt_templates") or []
        safe_tags = [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
        max_templates = 60

        found = False
        for p in prompts:
            if p.get("id") == prompt_id:
                p["title"] = title
                p["content"] = content
                p["enabled"] = bool(enabled)
                p["description"] = description or ""
                p["favorite"] = bool(favorite)
                p["tags"] = safe_tags
                p["updated_at"] = now
                found = True
                break

        if not found:
            if len(prompts) >= max_templates:
                raise ValueError(f"Prompt template limit reached (max {max_templates})")
            prompts.append(
                {
                    "id": prompt_id,
                    "title": title,
                    "content": content,
                    "enabled": bool(enabled),
                    "description": description or "",
                    "favorite": bool(favorite),
                    "tags": safe_tags,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"prompt_templates": prompts, "updated_at": now}},
        )
        return prompt_id

    def delete_prompt_template(self, user_id, prompt_id):
        """删除用户提示词模板"""
        res = self.users.update_one(
            {"user_id": user_id},
            {
                "$pull": {"prompt_templates": {"id": prompt_id}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return res.modified_count
    
    def save_content(self, user_id, topic, content_type, content_data, version=1):  
        """保存学习内容（并发安全：原子 upsert）"""  
        now = datetime.utcnow()
        self.contents.update_one(
            {"user_id": user_id, "topic": topic, "content_type": content_type},
            {
                "$set": {
                    "content_data": content_data,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "topic": topic,
                    "content_type": content_type,
                    "version": version,
                    "created_at": now
                }
            },
            upsert=True
        )

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
        """保存单次测验记录到 quiz_records 集合，包含分数信息"""
        now = datetime.utcnow()
        
        # 提取分数信息（来自base.py添加的字段）
        question_scores = record.get('question_scores', {})
        total_score = record.get('total_score', 0)
        max_possible_score = record.get('max_possible_score', 0)
        score_percentage = record.get('score_percentage', 0)
        
        doc = {
            "user_id": user_id,
            "course": course,
            "week": week,
            "subtopic": subtopic,
            "record": record,
            "score_info": {  # 新增：专门存储分数信息的字段
                "total_score": total_score,
                "max_possible_score": max_possible_score,
                "score_percentage": score_percentage,
                "question_count": len(record.get('questions', [])),
                "question_scores": question_scores,
                "calculated_at": now
            },
            "created_at": now,
            "updated_at": now
        }
        result = self.quiz_records.insert_one(doc)
        return str(result.inserted_id)

    def update_quiz_record(self, record_id, record, score_info=None):
        """更新测验记录内容与分数信息"""
        now = datetime.utcnow()
        try:
            obj_id = ObjectId(record_id)
        except Exception:
            obj_id = record_id

        update_doc = {
            "record": record,
            "updated_at": now
        }
        if score_info is not None:
            score_info = dict(score_info)
            score_info["calculated_at"] = now
            update_doc["score_info"] = score_info

        return self.quiz_records.update_one({"_id": obj_id}, {"$set": update_doc})

    # 新增：获取测验记录的分数汇总信息
    def get_quiz_score_summary(self, user_id, course=None, week=None, subtopic=None):
        """获取测验记录的分数汇总信息"""
        query = {"user_id": user_id}
        if course:
            query["course"] = course
        if week:
            query["week"] = week
        if subtopic:
            query["subtopic"] = subtopic
        
        # 只返回分数相关的字段，减少数据传输
        cursor = self.quiz_records.find(query, {
            "course": 1, 
            "week": 1, 
            "subtopic": 1, 
            "score_info": 1,
            "created_at": 1,
            "_id": 1
        }).sort([("created_at", -1)])
        
        summaries = []
        for doc in cursor:
            summary = {
                "record_id": str(doc.get('_id')),
                "course": doc.get('course'),
                "week": doc.get('week'),
                "subtopic": doc.get('subtopic'),
                "created_at": doc.get('created_at').isoformat() if doc.get('created_at') else None,
            }
            
            # 添加分数信息
            score_info = doc.get('score_info', {})
            if score_info:
                summary.update({
                    "total_score": score_info.get('total_score', 0),
                    "max_possible_score": score_info.get('max_possible_score', 0),
                    "score_percentage": score_info.get('score_percentage', 0),
                    "question_count": score_info.get('question_count', 0)
                })
            
            summaries.append(summary)
        
        return summaries

    # 新增：获取用户的分数历史
    def get_user_score_history(self, user_id, course=None, limit=50):
        """获取用户的分数历史记录"""
        query = {"user_id": user_id}
        if course:
            query["course"] = course
        
        cursor = self.quiz_records.find(query, {
            "course": 1, 
            "week": 1, 
            "subtopic": 1, 
            "score_info": 1,
            "created_at": 1
        }).sort([("created_at", -1)]).limit(limit)
        
        history = []
        for doc in cursor:
            score_info = doc.get('score_info', {})
            history.append({
                "course": doc.get('course'),
                "week": doc.get('week'),
                "subtopic": doc.get('subtopic'),
                "total_score": score_info.get('total_score', 0),
                "score_percentage": score_info.get('score_percentage', 0),
                "question_count": score_info.get('question_count', 0),
                "date": doc.get('created_at').isoformat() if doc.get('created_at') else None
            })
        
        return history

    def get_quiz_records(self, user_id, course=None, week=None, subtopic=None, limit: int = 50, skip: int = 0):
        """根据筛选条件返回测验记录列表（序列化日期和 _id）"""
        query = {"user_id": user_id}
        if course:
            query["course"] = course
        if week:
            query["week"] = week
        if subtopic:
            query["subtopic"] = subtopic

        cursor = self.quiz_records.find(query).sort([("created_at", -1)]).skip(int(skip)).limit(int(limit))
        docs = list(cursor)
        # 序列化
        for d in docs:
            d['id'] = str(d.get('_id'))
            if 'created_at' in d:
                d['created_at'] = d['created_at'].isoformat()
            if 'updated_at' in d:
                d['updated_at'] = d['updated_at'].isoformat()
        return docs

    def count_quiz_records(self, user_id, course=None, week=None, subtopic=None):
        """返回测验记录总数（与 get_quiz_records 相同筛选条件）"""
        query = {"user_id": user_id}
        if course:
            query["course"] = course
        if week:
            query["week"] = week
        if subtopic:
            query["subtopic"] = subtopic
        return self.quiz_records.count_documents(query)

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

    def get_user_contents(self, user_id, limit: int = 50, skip: int = 0):
        """获取用户的所有学习内容（返回可序列化的列表，支持分页）"""
        cursor = self.contents.find({"user_id": user_id}).skip(int(skip)).limit(int(limit))
        docs = list(cursor)
        # 将 ObjectId 和 datetime 等不可序列化字段转换为字符串
        for d in docs:
            d['id'] = str(d.get('_id'))
            if 'created_at' in d:
                d['created_at'] = d['created_at'].isoformat()
            if 'updated_at' in d:
                d['updated_at'] = d['updated_at'].isoformat()
        return docs

    def count_user_contents(self, user_id):
        """返回用户内容总数"""
        return self.contents.count_documents({"user_id": user_id})

    def _extract_score_percentage(self, quiz_doc):
        score_info = quiz_doc.get('score_info') or {}
        score_pct = score_info.get('score_percentage')
        if isinstance(score_pct, (int, float)):
            return float(score_pct)

        record = quiz_doc.get('record') or {}
        total_score = record.get('total_score')
        max_score = record.get('max_possible_score')
        if isinstance(total_score, (int, float)) and isinstance(max_score, (int, float)) and max_score > 0:
            return float(total_score) * 100.0 / float(max_score)
        return None

    def get_subjects_overview(self, user_id, search_text=None, sort_mode='recent'):
        now = datetime.utcnow()
        seven_days_ago = now.timestamp() - 7 * 24 * 3600

        # 先聚合所有出现过的学科
        subjects = set()
        for doc in self.quiz_records.find({"user_id": user_id}, {"course": 1}):
            if doc.get('course'):
                subjects.add(doc.get('course'))
        for doc in self.contents.find({"user_id": user_id}, {"topic": 1}):
            if doc.get('topic'):
                subjects.add(doc.get('topic'))
        for doc in self.wrong_questions.find({"user_id": user_id}, {"course": 1}):
            if doc.get('course'):
                subjects.add(doc.get('course'))
        for doc in self.redo_records.find({"user_id": user_id}, {"course": 1}):
            if doc.get('course'):
                subjects.add(doc.get('course'))

        if search_text:
            s = str(search_text).strip().lower()
            subjects = {x for x in subjects if s in str(x).lower()}

        user_doc = self.users.find_one({"user_id": user_id}, {"subject_order": 1}) or {}
        subject_order = user_doc.get('subject_order') or []
        order_index = {name: idx for idx, name in enumerate(subject_order)}

        results = []
        for subject in subjects:
            quiz_docs = list(self.quiz_records.find(
                {"user_id": user_id, "course": subject},
                {"created_at": 1, "week": 1, "subtopic": 1, "record": 1, "score_info": 1}
            ).sort([("created_at", -1)]))

            wrong_count = self.wrong_questions.count_documents({"user_id": user_id, "course": subject})

            # 最近学习时间取 quiz/wrong/redo/content 的最大时间
            last_candidates = []
            if quiz_docs and quiz_docs[0].get('created_at'):
                last_candidates.append(quiz_docs[0].get('created_at'))

            w = self.wrong_questions.find_one(
                {"user_id": user_id, "course": subject},
                {"updated_at": 1},
                sort=[("updated_at", -1)]
            )
            if w and w.get('updated_at'):
                last_candidates.append(w.get('updated_at'))

            r = self.redo_records.find_one(
                {"user_id": user_id, "course": subject},
                {"created_at": 1},
                sort=[("created_at", -1)]
            )
            if r and r.get('created_at'):
                last_candidates.append(r.get('created_at'))

            c = self.contents.find_one(
                {"user_id": user_id, "topic": subject},
                {"updated_at": 1},
                sort=[("updated_at", -1)]
            )
            if c and c.get('updated_at'):
                last_candidates.append(c.get('updated_at'))

            last_study_at = max(last_candidates).isoformat() if last_candidates else None

            # 最近7天学习次数（以测验记录计）
            last7d_sessions = 0
            for q in quiz_docs:
                dt = q.get('created_at')
                if dt and dt.timestamp() >= seven_days_ago:
                    last7d_sessions += 1

            # 最近5次平均分
            recent_scores = []
            for q in quiz_docs:
                pct = self._extract_score_percentage(q)
                if pct is not None:
                    recent_scores.append(pct)
                if len(recent_scores) >= 5:
                    break
            avg_score_recent5 = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else None

            # 错题率：错题数 / 作答题数
            total_questions = 0
            for q in quiz_docs:
                score_info = q.get('score_info') or {}
                q_count = score_info.get('question_count')
                if isinstance(q_count, int):
                    total_questions += q_count
                else:
                    record = q.get('record') or {}
                    questions = record.get('questions') or []
                    total_questions += len(questions)
            error_rate = round((wrong_count * 100.0 / total_questions), 2) if total_questions > 0 else None

            # 进度：完成=测验出现过的 week+subtopic 唯一组合；总数=roadmap 子主题总数（若可取）
            completed_keys = set()
            for q in quiz_docs:
                wk = str(q.get('week') or '')
                st = str(q.get('subtopic') or '')
                if wk or st:
                    completed_keys.add(f"{wk}::{st}")
            progress_completed = len(completed_keys)

            progress_total = progress_completed
            roadmap_doc = self.contents.find_one({"user_id": user_id, "topic": subject, "content_type": "roadmap"}, {"content_data": 1})
            if roadmap_doc:
                cd = roadmap_doc.get('content_data') or {}
                total = 0
                if isinstance(cd, dict):
                    for _, week_obj in cd.items():
                        if isinstance(week_obj, dict):
                            subs = week_obj.get('subtopics') or []
                            if isinstance(subs, list):
                                total += len(subs)
                if total > 0:
                    progress_total = total

            # 状态标签
            status = "normal"
            if last7d_sessions == 0:
                status = "inactive"
            elif error_rate is not None and error_rate >= 35:
                status = "review"
            elif len(recent_scores) >= 3 and recent_scores[0] > recent_scores[-1]:
                status = "improving"

            results.append({
                "subject": subject,
                "lastStudyAt": last_study_at,
                "progressCompleted": progress_completed,
                "progressTotal": progress_total,
                "last7dSessions": last7d_sessions,
                "avgScoreRecent5": avg_score_recent5,
                "errorRate": error_rate,
                "status": status,
                "customOrder": order_index.get(subject),
            })

        if sort_mode == 'custom':
            def custom_key(item):
                idx = item.get('customOrder')
                # 新增学科（无顺序）默认排最上面
                if idx is None:
                    return (-1, item.get('subject', ''))
                return (idx, item.get('subject', ''))
            results.sort(key=custom_key)
        else:
            results.sort(key=lambda x: x.get('lastStudyAt') or '', reverse=True)

        return results

    def set_subject_order(self, user_id, order_list):
        safe_order = [str(x) for x in (order_list or []) if str(x).strip()]
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"subject_order": safe_order, "updated_at": datetime.utcnow()}},
            upsert=False
        )
        return safe_order

    def get_subject_detail(self, user_id, subject):
        quiz_docs = list(self.quiz_records.find(
            {"user_id": user_id, "course": subject},
            {"created_at": 1, "week": 1, "subtopic": 1, "score_info": 1, "record": 1}
        ).sort([("created_at", -1)]))

        wrong_count = self.wrong_questions.count_documents({"user_id": user_id, "course": subject})
        redo_count = self.redo_records.count_documents({"user_id": user_id, "course": subject})

        progress_completed = len({f"{q.get('week')}::{q.get('subtopic')}" for q in quiz_docs})
        progress_total = progress_completed
        roadmap_doc = self.contents.find_one({"user_id": user_id, "topic": subject, "content_type": "roadmap"}, {"content_data": 1})

        def _norm_key(v):
            return str(v).strip().lower()

        def _extract_subtopic_text(raw):
            # roadmap 子主题可能是字符串、字典或字符串化字典，统一提取可读名称
            if isinstance(raw, dict):
                for k in ("subtopic", "title", "name", "topic"):
                    val = raw.get(k)
                    if val is not None and str(val).strip():
                        return str(val).strip()
                return str(raw).strip()

            text = str(raw or "").strip()
            if not text:
                return ""

            if text.startswith("{") and text.endswith("}"):
                try:
                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, dict):
                        return _extract_subtopic_text(parsed)
                except Exception:
                    pass
            return text

        def _is_numeric_like(v):
            try:
                int(str(v).strip())
                return True
            except Exception:
                return False

        def _is_generic_subtopic_label(v):
            text = str(v or "").strip().lower().replace(" ", "")
            if not text:
                return False
            # 识别常见占位命名，避免把它当作真实知识点
            patterns = [
                r"^知识点\d+$",
                r"^subtopic\d+$",
                r"^topic\d+$",
                r"^point\d+$",
                r"^第?\d+个?知识点$",
            ]
            return any(re.match(p, text) for p in patterns)

        def _extract_index_from_label(v):
            m = re.search(r"(\d+)", str(v or ""))
            return m.group(1) if m else None

        def _normalize_subtopic_key(v):
            """把 subtopic 的各种写法归一化为可映射键（如 1, 1.0, 知识点1 -> 1）。"""
            text = str(v or "").strip()
            if not text:
                return ""

            # 占位标签优先提取数字
            idx = _extract_index_from_label(text)
            if _is_generic_subtopic_label(text) and idx:
                return idx

            # 纯整数
            if _is_numeric_like(text):
                return str(int(text))

            # 浮点数字（例如 1.0）
            try:
                f = float(text)
                if f.is_integer():
                    return str(int(f))
            except Exception:
                pass

            # 混合字符串里提取首个数字（例如 subtopic_2）
            if idx:
                return idx
            return text

        # (week, subtopic) -> roadmap中的具体子主题名称
        subtopic_name_map = {}
        # subtopic索引的全局映射（week缺失时兜底）
        subtopic_index_global_map = {}
        if roadmap_doc:
            cd = roadmap_doc.get('content_data') or {}
            total = 0
            if isinstance(cd, dict):
                week_entries = list(cd.items())
            elif isinstance(cd, list):
                # 兼容 roadmap 为列表结构
                week_entries = [(str(i + 1), wk) for i, wk in enumerate(cd)]
            else:
                week_entries = []

            for week_key, week_obj in week_entries:
                if not isinstance(week_obj, dict):
                    continue
                subs = week_obj.get('subtopics') or []
                wk_key = _norm_key(week_key)
                wk_num = ''.join(ch for ch in wk_key if ch.isdigit())

                if isinstance(subs, list):
                    total += len(subs)
                    for idx, sub_name in enumerate(subs, start=1):
                        sub_name_text = _extract_subtopic_text(sub_name)
                        if not sub_name_text:
                            continue
                        idx_key = str(idx)
                        subtopic_name_map[(wk_key, idx_key)] = sub_name_text
                        if wk_num:
                            subtopic_name_map[(wk_num, idx_key)] = sub_name_text
                        subtopic_index_global_map.setdefault(idx_key, sub_name_text)
                elif isinstance(subs, dict):
                    total += len(subs)
                    auto_idx = 1
                    for sub_key, sub_val in subs.items():
                        sub_name_text = _extract_subtopic_text(sub_val)
                        if not sub_name_text:
                            sub_name_text = _extract_subtopic_text(sub_key)
                        if not sub_name_text:
                            auto_idx += 1
                            continue

                        raw_idx = _normalize_subtopic_key(sub_key)
                        idx_key = raw_idx if _is_numeric_like(raw_idx) else str(auto_idx)
                        subtopic_name_map[(wk_key, idx_key)] = sub_name_text
                        if wk_num:
                            subtopic_name_map[(wk_num, idx_key)] = sub_name_text
                        subtopic_index_global_map.setdefault(idx_key, sub_name_text)
                        auto_idx += 1
            if total > 0:
                progress_total = total

        def _resolve_subtopic_name(week, subtopic):
            wk = _norm_key(week)
            sb = _normalize_subtopic_key(subtopic)

            # subtopic 本身可能是对象/字符串化对象，优先提取可读名称
            extracted = _extract_subtopic_text(subtopic)
            if extracted and (not _is_numeric_like(extracted)) and (not _is_generic_subtopic_label(extracted)):
                return extracted

            # 占位命名（如 知识点1）先提取索引再走映射
            if _is_generic_subtopic_label(extracted):
                idx = _extract_index_from_label(extracted)
                if idx:
                    sb = idx

            # 字符串化字典、混合写法里也尝试抽取索引
            if _is_generic_subtopic_label(sb):
                idx = _extract_index_from_label(sb)
                if idx:
                    sb = idx

            # 直接命中
            direct = subtopic_name_map.get((wk, sb))
            if direct:
                return direct
            # week数字化重试
            wk_num = ''.join(ch for ch in wk if ch.isdigit())
            if wk_num:
                by_num_week = subtopic_name_map.get((wk_num, sb))
                if by_num_week:
                    return by_num_week
            # week缺失或映射未命中时，用全局索引兜底
            global_match = subtopic_index_global_map.get(sb)
            if global_match:
                return global_match
            # subtopic本身已是具体名称时直接返回
            if sb and (not _is_numeric_like(sb)) and (not _is_generic_subtopic_label(sb)):
                return sb
            # 都无法解析时兜底
            if sb:
                return f"未命名知识点({sb})"
            return "未分类知识点"

        recent_scores = []
        weekly_scores = {}
        total_questions = 0
        # 来自 quiz_records 的可读子主题名称，用于 roadmap 缺失/不规范时兜底
        quiz_subtopic_name_map = {}
        for q in quiz_docs:
            pct = self._extract_score_percentage(q)
            if pct is not None and len(recent_scores) < 5:
                recent_scores.append(pct)

            wk = str(q.get('week') or '-')
            if pct is not None:
                weekly_scores.setdefault(wk, []).append(pct)

            score_info = q.get('score_info') or {}
            q_count = score_info.get('question_count')
            if isinstance(q_count, int):
                total_questions += q_count
            else:
                total_questions += len((q.get('record') or {}).get('questions') or [])

            # 仅记录明确可读名称，避免把“知识点1”这类占位名写入兜底映射
            q_wk = _norm_key(q.get('week'))
            q_wk_num = ''.join(ch for ch in q_wk if ch.isdigit())
            q_sub_raw = q.get('subtopic')
            q_sub_key = _normalize_subtopic_key(q_sub_raw)
            q_sub_text = _extract_subtopic_text(q_sub_raw)
            if q_sub_text and (not _is_numeric_like(q_sub_text)) and (not _is_generic_subtopic_label(q_sub_text)):
                quiz_subtopic_name_map[(q_wk, q_sub_key)] = q_sub_text
                if q_wk_num:
                    quiz_subtopic_name_map[(q_wk_num, q_sub_key)] = q_sub_text

        avg_score_recent5 = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else None
        error_rate = round((wrong_count * 100.0 / total_questions), 2) if total_questions > 0 else None

        # 薄弱点：按子主题聚合错题数量，并结合该子主题测验均分估算薄弱率
        weak_points = []
        wrong_subtopic_docs = list(self.wrong_questions.find(
            {"user_id": user_id, "course": subject},
            {"week": 1, "subtopic": 1}
        ))
        wrong_subtopic_counts = {}
        for doc in wrong_subtopic_docs:
            wk = _norm_key(doc.get('week'))
            sub = _normalize_subtopic_key(doc.get('subtopic'))
            key = (wk, sub)
            wrong_subtopic_counts[key] = wrong_subtopic_counts.get(key, 0) + 1

        subtopic_scores = {}
        for q in quiz_docs:
            wk = _norm_key(q.get('week'))
            sub = _normalize_subtopic_key(q.get('subtopic'))
            pct = self._extract_score_percentage(q)
            if pct is None:
                continue
            subtopic_scores.setdefault((wk, sub), []).append(pct)

        for subtopic_key, wrong_sub_count in wrong_subtopic_counts.items():
            wk, sub = subtopic_key
            subtopic_name = _resolve_subtopic_name(wk, sub)

            # roadmap 未命中时，尝试用 quiz 中已有可读名称再兜底一次
            if str(subtopic_name).startswith("未命名知识点"):
                wk_num = ''.join(ch for ch in str(wk) if ch.isdigit())
                by_quiz = quiz_subtopic_name_map.get((wk, sub)) or (quiz_subtopic_name_map.get((wk_num, sub)) if wk_num else None)
                if by_quiz:
                    subtopic_name = by_quiz

            avg_sub_score = None
            if subtopic_key in subtopic_scores and subtopic_scores[subtopic_key]:
                avg_sub_score = sum(subtopic_scores[subtopic_key]) / len(subtopic_scores[subtopic_key])
            # 以 100-均分 作为薄弱率近似；无分数时用 60 作为保守默认
            rate = round((100.0 - avg_sub_score), 2) if avg_sub_score is not None else 60.0
            weak_points.append({
                "name": subtopic_name,
                "rate": rate,
                "count": wrong_sub_count,
            })

        weak_points.sort(key=lambda x: (x.get('count', 0), x.get('rate', 0)), reverse=True)
        weak_points = weak_points[:5]

        trend = []
        for wk, arr in weekly_scores.items():
            trend.append({"week": wk, "score": round(sum(arr) / len(arr), 2)})
        trend.sort(key=lambda x: x.get('week'))

        recommendations = []
        if error_rate is not None and error_rate >= 35:
            recommendations.append({
                "priority": "high",
                "title": "先处理错题密集知识点",
                "content": "当前错题率偏高，建议先做错题重练，再做同子主题新题，降低重复错误。",
            })
        if avg_score_recent5 is not None and avg_score_recent5 < 70:
            recommendations.append({
                "priority": "medium",
                "title": "提高基础题稳定性",
                "content": "最近5次均分偏低，建议每天固定15-20分钟进行基础题复盘。",
            })
        if weak_points:
            top_weak = weak_points[0].get('name')
            recommendations.append({
                "priority": "medium",
                "title": f"优先攻克：{top_weak}",
                "content": "围绕该薄弱点建立小目标：先复盘概念，再做3-5道同类题即时检验。",
            })
        if not recommendations:
            recommendations.append({
                "priority": "low",
                "title": "保持节奏，逐步进阶",
                "content": "当前学科表现稳定，建议继续保持学习频率，并逐步提高题目难度。",
            })

        last_study_at = quiz_docs[0].get('created_at').isoformat() if quiz_docs and quiz_docs[0].get('created_at') else None
        return {
            "subject": subject,
            "lastStudyAt": last_study_at,
            "totalQuizzes": len(quiz_docs),
            "avgScoreRecent5": avg_score_recent5,
            "errorRate": error_rate,
            "wrongCount": wrong_count,
            "redoCount": redo_count,
            "progressCompleted": progress_completed,
            "progressTotal": progress_total,
            "weeklyScores": trend,
            "weakPoints": weak_points,
            "recommendations": recommendations,
        }

    # ------------------ 错题集 / 重做  ------------------
    def _question_key(self, question_obj, course, week, subtopic):
        base = {
            "course": course,
            "week": week,
            "subtopic": subtopic,
            "question": question_obj.get('question'),
            "options": question_obj.get('options'),
            "type": question_obj.get('type')
        }
        raw = repr(base).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def upsert_wrong_question(self, user_id, course, week, subtopic, question_obj, user_answer=None, correct_answer=None, difficulty=None, source='auto', note=None):
        now = datetime.utcnow()
        qkey = self._question_key(question_obj, course, week, subtopic)
        doc = {
            "user_id": user_id,
            "course": course,
            "week": week,
            "subtopic": subtopic,
            "question_key": qkey,
            "question": question_obj.get('question'),
            "options": question_obj.get('options'),
            "type": question_obj.get('type'),
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "explanation": question_obj.get('explanation') or question_obj.get('reason'),
            "user_answer": user_answer,
            "source": source,
            "updated_at": now,
        }
        if note is not None:
            doc['note'] = note
        self.wrong_questions.update_one(
            {"user_id": user_id, "question_key": qkey},
            {
                "$set": doc,
                "$setOnInsert": {
                    "created_at": now,
                    "redo_history": [],
                }
            },
            upsert=True
        )
        return qkey

    def remove_wrong_question(self, user_id, question_key):
        res = self.wrong_questions.delete_one({"user_id": user_id, "question_key": question_key})
        return res.deleted_count

    def list_wrong_questions(self, user_id, course=None, week=None, subtopic=None, difficulty=None):
        query = {"user_id": user_id}
        if course:
            query['course'] = course
        if week:
            query['week'] = week
        if subtopic:
            query['subtopic'] = subtopic
        if difficulty:
            query['difficulty'] = difficulty
        docs = list(self.wrong_questions.find(query).sort([('updated_at', -1)]))
        for d in docs:
            if '_id' in d:
                d['id'] = str(d.get('_id'))
                d.pop('_id', None)
            if 'created_at' in d:
                d['created_at'] = d['created_at'].isoformat()
            if 'updated_at' in d:
                d['updated_at'] = d['updated_at'].isoformat()
            if 'redo_history' in d and isinstance(d['redo_history'], list):
                for entry in d['redo_history']:
                    if isinstance(entry, dict) and isinstance(entry.get('created_at'), datetime):
                        entry['created_at'] = entry['created_at'].isoformat()
        return docs

    def update_wrong_note(self, user_id, question_key, note):
        res = self.wrong_questions.update_one({"user_id": user_id, "question_key": question_key}, {"$set": {"note": note, "updated_at": datetime.utcnow()}})
        return res.modified_count

    def check_wrong_membership(self, user_id, questions, course, week, subtopic):
        result = []
        for idx, q in enumerate(questions):
            qkey = self._question_key(q, course, week, subtopic)
            exists = self.wrong_questions.find_one({"user_id": user_id, "question_key": qkey}, {'_id': 1})
            if exists:
                result.append(idx)
        return result

    def add_redo_record(self, user_id, course, week, subtopic, question_obj, correct_answer, attempt_answer, difficulty=None, batch_id=None, question_key=None):
        now = datetime.utcnow()
        qdict = question_obj if isinstance(question_obj, dict) else ({"question": question_obj} if question_obj else {})
        doc = {
            "user_id": user_id,
            "course": course,
            "week": week,
            "subtopic": subtopic,
            "question_key": question_key or self._question_key(qdict, course, week, subtopic),
            "question": qdict.get('question'),
            "options": qdict.get('options'),
            "type": qdict.get('type'),
            "correct_answer": correct_answer,
            "attempt_answer": attempt_answer,
            "difficulty": difficulty,
            "created_at": now,
        }
        if batch_id:
            doc['batch_id'] = batch_id
        res = self.redo_records.insert_one(doc)
        return str(res.inserted_id)

    def list_redo_records(self, user_id, course=None, week=None, subtopic=None):
        query = {"user_id": user_id}
        if course:
            query['course'] = course
        if week:
            query['week'] = week
        if subtopic:
            query['subtopic'] = subtopic
        docs = list(self.redo_records.find(query).sort([('created_at', -1)]))
        for d in docs:
            if '_id' in d:
                d['id'] = str(d.get('_id'))
                d.pop('_id', None)
            if 'created_at' in d:
                d['created_at'] = d['created_at'].isoformat()
        return docs

    def delete_redo_record(self, user_id, record_id):
        try:
            oid = ObjectId(record_id)
        except Exception:
            return 0
        res = self.redo_records.delete_one({"_id": oid, "user_id": user_id})
        return res.deleted_count

    def delete_course_data(self, user_id, topic):
        """删除用户与某课程相关的所有数据（内容/统计/测验/错题/重做）"""

        topic_text = str(topic or "").strip()
        if not topic_text:
            return {
                "deleted_contents_count": 0,
                "deleted_stats_count": 0,
                "deleted_quiz_count": 0,
                "deleted_wrong_count": 0,
                "deleted_redo_count": 0,
                "updated_user_count": 0,
                "deletion_mode": "skipped",
                "transaction_note": "empty_topic",
            }

        # 兼容历史数据中课程名大小写/空格不一致的情况
        topic_regex = re.compile(rf"^\s*{re.escape(topic_text)}\s*$", re.IGNORECASE)

        def _topic_query(field_name):
            return {
                "$or": [
                    {field_name: topic_text},
                    {field_name: topic_text.strip()},
                    {field_name: {"$regex": topic_regex}},
                ]
            }

        content_query = {"user_id": user_id, **_topic_query("topic")}
        course_query = {"user_id": user_id, **_topic_query("course")}

        def _delete_course(session=None):
            contents_result = self.contents.delete_many(content_query, session=session)
            stats_result = self.stats.delete_many(content_query, session=session)
            quiz_result = self.quiz_records.delete_many(course_query, session=session)
            wrong_result = self.wrong_questions.delete_many(course_query, session=session)
            redo_result = self.redo_records.delete_many(course_query, session=session)
            user_update = self.users.update_one(
                {"user_id": user_id},
                {
                    "$pull": {
                        "subject_order": {
                            "$in": [topic_text, topic_text.strip()],
                        }
                    },
                    "$set": {"updated_at": datetime.utcnow()},
                },
                session=session,
            )

            return {
                "deleted_contents_count": contents_result.deleted_count,
                "deleted_stats_count": stats_result.deleted_count,
                "deleted_quiz_count": quiz_result.deleted_count,
                "deleted_wrong_count": wrong_result.deleted_count,
                "deleted_redo_count": redo_result.deleted_count,
                "updated_user_count": user_update.modified_count,
            }

        try:
            with self.client.start_session() as session:
                with session.start_transaction():
                    result = _delete_course(session=session)
            result["deletion_mode"] = "transaction"
            return result
        except Exception:
            result = _delete_course(session=None)
            result["deletion_mode"] = "non_transaction"
            result["transaction_note"] = "transaction_not_available"
            return result

    def delete_user_account_data(self, user_id):
        """删除用户账号及其全部关联数据"""
        def _delete_all(session=None):
            users_result = self.users.delete_one({"user_id": user_id}, session=session)
            contents_result = self.contents.delete_many({"user_id": user_id}, session=session)
            stats_result = self.stats.delete_many({"user_id": user_id}, session=session)
            quiz_result = self.quiz_records.delete_many({"user_id": user_id}, session=session)
            wrong_result = self.wrong_questions.delete_many({"user_id": user_id}, session=session)
            redo_result = self.redo_records.delete_many({"user_id": user_id}, session=session)
            profile_result = self.user_profiles.delete_many({"user_id": user_id}, session=session)
            return {
                "deleted_user_count": users_result.deleted_count,
                "deleted_contents_count": contents_result.deleted_count,
                "deleted_stats_count": stats_result.deleted_count,
                "deleted_quiz_count": quiz_result.deleted_count,
                "deleted_wrong_count": wrong_result.deleted_count,
                "deleted_redo_count": redo_result.deleted_count,
                "deleted_profile_count": profile_result.deleted_count,
            }

        # Prefer transaction for consistency when Mongo deployment supports sessions.
        try:
            with self.client.start_session() as session:
                with session.start_transaction():
                    result = _delete_all(session=session)
            result["deletion_mode"] = "transaction"
            return result
        except Exception as txn_error:
            result = _delete_all(session=None)
            result["deletion_mode"] = "non_transaction"
            result["transaction_note"] = "transaction_not_available"
            return result

    def append_wrong_redo_history(self, user_id, question_key, attempt_answer, correct_answer=None, difficulty=None):
        """在错题文档上追加一条重做记录，最多保留20条（FIFO）。"""
        now = datetime.utcnow()
        entry = {
            "attempt_answer": attempt_answer,
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "created_at": now,
        }
        res = self.wrong_questions.update_one(
            {"user_id": user_id, "question_key": question_key},
            {
                "$push": {
                    "redo_history": {
                        "$each": [entry],
                        "$slice": -20  # 仅保留最新20条
                    }
                },
                "$set": {"updated_at": now}
            },
            upsert=False
        )
        return res.modified_count

# 全局实例
mongodb = MongoDB()