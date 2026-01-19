from openai import OpenAI
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import requests

# 游戏的基本策略有：占角：角落棋子永远不会被翻转；占边：边缘棋子相对安全；避免坏位置：某些位置会让对手轻易占角；控制行动力：尽量让对手可选位置少。\
# 常见战术有：星位开局：常见开局方式；边缘推进：从边缘向中间发展；牺牲战术：故意让对手吃子以获得更好位置。\
system_prompt = "You are an ai assistant."


def extract_think_content(text):
    pattern = r"<think>(.*?)</think>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else ""


def remove_think_content(text):
    """删除所有<think>标签及其内容，保留剩余部分"""
    pattern = r"<think>.*?</think>"
    # 使用 re.DOTALL 让 .* 匹配换行符
    cleaned_text = re.sub(pattern, "", text, flags=re.DOTALL)
    return cleaned_text.strip()


def query_requests(api_base, api_key, llm_name, system_prompt, user_prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try_ct = 0
    while try_ct < 3:
        # 生成答案
        payload = {
            "model": llm_name,
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        }
                    ],
                },
            ],
            "stream": False,
            # "max_completion_tokens": 512,
            # "thinking_budget": 1024,
            "response_format": {"type": "text"},
            "enable_thinking": True,
        }
        # if llm_name == "claude-sonnet-4-5-20250929":
        #     del payload["messages"][0]
        #     payload["system"] = system_prompt

        print(payload)

        llm_response = requests.post(api_base, json=payload, headers=headers)
        response_json = json.loads(llm_response.text)

        responsed_text = response_json["choices"][0]["message"]["content"]
        reasoning_text = ""

        reasoning_text = response_json["choices"][0]["message"].get(
            "reasoning_content", ""
        )
        if not reasoning_text:
            reasoning_text = extract_think_content(responsed_text)
            if responsed_text:
                responsed_text = remove_think_content(responsed_text)
        return response_json, responsed_text, reasoning_text


online_llms = {
    "Qwen3_235_Thinking": "qwen3-235b-a22b-thinking-2507",
    "Qwen3_235_Instruct": "qwen3-235b-a22b-instruct-2507",
    "DeepSeek3.2": "deepseek-v3.2",
    "Gemini3Pro_Preview": "gemini-3-pro-preview",
    "ClaudeSonnet4.5": "claude-sonnet-4-5-20250929",
    "GPT5.2": "gpt-5.2-2025-12-11",
}


model_name = "gpt-5.2-2025-12-11"

with open("../api_config/vllm_conf.json", "r") as f:
    json_data = json.load(f)
api_base = json_data["api_base"]
api_key = json_data["api_key"]

responsed_json, responsed_text, reasoning_text = query_requests(
    api_base,
    api_key,
    model_name,
    system_prompt,
    "Who are you?",
)


print(responsed_json)

print(responsed_text)  # 能输出结果即表示兼容

print(reasoning_text)  # 能输出结果即表示兼容
