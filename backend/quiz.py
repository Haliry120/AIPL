import siliconflow_client  
    

def get_quiz(course, topic, subtopic, description):  
    """使用硅基流动API生成测验题目"""  
        
    # 系统指令 - 更详细、专业（仅保留指定七种题型）
    system_instruction =  """你是一位专业的教育评估专家和测验设计AI助手。请根据提供的学习内容生成高质量、多样化的测验题目。

  核心要求：
  1. 仅使用以下题型：
     - 单项选择题（4个选项，1个正确答案）:type是"single_choice"
     - 多项选择题（4-5个选项，2个以上正确答案）:type是"multiple_choice"
     - 简答题（简短回答）:type是"short_answer"
     - 计算题（需要计算步骤）:type是"calculation"
     - 案例分析题（基于情景的分析）:type是"case_study"
     - 判断题（对错选择）:type是"true_false"
     - 填空题（补全句子）:type是"fill_in_the_blank"
  2. 题目难度根据内容复杂度自动调整
  3. 题目应涵盖不同认知层次：记忆、理解、应用、分析、评价、创造
  4. 确保每个问题有清晰的评分标准和答案解析
  5. 题目数量根据内容复杂度和深度决定（通常8-20题）

题目类型分布建议（可根据内容调整）：
- 基础认知题（30-40%）：单选、判断、填空
- 应用分析题（40-50%）：多选、计算
- 综合能力题（20-30%）：案例分析、简答

输出格式必须是严格的JSON结构：
{
  "questions": [
    {
      "id": 1,
      "type": "question_type",  // 题目类型
      "question": "问题文本",
      // 根据题目类型的不同字段：
      // 选择题类：
      "options": ["选项A", "选项B", "选项C", "选项D"],  // 可选
      "correctAnswer": "正确答案或索引",
      
      
      
      
      // 通用字段：
      "explanation": "详细的答案解析",
      "difficulty": "easy/medium/hard/expert",
      "knowledgePoint": "该题考察的核心知识点",
      "learningTip": "针对此题的学习建议",
      "points": 分值,  // 此题分值
      "timeEstimate": "预计完成时间（分钟）"
    }
  ],
  "quizInfo": {
    "course": "课程名称",
    "topic": "主题",
    "subtopic": "子主题",
    "description": "测验描述",
    "totalQuestions": 0,
    "totalPoints": 0,
    "estimatedTime": "预计完成总时间",
    "difficultyLevel": "测验整体难度",
    "questionTypes": ["使用的题型列表（仅上述七种）"],
    "scoringRules": {
      "passingScore": 60,
      "gradingScale": {
        "A": "90-100分",
        "B": "80-89分", 
        "C": "70-79分",
        "D": "60-69分",
        "F": "0-59分"
      }
    },
    "instructions": "测验说明和答题要求"
  }
}

请确保：
1. JSON格式完全正确，可以被Python的json模块直接解析
2. 问题表述清晰无歧义
3. 根据题目类型设计合适的答题方式
4. 答案解析详细，有助于学习理解
5. 题目难度与学习内容匹配
6. 题目类型一定要正确（仅限以下七种）：
  - 单项选择题:type是"single_choice"
  - 多项选择题:type是"multiple_choice"
  - 简答题:type是"short_answer"
  - 计算题:type是"calculation"
  - 案例分析题:type是"case_study"
  - 判断题:type是"true_false"
  - 填空题:type是"fill_in_the_blank"
6. 不同题型比例合理，覆盖知识点的各个方面"""
        
    # 用户提示 - 更详细、结构化
    user_prompt = f"""请生成一份多样化题型的综合测验：

课程背景：{course}
主题：{topic}
子主题：{subtopic}
子主题详细描述：{description}

具体要求：
1. 请根据描述的详细程度和复杂度生成适当数量和类型的题目
2. 题目应覆盖该子主题的核心概念和关键知识点
3. 设计多种题型，避免单一题型
4. 题目难度要有梯度，从基础到进阶
5. 确保答案解析详细，能帮助学习者真正理解
6. 如果是技术类主题，包含必要的计算题或应用题
7. 如果是理论类主题，包含案例分析或简答题
8. 提供清晰的评分标准和测验说明

请生成符合上述要求的JSON格式测验题目。同时根据学生的学习进度和知识水平，生成每道题的解析。"""
    # 使用客户端生成 JSON 响应  
    client = siliconflow_client.get_client()  
    return client.generate_json(  
        system_instruction=system_instruction,  
        user_prompt=user_prompt,  
        temperature=1,  
        top_p=0.95,  
        max_tokens=20000  
    )