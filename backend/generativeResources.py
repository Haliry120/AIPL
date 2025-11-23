import siliconflow_client  
  
  
def generate_resources(course, knowledge_level, description, time):  
    """使用硅基流动API生成学习资源"""  
      
    # 系统指令  
    system_instruction = "You are an AI tutor. Maintain a modest and calm language suitable for learning. You need to provide content to user to learn in given time."  
      
    # 用户提示  
    user_prompt = f"I am learning {course}. My knowledge level in this topic is {knowledge_level}. i want to {description}. I want to learn it in {time}. Teach me."  
      
    # 使用客户端生成文本响应  
    client = siliconflow_client.get_client()  
    return client.generate_text(  
        system_instruction=system_instruction,  
        user_prompt=user_prompt,  
        temperature=1,  
        top_p=0.95,  
        max_tokens=8192  
    )