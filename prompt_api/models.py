# models.py
import uuid
from sqlalchemy import (
    Column, String, DateTime, JSON, ForeignKey, Text, Float, Integer, ARRAY, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Central Task Tracking Table
class Task(Base):
    """
    A central table to track the status of all asynchronous Celery tasks.
    Each task, regardless of its type (generation, evaluation, etc.),
    will have an entry here. Specific results are stored in related tables.
    """
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String, nullable=False, index=True) # e.g., 'initial_generation', 'evaluation'
    status = Column(String, default="PENDING", index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships to specific result tables
    generated_prompt = relationship("GeneratedPrompt", back_populates="task", uselist=False)
    prompt_evaluation = relationship("PromptEvaluation", back_populates="task", uselist=False)
    prompt_suggestions = relationship("PromptSuggestion", back_populates="task")
    prompt_analysis = relationship("PromptAnalysis", back_populates="task", uselist=False)
    # FIX: Add the missing relationship to the LibraryPrompt model
    library_prompt = relationship("LibraryPrompt", back_populates="task", uselist=False)

# --- Library Prompt & Stars ---
class LibraryPrompt(Base):
    """
    Stores prompts that have been analyzed and added to the community library.
    """
    __tablename__ = "library_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    text = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    summary = Column(String, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # FIX: Add a task_id to link back to the creation task
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, unique=True)
    task = relationship("Task", back_populates="library_prompt")
    
    # Relationship to the stars, ensuring they are deleted if the prompt is deleted
    stars = relationship("PromptStar", back_populates="prompt", cascade="all, delete-orphan")

class PromptStar(Base):
    """
    Tracks which user has starred which library prompt (many-to-many relationship).
    """
    __tablename__ = "prompt_stars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("library_prompts.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)

    prompt = relationship("LibraryPrompt", back_populates="stars")


# Table for 'initial_generation' template results
class GeneratedPrompt(Base):
    """
    Stores the output from the 'initial_generation' template.
    """
    __tablename__ = "generated_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, unique=True)
    user_needs = Column(Text, nullable=False)
    initial_prompt = Column(Text, nullable=False)

    task = relationship("Task", back_populates="generated_prompt")


# Table for 'evaluation_and_improvement' template results
class PromptEvaluation(Base):
    """
    Stores the detailed evaluation metrics from the 'evaluation_and_improvement' template.
    """
    __tablename__ = "prompt_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, unique=True)
    
    original_prompt = Column(Text)
    improved_prompt = Column(Text)
    improvement_summary = Column(Text)

    # Bias Assessment
    bias_score = Column(Float)
    bias_summary = Column(Text)
    bias_issues = Column(ARRAY(String))
    bias_mitigations = Column(ARRAY(String))
    bias_test_cases = Column(ARRAY(String))

    # Toxicity Assessment
    toxicity_score = Column(Float)
    toxicity_summary = Column(Text)
    toxicity_risks = Column(ARRAY(String))
    toxicity_safeguards = Column(ARRAY(String))
    toxicity_test_cases = Column(ARRAY(String))

    # Prompt Alignment
    alignment_score = Column(Float)
    alignment_summary = Column(Text)
    alignment_strengths = Column(ARRAY(String))
    alignment_improvements = Column(ARRAY(String))
    alignment_test_cases = Column(ARRAY(String))

    task = relationship("Task", back_populates="prompt_evaluation")


# Table for 'suggestion_generation' template results
class PromptSuggestion(Base):
    """
    Stores an individual suggestion from the 'suggestion_generation' template.
    A single task can generate multiple suggestions.
    """
    __tablename__ = "prompt_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)

    category = Column(String) # critical|high|medium|enhancement
    title = Column(String)
    description = Column(Text)
    implementation = Column(Text)
    impact = Column(Text)
    priority_score = Column(Integer)

    task = relationship("Task", back_populates="prompt_suggestions")


# Table for 'analysis_and_tagging' template results
class PromptAnalysis(Base):
    """
    Stores the analysis and tags from the 'analysis_and_tagging' template.
    """
    __tablename__ = "prompt_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, unique=True)

    summary = Column(String(255))
    tags = Column(ARRAY(String))
    
    # Quality Indicators
    clarity = Column(String) # high|medium|low
    bias_risk = Column(String) # low|medium|high
    safety_level = Column(String) # high|medium|low
    completeness = Column(String) # high|medium|low
    professional_grade = Column(Boolean)
    
    # Category Analysis
    primary_domain = Column(String)
    main_purpose = Column(String)
    target_audience = Column(String)
    complexity_level = Column(String)
    
    task = relationship("Task", back_populates="prompt_analysis")
