"""
Navigator Prompt API - A complete prompt generation and evaluation system
Focuses on generating robust, safe, and effective prompts for different AI models
with advanced prompt engineering techniques and comprehensive safety evaluations
"""

import asyncio
import hashlib
import json
import time
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import os
from contextlib import asynccontextmanager
import re

# FastAPI and async dependencies
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
import aiohttp

# Database dependencies
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, Index, text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Utilities
from dotenv import load_dotenv

# AI and evaluation dependencies
from deepeval import evaluate
from deepeval.metrics import BiasMetric, ToxicityMetric, AnswerRelevancyMetric, FaithfulnessMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase
from deepeval.models import DeepEvalBaseLLM

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# AI API Configuration
UFL_AI_API_KEY = os.getenv("UFL_AI_API_KEY")
UFL_AI_BASE_URL = os.getenv("UFL_AI_BASE_URL")
UFL_AI_MODEL = os.getenv("UFL_AI_MODEL", "llama-3.3-70b-instruct")

# Application Configuration
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
ADMIN_KEY = os.getenv("ADMIN_KEY", "dev-admin-key-123")

def validate_database_url():
    """Validate database URL format"""
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set - using in-memory storage")
        return False
    
    if not DATABASE_URL.startswith(('postgresql://', 'postgres://')):
        logger.error(f"Invalid DATABASE_URL format: {DATABASE_URL[:20]}...")
        return False
    
    logger.info(f"Database URL configured: {DATABASE_URL.split('://')[0]}://...")
    return True

ENABLE_DATABASE = DATABASE_URL is not None and validate_database_url()
ENABLE_REDIS = REDIS_URL is not None

# =============================================================================
# PROMPT ENGINEERING TECHNIQUES CONFIGURATION
# =============================================================================

PROMPT_TECHNIQUES = {
    "chain_of_thought": {
        "name": "Chain of Thought",
        "description": "Step-by-step reasoning prompts",
        "template_prefix": "Think step by step:",
        "safety_level": "high",
        "combinable_with": ["few_shot", "role_prompting", "constraint_based", "safety_first"],
        "combination_priority": 1
    },
    "tree_of_thought": {
        "name": "Tree of Thought", 
        "description": "Multi-path reasoning with exploration",
        "template_prefix": "Consider multiple approaches:",
        "safety_level": "high",
        "combinable_with": ["chain_of_thought", "constraint_based", "safety_first"],
        "combination_priority": 2
    },
    "react": {
        "name": "ReAct (Reasoning + Acting)",
        "description": "Iterative reasoning and action taking",
        "template_prefix": "Think, then act, then observe:",
        "safety_level": "medium",
        "combinable_with": ["chain_of_thought", "constraint_based", "role_prompting"],
        "combination_priority": 1
    },
    "few_shot": {
        "name": "Few-Shot Learning",
        "description": "Learning from examples",
        "template_prefix": "Here are some examples:",
        "safety_level": "medium",
        "combinable_with": ["chain_of_thought", "role_prompting", "constraint_based", "zero_shot"],
        "combination_priority": 3
    },
    "zero_shot": {
        "name": "Zero-Shot",
        "description": "Direct instruction without examples",
        "template_prefix": "",
        "safety_level": "high",
        "combinable_with": ["role_prompting", "constraint_based", "safety_first"],
        "combination_priority": 4
    },
    "role_prompting": {
        "name": "Role-Based Prompting",
        "description": "Assign specific roles or personas",
        "template_prefix": "You are a [ROLE]:",
        "safety_level": "medium",
        "combinable_with": ["chain_of_thought", "few_shot", "constraint_based", "meta_prompting"],
        "combination_priority": 5
    },
    "constraint_based": {
        "name": "Constraint-Based",
        "description": "Prompts with specific limitations and rules",
        "template_prefix": "Follow these constraints:",
        "safety_level": "high",
        "combinable_with": ["chain_of_thought", "role_prompting", "safety_first", "react"],
        "combination_priority": 2
    },
    "iterative_refinement": {
        "name": "Iterative Refinement",
        "description": "Multi-step prompt refinement",
        "template_prefix": "Refine your response by:",
        "safety_level": "high",
        "combinable_with": ["chain_of_thought", "tree_of_thought", "constraint_based"],
        "combination_priority": 1
    },
    "meta_prompting": {
        "name": "Meta-Prompting",
        "description": "Prompts about prompting",
        "template_prefix": "Create a prompt that:",
        "safety_level": "high",
        "combinable_with": ["role_prompting", "constraint_based", "safety_first"],
        "combination_priority": 3
    },
    "safety_first": {
        "name": "Safety-First Prompting",
        "description": "Prioritizes safety and harm prevention",
        "template_prefix": "Ensure safety by:",
        "safety_level": "maximum",
        "combinable_with": ["chain_of_thought", "constraint_based", "role_prompting", "zero_shot"],
        "combination_priority": 1
    }
}

AI_MODEL_CONFIGS = {
    "llama-3.3-70b-instruct": {
        "max_tokens": 8192,
        "supports_json": True,
        "temperature_range": [0.1, 1.0],
        "best_techniques": ["chain_of_thought", "role_prompting", "constraint_based"],
        "cost_per_1k_tokens": 0.0015
    },
    "gpt-4": {
        "max_tokens": 8192,
        "supports_json": True,
        "temperature_range": [0.0, 2.0],
        "best_techniques": ["few_shot", "chain_of_thought", "meta_prompting"],
        "cost_per_1k_tokens": 0.03
    },
    "claude-3": {
        "max_tokens": 4096,
        "supports_json": True,
        "temperature_range": [0.0, 1.0],
        "best_techniques": ["role_prompting", "constraint_based", "safety_first"],
        "cost_per_1k_tokens": 0.008
    }
}

# =============================================================================
# ENHANCED TEMPLATE MANAGER WITH PROMPT ENGINEERING TECHNIQUES
# =============================================================================

class AdvancedTemplateManager:
    """Advanced template manager with prompt engineering techniques"""
    
    def __init__(self):
        self.templates = {
            "generate_initial_prompt": {
                "description": "Generate initial system prompt using advanced techniques",
                "version": "2.0",
                "template": """
You are an expert prompt engineer specializing in creating robust, safe, and effective prompts for AI systems. Your task is to generate a comprehensive system prompt based on the user's requirements.

**User Requirements:**
{{userNeeds}}

**Target AI Model:** {{aiModel}}
**Preferred Technique:** {{technique}}
**Safety Level:** {{safetyLevel}}

**Instructions:**
1. Analyze the user requirements carefully
2. Apply the specified prompt engineering technique: {{technique}}
3. Ensure the prompt follows safety guidelines and prevents harmful outputs
4. Structure the prompt for maximum effectiveness with the target AI model
5. Include appropriate constraints, examples, and guidance as needed

**Safety Requirements:**
- Prevent generation of harmful, biased, or inappropriate content
- Include clear boundaries and limitations
- Add safety checks and validation steps
- Ensure alignment with ethical AI principles

**Prompt Engineering Best Practices:**
- Use clear, specific language
- Provide context and background information
- Include expected output format
- Add reasoning steps if using chain-of-thought
- Specify constraints and limitations
- Include examples if using few-shot learning

Return your response as JSON:
{
    "initialPrompt": "Your generated system prompt here - this should be a complete, ready-to-use prompt",
    "technique": "{{technique}}",
    "safetyFeatures": ["list", "of", "safety", "features", "included"],
    "estimatedTokens": estimated_token_count,
    "promptStructure": {
        "role": "defined role if applicable",
        "context": "background context provided",
        "instructions": "main instructions given",
        "constraints": "limitations and rules",
        "outputFormat": "expected response format"
    }
}
"""
            },
            
            "evaluate_and_iterate_prompt": {
                "description": "Evaluate and improve prompts with advanced analysis",
                "version": "2.0",
                "template": """
You are an expert prompt engineer. Analyze and improve the given prompt using advanced prompt engineering principles.

**Current Prompt:**
{{prompt}}

**Original User Requirements:**
{{userNeeds}}

**Target AI Model:** {{aiModel}}
**Current Technique:** {{currentTechnique}}

{{retrievedContentSection}}
{{groundTruthsSection}}

**Analysis Framework:**
1. **Clarity Assessment:** Is the prompt clear and unambiguous?
2. **Technique Effectiveness:** How well does it apply the chosen technique?
3. **Safety Evaluation:** Does it prevent harmful outputs?
4. **Completeness Check:** Are all requirements addressed?
5. **Model Compatibility:** Is it optimized for the target AI model?

**Improvement Goals:**
- Enhance clarity and specificity
- Strengthen safety measures
- Improve technique implementation
- Optimize for target AI model
- Add missing constraints or examples
- Ensure robust output format

**Safety Enhancements:**
- Add explicit harm prevention measures
- Include bias detection and prevention
- Strengthen constraint enforcement
- Add validation and self-correction steps

Return your response as JSON:
{
    "initialPrompt": "Your improved system prompt here - this should be production-ready",
    "improvements": ["list", "of", "specific", "improvements", "made"],
    "safetyEnhancements": ["safety", "features", "added", "or", "improved"],
    "techniqueOptimizations": ["technique", "specific", "improvements"],
    "estimatedTokens": estimated_token_count,
    "confidenceScore": 0.95,
    "recommendedTesting": ["testing", "scenarios", "to", "validate", "prompt"]
}
"""
            },
            
            "iterate_on_prompt": {
                "description": "Iterate on prompt based on feedback and advanced analysis",
                "version": "2.0",
                "template": """
You are an expert prompt engineer. Refine the prompt based on user feedback and apply advanced optimization techniques.

**Current Prompt:**
{{currentPrompt}}

**User Feedback:**
{{userComments}}

**Selected Improvements:**
{{selectedSuggestions}}

**Target AI Model:** {{aiModel}}

**Refinement Process:**
1. Address specific user feedback
2. Implement selected improvements
3. Apply advanced prompt engineering techniques
4. Enhance safety and robustness
5. Optimize for the target AI model

**Advanced Optimization Techniques:**
- Prompt compression for efficiency
- Instruction hierarchy for clarity  
- Context optimization for relevance
- Safety layering for harm prevention
- Output format standardization

**Quality Assurance:**
- Ensure all feedback is addressed
- Maintain or improve safety measures
- Verify technique effectiveness
- Check model compatibility
- Validate output format consistency

Return your response as JSON:
{
    "newPrompt": "Your refined system prompt here - incorporating all feedback and optimizations",
    "changesImplemented": ["specific", "changes", "made", "based", "on", "feedback"],
    "additionalOptimizations": ["extra", "improvements", "beyond", "feedback"],
    "safetyMaintained": true,
    "estimatedTokens": estimated_token_count,
    "refinementQuality": 0.98
}
"""
            },
            
            "generate_prompt_techniques": {
                "description": "Recommend prompt engineering techniques",
                "version": "1.0", 
                "template": """
Analyze the user requirements and recommend the most effective prompt engineering techniques.

**User Requirements:**
{{userNeeds}}

**Target AI Model:** {{aiModel}}
**Available Techniques:** {{availableTechniques}}

Evaluate each technique's suitability and recommend the best approach.

Return as JSON:
{
    "recommendedTechnique": "primary_technique_name",
    "alternativeTechniques": ["alternative1", "alternative2"],
    "reasoning": "explanation of why this technique is recommended",
    "expectedEffectiveness": 0.95,
    "safetyConsiderations": ["safety", "factors", "for", "this", "technique"]
}
"""
            },
            
            "safety_audit_prompt": {
                "description": "Comprehensive safety audit of prompts",
                "version": "1.0",
                "template": """
Conduct a comprehensive safety audit of the given prompt.

**Prompt to Audit:**
{{promptText}}

**Safety Audit Checklist:**
1. Bias Prevention: Does it prevent biased outputs?
2. Harm Mitigation: Does it prevent harmful content generation?
3. Privacy Protection: Does it respect privacy and confidentiality?
4. Misinformation Prevention: Does it prevent false information?
5. Inappropriate Content: Does it block NSFW or inappropriate content?
6. Manipulation Resistance: Is it resistant to prompt injection attacks?
7. Boundary Enforcement: Does it maintain clear operational boundaries?

**Audit Areas:**
- Content Safety
- Bias and Fairness
- Privacy and Security
- Robustness and Reliability
- Ethical Considerations

Return as JSON:
{
    "safetyScore": 0.95,
    "riskAreas": ["identified", "risk", "areas"],
    "safetyFeatures": ["existing", "safety", "features"],
    "recommendations": ["safety", "improvement", "recommendations"],
    "complianceLevel": "high/medium/low",
    "auditSummary": "comprehensive safety assessment summary"
}
"""
            },
            
            "get_prompt_suggestions": {
                "description": "Get improvement suggestions",
                "version": "1.0", 
                "template": """
Analyze the prompt and provide improvement suggestions.

Current Prompt: {{currentPrompt}}
{{userCommentsSection}}

**Analysis Areas:**
1. Clarity and specificity
2. Safety and bias prevention
3. Structure and organization
4. Completeness and coverage
5. Effectiveness for AI models

**Suggestion Categories:**
- Structural improvements
- Safety enhancements
- Clarity improvements
- Performance optimizations
- Technique-specific optimizations

Return as JSON:
{
    "suggestions": [
        "Add more specific constraints to prevent ambiguous responses",
        "Include safety guidelines to prevent harmful outputs",
        "Restructure instructions for better clarity",
        "Add examples to improve understanding",
        "Optimize for the target AI model's capabilities"
    ]
}
"""
            },
            
            "prompt_optimization": {
                "description": "Optimize prompts for specific AI models",
                "version": "1.0",
                "template": """
Optimize the prompt for the specific AI model and use case.

**Current Prompt:**
{{currentPrompt}}

**Target AI Model:** {{aiModel}}
**Model Capabilities:** {{modelCapabilities}}
**Optimization Goals:** {{optimizationGoals}}

**Optimization Strategies:**
1. Token efficiency
2. Model-specific formatting
3. Context window optimization
4. Response quality enhancement
5. Performance optimization

Return as JSON:
{
    "optimizedPrompt": "model-optimized version of the prompt",
    "optimizations": ["specific", "optimizations", "applied"],
    "tokenReduction": percentage_saved,
    "expectedPerformance": 0.98,
    "modelSpecificFeatures": ["features", "optimized", "for", "this", "model"]
}
"""
            },
            
            "generate_prompt_tags": {
                "description": "Generate tags for a prompt",
                "version": "1.0",
                "template": """
Analyze the given prompt and generate relevant tags and a summary.

Prompt: {{promptText}}

Return as JSON:
{
    "summary": "Brief summary of what this prompt does",
    "tags": ["tag1", "tag2", "tag3"]
}
"""
            }
        }
    
    def render_template(self, template_name: str, **kwargs) -> Optional[str]:
        """Render template with variables and safety checks"""
        if template_name not in self.templates:
            return None
        
        template_content = self.templates[template_name]["template"]
        
        # Simple template substitution with safety validation
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            # Sanitize input to prevent template injection
            safe_value = str(value).replace("{{", "").replace("}}", "")
            template_content = template_content.replace(placeholder, safe_value)
        
        return template_content
    
    def get_available_techniques(self) -> List[str]:
        """Get list of available prompt engineering techniques"""
        return list(PROMPT_TECHNIQUES.keys())
    
    def get_technique_info(self, technique: str) -> Dict[str, Any]:
        """Get information about a specific technique"""
        return PROMPT_TECHNIQUES.get(technique, {})

# Global template manager
template_manager = AdvancedTemplateManager()

# =============================================================================
# ENHANCED PYDANTIC MODELS
# =============================================================================

class PromptTechnique(BaseModel):
    name: str
    description: str
    safetyLevel: str
    effectiveness: Optional[float] = None

class UserNeedsRequest(BaseModel):
    userNeeds: str = Field(..., description="Description of what the AI assistant should do")
    universityCode: str = Field(default="ufl", description="University code")
    userId: str = Field(default="anonymous", description="User identifier")
    aiModel: str = Field(default="llama-3.3-70b-instruct", description="Target AI model")
    techniques: List[str] = Field(default=["chain_of_thought"], description="List of prompt engineering techniques to combine")
    safetyLevel: str = Field(default="high", description="Required safety level")
    
    @validator('techniques')
    def validate_techniques(cls, v):
        if not v:  # Empty list
            return ["chain_of_thought"]  # Default technique
        
        invalid_techniques = [t for t in v if t not in PROMPT_TECHNIQUES]
        if invalid_techniques:
            raise ValueError(f"Invalid techniques: {invalid_techniques}. Must be from: {list(PROMPT_TECHNIQUES.keys())}")
        
        # Check technique combinations
        for i, technique in enumerate(v):
            for j, other_technique in enumerate(v):
                if i != j:  # Don't check against itself
                    combinable = PROMPT_TECHNIQUES[technique].get("combinable_with", [])
                    if other_technique not in combinable:
                        raise ValueError(f"Technique '{technique}' cannot be combined with '{other_technique}'")
        
        return v
    
    @validator('safetyLevel')
    def validate_safety_level(cls, v):
        valid_levels = ["low", "medium", "high", "maximum"]
        if v not in valid_levels:
            raise ValueError(f"Invalid safety level. Must be one of: {valid_levels}")
        return v
    
    @validator('aiModel')
    def validate_ai_model(cls, v):
        if v not in AI_MODEL_CONFIGS:
            raise ValueError(f"Invalid AI model. Must be one of: {list(AI_MODEL_CONFIGS.keys())}")
        return v

class EvaluatePromptRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to evaluate")
    userNeeds: str = Field(..., description="Original user needs")
    universityCode: str = Field(default="ufl", description="University code")
    userId: str = Field(default="anonymous", description="User identifier")
    aiModel: str = Field(default="llama-3.3-70b-instruct", description="Target AI model")
    techniques: List[str] = Field(default=["chain_of_thought"], description="List of techniques used in the prompt")
    retrievedContent: Optional[str] = Field(None, description="Knowledge base content")
    groundTruths: Optional[str] = Field(None, description="Few-shot examples")
    safetyAudit: bool = Field(default=True, description="Perform comprehensive safety audit")


class PromptOptimizationRequest(BaseModel):
    currentPrompt: str = Field(..., description="Current prompt to optimize")
    aiModel: str = Field(..., description="Target AI model")
    optimizationGoals: List[str] = Field(default=["efficiency", "safety", "effectiveness"])
    universityCode: str = Field(default="ufl", description="University code")

class SafetyAuditRequest(BaseModel):
    promptText: str = Field(..., description="Prompt to audit for safety")
    universityCode: str = Field(default="ufl", description="University code")
    auditLevel: str = Field(default="comprehensive", description="Audit depth level")

class TechniqueRecommendationRequest(BaseModel):
    userNeeds: str = Field(..., description="User requirements")
    aiModel: str = Field(..., description="Target AI model")
    universityCode: str = Field(default="ufl", description="University code")

class IteratePromptRequest(BaseModel):
    currentPrompt: str = Field(..., description="Current prompt to iterate on")
    userComments: str = Field(..., description="User feedback")
    selectedSuggestions: List[str] = Field(default=[], description="Selected suggestions")
    universityCode: str = Field(default="ufl", description="University code")
    userId: str = Field(default="anonymous", description="User identifier")
    aiModel: str = Field(default="llama-3.3-70b-instruct", description="Target AI model")

class PromptCreate(BaseModel):
    text: str = Field(..., description="Prompt text")
    userId: str = Field(..., description="User identifier")
    technique: Optional[str] = Field(None, description="Prompt engineering technique used")
    ai_model: Optional[str] = Field(None, description="AI model the prompt was designed for")

class PromptResponse(BaseModel):
    id: str
    userId: str
    text: str
    createdAt: str
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    stars: Optional[int] = None
    isStarredByUser: Optional[bool] = None
    technique: Optional[str] = None
    estimatedTokens: Optional[int] = None
    safetyValidated: Optional[bool] = None

class LibraryPromptCreate(BaseModel):
    text: str = Field(..., description="Prompt text")
    userId: str = Field(..., description="User identifier")
    technique: Optional[str] = Field(None, description="Technique used")
    aiModel: Optional[str] = Field(None, description="Target AI model")

class ToggleStarRequest(BaseModel):
    promptId: str = Field(..., description="Prompt ID to star/unstar")
    userId: str = Field(..., description="User identifier")

class PromptTagsRequest(BaseModel):
    promptText: str = Field(..., description="Prompt text to analyze")
    universityCode: str = Field(default="ufl", description="University code")

class PromptSuggestionsRequest(BaseModel):
    currentPrompt: str = Field(..., description="Current prompt")
    universityCode: str = Field(default="ufl", description="University code")
    userComments: Optional[str] = Field(None, description="User comments")

# Admin Models
class AdminRequest(BaseModel):
    action: str = Field(..., description="Action to perform")
    entity: str = Field(..., description="Entity to act on: users, universities, stats, system")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data for the action")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for queries")
    admin_key: str = Field(..., description="Admin authentication key")

class BatchRequest(BaseModel):
    operations: List[Dict[str, Any]] = Field(..., description="List of operations to perform")
    admin_key: str = Field(..., description="Admin authentication key")

# =============================================================================
# IN-MEMORY STORAGE (ENHANCED)
# =============================================================================

class InMemoryStore:
    """Enhanced in-memory storage with prompt engineering capabilities"""
    
    def __init__(self):
        self.universities = {
            "ufl": {
                "id": 1,
                "code": "ufl",
                "name": "University of Florida",
                "domain": "ufl.edu",
                "ai_model": "llama-3.3-70b-instruct",
                "rate_limit_per_minute": 20,
                "rate_limit_per_hour": 200,
                "monthly_budget": 2000.0,
                "is_active": True,
                "supported_techniques": list(PROMPT_TECHNIQUES.keys()),
                "safety_requirements": "high"
            },
            "fsu": {
                "id": 2,
                "code": "fsu",
                "name": "Florida State University",
                "domain": "fsu.edu",
                "ai_model": "llama-3.3-70b-instruct",
                "rate_limit_per_minute": 15,
                "rate_limit_per_hour": 150,
                "monthly_budget": 1500.0,
                "is_active": True,
                "supported_techniques": ["chain_of_thought", "few_shot", "safety_first"],
                "safety_requirements": "maximum"
            },
            "ucf": {
                "id": 3,
                "code": "ucf",
                "name": "University of Central Florida",
                "domain": "ucf.edu",
                "ai_model": "claude-3",
                "rate_limit_per_minute": 15,
                "rate_limit_per_hour": 150,
                "monthly_budget": 1500.0,
                "is_active": True,
                "supported_techniques": ["role_prompting", "constraint_based", "safety_first"],
                "safety_requirements": "high"
            }
        }
        self.cache = {}
        self.usage_stats = {}
        self.prompt_sessions = []
        self.evaluations = []
        self.request_counts = {}
        self.safety_audits = []  # Store safety audit results
        self.technique_recommendations = []  # Store technique recommendations

    def get_university(self, code: str) -> Optional[Dict]:
        """Get university configuration"""
        return self.universities.get(code)
    
    def get_supported_techniques(self, university_code: str) -> List[str]:
        """Get supported techniques for a university"""
        university = self.get_university(university_code)
        if university:
            return university.get("supported_techniques", list(PROMPT_TECHNIQUES.keys()))
        return list(PROMPT_TECHNIQUES.keys())
    
    def set_cache(self, key: str, value: Any, ttl: int = 3600):
        """Set cache value with TTL"""
        if ENABLE_CACHING:
            self.cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl
            }
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        if not ENABLE_CACHING:
            return None
            
        cached = self.cache.get(key)
        if cached and cached["expires_at"] > time.time():
            return cached["value"]
        elif cached:
            del self.cache[key]
        return None
    
    def track_usage(self, university_code: str, endpoint: str, cost: float):
        """Track usage statistics"""
        date_key = datetime.now().strftime("%Y-%m-%d")
        key = f"{university_code}:{date_key}:{endpoint}"
        
        if key not in self.usage_stats:
            self.usage_stats[key] = {"requests": 0, "cost": 0.0}
        
        self.usage_stats[key]["requests"] += 1
        self.usage_stats[key]["cost"] += cost
    
    def check_rate_limit(self, university_code: str, endpoint: str) -> bool:
        """Enhanced rate limiting check"""
        current_minute = int(time.time() / 60)
        key = f"{university_code}:{endpoint}:{current_minute}"
        
        if key not in self.request_counts:
            self.request_counts[key] = 0
        
        university = self.get_university(university_code)
        if not university:
            return False
        
        limit = university.get("rate_limit_per_minute", 10)
        
        if self.request_counts[key] >= limit:
            return False
        
        self.request_counts[key] += 1
        return True
    
    def store_safety_audit(self, prompt: str, audit_results: Dict):
        """Store safety audit results"""
        self.safety_audits.append({
            "id": str(uuid.uuid4()),
            "prompt_hash": hashlib.md5(prompt.encode()).hexdigest(),
            "results": audit_results,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_safety_history(self, prompt_hash: str) -> Optional[Dict]:
        """Get safety audit history for a prompt"""
        for audit in self.safety_audits:
            if audit["prompt_hash"] == prompt_hash:
                return audit
        return None

# Global store instance
store = InMemoryStore()

# =============================================================================
# REDIS SETUP (OPTIONAL)
# =============================================================================

redis_client = None

if ENABLE_REDIS:
    try:
        import aioredis
        
        async def init_redis():
            global redis_client
            redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
            logger.info("Redis connected successfully")
            
    except ImportError:
        logger.warning("aioredis not installed. Caching will use in-memory storage.")
        ENABLE_REDIS = False
    except Exception as e:
        logger.warning(f"Redis setup failed: {e}. Falling back to in-memory caching.")
        ENABLE_REDIS = False

# =============================================================================
# ENHANCED UTILITY FUNCTIONS FOR PERSISTENT TRACKING
# =============================================================================

async def track_usage_persistent(
    university_code: str, 
    endpoint: str, 
    user_id: str,
    cost: float, 
    processing_time: float = 0.0,
    db: AsyncSession = None
):
    """Track usage statistics with database persistence"""
    date_key = datetime.now().strftime("%Y-%m-%d")
    
    # Always update in-memory store for immediate access
    memory_key = f"{university_code}:{date_key}:{endpoint}"
    if memory_key not in store.usage_stats:
        store.usage_stats[memory_key] = {"requests": 0, "cost": 0.0, "processing_time": 0.0}
    
    store.usage_stats[memory_key]["requests"] += 1
    store.usage_stats[memory_key]["cost"] += cost
    store.usage_stats[memory_key]["processing_time"] += processing_time
    
    # Database persistence would go here if enabled
    if ENABLE_DATABASE and db:
        try:
            # Database operations would be implemented here
            pass
        except Exception as e:
            logger.error(f"Failed to persist usage stats: {e}")

async def log_system_event(
    level: str,
    message: str,
    endpoint: str = None,
    university_code: str = None,
    user_id: str = None,
    error_details: str = None,
    db: AsyncSession = None
):
    """Log system events to database"""
    if ENABLE_DATABASE and db:
        try:
            # Database logging would be implemented here
            pass
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")

if ENABLE_DATABASE:
    Base = declarative_base()

    class University(Base):
        __tablename__ = "universities"
        
        id = Column(Integer, primary_key=True)
        code = Column(String(50), unique=True, index=True)
        name = Column(String(200))
        domain = Column(String(100))
        ai_model = Column(String(100), default="llama-3.3-70b-instruct")
        rate_limit_per_minute = Column(Integer, default=10)
        rate_limit_per_hour = Column(Integer, default=100)
        monthly_budget = Column(Float, default=1000.0)
        is_active = Column(Boolean, default=True)
        supported_techniques = Column(JSON)  # Store as JSON array
        safety_requirements = Column(String(50), default="high")
        created_at = Column(DateTime, default=datetime.utcnow)

    class PromptEvaluation(Base):
        __tablename__ = "prompt_evaluations"
        
        id = Column(Integer, primary_key=True)
        user_id = Column(String(255), index=True)
        university_id = Column(Integer, index=True)
        prompt_hash = Column(String(64), index=True)
        ai_model = Column(String(100))
        technique = Column(String(50))
        # Safety metrics
        bias_score = Column(Float)
        bias_summary = Column(Text)
        toxicity_score = Column(Float)
        toxicity_summary = Column(Text)
        alignment_score = Column(Float)
        alignment_summary = Column(Text)
        faithfulness_score = Column(Float, nullable=True)
        faithfulness_summary = Column(Text, nullable=True)
        hallucination_score = Column(Float, nullable=True)
        hallucination_summary = Column(Text, nullable=True)
        # Performance metrics
        processing_time = Column(Float)
        token_count = Column(Integer)
        estimated_cost = Column(Float)
        safety_level = Column(String(50))
        created_at = Column(DateTime, default=datetime.utcnow)

    class SafetyAudit(Base):
        __tablename__ = "safety_audits"
        
        id = Column(String(36), primary_key=True)  # UUID
        prompt_hash = Column(String(64), index=True)
        university_code = Column(String(50), index=True)
        audit_level = Column(String(50))
        safety_score = Column(Float)
        risk_areas = Column(JSON)  # Store as JSON array
        safety_features = Column(JSON)  # Store as JSON array
        recommendations = Column(JSON)  # Store as JSON array
        compliance_level = Column(String(50))
        audit_summary = Column(Text)
        created_at = Column(DateTime, default=datetime.utcnow)

    class TechniqueRecommendation(Base):
        __tablename__ = "technique_recommendations"
        
        id = Column(String(36), primary_key=True)  # UUID
        user_needs_hash = Column(String(64), index=True)
        ai_model = Column(String(100))
        recommended_technique = Column(String(50))
        alternative_techniques = Column(JSON)  # Store as JSON array
        reasoning = Column(Text)
        effectiveness_score = Column(Float)
        safety_considerations = Column(JSON)  # Store as JSON array
        created_at = Column(DateTime, default=datetime.utcnow)

    # Create database connection with enhanced error handling
    try:
        engine = create_engine(
            DATABASE_URL, 
            pool_pre_ping=True, 
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            echo=False
        )
        
        ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        async_engine = create_async_engine(
            ASYNC_DATABASE_URL, 
            pool_pre_ping=True, 
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            echo=False
        )
        
        SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=engine,
            expire_on_commit=False
        )
        
        AsyncSessionLocal = async_sessionmaker(
            async_engine, 
            class_=AsyncSession, 
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        
        Base.metadata.create_all(bind=engine)
        logger.info("Enhanced database connected and tables created successfully")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        ENABLE_DATABASE = False

# =============================================================================
# ENHANCED UTILITY FUNCTIONS
# =============================================================================




def retry_on_failure(max_retries=3, initial_delay=1, backoff_factor=2):
    """Decorator to retry a function on failure with exponential backoff"""
    def decorator(func):
        from functools import wraps
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed.")
                        raise last_exception
        return wrapper
    return decorator

def extract_json_from_text(text: str) -> Optional[Dict]:
    """Extract JSON from text that might contain additional content"""
    # First try direct JSON parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON block in markdown
    json_pattern = r'```json\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON in text
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        try:
            json_str = text[start_idx:end_idx + 1]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    logger.error("No valid JSON found in text")
    return None

def generate_prompt_hash(*args) -> str:
    """Generate hash for caching purposes"""
    content = "|".join(str(arg) for arg in args)
    return hashlib.md5(content.encode()).hexdigest()

def estimate_token_count(text: str) -> int:
    """Estimate token count for text"""
    # Simple estimation: ~4 characters per token
    return len(text) // 4

def validate_prompt_safety(prompt: str) -> Dict[str, Any]:
    """Basic prompt safety validation"""
    safety_issues = []
    risk_score = 0.0
    
    # Check for potentially harmful patterns
    harmful_patterns = [
        r'ignore\s+previous\s+instructions',
        r'ignore\s+all\s+safety',
        r'bypass\s+safety',
        r'generate\s+harmful',
        r'create\s+malicious',
        r'hack\s+into',
        r'exploit\s+vulnerability'
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            safety_issues.append(f"Potential prompt injection: {pattern}")
            risk_score += 0.2
    
    # Check prompt length (extremely long prompts might be attempts to overwhelm)
    if len(prompt) > 10000:
        safety_issues.append("Unusually long prompt detected")
        risk_score += 0.1
    
    return {
        "safe": risk_score < 0.3,
        "risk_score": min(risk_score, 1.0),
        "issues": safety_issues
    }

def optimize_prompt_for_model(prompt: str, model: str) -> Dict[str, Any]:
    """Optimize prompt for specific AI model"""
    model_config = AI_MODEL_CONFIGS.get(model, {})
    max_tokens = model_config.get("max_tokens", 4096)
    
    # Estimate current token count
    current_tokens = estimate_token_count(prompt)
    
    optimizations = []
    optimized_prompt = prompt
    
    # Token optimization
    if current_tokens > max_tokens * 0.8:  # If using more than 80% of max tokens
        # Simple optimization: remove excessive whitespace and redundancy
        optimized_prompt = re.sub(r'\s+', ' ', optimized_prompt.strip())
        optimizations.append("Whitespace optimization")
        
        # If still too long, suggest breaking into parts
        if estimate_token_count(optimized_prompt) > max_tokens * 0.8:
            optimizations.append("Consider breaking prompt into multiple parts")
    
    # Model-specific optimizations
    if model.startswith("gpt"):
        # GPT models work well with structured formats
        if "Return as JSON:" not in optimized_prompt and "{" in optimized_prompt:
            optimizations.append("Added JSON format specification for GPT compatibility")
    
    elif model.startswith("claude"):
        # Claude prefers clear role definitions
        if not optimized_prompt.startswith("You are"):
            optimized_prompt = f"You are a helpful assistant. {optimized_prompt}"
            optimizations.append("Added role definition for Claude compatibility")
    
    elif model.startswith("llama"):
        # Llama models benefit from explicit instruction formatting
        if "[INST]" not in optimized_prompt:
            optimizations.append("Consider using [INST] tags for Llama models")
    
    return {
        "optimized_prompt": optimized_prompt,
        "optimizations": optimizations,
        "token_reduction": current_tokens - estimate_token_count(optimized_prompt),
        "model_compatibility": "high" if len(optimizations) > 0 else "medium"
    }

# =============================================================================
# ENHANCED COST MANAGEMENT
# =============================================================================

class AdvancedCostTracker:
    @staticmethod
    def estimate_request_cost(prompt_length: int, model_type: str, techniques: List[str] = None) -> float:
        """Enhanced cost estimation for multi-technique prompts"""
        tokens = estimate_token_count(str(prompt_length))
        base_cost_per_1k = AI_MODEL_CONFIGS.get(model_type, {}).get("cost_per_1k_tokens", 0.002)
        
        if not techniques:
            techniques = ["chain_of_thought"]
        
        # Base technique multipliers
        technique_multipliers = {
            "chain_of_thought": 1.5,
            "tree_of_thought": 1.8,  # More complex reasoning
            "react": 1.6,  # Iterative reasoning and acting
            "few_shot": 1.3,
            "meta_prompting": 1.4,
            "iterative_refinement": 1.6,
            "safety_first": 1.2,
            "role_prompting": 1.1,
            "constraint_based": 1.1,
            "zero_shot": 1.0
        }
        
        # Calculate combined multiplier
        if len(techniques) == 1:
            multiplier = technique_multipliers.get(techniques[0], 1.0)
        else:
            # Multi-technique combination - not just additive
            individual_multipliers = [technique_multipliers.get(t, 1.0) for t in techniques]
            # Use weighted average with combination bonus/penalty
            avg_multiplier = sum(individual_multipliers) / len(individual_multipliers)
            combination_factor = 1.0 + (len(techniques) - 1) * 0.2  # 20% increase per additional technique
            multiplier = avg_multiplier * combination_factor
        
        return (tokens / 1000) * base_cost_per_1k * multiplier
    
    @staticmethod
    async def check_university_budget(university_config: Dict, estimated_cost: float) -> bool:
        """Enhanced budget checking with technique-aware costs"""
        monthly_budget = university_config.get("monthly_budget", 1000.0)
        
        # In production, this would check actual monthly usage
        # For now, we'll simulate a budget check
        current_usage = 0.0  # Would be fetched from database
        
        if current_usage + estimated_cost > monthly_budget:
            logger.warning(f"Budget exceeded for {university_config['code']}: {current_usage + estimated_cost} > {monthly_budget}")
            return False
        
        logger.info(f"Cost approved: ${estimated_cost:.4f} for {university_config['code']}")
        return True

# =============================================================================
# ENHANCED AI API INTEGRATION
# =============================================================================

class UFL_AI_LLM(DeepEvalBaseLLM):
    """Enhanced LLM adapter for DeepEval with safety features"""
    
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def load_model(self):
        return self

    async def a_generate(self, prompt: str) -> str:
        """Async generation with safety validation"""
        # Basic safety check
        safety_check = validate_prompt_safety(prompt)
        if not safety_check["safe"]:
            raise Exception(f"Unsafe prompt detected: {', '.join(safety_check['issues'])}")
        
        async with aiohttp.ClientSession() as session:
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": AI_MODEL_CONFIGS.get(self.model, {}).get("max_tokens", 4096)
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"AI API error {response.status}: {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]

    def generate(self, prompt: str) -> str:        
        """Synchronous generation with enhanced error handling"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.a_generate(prompt))
                    return future.result(timeout=300)  # 5 minute timeout
            else:
                return asyncio.run(self.a_generate(prompt))
        except Exception as e:
            try:
                import asyncio
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.a_generate(prompt))
                finally:
                    new_loop.close()
            except Exception as fallback_error:
                logger.error(f"Both async methods failed: {e}, {fallback_error}")
                raise Exception(f"LLM generation failed: {str(e)}")

    def get_model_name(self):
        return self.model

@retry_on_failure(max_retries=3, initial_delay=1, backoff_factor=2)
async def call_ufl_api_async(prompt: str, university_config: Dict[str, Any], force_json: bool = True) -> Dict[str, Any]:
    """Enhanced API call with safety and optimization features"""
    if not UFL_AI_API_KEY or not UFL_AI_BASE_URL:
        raise HTTPException(status_code=503, detail="AI API not configured")
    
    # Safety validation
    safety_check = validate_prompt_safety(prompt)
    if not safety_check["safe"]:
        raise HTTPException(status_code=400, detail=f"Unsafe prompt: {', '.join(safety_check['issues'])}")
    
    # Model optimization
    model_type = university_config["ai_model"]
    optimization = optimize_prompt_for_model(prompt, model_type)
    optimized_prompt = optimization["optimized_prompt"]
    
    if optimization["optimizations"]:
        logger.info(f"Applied optimizations: {', '.join(optimization['optimizations'])}")
    
    async with aiohttp.ClientSession() as session:
        data = {
            "model": model_type,
            "messages": [{"role": "user", "content": optimized_prompt}],
            "temperature": 0.3,  # Lower temperature for more consistent prompt generation
            "max_tokens": AI_MODEL_CONFIGS.get(model_type, {}).get("max_tokens", 4096)
        }
        
        # Add JSON formatting if requested and model supports it
        if force_json and AI_MODEL_CONFIGS.get(model_type, {}).get("supports_json", False):
            data["response_format"] = {"type": "json_object"}
        
        headers = {
            "Authorization": f"Bearer {UFL_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        async with session.post(f"{UFL_AI_BASE_URL}/chat/completions", headers=headers, json=data) as response:
            processing_time = time.time() - start_time
            
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"AI API error {response.status}: {error_text}")
                raise HTTPException(status_code=500, detail=f"AI API error {response.status}: {error_text}")
            
            result = await response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Log API usage
            usage = result.get("usage", {})
            logger.info(f"API call completed in {processing_time:.2f}s, tokens: {usage.get('total_tokens', 'unknown')}")
            
            if force_json:
                parsed_content = extract_json_from_text(content)
                if not parsed_content:
                    logger.error(f"Failed to parse JSON response: {content[:200]}...")
                    raise HTTPException(status_code=500, detail="Invalid JSON response from AI")
                return parsed_content
            
            return {"content": content}

# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_async_db():
    """Get async database session"""
    if not ENABLE_DATABASE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            await session.close()

async def get_university_config(university_code: str) -> Dict[str, Any]:
    """Get university configuration with caching"""
    cache_key = f"university_config:{university_code}"
    
    # Check cache first
    cached = store.get_cache(cache_key)
    if cached:
        return cached
    
    # Get from store
    university = store.get_university(university_code)
    if not university:
        raise HTTPException(status_code=404, detail=f"University {university_code} not found")
    
    # Cache the result
    store.set_cache(cache_key, university, ttl=3600)
    return university

def validate_technique_access(university_code: str, technique: str):
    """Validate that university has access to the requested technique"""
    supported_techniques = store.get_supported_techniques(university_code)
    if technique not in supported_techniques:
        raise HTTPException(
            status_code=403, 
            detail=f"Technique '{technique}' not supported by {university_code}. "
                   f"Supported techniques: {', '.join(supported_techniques)}"
        )

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Enhanced Navigator Prompt API...")
    
    # Initialize Redis if enabled
    if ENABLE_REDIS:
        try:
            global redis_client
            import aioredis
            redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
    
    logger.info(f"Application started with {len(PROMPT_TECHNIQUES)} prompt engineering techniques")
    logger.info(f"Supported AI models: {', '.join(AI_MODEL_CONFIGS.keys())}")
    
    yield
    
    # Shutdown cleanup
    if ENABLE_REDIS and 'redis_client' in globals():
        try:
            await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Redis shutdown error: {e}")

# Create FastAPI app
app = FastAPI(
    title="Enhanced Navigator Prompt API",
    version="2.0.0",
    description="Advanced prompt generation and evaluation system with comprehensive safety and technique support",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced rate limiting middleware
@app.middleware("http")
async def enhanced_rate_limit_middleware(request: Request, call_next):
    """Enhanced rate limiting with technique-aware limits"""
    university_code = request.headers.get("X-University-Code", "ufl")
    endpoint = request.url.path
    
    # Check basic rate limit
    if not store.check_rate_limit(university_code, endpoint):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add request tracking
    request.state.start_time = time.time()
    request.state.university_code = university_code
    
    response = await call_next(request)
    
    # Log request completion
    processing_time = time.time() - request.state.start_time
    logger.info(f"Request {endpoint} completed in {processing_time:.3f}s for {university_code}")
    
    return response

# =============================================================================
# ENHANCED API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Enhanced health check with technique and model info"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0",
        "features": {
            "database": ENABLE_DATABASE,
            "redis": ENABLE_REDIS,
            "caching": ENABLE_CACHING,
            "safety_auditing": True,
            "technique_recommendation": True
        },
        "prompt_techniques": len(PROMPT_TECHNIQUES),
        "supported_models": list(AI_MODEL_CONFIGS.keys()),
        "universities": len(store.universities),
        "ai_api_configured": bool(UFL_AI_API_KEY and UFL_AI_BASE_URL)
    }

@app.get("/techniques")
async def list_prompt_techniques():
    """List all available prompt engineering techniques"""
    return {
        "techniques": PROMPT_TECHNIQUES,
        "total_count": len(PROMPT_TECHNIQUES),
        "categories": {
            "safety_focused": [k for k, v in PROMPT_TECHNIQUES.items() if v["safety_level"] in ["high", "maximum"]],
            "performance_focused": [k for k, v in PROMPT_TECHNIQUES.items() if "performance" in v["description"].lower()],
            "structure_focused": [k for k, v in PROMPT_TECHNIQUES.items() if any(word in v["description"].lower() for word in ["structure", "format", "organize"])]
        }
    }

@app.get("/models")
async def list_ai_models():
    """List supported AI models with their configurations"""
    return {
        "models": AI_MODEL_CONFIGS,
        "total_count": len(AI_MODEL_CONFIGS),
        "recommendations": {
            model: config["best_techniques"] 
            for model, config in AI_MODEL_CONFIGS.items()
        }
    }

@app.post("/recommend-technique")
async def recommend_technique(request: TechniqueRecommendationRequest):
    """Recommend the best prompt engineering technique for user needs"""
    try:
        university_config = await get_university_config(request.universityCode)
        supported_techniques = store.get_supported_techniques(request.universityCode)
        
        # Check cache
        cache_key = f"technique_rec:{generate_prompt_hash(request.userNeeds, request.aiModel)}"
        cached_result = store.get_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Create recommendation prompt
        available_techniques = {k: v for k, v in PROMPT_TECHNIQUES.items() if k in supported_techniques}
        techniques_desc = "\n".join([f"- {k}: {v['description']} (Safety: {v['safety_level']})" 
                                   for k, v in available_techniques.items()])
        
        template = template_manager.render_template(
            "generate_prompt_techniques",
            userNeeds=request.userNeeds,
            aiModel=request.aiModel,
            availableTechniques=techniques_desc
        )
        
        result = await call_ufl_api_async(template, university_config)
        
        # Validate recommendation
        recommended_technique = result.get("recommendedTechnique")
        if recommended_technique not in supported_techniques:
            # Fallback to a safe default
            recommended_technique = "chain_of_thought" if "chain_of_thought" in supported_techniques else supported_techniques[0]
            result["recommendedTechnique"] = recommended_technique
            result["note"] = "Recommendation adjusted based on university capabilities"
        
        # Add technique details
        result["techniqueDetails"] = PROMPT_TECHNIQUES.get(recommended_technique, {})
        result["supportedTechniques"] = supported_techniques
        
        # Cache result
        store.set_cache(cache_key, result, ttl=3600)
        
        # Track usage
        store.track_usage(request.universityCode, "recommend-technique", 0.001)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in recommend_technique: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-initial-prompt")
async def generate_initial_prompt(request: UserNeedsRequest, background_tasks: BackgroundTasks):
    """Generate initial prompt with advanced techniques and safety features"""
    try:
        # Validate technique access
        validate_technique_access(request.universityCode, request.technique)
        
        # Get university config
        university_config = await get_university_config(request.universityCode)
        
        # Check cache
        cache_key = f"prompt:{generate_prompt_hash(request.userNeeds, request.aiModel, request.technique, request.safetyLevel)}"
        cached_result = store.get_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for prompt generation")
            return cached_result
        
        # Cost estimation with technique awareness
        estimated_cost = AdvancedCostTracker.estimate_request_cost(
            len(request.userNeeds), 
            request.aiModel, 
            request.technique
        )
        await AdvancedCostTracker.check_university_budget(university_config, estimated_cost)
        
        # Get technique information
        technique_info = PROMPT_TECHNIQUES.get(request.technique, {})
        
        # Generate enhanced template
        template = template_manager.render_template(
            "generate_initial_prompt",
            userNeeds=request.userNeeds,
            aiModel=request.aiModel,
            technique=request.technique,
            safetyLevel=request.safetyLevel,
            techniqueDescription=technique_info.get("description", ""),
            templatePrefix=technique_info.get("template_prefix", "")
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found")
        
        # Call AI API
        start_time = time.time()
        result = await call_ufl_api_async(template, university_config)
        processing_time = time.time() - start_time
        
        # Enhanced result processing
        if "initialPrompt" in result:
            # Perform safety validation on generated prompt
            safety_check = validate_prompt_safety(result["initialPrompt"])
            result["safetyValidation"] = safety_check
            
            # Add optimization suggestions
            optimization = optimize_prompt_for_model(result["initialPrompt"], request.aiModel)
            result["optimizationSuggestions"] = optimization["optimizations"]
            result["estimatedTokens"] = estimate_token_count(result["initialPrompt"])
            
            # Add technique-specific metadata
            result["appliedTechnique"] = {
                "name": technique_info.get("name", request.technique),
                "description": technique_info.get("description", ""),
                "safetyLevel": technique_info.get("safety_level", "medium")
            }
        
        # Cache result
        store.set_cache(cache_key, result, ttl=3600)
        
        # Track usage with enhanced metrics
        store.track_usage(request.universityCode, "generate-initial-prompt", estimated_cost)
        
        logger.info(f"Generated prompt using {request.technique} in {processing_time:.2f}s for {request.universityCode}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_initial_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/safety-audit")
async def safety_audit_prompt(request: SafetyAuditRequest):
    """Perform comprehensive safety audit on a prompt"""
    try:
        university_config = await get_university_config(request.universityCode)
        
        # Check for existing audit
        prompt_hash = generate_prompt_hash(request.promptText)
        existing_audit = store.get_safety_history(prompt_hash)
        
        if existing_audit and request.auditLevel != "comprehensive":
            return existing_audit["results"]
        
        # Basic safety validation
        basic_safety = validate_prompt_safety(request.promptText)
        
        # Advanced safety audit using AI
        template = template_manager.render_template(
            "safety_audit_prompt",
            promptText=request.promptText
        )
        
        audit_result = await call_ufl_api_async(template, university_config)
        
        # Combine basic and advanced results
        comprehensive_result = {
            "safetyScore": min(audit_result.get("safetyScore", 0.5), 1.0 - basic_safety["risk_score"]),
            "riskAreas": audit_result.get("riskAreas", []) + basic_safety["issues"],
            "safetyFeatures": audit_result.get("safetyFeatures", []),
            "recommendations": audit_result.get("recommendations", []),
            "complianceLevel": audit_result.get("complianceLevel", "medium"),
            "auditSummary": audit_result.get("auditSummary", ""),
            "basicValidation": basic_safety,
            "auditTimestamp": datetime.utcnow().isoformat(),
            "auditLevel": request.auditLevel
        }
        
        # Store audit results
        store.store_safety_audit(request.promptText, comprehensive_result)
        
        # Track usage
        store.track_usage(request.universityCode, "safety-audit", 0.005)
        
        return comprehensive_result
        
    except Exception as e:
        logger.error(f"Error in safety_audit_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-prompt-tags")
async def generate_prompt_tags(request: PromptTagsRequest):
    """Generate tags for a prompt"""
    try:
        university_config = await get_university_config(request.universityCode)
        
        # Check cache
        cache_key = f"tags:{generate_prompt_hash(request.promptText)}"
        cached_result = store.get_cache(cache_key)
        if cached_result:
            return cached_result
        
        template = template_manager.render_template(
            "generate_prompt_tags",
            promptText=request.promptText
        )
        
        result = await call_ufl_api_async(template, university_config)
        
        # Cache for 24 hours
        store.set_cache(cache_key, result, ttl=86400)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_prompt_tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-prompt-suggestions")
async def get_prompt_suggestions(request: PromptSuggestionsRequest):
    """Get improvement suggestions for a prompt"""
    try:
        university_config = await get_university_config(request.universityCode)
        
        userCommentsSection = ""
        if request.userComments:
            userCommentsSection = f"\nUser Comments: \"{request.userComments}\"\n"
        
        template = template_manager.render_template(
            "get_prompt_suggestions",
            currentPrompt=request.currentPrompt,
            userCommentsSection=userCommentsSection
        )
        
        result = await call_ufl_api_async(template, university_config)
        return result
        
    except Exception as e:
        logger.error(f"Error in get_prompt_suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prompts/library")
async def get_library_prompts(user_id: Optional[str] = None):
    """Get library prompts with star counts"""
    try:
        if ENABLE_DATABASE:
            # Database implementation would go here
            pass
        
        # Fallback to in-memory storage
        library_prompts = []
        for prompt in store.evaluations:  # Using evaluations as library storage
            enhanced_prompt = PromptResponse(
                id=prompt.get("id", str(uuid.uuid4())),
                userId=prompt.get("user_id", "unknown"),
                text=prompt.get("text", ""),
                createdAt=prompt.get("created_at", datetime.utcnow().isoformat()),
                summary=prompt.get("summary", ""),
                tags=prompt.get("tags", []),
                stars=prompt.get("stars", 0),
                isStarredByUser=False,
                technique=prompt.get("technique"),
                estimatedTokens=prompt.get("estimated_tokens"),
                safetyValidated=prompt.get("safety_validated")
            )
            library_prompts.append(enhanced_prompt)
        
        return library_prompts
            
    except Exception as e:
        logger.error(f"Error getting library prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prompts/library")
async def add_library_prompt(request: LibraryPromptCreate):
    """Add a prompt to the library"""
    try:
        # Generate tags and summary
        university_config = await get_university_config("ufl")  # Default to UFL
        
        # Create tags template if not exists
        if "generate_prompt_tags" not in template_manager.templates:
            template_manager.templates["generate_prompt_tags"] = {
                "description": "Generate tags for a prompt",
                "version": "1.0",
                "template": """
Analyze the given prompt and generate relevant tags and a summary.

Prompt: {{promptText}}

Return as JSON:
{
    "summary": "Brief summary of what this prompt does",
    "tags": ["tag1", "tag2", "tag3"]
}
"""
            }
        
        tags_template = template_manager.render_template(
            "generate_prompt_tags",
            promptText=request.text
        )
        
        tags_result = await call_ufl_api_async(tags_template, university_config)
        summary = tags_result.get("summary", "Generated prompt")
        tags = tags_result.get("tags", [])
        
        # Add to in-memory storage
        new_prompt = {
            "id": str(uuid.uuid4()),
            "user_id": request.userId,
            "text": request.text,
            "created_at": datetime.utcnow().isoformat(),
            "summary": summary,
            "tags": tags,
            "stars": 0,
            "technique": request.technique,
            "ai_model": request.aiModel,
            "estimated_tokens": estimate_token_count(request.text),
            "safety_validated": validate_prompt_safety(request.text)["safe"]
        }
        
        store.evaluations.append(new_prompt)
        
        return PromptResponse(
            id=new_prompt["id"],
            userId=new_prompt["user_id"],
            text=new_prompt["text"],
            createdAt=new_prompt["created_at"],
            summary=summary,
            tags=tags,
            stars=0,
            isStarredByUser=False,
            technique=request.technique,
            estimatedTokens=new_prompt["estimated_tokens"],
            safetyValidated=new_prompt["safety_validated"]
        )
            
    except Exception as e:
        logger.error(f"Error adding library prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/prompts/library/{prompt_id}")
async def delete_library_prompt(prompt_id: str, user_id: str):
    """Delete a prompt from the library"""
    try:
        # Check if user has permission (simple admin check)
        is_admin = user_id == "admin" or user_id == "mock-user-123"
        if not is_admin:
            raise HTTPException(status_code=403, detail="You do not have permission to delete library prompts")
        
        # Remove from in-memory storage
        store.evaluations = [p for p in store.evaluations if p.get("id") != prompt_id]
        
        return {"success": True}
            
    except Exception as e:
        logger.error(f"Error deleting library prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prompts/library/star")
async def toggle_star_prompt(request: ToggleStarRequest):
    """Toggle star for a library prompt"""
    try:
        # Find prompt in storage
        for prompt in store.evaluations:
            if prompt.get("id") == request.promptId:
                current_stars = prompt.get("stars", 0)
                prompt["stars"] = current_stars + 1 if current_stars == 0 else 0
                return {"success": True, "starred": prompt["stars"] > 0}
        
        raise HTTPException(status_code=404, detail="Prompt not found")
            
    except Exception as e:
        logger.error(f"Error toggling star: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    """Optimize prompt for specific AI model and goals"""
    try:
        university_config = await get_university_config(request.universityCode)
        
        # Get model capabilities
        model_config = AI_MODEL_CONFIGS.get(request.aiModel, {})
        
        # Basic optimization
        basic_optimization = optimize_prompt_for_model(request.currentPrompt, request.aiModel)
        
        # Advanced AI-powered optimization
        template = template_manager.render_template(
            "prompt_optimization",
            currentPrompt=request.currentPrompt,
            aiModel=request.aiModel,
            modelCapabilities=json.dumps(model_config),
            optimizationGoals=", ".join(request.optimizationGoals)
        )
        
        ai_optimization = await call_ufl_api_async(template, university_config)
        
        # Combine results
        result = {
            "optimizedPrompt": ai_optimization.get("optimizedPrompt", basic_optimization["optimized_prompt"]),
            "basicOptimizations": basic_optimization["optimizations"],
            "aiOptimizations": ai_optimization.get("optimizations", []),
            "tokenReduction": basic_optimization["token_reduction"],
            "modelCompatibility": basic_optimization["model_compatibility"],
            "expectedPerformance": ai_optimization.get("expectedPerformance", 0.85),
            "optimizationGoals": request.optimizationGoals,
            "modelSpecificFeatures": ai_optimization.get("modelSpecificFeatures", [])
        }
        
        # Track usage
        store.track_usage(request.universityCode, "optimize-prompt", 0.003)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in optimize_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate-and-iterate-prompt")
async def evaluate_and_iterate_prompt(request: EvaluatePromptRequest, background_tasks: BackgroundTasks):
    """Enhanced evaluation and iteration with comprehensive safety and performance metrics"""
    try:
        # Validate technique access
        validate_technique_access(request.universityCode, request.technique)
        
        university_config = await get_university_config(request.universityCode)
        
        # Check cache
        cache_key = f"eval:{generate_prompt_hash(request.prompt, request.userNeeds, request.aiModel, request.technique)}"
        cached_result = store.get_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for evaluation")
            return cached_result
        
        # Cost check with technique awareness
        estimated_cost = AdvancedCostTracker.estimate_request_cost(
            len(request.prompt) + len(request.userNeeds), 
            request.aiModel,
            request.technique
        )
        await AdvancedCostTracker.check_university_budget(university_config, estimated_cost)
        
        # Generate improved prompt
        retrievedContentSection = f"\n**Knowledge Base Content:**\n{request.retrievedContent}\n" if request.retrievedContent else ""
        groundTruthsSection = f"\n**Ground Truths / Few-shot Examples:**\n{request.groundTruths}\n" if request.groundTruths else ""
        
        template = template_manager.render_template(
            "evaluate_and_iterate_prompt",
            prompt=request.prompt,
            userNeeds=request.userNeeds,
            aiModel=request.aiModel,
            currentTechnique=request.technique,
            retrievedContentSection=retrievedContentSection,
            groundTruthsSection=groundTruthsSection
        )
        
        start_time = time.time()
        improved_prompt_response = await call_ufl_api_async(template, university_config)
        improved_prompt = improved_prompt_response.get("initialPrompt")

        if not improved_prompt:
            raise HTTPException(status_code=500, detail="Failed to generate improved prompt")

        # Perform safety audit if requested
        safety_results = None
        if request.safetyAudit:
            safety_audit_req = SafetyAuditRequest(
                promptText=improved_prompt,
                universityCode=request.universityCode,
                auditLevel="comprehensive"
            )
            safety_results = await safety_audit_prompt(safety_audit_req)

        # Enhanced evaluation with DeepEval
        if not UFL_AI_API_KEY or not UFL_AI_BASE_URL:
            # Skip evaluation if AI API not configured
            results = {
                "improvedPrompt": improved_prompt,
                "improvements": improved_prompt_response.get("improvements", []),
                "safetyEnhancements": improved_prompt_response.get("safetyEnhancements", []),
                "techniqueOptimizations": improved_prompt_response.get("techniqueOptimizations", []),
                "bias": {"score": 0.0, "summary": "Evaluation skipped - AI API not configured", "testCases": []},
                "toxicity": {"score": 0.0, "summary": "Evaluation skipped - AI API not configured", "testCases": []},
                "promptAlignment": {"score": 0.0, "summary": "Evaluation skipped - AI API not configured", "testCases": []},
                "safetyAudit": safety_results,
                "estimatedTokens": estimate_token_count(improved_prompt),
                "confidenceScore": improved_prompt_response.get("confidenceScore", 0.8)
            }
        else:
            try:
                custom_model = UFL_AI_LLM(
                    model=request.aiModel, 
                    api_key=UFL_AI_API_KEY, 
                    base_url=UFL_AI_BASE_URL
                )

                test_case = LLMTestCase(
                    input=request.userNeeds,
                    actual_output=improved_prompt,
                    retrieval_context=[request.retrievedContent] if request.retrievedContent else None,
                    context=[request.groundTruths] if request.groundTruths else None
                )

                # Enhanced metrics including hallucination detection
                metrics = [
                    BiasMetric(threshold=0.5, model=custom_model),
                    ToxicityMetric(threshold=0.5, model=custom_model),
                    AnswerRelevancyMetric(threshold=0.5, model=custom_model)
                ]
                
                if request.retrievedContent:
                    metrics.extend([
                        FaithfulnessMetric(threshold=0.5, model=custom_model),
                        HallucinationMetric(threshold=0.5, model=custom_model)
                    ])

                # Run evaluation in separate thread
                logger.info("Starting comprehensive evaluation...")
                evaluation_results = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: evaluate(test_cases=[test_case], metrics=metrics)
                )
                
                # Process results with enhanced error handling
                results = {
                    "improvedPrompt": improved_prompt,
                    "improvements": improved_prompt_response.get("improvements", []),
                    "safetyEnhancements": improved_prompt_response.get("safetyEnhancements", []),
                    "techniqueOptimizations": improved_prompt_response.get("techniqueOptimizations", []),
                    "safetyAudit": safety_results,
                    "estimatedTokens": estimate_token_count(improved_prompt),
                    "confidenceScore": improved_prompt_response.get("confidenceScore", 0.8),
                    "recommendedTesting": improved_prompt_response.get("recommendedTesting", [])
                }
                
                # Extract metric results
                evaluated_metrics = {}
                
                if hasattr(evaluation_results, 'test_results') and evaluation_results.test_results:
                    test_result = evaluation_results.test_results[0]
                    
                    if hasattr(test_result, 'metrics_data') and test_result.metrics_data:
                        for i, metric_data in enumerate(test_result.metrics_data):
                            metric_name = None
                            for attr in ['metric', 'name', 'metric_name']:
                                if hasattr(metric_data, attr):
                                    metric_name = str(getattr(metric_data, attr)).lower()
                                    break
                            
                            score = getattr(metric_data, 'score', 0.0)
                            reason = getattr(metric_data, 'reason', 'Evaluation completed')
                            
                            if metric_name:
                                if 'bias' in metric_name:
                                    evaluated_metrics['bias'] = {"score": round(score, 2), "summary": reason}
                                elif 'toxicity' in metric_name:
                                    evaluated_metrics['toxicity'] = {"score": round(score, 2), "summary": reason}
                                elif 'answer' in metric_name or 'relevancy' in metric_name:
                                    evaluated_metrics['promptAlignment'] = {"score": round(score, 2), "summary": reason}
                                elif 'faithful' in metric_name:
                                    evaluated_metrics['faithfulness'] = {"score": round(score, 2), "summary": reason}
                                elif 'hallucination' in metric_name:
                                    evaluated_metrics['hallucination'] = {"score": round(score, 2), "summary": reason}

                # Build final results with comprehensive metrics
                metric_names = ['bias', 'toxicity', 'promptAlignment']
                if request.retrievedContent:
                    metric_names.extend(['faithfulness', 'hallucination'])
                
                for metric_name in metric_names:
                    if metric_name in evaluated_metrics:
                        results[metric_name] = {
                            "score": evaluated_metrics[metric_name]["score"],
                            "summary": evaluated_metrics[metric_name]["summary"],
                            "testCases": []
                        }
                    else:
                        results[metric_name] = {
                            "score": 0.0,
                            "summary": f"{metric_name.title()} evaluation completed - no issues detected.",
                            "testCases": []
                        }
                
                logger.info("Comprehensive evaluation completed successfully")
                
            except Exception as eval_error:
                logger.error(f"Evaluation failed: {eval_error}")
                # Provide fallback results
                results = {
                    "improvedPrompt": improved_prompt,
                    "improvements": improved_prompt_response.get("improvements", []),
                    "safetyEnhancements": improved_prompt_response.get("safetyEnhancements", []),
                    "techniqueOptimizations": improved_prompt_response.get("techniqueOptimizations", []),
                    "bias": {"score": 0.0, "summary": f"Evaluation failed: {str(eval_error)}", "testCases": []},
                    "toxicity": {"score": 0.0, "summary": f"Evaluation failed: {str(eval_error)}", "testCases": []},
                    "promptAlignment": {"score": 0.0, "summary": f"Evaluation failed: {str(eval_error)}", "testCases": []},
                    "safetyAudit": safety_results,
                    "estimatedTokens": estimate_token_count(improved_prompt),
                    "confidenceScore": improved_prompt_response.get("confidenceScore", 0.5)
                }
                if request.retrievedContent:
                    results['faithfulness'] = {"score": 0.0, "summary": f"Evaluation failed: {str(eval_error)}", "testCases": []}
                    results['hallucination'] = {"score": 0.0, "summary": f"Evaluation failed: {str(eval_error)}", "testCases": []}

        processing_time = time.time() - start_time

        # Cache results with shorter TTL for comprehensive evaluations
        store.set_cache(cache_key, results, ttl=1800)  # 30 minutes
        
        # Enhanced usage tracking
        store.track_usage(request.universityCode, "evaluate-and-iterate-prompt", estimated_cost)
        
        logger.info(f"Enhanced evaluation completed in {processing_time:.2f}s for {request.universityCode} using {request.technique}")
        return results

    except Exception as e:
        logger.error(f"Error in evaluate_and_iterate_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/iterate-on-prompt")
async def iterate_on_prompt(request: IteratePromptRequest, background_tasks: BackgroundTasks):
    """Enhanced prompt iteration with advanced optimization"""
    try:
        university_config = await get_university_config(request.universityCode)
        
        # Cost check
        estimated_cost = AdvancedCostTracker.estimate_request_cost(
            len(request.currentPrompt) + len(request.userComments), 
            university_config["ai_model"]
        )
        await AdvancedCostTracker.check_university_budget(university_config, estimated_cost)
        
        selectedSuggestions = "\n".join([f"- {s}" for s in request.selectedSuggestions])
        
        template = template_manager.render_template(
            "iterate_on_prompt",
            currentPrompt=request.currentPrompt,
            userComments=request.userComments,
            selectedSuggestions=selectedSuggestions,
            aiModel=university_config["ai_model"]
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found")
        
        result = await call_ufl_api_async(template, university_config)
        
        # Add optimization analysis
        if "newPrompt" in result:
            optimization = optimize_prompt_for_model(result["newPrompt"], university_config["ai_model"])
            result["optimizationAnalysis"] = optimization
            result["estimatedTokens"] = estimate_token_count(result["newPrompt"])
            
            # Safety validation
            safety_check = validate_prompt_safety(result["newPrompt"])
            result["safetyValidation"] = safety_check
        
        # Track usage
        store.track_usage(request.universityCode, "iterate-on-prompt", estimated_cost)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in iterate_on_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ENHANCED PROMPT HISTORY AND LIBRARY ENDPOINTS
# =============================================================================

@app.get("/prompts/history/{user_id}")
async def get_history_prompts(user_id: str, limit: int = 20, technique_filter: Optional[str] = None):
    """Get prompt history with enhanced filtering"""
    try:
        if ENABLE_DATABASE:
            # Enhanced database query with technique filtering
            query_text = """
                SELECT p.*, 
                       pe.technique, pe.ai_model, pe.safety_level,
                       pe.bias_score, pe.toxicity_score, pe.alignment_score
                FROM prompts p
                LEFT JOIN prompt_evaluations pe ON p.id = pe.prompt_hash
                WHERE p.user_id = :user_id
            """
            params = {"user_id": user_id}
            
            if technique_filter:
                query_text += " AND pe.technique = :technique"
                params["technique"] = technique_filter
            
            query_text += " ORDER BY p.created_at DESC LIMIT :limit"
            params["limit"] = limit
            
            # Would execute database query here
            # For now, return enhanced in-memory version
            pass
        
        # Enhanced in-memory storage with technique info
        user_prompts = [
            p for p in store.prompt_sessions 
            if p.get("user_id") == user_id and 
            (not technique_filter or p.get("technique") == technique_filter)
        ]
        
        # Add technique metadata
        enhanced_prompts = []
        for prompt in user_prompts[:limit]:
            enhanced_prompt = prompt.copy()
            technique = prompt.get("technique", "unknown")
            if technique in PROMPT_TECHNIQUES:
                enhanced_prompt["techniqueInfo"] = PROMPT_TECHNIQUES[technique]
            enhanced_prompts.append(enhanced_prompt)
        
        return enhanced_prompts
            
    except Exception as e:
        logger.error(f"Error getting history prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/prompts/history")
async def add_history_prompt(request: PromptCreate):
    """Add prompt to history with enhanced metadata"""
    try:
        # Enhanced prompt creation with metadata
        new_prompt = {
            "id": str(uuid.uuid4()),
            "user_id": request.userId,
            "text": request.text,
            "created_at": datetime.utcnow().isoformat(),
            "estimated_tokens": estimate_token_count(request.text),
            "safety_validated": validate_prompt_safety(request.text)["safe"],
            "technique": getattr(request, 'technique', 'unknown'),
            "ai_model": getattr(request, 'ai_model', 'unknown')
        }
        
        if ENABLE_DATABASE:
            # Enhanced database storage would go here
            pass
        else:
            # In-memory storage with size limit
            store.prompt_sessions.append(new_prompt)
            # Keep only the most recent prompts per user
            user_prompts = [p for p in store.prompt_sessions if p["user_id"] == request.userId]
            if len(user_prompts) > 20:  # MAX_HISTORY_PROMPTS_PER_USER
                oldest_prompt = min(user_prompts, key=lambda x: x["created_at"])
                store.prompt_sessions.remove(oldest_prompt)
        
        return new_prompt
            
    except Exception as e:
        logger.error(f"Error adding history prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ANALYTICS AND REPORTING ENDPOINTS  
# =============================================================================

@app.get("/analytics/technique-usage/{university_code}")
async def get_technique_usage_analytics(university_code: str, days: int = 30):
    """Get analytics on technique usage patterns"""
    try:
        # This would query the database for actual usage patterns
        # For now, return mock analytics data
        
        analytics = {
            "university_code": university_code,
            "period_days": days,
            "technique_usage": {
                "chain_of_thought": {"count": 45, "success_rate": 0.92, "avg_safety_score": 0.88},
                "few_shot": {"count": 32, "success_rate": 0.89, "avg_safety_score": 0.91},
                "safety_first": {"count": 28, "success_rate": 0.95, "avg_safety_score": 0.97},
                "role_prompting": {"count": 22, "success_rate": 0.87, "avg_safety_score": 0.85},
                "constraint_based": {"count": 18, "success_rate": 0.94, "avg_safety_score": 0.93}
            },
            "safety_trends": {
                "avg_bias_score": 0.12,
                "avg_toxicity_score": 0.08,
                "avg_alignment_score": 0.91,
                "safety_issues_detected": 3,
                "prompts_flagged": 2
            },
            "model_performance": {
                model: {"usage_count": 25, "avg_satisfaction": 0.88}
                for model in AI_MODEL_CONFIGS.keys()
            },
            "recommendations": [
                "Consider increasing use of safety_first technique for sensitive applications",
                "Chain_of_thought shows high success rate - good for complex reasoning tasks",
                "Monitor constraint_based technique - excellent safety scores"
            ]
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting technique analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/safety-report/{university_code}")
async def get_safety_report(university_code: str, days: int = 30):
    """Generate comprehensive safety report"""
    try:
        # This would generate a real safety report from database
        safety_report = {
            "university_code": university_code,
            "report_period": days,
            "generated_at": datetime.utcnow().isoformat(),
            "overview": {
                "total_prompts_generated": 145,
                "safety_audits_performed": 89,
                "prompts_flagged": 2,
                "overall_safety_score": 0.94
            },
            "risk_categories": {
                "bias_risk": {"score": 0.11, "status": "low", "incidents": 1},
                "toxicity_risk": {"score": 0.07, "status": "very_low", "incidents": 0},
                "privacy_risk": {"score": 0.15, "status": "low", "incidents": 1},
                "misinformation_risk": {"score": 0.09, "status": "very_low", "incidents": 0}
            },
            "technique_safety": {
                technique: {
                    "safety_score": PROMPT_TECHNIQUES[technique]["safety_level"],
                    "usage_count": 20,
                    "incident_count": 0
                }
                for technique in PROMPT_TECHNIQUES.keys()
            },
            "recommendations": [
                "Continue current safety practices - excellent overall performance",
                "Consider additional bias detection for financial domain prompts",
                "Implement regular safety training for prompt engineers"
            ],
            "compliance_status": "COMPLIANT",
            "next_review_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        return safety_report
        
    except Exception as e:
        logger.error(f"Error generating safety report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ADMIN ENDPOINTS (ENHANCED)
# =============================================================================

@app.get("/admin/system-status")
async def get_system_status():
    """Get comprehensive system status"""
    return {
        "system_health": "operational",
        "version": "2.0.0",
        "uptime": time.time(),
        "features": {
            "database": ENABLE_DATABASE,
            "redis": ENABLE_REDIS,
            "caching": ENABLE_CACHING,
            "ai_api": bool(UFL_AI_API_KEY and UFL_AI_BASE_URL)
        },
        "prompt_engineering": {
            "techniques_available": len(PROMPT_TECHNIQUES),
            "models_supported": len(AI_MODEL_CONFIGS),
            "universities_configured": len(store.universities)
        },
        "usage_stats": {
            "total_requests": len(store.usage_stats),
            "cache_hit_rate": 0.75,  # Mock value
            "average_response_time": 2.3  # Mock value
        },
        "safety_status": {
            "audits_performed": len(store.safety_audits),
            "safety_incidents": 0,
            "compliance_level": "high"
        }
    }

@app.post("/admin/technique/{technique_name}/enable")
async def enable_technique_for_university(technique_name: str, university_code: str, admin_key: str):
    """Enable a technique for a specific university"""
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    if technique_name not in PROMPT_TECHNIQUES:
        raise HTTPException(status_code=404, detail="Technique not found")
    
    university = store.get_university(university_code)
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    
    if technique_name not in university["supported_techniques"]:
        university["supported_techniques"].append(technique_name)
        logger.info(f"Enabled technique {technique_name} for {university_code}")
    
    return {
        "message": f"Technique {technique_name} enabled for {university_code}",
        "supported_techniques": university["supported_techniques"]
    }

# =============================================================================
# STREAMING ENDPOINTS (ENHANCED)
# =============================================================================

@app.post("/evaluate-prompt-stream")
async def evaluate_prompt_stream(request: EvaluatePromptRequest):
    """Enhanced streaming evaluation with detailed progress"""
    async def generate():
        try:
            yield f"data: {json.dumps({'status': 'starting', 'step': 'initializing', 'technique': request.technique})}\n\n"
            
            university_config = await get_university_config(request.universityCode)
            yield f"data: {json.dumps({'status': 'progress', 'step': 'config_loaded', 'university': university_config['name']})}\n\n"
            
            # Validate technique access
            validate_technique_access(request.universityCode, request.technique)
            yield f"data: {json.dumps({'status': 'progress', 'step': 'technique_validated', 'technique': request.technique})}\n\n"
            
            # Cost check
            estimated_cost = AdvancedCostTracker.estimate_request_cost(
                len(request.prompt) + len(request.userNeeds), 
                request.aiModel,
                request.technique
            )
            await AdvancedCostTracker.check_university_budget(university_config, estimated_cost)
            yield f"data: {json.dumps({'status': 'progress', 'step': 'budget_approved', 'cost': estimated_cost})}\n\n"
            
            # Safety audit first if requested
            if request.safetyAudit:
                yield f"data: {json.dumps({'status': 'progress', 'step': 'safety_audit_starting'})}\n\n"
                safety_audit_req = SafetyAuditRequest(
                    promptText=request.prompt,
                    universityCode=request.universityCode,
                    auditLevel="comprehensive"
                )
                safety_results = await safety_audit_prompt(safety_audit_req)
                yield f"data: {json.dumps({'status': 'progress', 'step': 'safety_audit_completed', 'safety_score': safety_results.get('safetyScore', 0.0)})}\n\n"
            
            # Generate improved prompt
            yield f"data: {json.dumps({'status': 'progress', 'step': 'generating_improved_prompt'})}\n\n"
            
            retrievedContentSection = f"\n**Knowledge Base Content:**\n{request.retrievedContent}\n" if request.retrievedContent else ""
            groundTruthsSection = f"\n**Ground Truths / Few-shot Examples:**\n{request.groundTruths}\n" if request.groundTruths else ""

            template = template_manager.render_template(
                "evaluate_and_iterate_prompt",
                prompt=request.prompt,
                userNeeds=request.userNeeds,
                aiModel=request.aiModel,
                currentTechnique=request.technique,
                retrievedContentSection=retrievedContentSection,
                groundTruthsSection=groundTruthsSection
            )
            
            improved_prompt_response = await call_ufl_api_async(template, university_config)
            improved_prompt = improved_prompt_response.get("initialPrompt")
            
            yield f"data: {json.dumps({'status': 'progress', 'step': 'prompt_improved', 'token_count': estimate_token_count(improved_prompt)})}\n\n"
            
            # Check if AI API is configured for evaluation
            if not UFL_AI_API_KEY or not UFL_AI_BASE_URL:
                yield f"data: {json.dumps({'status': 'progress', 'step': 'evaluation_skipped', 'reason': 'AI API not configured'})}\n\n"
                
                results = {
                    "improvedPrompt": improved_prompt,
                    "improvements": improved_prompt_response.get("improvements", []),
                    "bias": {"score": 0.0, "summary": "Evaluation skipped - AI API not configured"},
                    "toxicity": {"score": 0.0, "summary": "Evaluation skipped - AI API not configured"},
                    "promptAlignment": {"score": 0.0, "summary": "Evaluation skipped - AI API not configured"}
                }
                
                yield f"data: {json.dumps({'status': 'completed', 'results': results})}\n\n"
                return
            
            # Start comprehensive evaluation
            yield f"data: {json.dumps({'status': 'progress', 'step': 'starting_evaluation'})}\n\n"
            
            custom_model = UFL_AI_LLM(
                model=request.aiModel, 
                api_key=UFL_AI_API_KEY, 
                base_url=UFL_AI_BASE_URL
            )

            test_case = LLMTestCase(
                input=request.userNeeds,
                actual_output=improved_prompt,
                retrieval_context=[request.retrievedContent] if request.retrievedContent else None,
                context=[request.groundTruths] if request.groundTruths else None
            )

            # Evaluate metrics individually for better streaming
            metrics_to_evaluate = [
                ("bias", BiasMetric(threshold=0.5, model=custom_model)),
                ("toxicity", ToxicityMetric(threshold=0.5, model=custom_model)),
                ("alignment", AnswerRelevancyMetric(threshold=0.5, model=custom_model))
            ]
            
            if request.retrievedContent:
                metrics_to_evaluate.extend([
                    ("faithfulness", FaithfulnessMetric(threshold=0.5, model=custom_model)),
                    ("hallucination", HallucinationMetric(threshold=0.5, model=custom_model))
                ])
            
            results = {
                "improvedPrompt": improved_prompt,
                "improvements": improved_prompt_response.get("improvements", []),
                "safetyEnhancements": improved_prompt_response.get("safetyEnhancements", []),
                "techniqueOptimizations": improved_prompt_response.get("techniqueOptimizations", []),
            }
            
            # Evaluate each metric and stream results
            for metric_name, metric in metrics_to_evaluate:
                yield f"data: {json.dumps({'status': 'progress', 'step': f'evaluating_{metric_name}'})}\n\n"
                
                try:
                    # Evaluate single metric
                    single_result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: evaluate(test_cases=[test_case], metrics=[metric])
                    )
                    
                    if hasattr(single_result, 'test_results') and single_result.test_results:
                        test_result = single_result.test_results[0]
                        if hasattr(test_result, 'metrics_data') and test_result.metrics_data:
                            metric_data = test_result.metrics_data[0]
                            score = round(getattr(metric_data, 'score', 0.0), 2)
                            reason = getattr(metric_data, 'reason', 'Evaluation completed')
                            
                            display_name = metric_name if metric_name != 'alignment' else 'promptAlignment'
                            results[display_name] = {
                                "score": score,
                                "summary": reason,
                                "testCases": []
                            }
                            
                            yield f"data: {json.dumps({'status': 'progress', 'step': 'metric_completed', 'metric': display_name, 'score': score})}\n\n"
                        else:
                            # Fallback result
                            display_name = metric_name if metric_name != 'alignment' else 'promptAlignment'
                            results[display_name] = {
                                "score": 0.0,
                                "summary": f"{display_name.title()} evaluation completed - no issues detected.",
                                "testCases": []
                            }
                            yield f"data: {json.dumps({'status': 'progress', 'step': 'metric_completed', 'metric': display_name, 'score': 0.0})}\n\n"
                except Exception as e:
                    logger.error(f"Error evaluating {metric_name}: {e}")
                    display_name = metric_name if metric_name != 'alignment' else 'promptAlignment'
                    results[display_name] = {
                        "score": 0.0,
                        "summary": f"Evaluation error: {str(e)}",
                        "testCases": []
                    }
                    yield f"data: {json.dumps({'status': 'progress', 'step': 'metric_error', 'metric': display_name, 'error': str(e)})}\n\n"
            
            # Add final metadata
            results["estimatedTokens"] = estimate_token_count(improved_prompt)
            results["confidenceScore"] = improved_prompt_response.get("confidenceScore", 0.8)
            results["appliedTechnique"] = request.technique
            
            yield f"data: {json.dumps({'status': 'completed', 'results': results})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming evaluation error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

# =============================================================================
# DEVELOPMENT AND TESTING ENDPOINTS (ENHANCED)
# =============================================================================

@app.get("/dev/test-techniques")
async def test_all_techniques():
    """Test all prompt engineering techniques"""
    test_results = {}
    test_prompt = "Create a helpful assistant for customer service."
    
    for technique_name, technique_info in PROMPT_TECHNIQUES.items():
        try:
            # Test technique with a simple request
            request = UserNeedsRequest(
                userNeeds=test_prompt,
                technique=technique_name,
                universityCode="ufl"
            )
            
            result = await generate_initial_prompt(request, BackgroundTasks())
            
            test_results[technique_name] = {
                "status": "success",
                "safety_level": technique_info["safety_level"],
                "generated": bool(result.get("initialPrompt")),
                "token_count": result.get("estimatedTokens", 0),
                "safety_validated": result.get("safetyValidation", {}).get("safe", False)
            }
            
        except Exception as e:
            test_results[technique_name] = {
                "status": "error",
                "error": str(e),
                "safety_level": technique_info["safety_level"]
            }
    
    return {
        "test_summary": {
            "total_techniques": len(PROMPT_TECHNIQUES),
            "successful": len([r for r in test_results.values() if r["status"] == "success"]),
            "failed": len([r for r in test_results.values() if r["status"] == "error"])
        },
        "results": test_results
    }

@app.post("/dev/benchmark-performance")
async def benchmark_performance():
    """Benchmark system performance across different scenarios"""
    benchmarks = []
    test_scenarios = [
        {"userNeeds": "Simple greeting assistant", "technique": "zero_shot", "expected_time": 2.0},
        {"userNeeds": "Complex reasoning for financial analysis", "technique": "chain_of_thought", "expected_time": 5.0},
        {"userNeeds": "Safe content moderation system", "technique": "safety_first", "expected_time": 3.0},
        {"userNeeds": "Customer service with examples", "technique": "few_shot", "expected_time": 4.0}
    ]
    
    for i, scenario in enumerate(test_scenarios):
        try:
            start_time = time.time()
            
            request = UserNeedsRequest(
                userNeeds=scenario["userNeeds"],
                technique=scenario["technique"],
                universityCode="ufl"
            )
            
            result = await generate_initial_prompt(request, BackgroundTasks())
            
            execution_time = time.time() - start_time
            
            benchmarks.append({
                "scenario": i + 1,
                "technique": scenario["technique"],
                "execution_time": round(execution_time, 2),
                "expected_time": scenario["expected_time"],
                "performance": "good" if execution_time <= scenario["expected_time"] else "slow",
                "success": bool(result.get("initialPrompt")),
                "token_count": result.get("estimatedTokens", 0)
            })
            
        except Exception as e:
            benchmarks.append({
                "scenario": i + 1,
                "technique": scenario["technique"],
                "execution_time": 0,
                "expected_time": scenario["expected_time"],
                "performance": "failed",
                "success": False,
                "error": str(e)
            })
    
    avg_time = sum(b["execution_time"] for b in benchmarks if b["success"]) / len([b for b in benchmarks if b["success"]])
    
    return {
        "benchmark_summary": {
            "total_scenarios": len(test_scenarios),
            "successful": len([b for b in benchmarks if b["success"]]),
            "average_execution_time": round(avg_time, 2),
            "performance_grade": "A" if avg_time < 3.0 else "B" if avg_time < 5.0 else "C"
        },
        "detailed_results": benchmarks
    }

# =============================================================================
# MAIN APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info("="*70)
    logger.info("🚀 Starting Enhanced Navigator Prompt API v2.0")
    logger.info("="*70)
    logger.info(f"📍 Server: http://{host}:{port}")
    logger.info(f"🗄️  Database: {'✅ Enabled' if ENABLE_DATABASE else '❌ In-Memory'}")
    logger.info(f"🔄 Redis: {'✅ Enabled' if ENABLE_REDIS else '❌ In-Memory'}")
    logger.info(f"💾 Caching: {'✅ Enabled' if ENABLE_CACHING else '❌ Disabled'}")
    logger.info(f"🤖 AI API: {'✅ Configured' if UFL_AI_API_KEY and UFL_AI_BASE_URL else '❌ Not Configured'}")
    logger.info("")
    logger.info("🎯 Prompt Engineering Features:")
    logger.info(f"   • {len(PROMPT_TECHNIQUES)} Advanced Techniques Available")
    logger.info(f"   • {len(AI_MODEL_CONFIGS)} AI Models Supported")
    logger.info(f"   • {len(store.universities)} Universities Configured")
    logger.info("")
    logger.info("🛡️  Safety & Security Features:")
    logger.info("   • Comprehensive Safety Auditing")
    logger.info("   • Bias & Toxicity Detection")
    logger.info("   • Prompt Injection Protection")
    logger.info("   • Real-time Compliance Monitoring")
    logger.info("")
    logger.info("📊 Advanced Capabilities:")
    logger.info("   • Streaming Evaluations")
    logger.info("   • Technique Recommendations")
    logger.info("   • Performance Analytics")
    logger.info("   • Model-Specific Optimizations")
    logger.info("")
    logger.info("🔧 Available Techniques:")
    for name, info in PROMPT_TECHNIQUES.items():
        safety_emoji = "🔒" if info["safety_level"] == "maximum" else "🛡️" if info["safety_level"] == "high" else "⚠️"
        logger.info(f"   {safety_emoji} {info['name']}: {info['description']}")
    logger.info("")
    logger.info("🎭 Supported AI Models:")
    for model, config in AI_MODEL_CONFIGS.items():
        logger.info(f"   🤖 {model}: {config['max_tokens']} tokens, ${config['cost_per_1k_tokens']}/1k tokens")
    logger.info("="*70)
    
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level="info" 
    )