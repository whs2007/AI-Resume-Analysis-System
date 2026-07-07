"""应用配置管理"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量/.env 文件读取"""

    # DashScope API
    dashscope_api_key: str = ""

    # Redis
    redis_url: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
