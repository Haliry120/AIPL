import siliconflow_client  
  
  
def get_quiz(course, topic, subtopic, description):  
    """使用硅基流动API生成测验题目"""  
      
    # 系统指令  
    system_instruction = """You are an AI agent who provides quizzes to test understanding of user on a topic. The quiz will be based on topic, subtopic and the description of subtopic which describes what exactly to learn. Output questions in JSON format. The questions must be Multiple Choice Questions, can include calculation if necessary. Decide the number of questions based on description of the subtopic. Try to make as many questions as possible. Include questions that require deep thinking. output in format {questions:[ {question: "...", options:[...], answerIndex:"...", reason:"..."}]"""  
      
    # 用户提示  
    user_prompt = f'The user is learning the course {course}. In the course the user is learning topic "{topic}". Create quiz on subtopic "{subtopic}". The description of the subtopic is "{description}".'  
      
    # 使用客户端生成 JSON 响应  
    client = siliconflow_client.get_client()  
    return client.generate_json(  
        system_instruction=system_instruction,  
        user_prompt=user_prompt,  
        temperature=1,  
        top_p=0.95,  
        max_tokens=20000  
    )