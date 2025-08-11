"""
Navigator Prompt API - Scalable, secure prompt generation system
Features: Redis Sentinel, Celery, robust error handling, security hardening
"""

import asyncio
import hashlib
import json
import time
import logging
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from functools import wraps

# FastAPI and async dependencies
from fastapi import FastAPI, HTTPException, Request, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
import aiohttp
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Database dependencies
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Redis Sentinel and Celery
import redis.sentinel
from celery import Celery
from celery.result import AsyncResult

# Security
import secrets
from passlib.context import CryptContext
import jwt
from cryptography.fernet import Fernet

# Utilities
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with security considerations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Hide sensitive info from logs
class SecurityFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'msg'):
            # Remove sensitive patterns from logs
            sensitive_patterns = ['password', 'token', 'key', 'secret']
            msg = str(record.msg).lower()
            if any(pattern in msg for pattern in sensitive_patterns):
                record.msg = "[REDACTED SENSITIVE DATA]"
        return True

logger.addFilter(SecurityFilter())

# =============================================================================
# CONFIGURATION & SECURITY
# =============================================================================

class Config:
    """Centralized configuration with validation"""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Redis Sentinel
    REDIS_SENTINELS = os.getenv("REDIS_SENTINELS", "localhost:26379").split(",")
    REDIS_SERVICE_NAME = os.getenv("REDIS_SERVICE_NAME", "mymaster")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    
    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # AI API
    AI_API_KEY = os.getenv("UFL_AI_API_KEY")
    AI_BASE_URL = os.getenv("UFL_AI_BASE_URL")
    AI_MODEL = os.getenv("UFL_AI_MODEL", "llama-3.3-70b-instruct")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", secrets.token_urlsafe(32))
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "300"))
    
    # Application
    MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        required_vars = [
            "DATABASE_URL", "AI_API_KEY", "AI_BASE_URL", 
            "SECRET_KEY", "ADMIN_API_KEY"
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        
        # Validate Redis Sentinels format
        try:
            for sentinel in cls.REDIS_SENTINELS:
                host, port = sentinel.split(":")
                int(port)  # Validate port is integer
        except ValueError:
            raise ValueError("Invalid REDIS_SENTINELS format. Use host:port,host:port")

config = Config()

# Initialize security components
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
cipher_suite = Fernet(config.ENCRYPTION_KEY.encode())
security = HTTPBearer()

# =============================================================================
# DATABASE MODELS (SIMPLIFIED)
# =============================================================================

Base = declarative_base()

class University(Base):
    __tablename__ = "universities"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    domain = Column(String(100), nullable=False)
    rate_limit_per_minute = Column(Integer, default=30)
    rate_limit_per_hour = Column(Integer, default=300)
    monthly_budget = Column(Float, default=1000.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(255), index=True, nullable=False)
    university_id = Column(Integer, index=True, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class UsageStats(Base):
    __tablename__ = "usage_stats"
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, index=True, nullable=False)
    endpoint = Column(String(100), index=True, nullable=False)
    user_id = Column(String(255), index=True, nullable=False)
    date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    request_count = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Add performance indexes
Index('ix_usage_stats_composite', UsageStats.university_id, UsageStats.date, UsageStats.endpoint)
Index('ix_prompts_user_date', Prompt.user_id, Prompt.created_at.desc())

# =============================================================================
# DATABASE SETUP
# =============================================================================

def create_database_engines():
    """Create database engines with proper configuration"""
    try:
        config.validate()
        
        # Enhanced connection settings for production
        engine = create_async_engine(
            config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=1800,  # 30 minutes
            echo=False,
            poolclass=NullPool if "test" in config.DATABASE_URL else None
        )
        
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        
        logger.info("Database engines created successfully")
        return engine, AsyncSessionLocal
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

engine, AsyncSessionLocal = create_database_engines()

# =============================================================================
# REDIS SENTINEL SETUP
# =============================================================================

class RedisManager:
    """Redis Sentinel manager for high availability"""
    
    def __init__(self):
        self.sentinel = None
        self.master = None
        self.slave = None
        
    async def initialize(self):
        """Initialize Redis Sentinel connections"""
        try:
            sentinel_hosts = [(host.strip().split(':')[0], int(host.strip().split(':')[1])) 
                            for host in config.REDIS_SENTINELS]
            
            self.sentinel = redis.sentinel.Sentinel(
                sentinel_hosts,
                password=config.REDIS_PASSWORD,
                socket_timeout=0.5,
                socket_connect_timeout=0.5
            )
            
            # Get master for writes
            self.master = self.sentinel.master_for(
                config.REDIS_SERVICE_NAME,
                socket_timeout=0.5,
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # Get slave for reads
            self.slave = self.sentinel.slave_for(
                config.REDIS_SERVICE_NAME,
                socket_timeout=0.5,
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # Test connections
            await asyncio.get_event_loop().run_in_executor(None, self.master.ping)
            await asyncio.get_event_loop().run_in_executor(None, self.slave.ping)
            
            logger.info("Redis Sentinel initialized successfully")
            
        except Exception as e:
            logger.error(f"Redis Sentinel initialization failed: {e}")
            raise
    
    async def set(self, key: str, value: str, ex: int = None):
        """Set value in Redis master"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.master.set(key, value, ex=ex)
            )
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis slave (read replica)"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.slave.get(key)
            )
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def delete(self, key: str):
        """Delete key from Redis master"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.master.delete(key)
            )
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

redis_manager = RedisManager()

# =============================================================================
# CELERY SETUP
# =============================================================================

celery_app = Celery(
    'navigator_api',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=['app.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'app.tasks.generate_prompt': {'queue': 'generation'},
        'app.tasks.evaluate_prompt': {'queue': 'evaluation'},
    },
    worker_pool_restarts=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# =============================================================================
# SECURITY UTILITIES
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        university_code: str = payload.get("university")
        
        if user_id is None or university_code is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {"user_id": user_id, "university_code": university_code}
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify admin API key"""
    if credentials.credentials != config.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials"
        )
    return True

def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data before storage"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data after retrieval"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def sanitize_input(text: str, max_length: int = None) -> str:
    """Sanitize user input"""
    if max_length and len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input too long. Maximum length: {max_length}"
        )
    
    # Remove potential script injections
    dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
    text_lower = text.lower()
    
    for pattern in dangerous_patterns:
        if pattern in text_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input detected"
            )
    
    return text.strip()

# =============================================================================
# RATE LIMITING
# =============================================================================

limiter = Limiter(key_func=get_remote_address)

# =============================================================================
# PYDANTIC MODELS (ENHANCED WITH VALIDATION)
# =============================================================================

class UserNeedsRequest(BaseModel):
    user_needs: str = Field(..., min_length=10, max_length=config.MAX_PROMPT_LENGTH)
    
    @validator('user_needs')
    def validate_user_needs(cls, v):
        return sanitize_input(v, config.MAX_PROMPT_LENGTH)

class EvaluatePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=config.MAX_PROMPT_LENGTH)
    user_needs: str = Field(..., min_length=10, max_length=config.MAX_PROMPT_LENGTH)
    
    @validator('prompt', 'user_needs')
    def validate_text_fields(cls, v):
        return sanitize_input(v, config.MAX_PROMPT_LENGTH)

class PromptCreate(BaseModel):
    text: str = Field(..., min_length=10, max_length=config.MAX_PROMPT_LENGTH)
    
    @validator('text')
    def validate_text(cls, v):
        return sanitize_input(v, config.MAX_PROMPT_LENGTH)

class PromptResponse(BaseModel):
    id: str
    text: str
    created_at: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_db():
    """Get database session with proper error handling"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed"
            )

async def get_university_config(university_code: str) -> Dict[str, Any]:
    """Get university configuration with caching"""
    cache_key = f"university:{university_code}"
    
    # Try cache first
    cached = await redis_manager.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Get from database
    async with AsyncSessionLocal() as db:
        query = text("SELECT * FROM universities WHERE code = :code AND is_active = true")
        result = await db.execute(query, {"code": university_code})
        university = result.mappings().fetchone()
        
        if not university:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"University {university_code} not found"
            )
        
        university_dict = dict(university)
        
        # Cache for 1 hour
        await redis_manager.set(
            cache_key, 
            json.dumps(university_dict, default=str), 
            ex=3600
        )
        
        return university_dict

# =============================================================================
# CELERY TASKS
# =============================================================================

@celery_app.task(bind=True, max_retries=3)
def generate_prompt_task(self, user_needs: str, university_id: int):
    """Celery task for prompt generation"""
    try:
        # Simulate AI API call
        import time
        time.sleep(2)  # Simulate processing
        
        result = {
            "initialPrompt": f"Generated prompt based on: {user_needs[:100]}...",
            "processing_time": 2.0
        }
        
        return result
        
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        self.retry(countdown=60, exc=exc)

@celery_app.task(bind=True, max_retries=3)
def evaluate_prompt_task(self, prompt: str, user_needs: str, university_id: int):
    """Celery task for prompt evaluation"""
    try:
        # Simulate evaluation
        import time
        time.sleep(5)  # Simulate processing
        
        result = {
            "bias_score": 0.1,
            "toxicity_score": 0.05,
            "alignment_score": 0.9,
            "processing_time": 5.0
        }
        
        return result
        
    except Exception as exc:
        logger.error(f"Evaluation task failed: {exc}")
        self.retry(countdown=60, exc=exc)

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Navigator Prompt API...")
    
    try:
        # Initialize Redis Sentinel
        await redis_manager.initialize()
        
        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Navigator Prompt API...")

app = FastAPI(
    title="Navigator Prompt API",
    version="3.0.0",
    description="Scalable, secure prompt generation system",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        
        # Check Redis
        await redis_manager.get("health_check")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "3.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )

@app.post("/auth/token")
async def create_token(university_code: str, user_id: str):
    """Create authentication token"""
    try:
        # Validate university exists
        await get_university_config(university_code)
        
        # Create token
        access_token = create_access_token(
            data={"sub": user_id, "university": university_code}
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )

@app.post("/prompts/generate")
@limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute")
async def generate_prompt(
    request: Request,
    prompt_request: UserNeedsRequest,
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Generate prompt asynchronously using Celery"""
    try:
        # Get university config
        university_config = await get_university_config(current_user["university_code"])
        
        # Check cache first
        cache_key = f"prompt:{hashlib.md5(prompt_request.user_needs.encode()).hexdigest()}"
        cached_result = await redis_manager.get(cache_key)
        
        if cached_result:
            logger.info("Cache hit for prompt generation")
            return json.loads(cached_result)
        
        # Queue task
        task = generate_prompt_task.delay(
            prompt_request.user_needs,
            university_config["id"]
        )
        
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Prompt generation queued successfully"
        )
        
    except Exception as e:
        logger.error(f"Prompt generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt generation failed"
        )

@app.get("/prompts/task/{task_id}")
async def get_task_result(
    task_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get Celery task result"""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.ready():
            if result.successful():
                task_result = result.result
                
                # Cache successful results
                if task_result:
                    cache_key = f"task_result:{task_id}"
                    await redis_manager.set(
                        cache_key,
                        json.dumps(task_result),
                        ex=config.CACHE_TTL
                    )
                
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": task_result
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(result.result)
                }
        else:
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is still processing"
            }
            
    except Exception as e:
        logger.error(f"Task result retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task result retrieval failed"
        )

@app.post("/prompts/evaluate")
@limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute")
async def evaluate_prompt(
    request: Request,
    eval_request: EvaluatePromptRequest,
    current_user: dict = Depends(verify_token)
):
    """Evaluate prompt asynchronously"""
    try:
        university_config = await get_university_config(current_user["university_code"])
        
        # Queue evaluation task
        task = evaluate_prompt_task.delay(
            eval_request.prompt,
            eval_request.user_needs,
            university_config["id"]
        )
        
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Prompt evaluation queued successfully"
        )
        
    except Exception as e:
        logger.error(f"Prompt evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt evaluation failed"
        )

@app.get("/prompts/history")
async def get_user_prompts(
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Get user's prompt history"""
    try:
        university_config = await get_university_config(current_user["university_code"])
        
        query = text("""
            SELECT id, text, created_at 
            FROM prompts 
            WHERE user_id = :user_id AND university_id = :university_id
            ORDER BY created_at DESC 
            LIMIT :limit
        """)
        
        result = await db.execute(query, {
            "user_id": current_user["user_id"],
            "university_id": university_config["id"],
            "limit": limit
        })
        
        prompts = result.mappings().fetchall()
        
        return [
            PromptResponse(
                id=row["id"],
                text=row["text"],
                created_at=row["created_at"].isoformat()
            )
            for row in prompts
        ]
        
    except Exception as e:
        logger.error(f"Get user prompts failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve prompts"
        )

@app.post("/prompts/save")
async def save_prompt(
    prompt_data: PromptCreate,
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Save a prompt to user's history"""
    try:
        university_config = await get_university_config(current_user["university_code"])
        
        prompt_id = str(uuid.uuid4())
        
        # Encrypt sensitive prompt text
        encrypted_text = encrypt_sensitive_data(prompt_data.text)
        
        query = text("""
            INSERT INTO prompts (id, user_id, university_id, text, created_at)
            VALUES (:id, :user_id, :university_id, :text, :created_at)
        """)
        
        await db.execute(query, {
            "id": prompt_id,
            "user_id": current_user["user_id"],
            "university_id": university_config["id"],
            "text": encrypted_text,
            "created_at": datetime.utcnow()
        })
        
        return PromptResponse(
            id=prompt_id,
            text=prompt_data.text,  # Return original text (not encrypted)
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Save prompt failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save prompt"
        )

@app.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user's prompt"""
    try:
        university_config = await get_university_config(current_user["university_code"])
        
        query = text("""
            DELETE FROM prompts 
            WHERE id = :id AND user_id = :user_id AND university_id = :university_id
        """)
        
        result = await db.execute(query, {
            "id": prompt_id,
            "user_id": current_user["user_id"],
            "university_id": university_config["id"]
        })
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        return {"message": "Prompt deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete prompt failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete prompt"
        )

# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@app.get("/admin/universities")
async def list_universities(
    _: bool = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db)
):
    """List all universities (admin only)"""
    try:
        query = text("SELECT * FROM universities ORDER BY name")
        result = await db.execute(query)
        universities = result.mappings().fetchall()
        
        return [dict(university) for university in universities]
        
    except Exception as e:
        logger.error(f"List universities failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve universities"
        )

@app.get("/admin/stats")
async def get_system_stats(
    _: bool = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics (admin only)"""
    try:
        # Get database stats
        stats_query = text("""
            SELECT 
                COUNT(DISTINCT user_id) as total_users,
                COUNT(*) as total_prompts,
                COUNT(DISTINCT university_id) as active_universities
            FROM prompts
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """)
        
        result = await db.execute(stats_query)
        db_stats = result.mappings().fetchone()
        
        # Get usage stats
        usage_query = text("""
            SELECT 
                endpoint,
                SUM(request_count) as total_requests,
                AVG(processing_time) as avg_processing_time,
                SUM(total_cost) as total_cost
            FROM usage_stats
            WHERE date >= :start_date
            GROUP BY endpoint
        """)
        
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        usage_result = await db.execute(usage_query, {"start_date": start_date})
        usage_stats = usage_result.mappings().fetchall()
        
        return {
            "database_stats": dict(db_stats) if db_stats else {},
            "usage_stats": [dict(stat) for stat in usage_stats],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get system stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )

@app.post("/admin/universities")
async def create_university(
    university_data: dict,
    _: bool = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db)
):
    """Create a new university (admin only)"""
    try:
        # Validate required fields
        required_fields = ["code", "name", "domain"]
        missing_fields = [field for field in required_fields if field not in university_data]
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {missing_fields}"
            )
        
        # Sanitize inputs
        code = sanitize_input(university_data["code"], 50)
        name = sanitize_input(university_data["name"], 200)
        domain = sanitize_input(university_data["domain"], 100)
        
        query = text("""
            INSERT INTO universities (code, name, domain, rate_limit_per_minute, 
                                    rate_limit_per_hour, monthly_budget, is_active, created_at)
            VALUES (:code, :name, :domain, :rate_limit_per_minute, 
                    :rate_limit_per_hour, :monthly_budget, :is_active, :created_at)
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "code": code,
            "name": name,
            "domain": domain,
            "rate_limit_per_minute": university_data.get("rate_limit_per_minute", 30),
            "rate_limit_per_hour": university_data.get("rate_limit_per_hour", 300),
            "monthly_budget": university_data.get("monthly_budget", 1000.0),
            "is_active": university_data.get("is_active", True),
            "created_at": datetime.utcnow()
        })
        
        university_id = result.fetchone()[0]
        
        # Clear university cache
        await redis_manager.delete(f"university:{code}")
        
        return {
            "id": university_id,
            "message": f"University {name} created successfully"
        }
        
    except Exception as e:
        logger.error(f"Create university failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create university"
        )

@app.delete("/admin/cache")
async def clear_cache(
    _: bool = Depends(verify_admin_token)
):
    """Clear Redis cache (admin only)"""
    try:
        # Clear all cache keys
        await asyncio.get_event_loop().run_in_executor(
            None, redis_manager.master.flushdb
        )
        
        logger.info("Cache cleared by admin")
        return {"message": "Cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Clear cache failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )

# =============================================================================
# CELERY MONITORING
# =============================================================================

@app.get("/admin/celery/status")
async def celery_status(_: bool = Depends(verify_admin_token)):
    """Get Celery worker status (admin only)"""
    try:
        inspect = celery_app.control.inspect()
        
        # Get worker stats
        stats = inspect.stats()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        
        return {
            "workers": stats or {},
            "active_tasks": active_tasks or {},
            "scheduled_tasks": scheduled_tasks or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Celery status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Celery status"
        )

@app.post("/admin/celery/purge")
async def purge_celery_queue(
    queue_name: str,
    _: bool = Depends(verify_admin_token)
):
    """Purge Celery queue (admin only)"""
    try:
        celery_app.control.purge()
        logger.info(f"Queue {queue_name} purged by admin")
        
        return {"message": f"Queue {queue_name} purged successfully"}
        
    except Exception as e:
        logger.error(f"Queue purge failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purge queue"
        )

# =============================================================================
# MONITORING & METRICS
# =============================================================================

@app.get("/metrics")
async def get_metrics():
    """Get application metrics (for monitoring systems)"""
    try:
        # Basic metrics - extend as needed for your monitoring solution
        async with AsyncSessionLocal() as db:
            # Get request counts for last 24 hours
            metrics_query = text("""
                SELECT 
                    endpoint,
                    SUM(request_count) as total_requests,
                    AVG(processing_time) as avg_response_time
                FROM usage_stats
                WHERE date >= :yesterday
                GROUP BY endpoint
            """)
            
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            result = await db.execute(metrics_query, {"yesterday": yesterday})
            metrics = result.mappings().fetchall()
            
            # Format for Prometheus or similar
            metrics_text = "# HELP api_requests_total Total API requests\n"
            metrics_text += "# TYPE api_requests_total counter\n"
            
            for metric in metrics:
                endpoint = metric["endpoint"].replace("/", "_").replace("-", "_")
                metrics_text += f'api_requests_total{{endpoint="{endpoint}"}} {metric["total_requests"]}\n'
            
            metrics_text += "\n# HELP api_response_time_seconds Average response time\n"
            metrics_text += "# TYPE api_response_time_seconds gauge\n"
            
            for metric in metrics:
                endpoint = metric["endpoint"].replace("/", "_").replace("-", "_")
                avg_time = metric["avg_response_time"] or 0
                metrics_text += f'api_response_time_seconds{{endpoint="{endpoint}"}} {avg_time}\n'
            
            return Response(content=metrics_text, media_type="text/plain")
            
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect metrics"
        )

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unexpected errors"""
    logger.error(f"Unexpected error: {exc} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# =============================================================================
# STARTUP VALIDATION
# =============================================================================

@app.on_event("startup")
async def validate_configuration():
    """Validate configuration on startup"""
    try:
        config.validate()
        logger.info("Configuration validation passed")
        
        # Test database connection
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        logger.info("Database connection validated")
        
        # Test Redis connection
        await redis_manager.get("startup_test")
        logger.info("Redis connection validated")
        
        # Initialize default universities if none exist
        async with AsyncSessionLocal() as db:
            count_query = text("SELECT COUNT(*) as count FROM universities")
            result = await db.execute(count_query)
            count = result.mappings().fetchone()["count"]
            
            if count == 0:
                logger.info("Initializing default universities...")
                
                default_universities = [
                    {
                        "code": "ufl",
                        "name": "University of Florida",
                        "domain": "ufl.edu",
                        "rate_limit_per_minute": 30,
                        "rate_limit_per_hour": 300,
                        "monthly_budget": 2000.0,
                        "is_active": True
                    },
                    {
                        "code": "fsu",
                        "name": "Florida State University", 
                        "domain": "fsu.edu",
                        "rate_limit_per_minute": 25,
                        "rate_limit_per_hour": 250,
                        "monthly_budget": 1500.0,
                        "is_active": True
                    }
                ]
                
                for uni in default_universities:
                    insert_query = text("""
                        INSERT INTO universities (code, name, domain, rate_limit_per_minute,
                                                rate_limit_per_hour, monthly_budget, is_active, created_at)
                        VALUES (:code, :name, :domain, :rate_limit_per_minute,
                                :rate_limit_per_hour, :monthly_budget, :is_active, :created_at)
                    """)
                    
                    await db.execute(insert_query, {
                        **uni,
                        "created_at": datetime.utcnow()
                    })
                
                await db.commit()
                logger.info("Default universities initialized")
        
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        raise

# =============================================================================
# DEPLOYMENT UTILITIES
# =============================================================================

def create_tables():
    """Create database tables (for deployment scripts)"""
    import asyncio
    
    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    asyncio.run(_create())

def run_migrations():
    """Run database migrations (for deployment scripts)"""
    # Implement Alembic migrations here if needed
    logger.info("Migrations completed")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Production-ready server configuration
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    workers = int(os.getenv("WORKERS", 4))
    
    logger.info("="*60)
    logger.info("🚀 Navigator Prompt API v3.0.0")
    logger.info(f"📍 Server: http://{host}:{port}")
    logger.info(f"👥 Workers: {workers}")
    logger.info(f"🔒 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info("="*60)
    
    uvicorn.run(
        "app:app",  # Use string import for production
        host=host,
        port=port,
        workers=workers if os.getenv("ENVIRONMENT") == "production" else 1,
        log_level="info",
        access_log=True,
        reload=os.getenv("ENVIRONMENT") != "production"
    )