from openai import OpenAI


# 游戏的基本策略有：占角：角落棋子永远不会被翻转；占边：边缘棋子相对安全；避免坏位置：某些位置会让对手轻易占角；控制行动力：尽量让对手可选位置少。\
# 常见战术有：星位开局：常见开局方式；边缘推进：从边缘向中间发展；牺牲战术：故意让对手吃子以获得更好位置。\
system_prompt = "你是一名作家，请翻译这段话。"

# 连接VLLM的OpenAI兼容接口
client = OpenAI(
    base_url="http://127.0.0.1:11434/v1",  # 注意路径必须包含/v1
    api_key="dummy",  # VLLM不需要实际API密钥，任意值即可
)

# 测试聊天接口
response = client.chat.completions.create(
    model="qwen3:4b-15360",  # 填写你的模型名称
    messages=[
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": "This is a very peaceful afternoon.",
        },
    ],
)


print(response.choices[0].message.content)  # 能输出结果即表示兼容
