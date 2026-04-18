# LLM Configuration
# 存储所有 LLM API 相关配置

# DeepSeek 官方 OpenAI 兼容 Chat Completions
# 文档: https://api-docs.deepseek.com/
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

# API Key 勿写入仓库：本地或 CI 中设置环境变量
#   export DEEPSEEK_API_KEY="sk-..."
import os

# 兼容旧字段名（若有代码引用）
DEEPSEEK_MODEL = "deepseek-chat"


def get_api_key():
    """从环境变量 DEEPSEEK_API_KEY 读取密钥（不在代码库中保存明文）。"""
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key
    raise ValueError(
        "API key not configured. Export DEEPSEEK_API_KEY before running (do not commit keys)."
    )


# 逻辑名 -> 官方 model 字段（见 DeepSeek 文档）
# deepseek-chat: DeepSeek-V3.2 非思考模式
# deepseek-reasoner: DeepSeek-V3.2 思考模式（原 R1 能力）
MODELS = {
    "deepseek-chat": "deepseek-chat",
    "deepseek-v3": "deepseek-chat",
    "deepseek-r1": "deepseek-reasoner",
    "deepseek-reasoner": "deepseek-reasoner",
    "default": "deepseek-chat",
}

# 请求配置
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 4000
MAX_RETRIES = 3
TIMEOUT = 30
