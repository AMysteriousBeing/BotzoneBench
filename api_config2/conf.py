import json
import os
from openai import OpenAI
import requests
import time
import re


def access_mode_and_llm():
    """
    Docstring for access_mode_and_llm
    access_mode: lab_openai_chinese, lab_openai_foreign, silicon_flow, local_vllm
    Return access_mode and llm_name
    """
    if os.path.exists("/data/llm_config.json"):
        with open("/data/llm_config.json", "r") as f:
            json_data = json.load(f)
        access_mode = json_data["api_access"]
        llm_name = json_data["llm_name"]
        return access_mode, llm_name
    else:
        return None, None


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


def query_openai(api_base, api_key, llm_name, system_prompt, user_prompt):
    # 连接VLLM的OpenAI兼容接口
    client = OpenAI(
        base_url=api_base,  # 注意路径必须包含/v1
        api_key=api_key,  # VLLM不需要实际API密钥，任意值即可
    )
    response = client.chat.completions.create(
        model=llm_name,
        messages=[
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
    )
    # 提取答案
    responsed_text = response.choices[0].message.content
    return responsed_text


def query_requests(api_base, api_key, llm_name, system_prompt, user_prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    max_try = 5
    try_ct = 0
    while try_ct < max_try:
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
            # "max_completion_tokens": 4096,
            # "thinking_budget": 2048,
            "response_format": {"type": "text"},
        }
        # if llm_name == "claude-sonnet-4-5-20250929":
        #     del payload["messages"][0]
        #     payload["system"] = system_prompt

        llm_response = requests.post(api_base, json=payload, headers=headers)
        response_json = json.loads(llm_response.text)
        # 检查响应结构
        if "choices" in response_json:
            try_ct = max_try
        try_ct += 1
        time.sleep(3)
    # 提取答案
    responsed_text = response_json["choices"][0]["message"]["content"]
    reasoning_text = response_json["choices"][0]["message"].get("reasoning_content", "")
    if not reasoning_text:
        reasoning_text = extract_think_content(responsed_text)
        if responsed_text:
            responsed_text = remove_think_content(responsed_text)
    return responsed_text, reasoning_text


def openai_foreign_info():
    """
    Return api_base and key stored in api_config/conf.json
    """

    if os.path.exists("/data/openai_foreign_conf.json"):
        with open("/data/openai_foreign_conf.json", "r") as f:
            json_data = json.load(f)
        api_base = json_data["api_base"]
        api_key = json_data["api_key"]
        return api_base, api_key, query_requests
    else:
        print(f"Error: The required file 'api_config/openai_conf.json' does not exist.")
        return None, None, None


def openai_chinese_info():
    """
    Return api_base and key stored in api_config/conf.json
    """

    if os.path.exists("/data/openai_chinese_conf.json"):
        with open("/data/openai_chinese_conf.json", "r") as f:
            json_data = json.load(f)
        api_base = json_data["api_base"]
        api_key = json_data["api_key"]
        return api_base, api_key, query_requests
    else:
        print(f"Error: The required file 'api_config/openai_conf.json' does not exist.")
        return None, None, None


def silicon_flow_info():
    """
    Return api_base and key stored in api_config/conf.json
    """

    if os.path.exists("/data/silicon_flow_conf.json"):
        with open("/data/silicon_flow_conf.json", "r") as f:
            json_data = json.load(f)
        api_base = json_data["api_base"]
        api_key = json_data["api_key"]
        return api_base, api_key, query_requests
    else:
        print(
            f"Error: The required file 'api_config/silicon_flow_conf.json' does not exist."
        )
        return None, None, None


def local_vllm_info():
    if os.path.exists("/data/vllm_conf.json"):
        with open("/data/vllm_conf.json", "r") as f:
            json_data = json.load(f)
        api_base = json_data["api_base"]
        api_key = json_data["api_key"]
        return api_base, api_key, query_requests
    else:
        print(
            f"Error: The required file 'api_config/silicon_flow_conf.json' does not exist."
        )
        return None, None, None
