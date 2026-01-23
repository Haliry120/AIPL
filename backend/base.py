from flask import Flask, request
import roadmap
import quiz
import generativeResources
from flask_cors import CORS
import bilibili_search
import translate
from database import get_or_create_user, save_content, get_content
import uuid
import siliconflow_client

api = Flask(__name__)
CORS(api)

def get_user_id():  
    """从请求中获取或创建用户ID"""  
    user_id = request.headers.get('X-User-ID')  
    if not user_id:  
        # 从 localStorage 或创建新的临时ID  
        user_id = request.json.get('user_id') if request.json else None  
      
    user = get_or_create_user(user_id)  
    return user['user_id'] 

@api.route("/api/roadmap", methods=["POST"])
def get_roadmap():
    req = request.get_json()

    # 检查是否需要重新生成
    regenerate = req.get("regenerate", False)
    topic = req.get("topic", "Machine Learning")

    # 如果不是重新生成，尝试从数据库获取
    if not regenerate:
        try:
            from database import get_content
            user_id = request.headers.get('X-User-ID')
            if user_id:
                existing = get_content(user_id, topic, "roadmap")
                if existing:
                    return existing["content_data"]
        except:
            pass  # 如果数据库出错，继续生成新的

    # 生成新的路线图
    response_body = roadmap.create_roadmap(
        topic=topic,
        time=req.get("time", "4 weeks"),
        knowledge_level=req.get("knowledge_level", "Absolute Beginner"),
    )

    # 保存到数据库
    try:
        from database import save_content
        user_id = request.headers.get('X-User-ID')
        if user_id:
            save_content(user_id, topic, "roadmap", response_body)
    except:
        pass  # 如果数据库出错，仍然返回结果

    return response_body


@api.route("/api/quiz", methods=["POST"])
def get_quiz():
    req = request.get_json()
    user_id = get_user_id()

    course = req.get("course")
    topic = req.get("topic")
    subtopic = req.get("subtopic")
    description = req.get("description")

    if not (course and topic and subtopic and description):
        return "Required Fields not provided", 400

    # 生成测验（测验通常不需要缓存，每次都是新的）
    response_body = quiz.get_quiz(course, topic, subtopic, description)
    return response_body

@api.route("/api/quiz-score", methods=["POST"])  
def save_quiz_score():  
    """保存测验成绩"""  
    req = request.get_json()  
    user_id = get_user_id()  
      
    topic = req.get("topic")  
    score = req.get("score")  
      
    if not topic or score is None:  
        return "Required Fields not provided", 400  
      
    from database import update_quiz_score  
    update_quiz_score(user_id, topic, score)  
      
    return {"success": True}  


@api.route("/api/save-quiz-record", methods=["POST"])
def save_quiz_record():
    """保存单次测验的完整记录到数据库"""
    req = request.get_json()
    user_id = get_user_id()

    course = req.get('course')
    week = str(req.get('week')) if req.get('week') is not None else None
    subtopic = str(req.get('subtopic')) if req.get('subtopic') is not None else None
    record = req.get('record')

    if not (course and week and subtopic and record is not None):
        return "Required Fields not provided", 400

    from database import save_quiz_record as db_save
    try:
        print(f"保存测验记录: user={user_id} course={course} week={week} subtopic={subtopic} questions={len(record.get('questions',[]))}")
        db_save(user_id, course, week, subtopic, record)
        return {"success": True}
    except Exception as e:
        print('保存测验记录失败:', e)
        return {"success": False, "error": str(e)}, 500


@api.route("/api/quiz-records", methods=["GET"])
def get_quiz_records():
    """返回用户的测验记录；支持按 course/week/subtopic 过滤"""
    user_id = get_user_id()
    course = request.args.get('course')
    week = str(request.args.get('week')) if request.args.get('week') is not None else None
    subtopic = str(request.args.get('subtopic')) if request.args.get('subtopic') is not None else None

    from database import get_quiz_records as db_get
    try:
        print(f"查询测验记录: user={user_id} course={course} week={week} subtopic={subtopic}")
        records = db_get(user_id, course=course, week=week, subtopic=subtopic)
        print(f"返回记录数: {len(records)}")
        return {"success": True, "records": records}
    except Exception as e:
        print('获取测验记录失败:', e)
        return {"success": False, "error": str(e)}, 500


@api.route("/api/delete-quiz-records", methods=["POST"])
def delete_quiz_records():
    """删除用户的测验记录；可按 course/week/subtopic 过滤"""
    req = request.get_json() or {}
    user_id = get_user_id()
    course = req.get('course')
    week = str(req.get('week')) if req.get('week') is not None else None
    subtopic = str(req.get('subtopic')) if req.get('subtopic') is not None else None

    from database import delete_quiz_records as db_delete
    try:
        print(f"删除测验记录: user={user_id} course={course} week={week} subtopic={subtopic}")
        result = db_delete(user_id, course=course, week=week, subtopic=subtopic)
        return {"success": True, "deleted": result.get("deleted_count", 0)}
    except Exception as e:
        print('删除测验记录失败:', e)
        return {"success": False, "error": str(e)}, 500


@api.route("/api/user-data", methods=["GET"])  
def get_user_data():  
    """获取用户的所有学习数据"""  
    user_id = get_user_id()  
      
    # 获取用户的所有内容  
    from database import get_user_contents  
    contents = get_user_contents(user_id)  
      
    return {  
        "user_id": user_id,  
        "contents": contents  
    }


@api.route("/api/cancel-course", methods=["POST"])  
def cancel_course():
    """取消学习某课程并删除数据库中与该课程相关的所有数据"""
    req = request.get_json()
    user_id = get_user_id()

    topic = req.get("course") or req.get("topic")
    if not topic:
        return {"error": "Required Fields not provided"}, 400

    from database import cancel_course as db_cancel
    result = db_cancel(user_id, topic)

    return {"success": True, "result": result}

@api.route("/api/translate", methods=["POST"])
def get_translations():
    req = request.get_json()

    text = req.get("textArr")
    toLang = req.get("toLang")

    print(f"Translating to {toLang}: { text}")
    translated_text = translate.translate_text_arr(text_arr=text, target=toLang)
    return translated_text


@api.route("/api/generate-resource", methods=["POST"])
def generative_resource():
    req = request.get_json()
    user_id = get_user_id()

    # 检查是否需要重新生成
    regenerate = req.get("regenerate", False)
    course = req.get("course")

    if not regenerate:
        # 尝试从数据库获取现有资源
        existing = get_content(user_id, course, "resource")
        if existing:
            return existing["content_data"]

    # 验证必需字段
    req_data = {
        "course": req.get("course"),
        "knowledge_level": req.get("knowledge_level"),
        "description": req.get("description"),
        "time": req.get("time"),
    }

    for key, value in req_data.items():
        if not value:
            return "Required Fields not provided", 400
    
    # 生成新的资源
    resources = generativeResources.generate_resources(**req_data)

    # 保存到数据库
    save_content(user_id, course, "resource", resources)

    return resources


@api.route("/api/search-bilibili", methods=["POST"])
def search_bilibili():
    req = request.get_json()

    subtopic = req.get("subtopic", "")
    course = req.get("course", "")

    # 将英文关键词翻译成中文
    try:
        subtopic_cn = translate.translate_text_arr([subtopic], target="zh-CN")[0] if subtopic else ""
        course_cn = translate.translate_text_arr([course], target="zh-CN")[0] if course else ""
        print(f"Translated: {subtopic} -> {subtopic_cn}, {course} -> {course_cn}")
    except Exception as e:
        print(f"Translation error: {e}, using original keywords")
        subtopic_cn = subtopic
        course_cn = course

        # 使用翻译后的中文关键词搜索
    keyword = f"{subtopic_cn} 教程"

    print(f"Searching Bilibili for: {keyword}")
    courses = bilibili_search.search_bilibili_courses(keyword)

    # 如果第一次搜索无结果,尝试其他组合
    if not courses:
        print(f"No results for '{keyword}', trying with course name")
        keyword = f"{course_cn} {subtopic_cn}"
        courses = bilibili_search.search_bilibili_courses(keyword)

    if not courses:
        print(f"No results for '{keyword}', trying with course only")
        keyword = f"{course_cn}"
        courses = bilibili_search.search_bilibili_courses(keyword)

    return {"courses": courses, "keyword": keyword}


@api.route("/api/personalized-explanation", methods=["POST"])
def get_personalized_explanation():
    """根据用户回答生成个性化解析"""
    req = request.get_json()

    question = req.get("question")
    user_answer = req.get("userAnswer")
    correct_answer = req.get("correctAnswer")
    question_type = req.get("questionType")
    course = req.get("course")
    topic = req.get("topic")
    subtopic = req.get("subtopic")
    knowledge_level = req.get("KnowledgeLevel")

    if not question or not user_answer:
        return {"error": "Required Fields not provided"}, 400

    print(f"=== 个性化解析请求 ===")
    print(f"题目: {question[:100]}...")
    print(f"用户答案: {user_answer[:100] if len(user_answer) > 100 else user_answer}")
    print(f"正确答案: {correct_answer}")
    print(f"题目类型: {question_type}")

    # 系统指令 - 简单直接版本
    system_instruction =  """你是专业的学科导师和教育评估专家，擅长根据学生的具体错误提供有针对性的学习指导。

请严格遵循以下要求生成个性化解析：

【核心任务】
1. 分析学生答案与正确答案的差异，找出具体错误点
2. 根据错误类型（概念混淆、计算错误、理解偏差等）提供针对性解释
3. 用温和鼓励的语气帮助学生建立信心
4. 根据学生水平提供针对性的指导
解析框架（深度分析维度）：
1. 知识掌握度分析
   - 哪些概念掌握了，哪些有误解
   - 知识点的联系是否建立
   - 记忆、理解、应用层面的表现

2. 思维过程分析
   - 解题思路的合理性
   - 逻辑推理的严密性
   - 问题拆解能力

3. 学习习惯分析
   - 回答中反映的学习方法
   - 常见错误模式
   - 需要培养的学习策略

4. 情感态度分析（如有信息）
   - 回答体现的学习态度
   - 信心水平和学习动力

指导原则：
- 语气：温和、鼓励、建设性，保护学生自信
- 重点：不仅指出错误，更要解释"为什么"会错
- 方法：提供具体的、可操作的学习策略
- 视角：从学生当前水平出发，设定可达成的下一步目标

【输出要求】
1. 必须使用以下JSON格式，不添加任何额外文本
2. 各字段内容要求：
{
  "analysis": "200-500字，详细分析错误原因，体现个性化",
  "correction": "对错误部分的纠正说明,清晰指出正确思路，避免简单复述答案，根据学生的个人情况和水平举出一些具体的例子，或者从高层的理论上进行解释",
  "suggestion": "具体可行的学习行动建议，比如推荐阅读可以指出可以去阅读哪些书哪些内容，推荐写代码可以给出具体的题目等，总之一定要是切实可行的，结合题目类型和知识点,添加一句适用于该学生个性化的鼓励的话",
}
【教学原则】
- 先肯定学生的努力，再指出问题
- 错误分析要具体，避免泛泛而谈
- 建议要可执行，如"建议练习3道同类题目"
- 适当使用类比、示例帮助学生理解

请生成专业、温暖、有指导价值的个性化解析"""
        
    # 用户提示 - 简单直接
    user_prompt = f"""请分析以下学生回答并提供个性化解析：

【题目】
{question}

【题目类型】
{question_type}

【学生回答】
{user_answer}

【正确答案】
{correct_answer}

【课程背景】
{course} - {topic}
知识点：{topic} - {subtopic}
学生知识水平：{knowledge_level}
【分析重点】
1. 请分析学生答案中的具体错误点（概念、步骤、理解等）
2. 结合题目类型（{question_type}）提供针对性指导
3. 根据学生的知识水平（{knowledge_level}）调整解释深度
4. 针对{topic}知识点提供学习建议

请基于以上信息生成个性化学习解析，帮助学生理解错误并改进学习。"""

    try:
        client = siliconflow_client.get_client()
        
        # 使用 generate_text 方法，然后手动解析 JSON
        response = client.generate_text(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.7,
            top_p=0.9,
            max_tokens=2000
        )
        
        print(f"原始响应: {response[:500]}...")
        
        # 尝试提取 JSON
        import json
        import re
        
        # 尝试直接解析
        try:
            result = json.loads(response)
            print("直接解析成功")
            return result
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                    print("从代码块中解析成功")
                    return result
                except json.JSONDecodeError:
                    pass
            
            # 尝试提取花括号中的内容
            brace_match = re.search(r'\{[\s\S]*\}', response)
            if brace_match:
                try:
                    result = json.loads(brace_match.group(0))
                    print("从花括号中解析成功")
                    return result
                except json.JSONDecodeError:
                    pass
        
        # 如果所有解析都失败，返回结构化错误
        print("无法解析 JSON，返回默认响应")
        return {
            "analysis": f"很遗憾，你的回答与正确答案有所偏差。",
            "correction": f"正确答案是：{correct_answer}",
            "suggestion": "建议回顾相关知识点，加强理解后再尝试类似题目。",
            
        }
        
    except Exception as e:
        print(f"个性化解析生成失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "analysis": f"很遗憾，你的回答与正确答案有所偏差。",
            "correction": f"正确答案是：{correct_answer}",
            "suggestion": "建议回顾相关知识点，加强理解后再尝试类似题目。",
            
        }

@api.route("/api/quiz-followup", methods=["POST"])
def quiz_followup():
    """处理用户对题目的追问，支持多轮对话"""
    req = request.get_json()
    
    question = req.get("question")
    correct_answer = req.get("correctAnswer")
    user_answer = req.get("userAnswer")
    question_type = req.get("questionType")
    course = req.get("course")
    topic = req.get("topic")
    subtopic = req.get("subtopic")
    conversation_history = req.get("conversationHistory", [])
    user_question = req.get("userQuestion")
    
    if not question or not user_question:
        return {"error": "缺少必要参数"}, 400
    
    print(f"=== 题目追问请求 ===")
    print(f"题目: {question[:100]}...")
    print(f"用户追问: {user_question}")
    print(f"对话历史: {len(conversation_history)} 轮")
    
    # 构建对话历史
    history_text = ""
    for i, (q, a) in enumerate(conversation_history):
        history_text += f"\n[对话 {i+1}] 用户: {q}\n[对话 {i+1}] AI: {a}"
    
    system_instruction = """你是一位专业的学习辅导老师。学生做完题目后可能会有各种疑问，你需要：

1. 耐心解答学生关于这道题目的任何问题
2. 可以扩展讲解相关的知识点
3. 提供更多例子帮助学生理解
4. 如果学生问的是关于答案为什么对/错，要清晰解释
5. 语气要温和鼓励，保护学生的学习热情

请直接回答学生的问题，不要重复题目内容，答案要简洁明了。"""

    user_prompt = f"""请回答学生关于这道题目的追问：

【题目信息】
- 题目类型：{question_type}
- 正确答案：{correct_answer}
- 学生答案：{user_answer}
- 课程：{course}
- 主题：{topic}
{f"- 子主题：{subtopic}" if subtopic else ""}

【之前的对话】{history_text}

【学生的新问题】
{user_question}

请直接回答学生的问题。如果问题与题目或知识点无关，请礼貌地引导学生回到学习上来。"""

    try:
        client = siliconflow_client.get_client()
        response = client.generate_text(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.7,
            top_p=0.9,
            max_tokens=1500
        )
        
        print(f"追问回答: {response[:200]}...")
        return {"answer": response}
        
    except Exception as e:
        print(f"追问回答生成失败: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "生成回答失败，请稍后重试"}, 500


if __name__ == "__main__":
    api.run(host="0.0.0.0", port=5000, debug=True)


@api.route("/api/resource-qa", methods=["POST"])
def resource_qa():
    """处理用户对学习资源的问题，支持多轮对话"""
    req = request.get_json()
    
    topic = req.get("topic")
    subtopic = req.get("subtopic")
    resource_content = req.get("resourceContent")
    user_question = req.get("userQuestion")
    conversation_history = req.get("conversationHistory", [])
    
    if not user_question:
        return {"error": "问题不能为空"}, 400
    
    print(f"=== 学习资源问答请求 ===")
    print(f"主题: {topic} - {subtopic}")
    print(f"用户问题: {user_question}")
    print(f"对话历史: {len(conversation_history)} 轮")
    
    history_text = ""
    for i, (q, a) in enumerate(conversation_history):
        history_text += f"\n[对话 {i+1}] 用户: {q}\n[对话 {i+1}] AI: {a}"
    
    system_instruction = """你是一位专业的学习导师。用户正在学习特定的学习资源内容，你需要：

1. 根据提供的学习资源内容回答用户的问题
2. 如果问题超出资源范围，基于你的知识给出合理回答
3. 回答要简洁明了，易于理解
4. 适当举例子帮助解释概念
5. 语气要温和鼓励，保护学生的学习热情
6. 如果用户问的是作业或练习，可以给出解题思路但不要直接给答案

请直接回答问题，答案要简洁明了。"""

    user_prompt = f"""用户正在学习以下内容：
- 主题：{topic}
- 子主题：{subtopic}

【学习资源内容】
{resource_content[:3000]}

【之前的对话】{history_text}

【用户的新问题】
{user_question}

请根据学习资源内容回答用户的问题。如果问题超出资源范围，可以基于你的知识给出回答，但要在回答开始时说明这一点。"""

    try:
        client = siliconflow_client.get_client()
        response = client.generate_text(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.7,
            top_p=0.9,
            max_tokens=1500
        )
        
        print(f"问答回答: {response[:200]}...")
        return {"answer": response}
        
    except Exception as e:
        print(f"问答回答生成失败: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "生成回答失败，请稍后重试"}, 500
