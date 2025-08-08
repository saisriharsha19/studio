"""
Performance optimization utilities for Prompt Forge
Includes caching, connection pooling, and batch processing
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import logging

import aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

logger = logging.getLogger(__name__)

class CacheManager:
    """Advanced caching manager with TTL, invalidation, and compression"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.cache_stats = {"hits": 0, "misses": 0, "errors": 0}
    
    async def get(self, key: str, default=None) -> Any:
        """Get value from cache with stats tracking"""
        try:
            value = await self.redis.get(key)
            if value is not None:
                self.cache_stats["hits"] += 1
                return json.loads(value)
            else:
                self.cache_stats["misses"] += 1
                return default
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: int = 3600, compress: bool = False) -> bool:
        """Set value in cache with optional compression"""
        try:
            serialized = json.dumps(value, default=str)
            
            if compress and len(serialized) > 1024:  # Compress if > 1KB
                import gzip
                serialized = gzip.compress(serialized.encode()).decode('latin1')
                key = f"compressed:{key}"
            
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2)
        }

class ConnectionPoolManager:
    """Database connection pool manager with health checks"""
    
    def __init__(self, engine, max_connections: int = 20):
        self.engine = engine
        self.max_connections = max_connections
        self.active_connections = 0
        self.connection_stats = {
            "total_created": 0,
            "total_closed": 0,
            "errors": 0,
            "avg_response_time": 0.0
        }
    
    async def get_session(self) -> AsyncSession:
        """Get database session with connection tracking"""
        start_time = time.time()
        
        try:
            session = AsyncSession(self.engine)
            self.active_connections += 1
            self.connection_stats["total_created"] += 1
            
            # Update average response time
            response_time = time.time() - start_time
            current_avg = self.connection_stats["avg_response_time"]
            total_requests = self.connection_stats["total_created"]
            self.connection_stats["avg_response_time"] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
            
            return session
        except Exception as e:
            self.connection_stats["errors"] += 1
            logger.error(f"Database connection error: {e}")
            raise
    
    async def close_session(self, session: AsyncSession):
        """Close database session"""
        try:
            await session.close()
            self.active_connections -= 1
            self.connection_stats["total_closed"] += 1
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            session = await self.get_session()
            start_time = time.time()
            
            # Simple query to test connection
            result = await session.execute(text("SELECT 1"))
            response_time = time.time() - start_time
            
            await self.close_session(session)
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "active_connections": self.active_connections,
                "stats": self.connection_stats
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "active_connections": self.active_connections
            }

class BatchProcessor:
    """Batch processing utility for AI API calls"""
    
    def __init__(self, batch_size: int = 10, timeout: float = 5.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self.pending_requests = []
        self.batch_lock = asyncio.Lock()
    
    async def add_request(self, request_data: Dict[str, Any], callback: Callable) -> Any:
        """Add request to batch queue"""
        request_future = asyncio.Future()
        
        async with self.batch_lock:
            self.pending_requests.append({
                "data": request_data,
                "callback": callback,
                "future": request_future,
                "timestamp": time.time()
            })
            
            # Process batch if full or timeout reached
            if (len(self.pending_requests) >= self.batch_size or 
                self._should_process_batch()):
                await self._process_batch()
        
        return await request_future
    
    def _should_process_batch(self) -> bool:
        """Check if batch should be processed based on timeout"""
        if not self.pending_requests:
            return False
        
        oldest_request_time = min(req["timestamp"] for req in self.pending_requests)
        return time.time() - oldest_request_time >= self.timeout
    
    async def _process_batch(self):
        """Process all pending requests in batch"""
        if not self.pending_requests:
            return
        
        batch = self.pending_requests.copy()
        self.pending_requests.clear()
        
        logger.info(f"Processing batch of {len(batch)} requests")
        
        # Process all requests concurrently
        tasks = []
        for request in batch:
            task = asyncio.create_task(
                self._process_single_request(request)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_request(self, request: Dict[str, Any]):
        """Process a single request"""
        try:
            result = await request["callback"](request["data"])
            request["future"].set_result(result)
        except Exception as e:
            request["future"].set_exception(e)

class SmartCache:
    """Smart caching decorator with automatic invalidation"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def cached(self, 
               ttl: int = 3600, 
               key_prefix: str = "", 
               invalidate_on: List[str] = None,
               compress: bool = False):
        """
        Caching decorator
        
        Args:
            ttl: Time to live in seconds
            key_prefix: Prefix for cache key
            invalidate_on: List of events that should invalidate this cache
            compress: Whether to compress large values
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                key_parts = [key_prefix, func.__name__]
                
                # Add arguments to key
                for arg in args:
                    if isinstance(arg, (str, int, float, bool)):
                        key_parts.append(str(arg))
                    else:
                        key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
                
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}:{v}")
                
                cache_key = ":".join(filter(None, key_parts))
                
                # Try to get from cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.cache_manager.set(cache_key, result, ttl, compress)
                
                return result
            
            return wrapper
        return decorator

class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "request_count": 0,
            "total_response_time": 0.0,
            "error_count": 0,
            "slow_requests": 0,
            "endpoint_stats": {}
        }
        self.slow_request_threshold = 5.0  # 5 seconds
    
    def record_request(self, endpoint: str, response_time: float, success: bool = True):
        """Record request metrics"""
        self.metrics["request_count"] += 1
        self.metrics["total_response_time"] += response_time
        
        if not success:
            self.metrics["error_count"] += 1
        
        if response_time > self.slow_request_threshold:
            self.metrics["slow_requests"] += 1
        
        # Track per-endpoint stats
        if endpoint not in self.metrics["endpoint_stats"]:
            self.metrics["endpoint_stats"][endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "errors": 0,
                "avg_time": 0.0
            }
        
        endpoint_stats = self.metrics["endpoint_stats"][endpoint]
        endpoint_stats["count"] += 1
        endpoint_stats["total_time"] += response_time
        endpoint_stats["avg_time"] = endpoint_stats["total_time"] / endpoint_stats["count"]
        
        if not success:
            endpoint_stats["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total_requests = self.metrics["request_count"]
        avg_response_time = (
            self.metrics["total_response_time"] / total_requests 
            if total_requests > 0 else 0
        )
        error_rate = (
            self.metrics["error_count"] / total_requests * 100 
            if total_requests > 0 else 0
        )
        
        return {
            "total_requests": total_requests,
            "avg_response_time": round(avg_response_time, 3),
            "error_rate": round(error_rate, 2),
            "slow_requests": self.metrics["slow_requests"],
            "endpoints": self.metrics["endpoint_stats"]
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            "request_count": 0,
            "total_response_time": 0.0,
            "error_count": 0,
            "slow_requests": 0,
            "endpoint_stats": {}
        }

class RequestThrottler:
    """Intelligent request throttling based on system load"""
    
    def __init__(self, max_concurrent: int = 50, university_limits: Dict[str, int] = None):
        self.max_concurrent = max_concurrent
        self.university_limits = university_limits or {}
        self.active_requests = {}
        self.request_semaphore = asyncio.Semaphore(max_concurrent)
        self.university_semaphores = {}
    
    async def acquire(self, university_code: str) -> bool:
        """Acquire throttling permission"""
        # Global throttling
        await self.request_semaphore.acquire()
        
        # University-specific throttling
        if university_code in self.university_limits:
            if university_code not in self.university_semaphores:
                limit = self.university_limits[university_code]
                self.university_semaphores[university_code] = asyncio.Semaphore(limit)
            
            await self.university_semaphores[university_code].acquire()
        
        # Track active requests
        if university_code not in self.active_requests:
            self.active_requests[university_code] = 0
        self.active_requests[university_code] += 1
        
        return True
    
    def release(self, university_code: str):
        """Release throttling permission"""
        self.request_semaphore.release()
        
        if university_code in self.university_semaphores:
            self.university_semaphores[university_code].release()
        
        if university_code in self.active_requests:
            self.active_requests[university_code] -= 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get throttling status"""
        return {
            "global_active": self.max_concurrent - self.request_semaphore._value,
            "university_active": self.active_requests,
            "global_limit": self.max_concurrent,
            "university_limits": self.university_limits
        }

# Utility functions
def performance_timer(func):
    """Decorator to time function execution"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper

async def warm_up_cache(cache_manager: CacheManager, university_configs: List[Dict]):
    """Warm up cache with frequently accessed data"""
    logger.info("Starting cache warm-up...")
    
    for config in university_configs:
        cache_key = f"university_config:{config['code']}"
        await cache_manager.set(cache_key, config, ttl=7200)  # 2 hours
    
    logger.info(f"Cache warmed up with {len(university_configs)} university configs")

def generate_cache_key(*args, **kwargs) -> str:
    """Generate consistent cache key from arguments"""
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    return ":".join(key_parts)