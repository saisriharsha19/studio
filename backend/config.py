# config.py - Production configuration
import os
from typing import Optional

class Config:
    """Production configuration class"""
    
    # API Configuration
    UFL_AI_API_KEY: str = os.getenv("UFL_AI_API_KEY", "")
    UFL_AI_BASE_URL: str = os.getenv("UFL_AI_BASE_URL", "")
    UFL_AI_MODEL: str = os.getenv("UFL_AI_MODEL", "llama-3.3-70b-instruct")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Performance Configuration
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "100"))
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "30"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Cache Configuration
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    MAX_CACHE_SIZE: int = int(os.getenv("MAX_CACHE_SIZE", "1000"))
    CACHE_CLEANUP_INTERVAL: int = int(os.getenv("CACHE_CLEANUP_INTERVAL", "300"))  # 5 minutes
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour
    
    # Security
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
    
    # Memory Management
    MEMORY_CLEANUP_THRESHOLD: float = float(os.getenv("MEMORY_CLEANUP_THRESHOLD", "80.0"))  # 80%
    GC_COLLECTION_INTERVAL: int = int(os.getenv("GC_COLLECTION_INTERVAL", "600"))  # 10 minutes
    
    # Template Configuration
    TEMPLATE_CACHE_SIZE: int = int(os.getenv("TEMPLATE_CACHE_SIZE", "128"))
    
    @classmethod
    def validate(cls) -> list:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not cls.UFL_AI_API_KEY:
            errors.append("UFL_AI_API_KEY is required")
        
        if not cls.UFL_AI_BASE_URL:
            errors.append("UFL_AI_BASE_URL is required")
        
        if cls.PORT < 1 or cls.PORT > 65535:
            errors.append("PORT must be between 1 and 65535")
        
        if cls.CACHE_TTL < 0:
            errors.append("CACHE_TTL must be non-negative")
        
        if cls.RATE_LIMIT_REQUESTS < 1:
            errors.append("RATE_LIMIT_REQUESTS must be positive")
        
        return errors
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return not cls.DEBUG and os.getenv("ENVIRONMENT", "").lower() == "production"

# Production-specific settings
class ProductionConfig(Config):
    """Production-specific configuration overrides"""
    
    # Stricter security in production
    ALLOWED_ORIGINS = ["https://glorious-giggle-v666jp9xwpwwfxv5-3000.app.github.dev/", "*"]  # Replace with actual domain
    LOG_LEVEL = "ERROR"
    DEBUG = False
    
    # Optimized for production
    CACHE_TTL = 7200  # 2 hours
    MAX_CACHE_SIZE = 2000
    RATE_LIMIT_REQUESTS = 1000
    
    # More aggressive memory management
    MEMORY_CLEANUP_THRESHOLD = 70.0
    GC_COLLECTION_INTERVAL = 300  # 5 minutes

# Development settings
class DevelopmentConfig(Config):
    """Development configuration"""
    
    DEBUG = True
    LOG_LEVEL = "INFO"
    CACHE_TTL = 300  # 5 minutes
    RATE_LIMIT_REQUESTS = 10  # Lower for testing

# Get the appropriate configuration based on environment
def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    else:
        return DevelopmentConfig()

# Global config instance
config = get_config()