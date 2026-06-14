import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 加载 .env 文件中的变量
load_dotenv()

# 2. 从环境变量中获取配置
# 使用 os.getenv("变量名", "默认值") 增加鲁棒性
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("OPENAI_MODEL", "gpt-5.4")
reasoning_effort = os.getenv("REASONING_EFFORT", "medium")
# 将字符串 "true" 转换为布尔值，并映射到 OpenAI 的 store 参数

# 3. 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

def get_chat_response(prompt):
    try:
        # 4. 发起调用
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            # 这里的参数根据你的 .env 动态传入
            reasoning_effort=reasoning_effort,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"发生错误: {str(e)}"

# 测试调用
if __name__ == "__main__":
    user_input = "请介绍你的模型型号，并指出你是否具有识图能力。"
    result = get_chat_response(user_input)
    print(f"模型回复:\n{result}")