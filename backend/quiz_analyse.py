import siliconflow_client  
def get_quiz_analyse(course, topic, subtopic, description,questions):  
    """使用硅基流动API生成测验分析"""  
    system_instruction = '''  '''

    user_prompt = f'''  '''

    client = siliconflow_client.get_client()  
    return client.generate_json(  
        system_instruction=system_instruction,  
        user_prompt=user_prompt,  
        temperature=1,  
        top_p=0.95,  
        max_tokens=20000  
    )