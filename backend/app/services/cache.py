"""Redis 缓存服务

缓存策略：
- 以 PDF 文件 MD5 作为缓存 key
- 缓存解析结果 (resume:{md5}) 和匹配结果 (match:{md5}:{jd_hash})
- TTL 24 小时
- Redis 不可用时自动降级，跳过缓存
"""

import json
import logging
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# 缓存过期时间
CACHE_TTL = 60 * 60 * 24  # 24 小时


class CacheService:
    """Redis 缓存服务封装"""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._available = False

    async def connect(self) -> None:
        """尝试连接 Redis"""
        if not self._redis_url:
            logger.info("未配置 REDIS_URL，缓存功能已禁用")
            return

        try:
            self._client = redis.from_url(
                self._redis_url,
                socket_connect_timeout=3,
                socket_timeout=3,
                decode_responses=True,
            )
            await self._client.ping()
            self._available = True
            logger.info("Redis 连接成功，缓存已启用")
        except Exception as e:
            self._client = None
            self._available = False
            logger.warning(f"Redis 连接失败 ({e})，缓存功能已降级")

    async def disconnect(self) -> None:
        """断开 Redis 连接"""
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    async def get_resume(self, file_hash: str) -> Optional[dict]:
        """获取缓存的简历解析结果"""
        if not self.available:
            return None
        try:
            key = f"resume:{file_hash}"
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"读取简历缓存失败: {e}")
            return None

    async def set_resume(self, file_hash: str, data: dict) -> None:
        """缓存简历解析结果"""
        if not self.available:
            return
        try:
            key = f"resume:{file_hash}"
            await self._client.setex(key, CACHE_TTL, json.dumps(data, ensure_ascii=False))
            logger.info(f"简历解析结果已缓存: {file_hash}")
        except Exception as e:
            logger.warning(f"写入简历缓存失败: {e}")

    async def get_match(self, file_hash: str, jd_hash: str) -> Optional[dict]:
        """获取缓存的匹配结果"""
        if not self.available:
            return None
        try:
            key = f"match:{file_hash}:{jd_hash}"
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"读取匹配缓存失败: {e}")
            return None

    async def set_match(self, file_hash: str, jd_hash: str, data: dict) -> None:
        """缓存匹配结果"""
        if not self.available:
            return
        try:
            key = f"match:{file_hash}:{jd_hash}"
            await self._client.setex(key, CACHE_TTL, json.dumps(data, ensure_ascii=False))
            logger.info(f"匹配结果已缓存: {file_hash}:{jd_hash}")
        except Exception as e:
            logger.warning(f"写入匹配缓存失败: {e}")


# 全局缓存实例（在 main.py 中初始化）
cache_service: Optional[CacheService] = None
