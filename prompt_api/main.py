# main.py
import uuid
import asyncio
import json
import logging
from fastapi import FastAPI, Depends, HTTPException, status, Body, Query, Request
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from database import engine, Base, get_db
from models import (
    Task, GeneratedPrompt, PromptEvaluation, PromptSuggestion, PromptAnalysis, LibraryPrompt, PromptStar
)
from celery_worker import (
    create_initial_prompt_task,
    evaluate_prompt_task,
    generate_suggestions_task,
    analyze_and_tag_task,
    add_to_library_task # Import the new task
)

# --- Logging Middleware ---
# Configure logging to see the output in your console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            logger.info(f"Request Body for {request.url.path}: {body.decode()}")
            
            async def receive():
                return {"type": "http.request", "body": body}
            
            new_request = Request(request.scope, receive)
            response = await call_next(new_request)
        else:
            response = await call_next(request)
        
        return response

# --- Pydantic Models for API Requests ---

class InitialGenerationRequest(BaseModel):
    user_needs: str
    deepeval_context: Optional[str] = None

class EvaluationRequest(BaseModel):
    prompt: str
    user_needs: str
    retrieved_content: Optional[str] = None
    ground_truths: Optional[str] = None

class SuggestionRequest(BaseModel):
    current_prompt: str
    user_comments: Optional[str] = None
    retrieved_content: Optional[str] = None

class AnalysisRequest(BaseModel):
    prompt_text: str
    targeted_context: Optional[str] = None

class AddLibraryPromptRequest(BaseModel):
    prompt_text: str
    user_id: str

class ToggleStarRequest(BaseModel):
    user_id: str

# --- Pydantic Models for API Responses ---

class TaskCreationResponse(BaseModel):
    task_id: uuid.UUID
    status_url: str

class BaseTaskResponse(BaseModel):
    task_id: uuid.UUID
    task_type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

class GeneratedPromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_needs: str
    initial_prompt: str

class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    original_prompt: str
    improved_prompt: str
    improvement_summary: str
    bias_score: Optional[float] = None
    toxicity_score: Optional[float] = None
    alignment_score: Optional[float] = None

class SuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str
    title: str
    description: str
    priority_score: int

class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    summary: str
    tags: List[str]
    quality_indicators: Dict[str, Any]
    category_analysis: Dict[str, str]

class TaskStatusResponse(BaseTaskResponse):
    # The result for add_to_library is the prompt itself
    result: Optional[Union[GeneratedPromptResponse, EvaluationResponse, List[SuggestionResponse], AnalysisResponse, "LibraryPromptResponse"]] = None

class LibraryPromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: str
    text: str
    created_at: datetime
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    stars: int = 0
    is_starred_by_user: bool = False

class AuthSessionResponse(BaseModel):
    isAuthenticated: bool
    user: Optional[Dict[str, str]] = None


# --- FastAPI App ---
app = FastAPI(
    title="Advanced Prompt Engineering Service",
    description="A comprehensive API for generating, evaluating, and optimizing prompts.",
    version="2.5.0"
)

app.add_middleware(RequestLoggingMiddleware)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --- API Endpoints ---

@app.get("/auth/session", response_model=AuthSessionResponse, tags=["Authentication"])
async def get_mock_session():
    return AuthSessionResponse(
        isAuthenticated=True,
        user={"id": "mock-user-123", "name": "Demo User", "email": "demo@example.com"}
    )

@app.get("/library/prompts", response_model=List[LibraryPromptResponse], tags=["Library"])
async def get_library_prompts(user_id: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    prompts = (await db.execute(select(LibraryPrompt).options(selectinload(LibraryPrompt.stars)).order_by(LibraryPrompt.created_at.desc()))).scalars().all()
    
    response_prompts = []
    for prompt in prompts:
        response_prompts.append(
            LibraryPromptResponse(
                id=prompt.id, user_id=prompt.user_id, text=prompt.text,
                created_at=prompt.created_at, summary=prompt.summary, tags=prompt.tags,
                stars=len(prompt.stars),
                is_starred_by_user=any(star.user_id == user_id for star in prompt.stars) if user_id else False
            )
        )
    
    response_prompts.sort(key=lambda p: p.stars, reverse=True)
    return response_prompts

# FIX: Refactored to be a non-blocking task dispatcher
@app.post("/library/prompts", response_model=TaskCreationResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Library"])
async def add_library_prompt(
    request: AddLibraryPromptRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Starts a background task to analyze and save a prompt to the library.
    """
    # Check for existing prompt to fail fast
    existing = await db.execute(select(LibraryPrompt).where(LibraryPrompt.text == request.prompt_text))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This prompt is already in the library.")

    # Dispatch the full workflow to a Celery task
    new_task = Task(task_type="add_to_library")
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    add_to_library_task.delay(str(new_task.id), request.dict())
    
    return TaskCreationResponse(task_id=new_task.id, status_url=f"/tasks/{new_task.id}")

@app.delete("/library/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Library"])
async def delete_library_prompt(prompt_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    prompt = await db.get(LibraryPrompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    await db.delete(prompt)
    await db.commit()
    return None

@app.post("/library/prompts/{prompt_id}/toggle-star", tags=["Library"])
async def toggle_star_for_prompt(prompt_id: uuid.UUID, request: ToggleStarRequest, db: AsyncSession = Depends(get_db)):
    prompt = await db.get(LibraryPrompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    stmt = select(PromptStar).where(PromptStar.prompt_id == prompt_id, PromptStar.user_id == request.user_id)
    existing_star = (await db.execute(stmt)).scalar_one_or_none()

    if existing_star:
        await db.delete(existing_star)
        await db.commit()
        return {"success": True, "action": "unstarred"}
    else:
        new_star = PromptStar(prompt_id=prompt_id, user_id=request.user_id)
        db.add(new_star)
        await db.commit()
        return {"success": True, "action": "starred"}

# --- Existing Prompt Endpoints ---
@app.post("/prompts/generate", response_model=TaskCreationResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Prompt Generation"])
async def generate_new_prompt(request: InitialGenerationRequest, db: AsyncSession = Depends(get_db)):
    new_task = Task(task_type="initial_generation")
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    create_initial_prompt_task.delay(str(new_task.id), request.dict())
    return TaskCreationResponse(task_id=new_task.id, status_url=f"/tasks/{new_task.id}")

@app.post("/prompts/evaluate", response_model=TaskCreationResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Prompt Evaluation"])
async def evaluate_existing_prompt(request: EvaluationRequest, db: AsyncSession = Depends(get_db)):
    new_task = Task(task_type="evaluation_and_improvement")
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    evaluate_prompt_task.delay(str(new_task.id), request.dict())
    return TaskCreationResponse(task_id=new_task.id, status_url=f"/tasks/{new_task.id}")

@app.post("/prompts/suggest-improvements", response_model=TaskCreationResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Prompt Optimization"])
async def get_improvement_suggestions(request: SuggestionRequest, db: AsyncSession = Depends(get_db)):
    new_task = Task(task_type="suggestion_generation")
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    generate_suggestions_task.delay(str(new_task.id), request.dict())
    return TaskCreationResponse(task_id=new_task.id, status_url=f"/tasks/{new_task.id}")

@app.post("/prompts/analyze-and-tag", response_model=TaskCreationResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Prompt Analysis"])
async def analyze_and_tag_prompt(request: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    new_task = Task(task_type="analysis_and_tagging")
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    analyze_and_tag_task.delay(str(new_task.id), request.dict())
    return TaskCreationResponse(task_id=new_task.id, status_url=f"/tasks/{new_task.id}")

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["Task Management"])
async def get_task_status(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.id == task_id).options(
        selectinload(Task.generated_prompt),
        selectinload(Task.prompt_evaluation),
        selectinload(Task.prompt_suggestions),
        selectinload(Task.prompt_analysis),
        # Also load the library prompt if it's the result
        selectinload(Task.library_prompt) 
    )
    task = (await db.execute(stmt)).scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    response_data = {
        "task_id": task.id, "task_type": task.task_type, "status": task.status,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message, "result": None
    }

    if task.status == "SUCCESS":
        if task.task_type == "initial_generation" and task.generated_prompt:
            response_data["result"] = GeneratedPromptResponse.from_orm(task.generated_prompt)
        elif task.task_type == "evaluation_and_improvement" and task.prompt_evaluation:
            response_data["result"] = EvaluationResponse.from_orm(task.prompt_evaluation)
        elif task.task_type == "suggestion_generation" and task.prompt_suggestions:
            response_data["result"] = [SuggestionResponse.from_orm(s) for s in task.prompt_suggestions]
        elif task.task_type == "analysis_and_tagging" and task.prompt_analysis:
            analysis = task.prompt_analysis
            response_data["result"] = AnalysisResponse.from_orm(analysis)
        elif task.task_type == "add_to_library" and task.library_prompt:
             # When the add_to_library task is done, the result is the LibraryPrompt itself
            response_data["result"] = LibraryPromptResponse.from_orm(task.library_prompt)

    return TaskStatusResponse(**response_data)
