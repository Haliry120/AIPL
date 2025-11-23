import siliconflow_client  
  
  
def create_roadmap(topic, time, knowledge_level):  
    """使用硅基流动API生成学习路线图"""  
      
    # 系统指令  
    system_instruction = '''You are an AI agent who provides good personalized learning paths based on user input. You have to provide subtopics to learn with a small description of the subtopic telling what exactly to learn and how much time each subtopic will take. Give more time to subtopics that require more understanding. One more important thing, make sure to keep every key lowercase   
Example output:  
{  
  "week 1": {  
    "topic":"Introduction to Python",  
    "subtopics":[  
      {  
        "subtopic":"Getting Started with Python",  
        "time":"10 minute",  
        "description":"Learn Hello world in python"  
      },  
      {  
        "subtopic":"Data types in Python",  
        "time":"1 hour",  
        "description":"Learn about int, string, boolean, array, dict and casting data types"  
      }  
    ]  
  }  
}'''  
      
    # 用户提示  
    user_prompt = f"Suggest a roadmap for learning {topic} in {time}. My Knowledge level is {knowledge_level}. I can spend total of 16 hours every week."  
      
    # 使用客户端生成 JSON 响应  
    client = siliconflow_client.get_client()  
    return client.generate_json(  
        system_instruction=system_instruction,  
        user_prompt=user_prompt,  
        temperature=1,  
        top_p=0.95,  
        max_tokens=8192  
    )