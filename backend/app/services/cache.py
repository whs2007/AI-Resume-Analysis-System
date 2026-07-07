"""缓存服务

缓存策略：
- 以 PDF 文件 MD5 作为缓存 key
- 缓存解析结果 (resume:{md5}) 和匹配结果 (match:{md5}:{jd_hash})
- Redis 可用时使用 Redis（24h TTL），不可用时使用内存缓存
"""

import json
import logging
import time
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# 缓存过期时间
CACHE_TTL = 60 * 60 * 24  # 24 小时


class InMemoryStore:
    """内存缓存（Redis 降级方案）"""

    def __init__(self):
        self._store: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> Optional[dict]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, data = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return data

    def setex(self, key: str, ttl: int, data: dict) -> None:
        self._store[key] = (time.time() + ttl, data)

    def _cleanup(self) -> None:
        """清理过期条目"""
        now = time.time()
        expired = [k for k, (t, _) in self._store.items() if now > t]
        for k in expired:
            del self._store[k]


class CacheService:
    """缓存服务封装，支持 Redis + 内存降级"""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._memory = InMemoryStore()  # 始终可用的内存缓存
        self._redis_ok = False

    async def connect(self) -> None:
        """尝试连接 Redis"""
        if not self._redis_url:
            logger.info("未配置 REDIS_URL，使用内存缓存")
            return

        try:
            self._client = redis.from_url(
                self._redis_url,
                socket_connect_timeout=3,
                socket_timeout=3,
                decode_responses=True,
            )
            await self._client.ping()
            self._redis_ok = True
            logger.info("Redis 连接成功")
        except Exception as e:
            self._client = None
            self._redis_ok = False
            logger.warning(f"Redis 连接失败 ({e})，降级为内存缓存")

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
            self._redis_ok = False

    @property
    def available(self) -> bool:
        """缓存服务永远可用（Redis 或内存）"""
        return True

    @property
    def using_redis(self) -> bool:
        return self._redis_ok and self._client is not None

    async def get_resume(self, file_hash: str) -> Optional[dict]:
        key = f"resume:{file_hash}"
        if self.using_redis:
            try:
                data = await self._client.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.warning(f"Redis 读取失败: {e}")
        return self._memory.get(key)

    async def set_resume(self, file_hash: str, data: dict) -> None:
        key = f"resume:{file_hash}"
        if self.using_redis:
            try:
                await self._client.setex(key, CACHE_TTL, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"Redis 写入失败: {e}")
        self._memory.setex(key, CACHE_TTL, data)
        logger.info(f"简历已缓存: {file_hash}")

    async def get_match(self, file_hash: str, jd_hash: str) -> Optional[dict]:
        key = f"match:{file_hash}:{jd_hash}"
        if self.using_redis:
            try:
                data = await self._client.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.warning(f"Redis 读取失败: {e}")
        return self._memory.get(key)

    async def set_match(self, file_hash: str, jd_hash: str, data: dict) -> None:
        key = f"match:{file_hash}:{jd_hash}"
        if self.using_redis:
            try:
                await self._client.setex(key, CACHE_TTL, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"Redis 写入失败: {e}")
        self._memory.setex(key, CACHE_TTL, data)
        logger.info(f"匹配结果已缓存: {file_hash}:{jd_hash}")


# 全局缓存实例（在 main.py 中初始化）
cache_service: Optional[CacheService] = None
