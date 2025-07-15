#!/usr/bin/env python3
"""
FastAPI Web Crawler API Server - Simplified Production Ready
Serves as the main API endpoint for the Enhanced Web Crawler with Sitemap Discovery
Enhanced with in-memory caching, rate limiting, monitoring, and robust error handling
"""

import asyncio
import json
import logging
import os
import sys
import time
import hashlib
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from contextlib import asynccontextmanager
import gc
import psutil
from functools import wraps, lru_cache
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
import threading
import pickle
import zlib

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import uvicorn
import validators
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from urllib.parse import urljoin, urlparse

# Import the crawler from the existing module
from crawler import EnhancedWebCrawler, CrawlResult

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
class Config:
    # Cache configuration
    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))  # Max cache entries
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = os.getenv('RATE_LIMIT_REQUESTS', '10/minute')
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    
    # Security
    API_KEY_ENABLED = os.getenv('API_KEY_ENABLED', 'false').lower() == 'true'
    API_KEY = os.getenv('API_KEY', 'your-secret-api-key')
    
    # Performance
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))  # 5 minutes
    MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', '2048'))
    
    # Monitoring
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

config = Config()

# Global variables
start_time = time.time()
active_crawls: Dict[str, asyncio.Task] = {}
thread_pool = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)

# In-memory cache with TTL
class MemoryCache:
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def _is_expired(self, key: str) -> bool:
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self.timestamps.items():
            if current_time - timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def _enforce_size_limit(self):
        """Remove oldest entries if cache exceeds max size"""
        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            self.cache.pop(oldest_key)
            self.timestamps.pop(oldest_key, None)
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.cache or self._is_expired(key):
                self.misses += 1
                if key in self.cache:
                    self.cache.pop(key)
                    self.timestamps.pop(key, None)
                return None
            
            # Move to end (mark as recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value
    
    def set(self, key: str, value: Any) -> None:
        with self.lock:
            # Compress large values
            if isinstance(value, (dict, list)) and len(str(value)) > 1024:
                compressed_value = zlib.compress(pickle.dumps(value))
                self.cache[key] = compressed_value
            else:
                self.cache[key] = value
            
            self.timestamps[key] = time.time()
            
            # Move to end
            self.cache.move_to_end(key)
            
            # Cleanup and enforce limits
            self._cleanup_expired()
            self._enforce_size_limit()
    
    def delete(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                self.timestamps.pop(key, None)
                return True
            return False
    
    def clear(self) -> int:
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self.timestamps.clear()
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
                "ttl_seconds": self.ttl
            }

# Initialize cache
memory_cache = MemoryCache(max_size=config.CACHE_MAX_SIZE, ttl=config.CACHE_TTL)

# Cache manager
class CacheManager:
    def __init__(self, cache: MemoryCache):
        self.cache = cache
    
    def _get_cache_key(self, request: 'ScrapeRequest') -> str:
        """Generate cache key from request parameters"""
        request_dict = request.dict()
        # Remove non-cacheable parameters
        request_dict.pop('delay_between_requests', None)
        request_dict.pop('max_concurrent', None)
        
        # Create hash from sorted request parameters
        request_str = json.dumps(request_dict, sort_keys=True)
        request_hash = hashlib.md5(request_str.encode()).hexdigest()
        return f"request:{request_hash}"
    
    def get_cached_result(self, request: 'ScrapeRequest') -> Optional['ScrapeResponse']:
        """Get cached result if available"""
        try:
            cache_key = self._get_cache_key(request)
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                # Handle compressed data
                if isinstance(cached_data, bytes):
                    try:
                        decompressed = zlib.decompress(cached_data)
                        result_dict = pickle.loads(decompressed)
                    except:
                        return None
                else:
                    result_dict = cached_data
                
                return ScrapeResponse(**result_dict)
            
            return None
        except Exception as e:
            logger.error("Cache retrieval failed", error=str(e))
            return None
    
    def cache_result(self, request: 'ScrapeRequest', response: 'ScrapeResponse') -> None:
        """Cache the result"""
        try:
            cache_key = self._get_cache_key(request)
            self.cache.set(cache_key, response.dict())
            logger.info("Result cached successfully", cache_key=cache_key)
        except Exception as e:
            logger.error("Cache storage failed", error=str(e))
    
    def invalidate_cache(self, pattern: str = None) -> int:
        """Invalidate cache entries"""
        try:
            if pattern:
                # Simple pattern matching for keys
                deleted = 0
                keys_to_delete = []
                
                with self.cache.lock:
                    for key in self.cache.cache.keys():
                        if pattern in key:
                            keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    if self.cache.delete(key):
                        deleted += 1
                
                logger.info("Cache invalidated", deleted_keys=deleted, pattern=pattern)
                return deleted
            else:
                deleted = self.cache.clear()
                logger.info("Cache cleared", deleted_keys=deleted)
                return deleted
        except Exception as e:
            logger.error("Cache invalidation failed", error=str(e))
            return 0

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_REQUESTS]
)

# Security
security = HTTPBearer(auto_error=False)

async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate API key if enabled"""
    if not config.API_KEY_ENABLED:
        return None
    
    if not credentials or credentials.credentials != config.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return credentials.credentials

# Monitoring middleware
class MonitoringMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        self.request_count += 1
        
        try:
            response = await call_next(request)
            if response.status_code >= 400:
                self.error_count += 1
            return response
        except Exception as e:
            self.error_count += 1
            raise
        finally:
            # Log slow requests
            duration = time.time() - start_time
            if duration > 10:  # Log requests taking more than 10 seconds
                logger.warning("Slow request detected", 
                             path=request.url.path,
                             duration=duration)

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    
    # Startup
    logger.info("Starting Enhanced Web Crawler API")
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        # Cancel active crawls
        for task in active_crawls.values():
            task.cancel()
        
        # Close thread pool
        thread_pool.shutdown(wait=True)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Enhanced Web Crawler API")
    
    # Cancel active crawls
    for task in active_crawls.values():
        task.cancel()
    
    # Close thread pool
    thread_pool.shutdown(wait=True)

# FastAPI app initialization
app = FastAPI(
    title="Enhanced Web Crawler API",
    description="A powerful web scraping API with sitemap discovery, in-memory caching, and intelligent content extraction",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middlewares
app.add_middleware(MonitoringMiddleware)


if config.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models (keeping original structure)
class ScrapeRequest(BaseModel):
    base_url: str = Field(..., description="The base URL to scrape")
    max_subdomains: int = Field(default=5, ge=0, le=50, description="Maximum number of subdomains to discover (0-50)")
    max_pages: int = Field(default=100, ge=1, le=1000, description="Maximum pages per domain (1-1000)")
    max_concurrent: int = Field(default=10, ge=1, le=50, description="Maximum concurrent requests (1-50)")
    delay_between_requests: float = Field(default=1.0, ge=0.1, le=10.0, description="Delay between requests in seconds (0.1-10.0)")
    max_memory_mb: int = Field(default=1000, ge=100, le=2000, description="Maximum memory usage in MB (100-2000)")
    prefer_sitemap: bool = Field(default=True, description="Prefer sitemap over manual crawling")
    sitemap_override: Optional[str] = Field(default=None, description="Direct URL to a specific sitemap.xml file")
    include_content: bool = Field(default=True, description="Include full content in response")
    include_links: bool = Field(default=True, description="Include extracted links in response")
    include_metadata: bool = Field(default=True, description="Include metadata in response")
    use_cache: bool = Field(default=True, description="Use cached results if available")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not validators.url(v):
            raise ValueError('Invalid URL format!')
        return v
    
    @validator('sitemap_override')
    def validate_sitemap_override(cls, v):
        if v and not validators.url(v):
            raise ValueError('Invalid sitemap URL format!')
        return v

class SubdomainResult(BaseModel):
    subdomain: str
    pages_crawled: int
    content_preview: str
    summary: Optional[str] = None
    error: Optional[str] = None

class CrawlMetadata(BaseModel):
    crawl_time: str
    base_url: str
    total_pages: int
    discovered_subdomains: List[str]
    sitemap_urls_found: int
    crawl_method: str
    resource_stats: Dict
    processing_time_seconds: float
    cache_hit: bool = False
    memory_peak_mb: Optional[float] = None

class CrawlResultResponse(BaseModel):
    url: str
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[Dict] = None
    crawl_time: str
    content_hash: str
    word_count: int
    links: Optional[List[str]] = None
    error: Optional[str] = None

class ScrapeResponse(BaseModel):
    success: bool
    message: str
    metadata: CrawlMetadata
    results: List[CrawlResultResponse]
    subdomains_results: Optional[List[SubdomainResult]] = None
    sitemap_urls: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    memory_usage_mb: float
    active_crawls: int
    cache_stats: Dict[str, Any]

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: str
    request_id: Optional[str] = None

# Initialize cache manager
cache_manager = CacheManager(memory_cache)

# Utility functions
def get_request_id() -> str:
    """Generate unique request ID"""
    return hashlib.md5(f"{time.time()}{os.getpid()}".encode()).hexdigest()[:8]

def monitor_memory() -> Dict[str, Any]:
    """Monitor memory usage"""
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        'rss_mb': memory_info.rss / 1024 / 1024,
        'vms_mb': memory_info.vms / 1024 / 1024,
        'percent': process.memory_percent(),
        'available_mb': psutil.virtual_memory().available / 1024 / 1024
    }

def filter_response_data(results: List[CrawlResult], request: ScrapeRequest) -> List[CrawlResultResponse]:
    """Filter and format response data based on request parameters"""
    filtered_results = []
    
    for result in results:
        response_result = CrawlResultResponse(
            url=result.url,
            title=result.title,
            content=result.content if request.include_content else None,
            summary=result.summary,
            metadata=result.metadata if request.include_metadata else None,
            crawl_time=result.crawl_time,
            content_hash=result.content_hash,
            word_count=result.word_count,
            links=result.links if request.include_links else None,
            error=result.error
        )
        filtered_results.append(response_result)
    
    return filtered_results

def extract_subdomain_results(results: List[CrawlResult], base_domain: str) -> List[SubdomainResult]:
    """Extract subdomain-specific results"""
    subdomain_results = []
    subdomain_groups = {}
    
    for result in results:
        parsed_url = urlparse(result.url)
        subdomain = parsed_url.netloc
        
        if subdomain != base_domain:
            if subdomain not in subdomain_groups:
                subdomain_groups[subdomain] = []
            subdomain_groups[subdomain].append(result)
    
    for subdomain, subdomain_results_list in subdomain_groups.items():
        combined_content = " ".join([r.content[:200] for r in subdomain_results_list if r.content])
        combined_summary = " ".join([r.summary for r in subdomain_results_list if r.summary])
        
        subdomain_result = SubdomainResult(
            subdomain=subdomain,
            pages_crawled=len(subdomain_results_list),
            content_preview=combined_content[:500] + "..." if len(combined_content) > 500 else combined_content,
            summary=combined_summary[:300] + "..." if len(combined_summary) > 300 else combined_summary,
            error=None
        )
        subdomain_results.append(subdomain_result)
    
    return subdomain_results

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Enhanced Web Crawler API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    memory_info = monitor_memory()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0",
        uptime_seconds=time.time() - start_time,
        memory_usage_mb=memory_info['rss_mb'],
        active_crawls=len(active_crawls),
        cache_stats=memory_cache.get_stats()
    )

@app.post("/scrape", response_model=ScrapeResponse)
@limiter.limit(config.RATE_LIMIT_REQUESTS)
async def scrape_url(
    request: Request,
    scrape_request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    api_key: Optional[str] = Depends(get_api_key)
):
    """Main scraping endpoint that processes a URL and returns structured content"""
    request_id = get_request_id()
    request_start_time = time.time()
    
    try:
        logger.info("Starting scrape request", 
                   request_id=request_id,
                   base_url=scrape_request.base_url,
                   max_pages=scrape_request.max_pages)
        
        # Check cache first
        cached_result = None
        if scrape_request.use_cache:
            cached_result = cache_manager.get_cached_result(scrape_request)
            if cached_result:
                logger.info("Cache hit", request_id=request_id)
                cached_result.metadata.cache_hit = True
                return cached_result
        
        # Memory check
        memory_info = monitor_memory()
        if memory_info['rss_mb'] > config.MAX_MEMORY_MB:
            raise HTTPException(
                status_code=503,
                detail="Server memory usage too high. Please try again later."
            )
        
        # Create crawler with timeout
        crawler = EnhancedWebCrawler(
            base_url=scrape_request.base_url,
            max_subdomains=scrape_request.max_subdomains,
            max_pages_per_domain=scrape_request.max_pages,
            max_concurrent=scrape_request.max_concurrent,
            delay_between_requests=scrape_request.delay_between_requests,
            output_file=f"crawl_{request_id}_{int(time.time())}.json",
            max_memory_mb=scrape_request.max_memory_mb,
            prefer_sitemap=scrape_request.prefer_sitemap
        )
        
        # Override sitemap if provided
        if scrape_request.sitemap_override:
            crawler.sitemap_discovery.sitemap_locations.insert(0, scrape_request.sitemap_override)
        
        # Track active crawl
        crawl_task = asyncio.create_task(crawler.crawl())
        active_crawls[request_id] = crawl_task
        
        try:
            # Execute crawling with timeout
            results = await asyncio.wait_for(crawl_task, timeout=config.REQUEST_TIMEOUT)
            
        except asyncio.TimeoutError:
            logger.error("Crawl timeout", request_id=request_id)
            raise HTTPException(
                status_code=408,
                detail="Request timed out. The website may be slow or unresponsive."
            )
        
        finally:
            # Remove from active crawls
            active_crawls.pop(request_id, None)
        
        processing_time = time.time() - request_start_time
        memory_peak = monitor_memory()['rss_mb']
        
        # Extract base domain
        base_domain = urlparse(scrape_request.base_url).netloc
        
        # Create metadata
        metadata = CrawlMetadata(
            crawl_time=datetime.now().isoformat(),
            base_url=scrape_request.base_url,
            total_pages=len(results),
            discovered_subdomains=list(crawler.discovered_subdomains),
            sitemap_urls_found=len(crawler.sitemap_urls),
            crawl_method=crawler.crawl_method,
            resource_stats=crawler.resource_monitor.get_stats(),
            processing_time_seconds=processing_time,
            cache_hit=False,
            memory_peak_mb=memory_peak
        )
        
        # Filter and format results
        formatted_results = filter_response_data(results, scrape_request)
        
        # Extract subdomain results
        subdomains_results = None
        if scrape_request.max_subdomains > 0 and crawler.discovered_subdomains:
            subdomains_results = extract_subdomain_results(results, base_domain)
        
        # Create response
        response = ScrapeResponse(
            success=True,
            message=f"Successfully crawled {len(results)} pages using {crawler.crawl_method} method",
            metadata=metadata,
            results=formatted_results,
            subdomains_results=subdomains_results,
            sitemap_urls=list(crawler.sitemap_urls) if crawler.sitemap_urls else None
        )
        
        # Cache result asynchronously
        if scrape_request.use_cache:
            background_tasks.add_task(cache_manager.cache_result, scrape_request, response)
        
        # Schedule cleanup
        if crawler.output_file and os.path.exists(crawler.output_file):
            background_tasks.add_task(cleanup_temp_file, crawler.output_file)
        
        logger.info("Scrape completed successfully",
                   request_id=request_id,
                   pages_crawled=len(results),
                   processing_time=processing_time,
                   memory_peak_mb=memory_peak)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Scrape request failed",
                    request_id=request_id,
                    base_url=scrape_request.base_url,
                    error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/scrape/status")
async def scrape_status():
    """Get status of active scraping operations"""
    memory_info = monitor_memory()
    return {
        "active_crawls": len(active_crawls),
        "uptime_seconds": time.time() - start_time,
        "memory_usage_mb": memory_info['rss_mb'],
        "memory_percent": memory_info['percent'],
        "available_memory_mb": memory_info['available_mb'],
        "cache_stats": memory_cache.get_stats()
    }

@app.delete("/cache")
async def clear_cache(
    pattern: Optional[str] = None,
    api_key: Optional[str] = Depends(get_api_key)
):
    """Clear cache entries"""
    deleted = cache_manager.invalidate_cache(pattern)
    
    return {
        "message": f"Cache cleared: {deleted} entries deleted",
        "deleted_count": deleted,
        "cache_stats": memory_cache.get_stats()
    }

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    return {
        "cache_stats": memory_cache.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            message=exc.detail,
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error("Unhandled exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred",
            timestamp=datetime.now().isoformat(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )

async def cleanup_temp_file(filepath: str):
    """Background task to clean up temporary files"""
    try:
        await asyncio.sleep(300)  # Wait 5 minutes
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info("Cleaned up temporary file", filepath=filepath)
    except Exception as e:
        logger.warning("Failed to clean up temporary file", filepath=filepath, error=str(e))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Web Crawler API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    
    args = parser.parse_args()
    
    print("Enhanced Web Crawler API Server v2.0.0 (Simplified)")
    print("=" * 60)
    print(f"Starting server on {args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Health Check: http://{args.host}:{args.port}/health")
    print(f"Cache Stats: http://{args.host}:{args.port}/cache/stats")
    print("=" * 60)
    
    # Required packages (simplified)
    required_packages = [
        'fastapi>=0.104.0',
        'uvicorn[standard]>=0.24.0',
        'pydantic>=2.0.0',
        'validators>=0.22.0',
        'aiohttp>=3.8.0',
        'beautifulsoup4>=4.12.0',
        'trafilatura>=1.6.0',
        'psutil>=5.9.0',
        'slowapi>=0.1.9',
        'structlog>=23.0.0',
    ]
    
    print("\nRequired packages:")
    print("pip install " + " ".join(required_packages))
    
    print("\nEnvironment variables (optional):")
    print("API_KEY_ENABLED=true")
    print("API_KEY=your-secret-api-key")
    print("RATE_LIMIT_REQUESTS=10/minute")
    print("CACHE_TTL=3600")
    print("CACHE_MAX_SIZE=1000")
    print("MAX_MEMORY_MB=2048")
    print("LOG_LEVEL=INFO")
    
    print("\nExample API Usage:")
    print("# Basic scrape request")
    print("curl -X POST 'http://localhost:8000/scrape' \\")
    print("  -H 'Content-Type: application/json' \\")
    if config.API_KEY_ENABLED:
        print(f"  -H 'Authorization: Bearer {config.API_KEY}' \\")
    print("  -d '{")
    print('    "base_url": "https://example.com",')
    print('    "max_pages": 50,')
    print('    "prefer_sitemap": true,')
    print('    "use_cache": true')
    print("  }'")
    print()
    
    print("# Health check")
    print("curl http://localhost:8000/health")
    print()
    
    print("# Cache statistics")
    print("curl http://localhost:8000/cache/stats")
    print()
    
    print("# Clear cache")
    print("curl -X DELETE 'http://localhost:8000/cache'")
    if config.API_KEY_ENABLED:
        print(f"  -H 'Authorization: Bearer {config.API_KEY}'")
    print()
    
    print("Features included:")
    print("✓ In-memory caching with TTL and LRU eviction")
    print("✓ Rate limiting and API key authentication")
    print("✓ Memory monitoring and resource management")
    print("✓ Structured logging and error handling")
    print("✓ Background task processing")
    print("✓ Health checks and status monitoring")
    print("✓ Automatic cleanup and garbage collection")
    print("✓ Request timeout and concurrent request management")
    print()
    
    # Run the server
    uvicorn.run(
        "__main__:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        log_level=args.log_level.lower(),
        access_log=True,
        server_header=False,
        date_header=False
    )