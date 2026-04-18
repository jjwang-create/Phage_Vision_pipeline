# core/api_client.py

import requests
import json
import time
from typing import Dict, Any

class DeepSeekClient:
    def __init__(self, base_url: str, api_key: str, model: str, max_retries=3):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries

    def call(self, system_prompt: str, user_input: str, temperature=0.1, max_tokens=4000) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 添加重试机制
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()

                # 检查API返回结构
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    # 检查message字段是否存在且有content
                    if message.get("content"):
                        content = message["content"]
                    elif message.get("reasoning_content"):
                        # DeepSeek R1 模型使用 reasoning_content 字段
                        content = message["reasoning_content"]
                    else:
                        # 如果message字段为空，返回一个默认响应
                        content = "No response content"
                else:
                    content = "No choices returned"

                return {
                    "content": content,
                    "usage": data.get("usage", {})
                }
            except Exception as e:
                print(f"API call attempt {attempt+1}/{self.max_retries} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    print("Retrying...")
                    time.sleep(2)  # 等待2秒后重试
                else:
                    # 最后一次尝试失败，返回默认响应
                    print("All retry attempts failed")
                    return {
                        "content": "API call failed",
                        "usage": {}
                    }
