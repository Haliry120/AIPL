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

def create_user(username, email, password_hash):
    """创建注册用户"""
    return mongodb.create_user(username, email, password_hash)

def get_user_by_id(user_id):
    return mongodb.get_user_by_id(user_id)

def get_user_by_identifier(identifier):
    return mongodb.get_user_by_identifier(identifier)

def update_last_login(user_id):
    return mongodb.update_last_login(user_id)

def get_user_settings(user_id):
    return mongodb.get_user_settings(user_id)

def update_user_settings(user_id, username=None, avatar_url=None):
    return mongodb.update_user_settings(user_id, username=username, avatar_url=avatar_url)

def update_user_password_hash(user_id, password_hash):
    return mongodb.update_user_password_hash(user_id, password_hash)

def list_prompt_templates(user_id):
    return mongodb.list_prompt_templates(user_id)

def upsert_prompt_template(user_id, prompt_id, title, content, enabled=True, description=None, favorite=False, tags=None):
    return mongodb.upsert_prompt_template(
        user_id,
        prompt_id,
        title,
        content,
        enabled=enabled,
        description=description,
        favorite=favorite,
        tags=tags,
    )

def delete_prompt_template(user_id, prompt_id):
    return mongodb.delete_prompt_template(user_id, prompt_id)

def delete_user_account_data(user_id):
    return mongodb.delete_user_account_data(user_id)

def update_quiz_score(user_id, topic, score):
    """更新测验成绩"""
    return mongodb.update_quiz_score(user_id, topic, score)

def save_quiz_record(user_id, course, week, subtopic, record):
    """保存测验完整记录，包含分数信息"""
    return mongodb.save_quiz_record(user_id, course, week, subtopic, record)

# 新增：更新测验记录（用于后台评分）
def update_quiz_record(record_id, record, score_info=None):
    """更新测验记录内容与分数信息"""
    return mongodb.update_quiz_record(record_id, record, score_info)

# 新增函数：获取测验记录的分数详情
def get_quiz_score_summary(user_id, course=None, week=None, subtopic=None):
    """获取测验记录的分数汇总信息"""
    return mongodb.get_quiz_score_summary(user_id, course, week, subtopic)

# 新增函数：获取用户的分数历史
def get_user_score_history(user_id, course=None, limit=50):
    """获取用户的分数历史记录"""
    return mongodb.get_user_score_history(user_id, course, limit)

# 导入用户画像模块
try:
    import user_profile
except ImportError:
    print("Warning: user_profile module not available")

def generate_user_profile(user_id):
    """生成用户画像"""
    return user_profile.generate_and_save_profile(user_id)

def get_user_profile_db(user_id):
    """获取用户画像"""
    return user_profile.get_user_profile(user_id)

def save_user_profile_db(user_id, profile_data):
    """保存用户画像（用于导入场景）"""
    return user_profile.save_user_profile(user_id, profile_data)

def update_profile_on_quiz_completion(user_id, quiz_record_id=None):
    """测验完成后更新用户画像（可选）"""
    try:
        # 导入用户画像模块
        try:
            import user_profile
        except ImportError:
            print("Warning: user_profile module not available")
            return None
        
        # 异步或延迟更新，这里简单调用
        result = user_profile.generate_and_save_profile(user_id)
        print(f"用户画像更新完成: {result.get('success') if result else 'No result'}")
        return result
    except Exception as e:
        print(f"更新用户画像失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_user_contents(user_id, limit: int = 50, skip: int = 0):
    """获取用户的所有内容（支持分页，默认 limit=50）"""
    return mongodb.get_user_contents(user_id, limit=limit, skip=skip)

def get_quiz_records(user_id, course=None, week=None, subtopic=None, limit: int = 50, skip: int = 0):
    """根据条件获取测验记录（可按 course/week/subtopic 过滤，支持分页）"""
    return mongodb.get_quiz_records(user_id, course, week, subtopic, limit=limit, skip=skip)

def delete_quiz_records(user_id, course=None, week=None, subtopic=None):
    """按条件删除测验记录"""
    return mongodb.delete_quiz_records(user_id, course, week, subtopic)

def cancel_course(user_id, topic):
    """取消学习某课程，删除与该课程相关的所有数据库数据"""
    return mongodb.delete_course_data(user_id, topic)

# 统计辅助
def count_quiz_records(user_id, course=None, week=None, subtopic=None):
    """返回测验记录总数（与 get_quiz_records 相同筛选条件）"""
    return mongodb.count_quiz_records(user_id, course, week, subtopic)

def count_user_contents(user_id):
    """返回用户内容总数"""
    return mongodb.count_user_contents(user_id)

def get_subjects_overview(user_id, search_text=None, sort_mode='recent'):
    return mongodb.get_subjects_overview(user_id, search_text=search_text, sort_mode=sort_mode)

def set_subject_order(user_id, order_list):
    return mongodb.set_subject_order(user_id, order_list)

def get_subject_detail(user_id, subject):
    return mongodb.get_subject_detail(user_id, subject)

# 错题集 / 重做
def add_wrong_question(user_id, course, week, subtopic, question_obj, user_answer=None, correct_answer=None, difficulty=None, source='auto', note=None):
    return mongodb.upsert_wrong_question(user_id, course, week, subtopic, question_obj, user_answer, correct_answer, difficulty, source, note)

def remove_wrong_question(user_id, question_key):
    return mongodb.remove_wrong_question(user_id, question_key)

def list_wrong_questions(user_id, course=None, week=None, subtopic=None, difficulty=None):
    return mongodb.list_wrong_questions(user_id, course, week, subtopic, difficulty)

def update_wrong_note(user_id, question_key, note):
    return mongodb.update_wrong_note(user_id, question_key, note)

def check_wrong_membership(user_id, questions, course, week, subtopic):
    return mongodb.check_wrong_membership(user_id, questions, course, week, subtopic)

def add_redo_record(user_id, course, week, subtopic, question_obj, correct_answer, attempt_answer, difficulty=None, batch_id=None, question_key=None):
    return mongodb.add_redo_record(user_id, course, week, subtopic, question_obj, correct_answer, attempt_answer, difficulty, batch_id, question_key)

def list_redo_records(user_id, course=None, week=None, subtopic=None):
    return mongodb.list_redo_records(user_id, course, week, subtopic)

def delete_redo_record(user_id, record_id):
    return mongodb.delete_redo_record(user_id, record_id)

# 重做历史记录（存于 wrong_questions 文档内）
def append_wrong_redo_history(user_id, question_key, attempt_answer, correct_answer=None, difficulty=None):
    return mongodb.append_wrong_redo_history(user_id, question_key, attempt_answer, correct_answer, difficulty)