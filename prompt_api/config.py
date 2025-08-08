# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # LLM Config
    API_KEY = os.getenv("UFL_AI_API_KEY")
    BASE_URL = os.getenv("UFL_AI_BASE_URL")
    MODEL_NAME = os.getenv("UFL_AI_MODEL")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Celery & Redis Sentinel
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
    REDIS_SERVICE_NAME = os.getenv("REDIS_SERVICE_NAME")

settings = Settings()