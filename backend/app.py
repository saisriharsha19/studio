# app.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import asyncio
import aiohttp
import json
import time
import logging
import hashlib
from contextlib import asynccontextmanager
from collections import defaultdict
import gc
from dotenv import load_dotenv
from utils import (
    retry_on_failure, extract_json_from_text, validate_response_against_schema,
    deepeval_integration, prompt_quality_assessor, UFLCustomLLM, DeepEvalIntegration
)
from prompt_templates import template_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for connection pooling and caching
aiohttp_session = None
cache = {}
cache_ttl = {}
rate_limiter = defaultdict(list)

# Configure API settings from environment variables
UFL_AI_API_KEY = os.getenv("UFL_AI_API_KEY")
UFL_AI_BASE_URL = os.getenv("UFL_AI_BASE_URL")
UFL_AI_MODEL = os.getenv("UFL_AI_MODEL", "llama-3.3-70b-instruct")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

if not UFL_AI_API_KEY:
    logger.warning("UFL_AI_API_KEY not set in environment variables!")
if not UFL_AI_BASE_URL:
    logger.warning("UFL_AI_BASE_URL not set in environment variables!")

# Headers for UFL AI API requests
headers = {
    "Authorization": f"Bearer {UFL_AI_API_KEY}",
    "Content-Type": "application/json"
}

# Schema validation for each endpoint
ENDPOINT_SCHEMAS = {
    "generate-initial-prompt": ["initialPrompt"],
    "evaluate-and-iterate-prompt": ["improvedPrompt", "bias", "toxicity", "promptAlignment"],
    "iterate-on-prompt": ["newPrompt"],
    "generate-prompt-tags": ["summary", "tags"],
    "get-prompt-suggestions": ["suggestions"],
    "optimize-prompt-with-context": ["optimizedPrompt", "reasoning"]
}

# Pydantic models for request validation
class UserNeedsRequest(BaseModel):
    userNeeds: str

class EvaluatePromptRequest(BaseModel):
    prompt: str
    userNeeds: str
    retrievedContent: Optional[str] = None
    groundTruths: Optional[str] = None

class IteratePromptRequest(BaseModel):
    currentPrompt: str
    userComments: str
    selectedSuggestions: List[str]

class PromptTagsRequest(BaseModel):
    promptText: str

class PromptSuggestionsRequest(BaseModel):
    currentPrompt: str
    userComments: Optional[str] = None

class OptimizePromptRequest(BaseModel):
    prompt: str
    retrievedContent: str
    groundTruths: str

class TemplateUpdateRequest(BaseModel):
    template: str
    description: Optional[str] = "No description"
    version: Optional[str] = "1.0"

# Cache utilities
def get_cache_key(endpoint: str, **kwargs) -> str:
    """Generate cache key from endpoint and parameters"""
    key_data = f"{endpoint}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_cached_response(key: str):
    """Get cached response if valid"""
    if key in cache and key in cache_ttl:
        if time.time() < cache_ttl[key]:
            return cache[key]
        else:
            # Expired, remove from cache
            cache.pop(key, None)
            cache_ttl.pop(key, None)
    return None

def set_cache(key: str, value, ttl: int = CACHE_TTL):
    """Set cache with TTL"""
    cache[key] = value
    cache_ttl[key] = time.time() + ttl

# Rate limiting
def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old entries
    rate_limiter[client_ip] = [req_time for req_time in rate_limiter[client_ip] if req_time > window_start]
    
    # Check current count
    if len(rate_limiter[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    rate_limiter[client_ip].append(now)
    return True

# Background task for cache cleanup
async def cache_cleanup_task():
    """Background task to clean expired cache entries"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            current_time = time.time()
            expired_keys = [key for key, ttl in cache_ttl.items() if current_time > ttl]
            
            for key in expired_keys:
                cache.pop(key, None)
                cache_ttl.pop(key, None)
            
            # Force garbage collection periodically
            if len(expired_keys) > 0:
                gc.collect()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

# Async context manager for application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global aiohttp_session
    connector = aiohttp.TCPConnector(
        limit=300,
        limit_per_host=100,
        ttl_dns_cache=300,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    aiohttp_session = aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"Authorization": f"Bearer {UFL_AI_API_KEY}", "Content-Type": "application/json"}
    )
    
    # Background task for cache cleanup
    cleanup_task = asyncio.create_task(cache_cleanup_task())
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    if aiohttp_session:
        await aiohttp_session.close()

app = FastAPI(lifespan=lifespan)

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@retry_on_failure(max_retries=3, initial_delay=1, backoff_factor=2)
async def call_ufl_api(prompt, endpoint_name=None):
    """
    Helper function to call the UFL AI API with retry logic (now async with connection pooling)
    
    Args:
        prompt (str): The prompt to send to the model
        endpoint_name (str, optional): The name of the endpoint for schema validation
        
    Returns:
        dict: The parsed response from the model
    """
    try:
        logger.info(f"Calling UFL AI API for endpoint: {endpoint_name}")
        logger.debug(f"Prompt: {prompt[:200]}...")
        
        data = {
            "model": UFL_AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp_session.post(f"{UFL_AI_BASE_URL}/chat/completions", json=data) as response:
            response.raise_for_status()
            result = await response.json()
        
        content = result["choices"][0]["message"]["content"]
        
        # Try to parse the content as JSON
        parsed_content = extract_json_from_text(content)
        
        if not parsed_content:
            logger.error(f"Failed to parse response as JSON: {content[:500]}")
            return {"error": "Invalid JSON response", "content": content}
        
        # Validate against schema if endpoint_name is provided
        if endpoint_name and endpoint_name in ENDPOINT_SCHEMAS:
            is_valid, missing_keys = validate_response_against_schema(
                parsed_content, ENDPOINT_SCHEMAS[endpoint_name]
            )
            
            if not is_valid:
                logger.error(f"Response missing required keys: {missing_keys}")
                return {
                    "error": f"Response missing required keys: {missing_keys}",
                    "content": parsed_content
                }
        
        return parsed_content
            
    except Exception as e:
        logger.error(f"API request failed: {str(e)}")
        raise Exception(f"API request failed: {str(e)}")

async def generate_test_response_for_deepeval(prompt: str) -> str:
    """
    Generate a test response for DeepEval assessment
    
    Args:
        prompt (str): The prompt to test
        
    Returns:
        str: Generated test response
    """
    try:
        test_prompt = f"Given this prompt, generate a typical response that would be produced:\n\nPROMPT: {prompt}\n\nGenerate a realistic response as if you were following this prompt:"
        
        data = {
            "model": UFL_AI_MODEL,
            "messages": [{"role": "user", "content": test_prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        async with aiohttp_session.post(f"{UFL_AI_BASE_URL}/chat/completions", json=data) as response:
            response.raise_for_status()
            result = await response.json()
            return result["choices"][0]["message"]["content"]
            
    except Exception as e:
        logger.error(f"Failed to generate test response: {str(e)}")
        return "Unable to generate test response for evaluation."

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "model": UFL_AI_MODEL,
        "template_count": len(template_manager.templates),
        "deepeval_enabled": deepeval_integration is not None
    }

@app.post("/generate-initial-prompt")
async def generate_initial_prompt(request: UserNeedsRequest):
    """Generate an initial system prompt based on user needs"""
    # Check cache first
    cache_key = get_cache_key("generate-initial-prompt", userNeeds=request.userNeeds)
    cached_result = get_cached_response(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Get the template and render it with the user needs
        template = template_manager.render_template(
            "generate_initial_prompt",
            userNeeds=request.userNeeds
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = await call_ufl_api(template, "generate-initial-prompt")
        
        # Add DeepEval assessment if available and if we have a valid result
        if deepeval_integration and "initialPrompt" in result and "error" not in result:
            try:
                # Generate a test response for evaluation
                test_response = await generate_test_response_for_deepeval(result["initialPrompt"])
                
                # Run comprehensive evaluation
                deepeval_assessment = await deepeval_integration.comprehensive_evaluation(
                    result["initialPrompt"], 
                    test_response
                )
                
                # Add assessment to result without changing the main structure
                result["deepeval_assessment"] = deepeval_assessment
                
            except Exception as e:
                logger.error(f"DeepEval assessment failed: {str(e)}")
                result["deepeval_error"] = str(e)
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate-and-iterate-prompt")
async def evaluate_and_iterate_prompt(request: EvaluatePromptRequest):
    """Evaluate and iterate on a prompt based on user needs and optional content"""
    # Check cache first
    cache_key = get_cache_key("evaluate-and-iterate-prompt", 
                             prompt=request.prompt, 
                             userNeeds=request.userNeeds,
                             retrievedContent=request.retrievedContent,
                             groundTruths=request.groundTruths)
    cached_result = get_cached_response(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Prepare optional sections
        retrievedContentSection = ""
        groundTruthsSection = ""
        faithfulnessSection = ""
        
        if request.retrievedContent:
            retrievedContentSection = f"\n**Knowledge Base Content:**\n{request.retrievedContent}\n"
        
        if request.groundTruths:
            groundTruthsSection = f"\n**Ground Truths / Few-shot Examples:**\n{request.groundTruths}\n"
            
        if request.retrievedContent:
            faithfulnessSection = """
4.  **FaithfulnessMetric**:
    *   **Score**: (0-1) How likely is the prompt to generate responses that are faithful to the provided Knowledge Base Content?
    *   **Summary**: Explain your reasoning.
    *   **Test Cases**: List examples you would use to test faithfulness to the knowledge base.
"""
        
        # Get the template and render it with the data
        template = template_manager.render_template(
            "evaluate_and_iterate_prompt",
            prompt=request.prompt,
            userNeeds=request.userNeeds,
            retrievedContentSection=retrievedContentSection,
            groundTruthsSection=groundTruthsSection,
            faithfulnessSection=faithfulnessSection
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = await call_ufl_api(template, "evaluate-and-iterate-prompt")
        
        # Enhanced DeepEval assessment for this endpoint
        if deepeval_integration and "improvedPrompt" in result and "error" not in result:
            try:
                # Generate test response for the improved prompt
                test_response = await generate_test_response_for_deepeval(result["improvedPrompt"])
                
                # Run comprehensive evaluation including faithfulness if context is available
                deepeval_assessment = await deepeval_integration.comprehensive_evaluation(
                    result["improvedPrompt"], 
                    test_response,
                    request.retrievedContent
                )
                
                # Map DeepEval results to the expected response format
                if "bias" in deepeval_assessment and isinstance(deepeval_assessment["bias"], dict):
                    bias_data = deepeval_assessment["bias"]
                    if "bias_score" in bias_data:
                        # Update the bias score in the result if DeepEval provides better assessment
                        if "bias" in result and isinstance(result["bias"], dict):
                            result["bias"]["deepeval_score"] = bias_data["bias_score"]
                            result["bias"]["deepeval_explanation"] = bias_data.get("explanation", "")
                
                if "toxicity" in deepeval_assessment and isinstance(deepeval_assessment["toxicity"], dict):
                    toxicity_data = deepeval_assessment["toxicity"]
                    if "toxicity_score" in toxicity_data:
                        # Update the toxicity score in the result
                        if "toxicity" in result and isinstance(result["toxicity"], dict):
                            result["toxicity"]["deepeval_score"] = toxicity_data["toxicity_score"]
                            result["toxicity"]["deepeval_explanation"] = toxicity_data.get("explanation", "")
                
                # Add full DeepEval assessment for reference
                result["deepeval_assessment"] = deepeval_assessment
                
            except Exception as e:
                logger.error(f"DeepEval assessment failed: {str(e)}")
                result["deepeval_error"] = str(e)
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/iterate-on-prompt")
async def iterate_on_prompt(request: IteratePromptRequest):
    """Iterate and refine a prompt based on user feedback and selected suggestions"""
    # Check cache first
    cache_key = get_cache_key("iterate-on-prompt", 
                             currentPrompt=request.currentPrompt,
                             userComments=request.userComments,
                             selectedSuggestions=str(request.selectedSuggestions))
    cached_result = get_cached_response(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Format selected suggestions as a bulleted list
        selectedSuggestions = "\n".join([f"- {s}" for s in request.selectedSuggestions])
        
        # Get the template and render it with the data
        template = template_manager.render_template(
            "iterate_on_prompt",
            currentPrompt=request.currentPrompt,
            userComments=request.userComments,
            selectedSuggestions=selectedSuggestions
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = await call_ufl_api(template, "iterate-on-prompt")
        
        # Add DeepEval comparison between old and new prompt
        if deepeval_integration and "newPrompt" in result and "error" not in result:
            try:
                # Generate test responses for both prompts
                old_test_response = await generate_test_response_for_deepeval(request.currentPrompt)
                new_test_response = await generate_test_response_for_deepeval(result["newPrompt"])
                
                # Evaluate both prompts
                old_assessment = await deepeval_integration.comprehensive_evaluation(
                    request.currentPrompt, old_test_response
                )
                new_assessment = await deepeval_integration.comprehensive_evaluation(
                    result["newPrompt"], new_test_response
                )
                
                # Add comparative analysis
                result["deepeval_comparison"] = {
                    "original_assessment": old_assessment,
                    "improved_assessment": new_assessment,
                    "improvement_analysis": {
                        "overall_improvement": (
                            new_assessment.get("overall_score", 0.5) - 
                            old_assessment.get("overall_score", 0.5)
                        ),
                        "bias_improvement": (
                            old_assessment.get("bias", {}).get("bias_score", 0.5) - 
                            new_assessment.get("bias", {}).get("bias_score", 0.5)
                        ),
                        "toxicity_improvement": (
                            old_assessment.get("toxicity", {}).get("toxicity_score", 0.5) - 
                            new_assessment.get("toxicity", {}).get("toxicity_score", 0.5)
                        )
                    }
                }
                
            except Exception as e:
                logger.error(f"DeepEval comparison failed: {str(e)}")
                result["deepeval_error"] = str(e)
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-prompt-tags")
async def generate_prompt_tags(request: PromptTagsRequest):
    """Generate a summary and tags for a given prompt"""
    # Check cache first
    cache_key = get_cache_key("generate-prompt-tags", promptText=request.promptText)
    cached_result = get_cached_response(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Get the template and render it with the data
        template = template_manager.render_template(
            "generate_prompt_tags",
            promptText=request.promptText
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = await call_ufl_api(template, "generate-prompt-tags")
        
        # Add quality assessment to tags
        if deepeval_integration and "error" not in result:
            try:
                # Use prompt quality assessor with DeepEval integration
                test_response = await generate_test_response_for_deepeval(request.promptText)
                quality_assessment = await prompt_quality_assessor.assess_prompt_quality(
                    request.promptText, test_response
                )
                
                # Add quality-based tags
                quality_tags = []
                if "quality_grade" in quality_assessment:
                    quality_tags.append(f"quality-{quality_assessment['quality_grade'].lower()}")
                
                if "deepeval_assessment" in quality_assessment:
                    deepeval_data = quality_assessment["deepeval_assessment"]
                    if "overall_score" in deepeval_data:
                        score = deepeval_data["overall_score"]
                        if score >= 0.8:
                            quality_tags.append("high-quality")
                        elif score >= 0.6:
                            quality_tags.append("medium-quality")
                        else:
                            quality_tags.append("needs-improvement")
                
                # Add quality tags to the result
                if "tags" in result and quality_tags:
                    if isinstance(result["tags"], list):
                        result["tags"].extend(quality_tags)
                    else:
                        result["tags"] = quality_tags
                
                # Add quality assessment for reference
                result["quality_assessment"] = quality_assessment
                
            except Exception as e:
                logger.error(f"Quality assessment failed: {str(e)}")
                result["quality_assessment_error"] = str(e)
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-prompt-suggestions")
async def get_prompt_suggestions(request: PromptSuggestionsRequest):
    """Generate suggestions for improving a prompt"""
    # Check cache first
    cache_key = get_cache_key("get-prompt-suggestions", 
                             currentPrompt=request.currentPrompt,
                             userComments=request.userComments)
    cached_result = get_cached_response(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Prepare optional user comments section
        userCommentsSection = ""
        if request.userComments:
            userCommentsSection = f"\nUser Comments: \"{request.userComments}\"\n"
        
        # Get the template and render it with the data
        template = template_manager.render_template(
            "get_prompt_suggestions",
            currentPrompt=request.currentPrompt,
            userCommentsSection=userCommentsSection
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = await call_ufl_api(template, "get-prompt-suggestions")
        
        # Enhanced suggestions with DeepEval insights
        if deepeval_integration and "suggestions" in result and "error" not in result:
            try:
                # Generate test response and assess current prompt
                test_response = await generate_test_response_for_deepeval(request.currentPrompt)
                assessment = await deepeval_integration.comprehensive_evaluation(
                    request.currentPrompt, test_response
                )
                
                # Generate DeepEval-based suggestions
                deepeval_suggestions = []
                
                if "bias" in assessment and isinstance(assessment["bias"], dict):
                    bias_score = assessment["bias"].get("bias_score", 0)
                    if bias_score > 0.3:
                        deepeval_suggestions.extend(assessment["bias"].get("recommendations", []))
                
                if "toxicity" in assessment and isinstance(assessment["toxicity"], dict):
                    toxicity_score = assessment["toxicity"].get("toxicity_score", 0)
                    if toxicity_score > 0.3:
                        deepeval_suggestions.extend(assessment["toxicity"].get("recommendations", []))
                
                if "relevance" in assessment and isinstance(assessment["relevance"], dict):
                    relevance_score = assessment["relevance"].get("relevance_score", 1)
                    if relevance_score < 0.7:
                        deepeval_suggestions.extend(assessment["relevance"].get("recommendations", []))
                
                if "coherence" in assessment and isinstance(assessment["coherence"], dict):
                    coherence_score = assessment["coherence"].get("coherence_score", 1)
                    if coherence_score < 0.7:
                        deepeval_suggestions.extend(assessment["coherence"].get("recommendations", []))
                
                # Merge with existing suggestions
                if deepeval_suggestions and isinstance(result["suggestions"], list):
                    # Remove duplicates while preserving order
                    all_suggestions = result["suggestions"] + deepeval_suggestions
                    unique_suggestions = []
                    seen = set()
                    for suggestion in all_suggestions:
                        if suggestion.lower() not in seen:
                            unique_suggestions.append(suggestion)
                            seen.add(suggestion.lower())
                    result["suggestions"] = unique_suggestions
                
                # Add assessment details
                result["deepeval_assessment"] = assessment
                
            except Exception as e:
                logger.error(f"DeepEval suggestion enhancement failed: {str(e)}")
                result["deepeval_error"] = str(e)
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize-prompt-with-context")
async def optimize_prompt_with_context(request: OptimizePromptRequest):
    """Optimize a prompt using retrieved content and ground truths"""
    # Check cache first
    cache_key = get_cache_key("optimize-prompt-with-context", 
                             prompt=request.prompt,
                             retrievedContent=request.retrievedContent,
                             groundTruths=request.groundTruths)
    cached_result = get_cached_response(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Get the template and render it with the data
        template = template_manager.render_template(
            "optimize_prompt_with_context",
            prompt=request.prompt,
            retrievedContent=request.retrievedContent,
            groundTruths=request.groundTruths
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = await call_ufl_api(template, "optimize-prompt-with-context")
        
        # Advanced DeepEval assessment with context
        if deepeval_integration and "optimizedPrompt" in result and "error" not in result:
            try:
                # Generate test responses for both original and optimized prompts
                original_test_response = await generate_test_response_for_deepeval(request.prompt)
                optimized_test_response = await generate_test_response_for_deepeval(result["optimizedPrompt"])
                
                # Comprehensive evaluation with context
                original_assessment = await deepeval_integration.comprehensive_evaluation(
                    request.prompt, original_test_response, request.retrievedContent
                )
                optimized_assessment = await deepeval_integration.comprehensive_evaluation(
                    result["optimizedPrompt"], optimized_test_response, request.retrievedContent
                )
                
                # Calculate optimization effectiveness
                optimization_metrics = {
                    "faithfulness_improvement": 0,
                    "relevance_improvement": 0,
                    "coherence_improvement": 0,
                    "bias_reduction": 0,
                    "toxicity_reduction": 0,
                    "overall_improvement": 0
                }
                
                if "faithfulness" in original_assessment and "faithfulness" in optimized_assessment:
                    orig_faith = original_assessment["faithfulness"].get("faithfulness_score", 0.5)
                    opt_faith = optimized_assessment["faithfulness"].get("faithfulness_score", 0.5)
                    optimization_metrics["faithfulness_improvement"] = opt_faith - orig_faith
                
                if "relevance" in original_assessment and "relevance" in optimized_assessment:
                    orig_rel = original_assessment["relevance"].get("relevance_score", 0.5)
                    opt_rel = optimized_assessment["relevance"].get("relevance_score", 0.5)
                    optimization_metrics["relevance_improvement"] = opt_rel - orig_rel
                
                if "coherence" in original_assessment and "coherence" in optimized_assessment:
                    orig_coh = original_assessment["coherence"].get("coherence_score", 0.5)
                    opt_coh = optimized_assessment["coherence"].get("coherence_score", 0.5)
                    optimization_metrics["coherence_improvement"] = opt_coh - orig_coh
                
                if "bias" in original_assessment and "bias" in optimized_assessment:
                    orig_bias = original_assessment["bias"].get("bias_score", 0.5)
                    opt_bias = optimized_assessment["bias"].get("bias_score", 0.5)
                    optimization_metrics["bias_reduction"] = orig_bias - opt_bias
                
                if "toxicity" in original_assessment and "toxicity" in optimized_assessment:
                    orig_tox = original_assessment["toxicity"].get("toxicity_score", 0.5)
                    opt_tox = optimized_assessment["toxicity"].get("toxicity_score", 0.5)
                    optimization_metrics["toxicity_reduction"] = orig_tox - opt_tox
                
                if "overall_score" in original_assessment and "overall_score" in optimized_assessment:
                    optimization_metrics["overall_improvement"] = (
                        optimized_assessment["overall_score"] - original_assessment["overall_score"]
                    )
                
                # Add comprehensive optimization analysis
                result["deepeval_optimization_analysis"] = {
                    "original_assessment": original_assessment,
                    "optimized_assessment": optimized_assessment,
                    "optimization_metrics": optimization_metrics,
                    "optimization_success": optimization_metrics["overall_improvement"] > 0,
                    "key_improvements": [
                        metric for metric, value in optimization_metrics.items() 
                        if value > 0.1 and metric != "overall_improvement"
                    ]
                }
                
            except Exception as e:
                logger.error(f"DeepEval optimization analysis failed: {str(e)}")
                result["deepeval_error"] = str(e)
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Template management endpoints (unchanged)
@app.get("/templates")
async def list_templates():
    """List all available templates"""
    try:
        templates = {}
        for name, template_data in template_manager.templates.items():
            # Only include description and version, not the full template text
            templates[name] = {
                "description": template_data.get("description", "No description"),
                "version": template_data.get("version", "1.0")
            }
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_name}")
async def get_template(template_name: str):
    """Get a specific template by name"""
    try:
        template_data = template_manager.get_template(template_name)
        if not template_data:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        return template_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/templates/{template_name}")
async def update_template(template_name: str, request: TemplateUpdateRequest):
    """Update a specific template"""
    try:
        # Ensure the template data has at least the required fields
        template_data = {
            "description": request.description,
            "version": request.version,
            "template": request.template
        }
        
        # Save the updated template
        success = template_manager.save_template(template_name, template_data)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to save template '{template_name}'")
        
        return {"message": f"Template '{template_name}' updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/templates/reload")
async def reload_templates():
    """Reload all templates from disk"""
    try:
        template_manager.reload_templates()
        return {"message": "Templates reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/render-template/{template_name}")
async def render_template_endpoint(template_name: str, request: dict):
    """Render a template with the provided variables (for testing)"""
    try:
        rendered = template_manager.render_template(template_name, **request)
        if not rendered:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found or rendering failed")
        return {"rendered": rendered}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New DeepEval-specific endpoints

@app.post("/deepeval/assess-prompt")
async def deepeval_assess_prompt(request: dict):
    """
    Direct DeepEval assessment endpoint for comprehensive prompt evaluation
    """
    try:
        if not deepeval_integration:
            raise HTTPException(status_code=503, detail="DeepEval integration not available")
        
        prompt = request.get("prompt")
        response = request.get("response")
        context = request.get("context")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Generate test response if not provided
        if not response:
            response = await generate_test_response_for_deepeval(prompt)
        
        # Run comprehensive evaluation
        assessment = await deepeval_integration.comprehensive_evaluation(prompt, response, context)
        
        return {
            "prompt": prompt,
            "response": response,
            "context": context,
            "assessment": assessment,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deepeval/compare-prompts")
async def deepeval_compare_prompts(request: dict):
    """
    Compare multiple prompts using DeepEval metrics
    """
    try:
        if not deepeval_integration:
            raise HTTPException(status_code=503, detail="DeepEval integration not available")
        
        prompts = request.get("prompts", [])
        context = request.get("context")
        
        if len(prompts) < 2:
            raise HTTPException(status_code=400, detail="At least 2 prompts are required for comparison")
        
        # Assess each prompt
        assessments = []
        for i, prompt in enumerate(prompts):
            test_response = await generate_test_response_for_deepeval(prompt)
            assessment = await deepeval_integration.comprehensive_evaluation(prompt, test_response, context)
            assessments.append({
                "prompt_index": i,
                "prompt": prompt,
                "test_response": test_response,
                "assessment": assessment
            })
        
        # Calculate comparative metrics
        comparison_metrics = {}
        metric_names = ["overall_score", "bias", "toxicity", "relevance", "coherence", "faithfulness"]
        
        for metric in metric_names:
            scores = []
            for assessment in assessments:
                if metric == "overall_score":
                    score = assessment["assessment"].get("overall_score", 0.5)
                else:
                    metric_data = assessment["assessment"].get(metric, {})
                    if isinstance(metric_data, dict):
                        score_key = f"{metric}_score"
                        score = metric_data.get(score_key, 0.5)
                        # For bias and toxicity, lower is better, so invert
                        if metric in ["bias", "toxicity"]:
                            score = 1.0 - score
                    else:
                        continue
                scores.append(score)
            
            if scores:
                comparison_metrics[metric] = {
                    "scores": scores,
                    "best_prompt_index": scores.index(max(scores)),
                    "worst_prompt_index": scores.index(min(scores)),
                    "average": sum(scores) / len(scores),
                    "range": max(scores) - min(scores)
                }
        
        return {
            "individual_assessments": assessments,
            "comparison_metrics": comparison_metrics,
            "context": context,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deepeval/batch-evaluate")
async def deepeval_batch_evaluate(request: dict):
    """
    Batch evaluation of multiple prompt-response pairs
    """
    try:
        if not deepeval_integration:
            raise HTTPException(status_code=503, detail="DeepEval integration not available")
        
        test_cases = request.get("test_cases", [])
        include_detailed = request.get("include_detailed", False)
        
        if not test_cases:
            raise HTTPException(status_code=400, detail="Test cases are required")
        
        # Process each test case
        results = []
        batch_metrics = {
            "total_cases": len(test_cases),
            "successful_evaluations": 0,
            "failed_evaluations": 0,
            "average_scores": {},
            "score_distribution": {}
        }
        
        for i, test_case in enumerate(test_cases):
            try:
                prompt = test_case.get("prompt", "")
                response = test_case.get("response", "")
                context = test_case.get("context")
                
                if not prompt:
                    results.append({
                        "test_case_index": i,
                        "error": "Missing prompt",
                        "success": False
                    })
                    batch_metrics["failed_evaluations"] += 1
                    continue
                
                # Generate response if not provided
                if not response:
                    response = await generate_test_response_for_deepeval(prompt)
                
                # Run evaluation
                assessment = await deepeval_integration.comprehensive_evaluation(prompt, response, context)
                
                result = {
                    "test_case_index": i,
                    "success": True,
                    "overall_score": assessment.get("overall_score", 0.5)
                }
                
                if include_detailed:
                    result["detailed_assessment"] = assessment
                    result["prompt"] = prompt
                    result["response"] = response
                    result["context"] = context
                
                results.append(result)
                batch_metrics["successful_evaluations"] += 1
                
            except Exception as e:
                results.append({
                    "test_case_index": i,
                    "error": str(e),
                    "success": False
                })
                batch_metrics["failed_evaluations"] += 1
        
        # Calculate batch statistics
        successful_results = [r for r in results if r.get("success", False)]
        if successful_results:
            overall_scores = [r["overall_score"] for r in successful_results]
            batch_metrics["average_scores"]["overall"] = sum(overall_scores) / len(overall_scores)
            batch_metrics["score_distribution"]["overall"] = {
                "min": min(overall_scores),
                "max": max(overall_scores),
                "median": sorted(overall_scores)[len(overall_scores) // 2]
            }
        
        return {
            "results": results,
            "batch_metrics": batch_metrics,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deepeval/metrics-summary")
async def get_deepeval_metrics_summary():
    """
    Get summary of all DeepEval assessments performed
    """
    try:
        from utils import dspy_metrics_collector
        
        summary = dspy_metrics_collector.get_performance_summary()
        
        # Add DeepEval-specific information
        deepeval_info = {
            "integration_status": "enabled" if deepeval_integration else "disabled",
            "available_metrics": [
                "bias", "toxicity", "relevance", "coherence", "faithfulness"
            ] if deepeval_integration else [],
            "llm_model": UFL_AI_MODEL,
            "cache_status": {
                "entries": len(cache),
                "hit_ratio": "N/A"  # Could be calculated if we track hits/misses
            }
        }
        
        return {
            "deepeval_info": deepeval_info,
            "performance_summary": summary,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quality/assess-prompt")
async def assess_prompt_quality(request: dict):
    """
    Comprehensive prompt quality assessment using both traditional metrics and DeepEval
    """
    try:
        prompt = request.get("prompt")
        test_response = request.get("test_response")
        context = request.get("context")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Generate test response if not provided
        if not test_response:
            test_response = await generate_test_response_for_deepeval(prompt)
        
        # Run comprehensive quality assessment
        quality_assessment = await prompt_quality_assessor.assess_prompt_quality(
            prompt, test_response, context
        )
        
        return {
            "prompt": prompt,
            "test_response": test_response,
            "context": context,
            "quality_assessment": quality_assessment,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize/suggest-improvements")
async def suggest_prompt_improvements(request: dict):
    """
    Generate improvement suggestions based on comprehensive analysis
    """
    try:
        prompt = request.get("prompt")
        user_goals = request.get("user_goals", "")
        context = request.get("context")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Generate test response for analysis
        test_response = await generate_test_response_for_deepeval(prompt)
        
        # Get quality assessment
        quality_assessment = await prompt_quality_assessor.assess_prompt_quality(
            prompt, test_response, context
        )
        
        # Generate comprehensive suggestions
        suggestions = {
            "traditional_suggestions": quality_assessment.get("recommendations", []),
            "deepeval_suggestions": [],
            "priority_improvements": [],
            "overall_recommendation": ""
        }
        
        # Extract DeepEval-based suggestions
        if "deepeval_assessment" in quality_assessment:
            deepeval_data = quality_assessment["deepeval_assessment"]
            
            for metric in ["bias", "toxicity", "relevance", "coherence", "faithfulness"]:
                if metric in deepeval_data and isinstance(deepeval_data[metric], dict):
                    metric_recommendations = deepeval_data[metric].get("recommendations", [])
                    suggestions["deepeval_suggestions"].extend(metric_recommendations)
        
        # Determine priority improvements based on scores
        if "deepeval_assessment" in quality_assessment:
            deepeval_data = quality_assessment["deepeval_assessment"]
            priority_areas = []
            
            if "bias" in deepeval_data and deepeval_data["bias"].get("bias_score", 0) > 0.3:
                priority_areas.append("Reduce bias in language and examples")
            if "toxicity" in deepeval_data and deepeval_data["toxicity"].get("toxicity_score", 0) > 0.2:
                priority_areas.append("Eliminate potential toxicity triggers")
            if "relevance" in deepeval_data and deepeval_data["relevance"].get("relevance_score", 1) < 0.7:
                priority_areas.append("Improve relevance to the intended task")
            if "coherence" in deepeval_data and deepeval_data["coherence"].get("coherence_score", 1) < 0.7:
                priority_areas.append("Enhance logical structure and flow")
            
            suggestions["priority_improvements"] = priority_areas
        
        # Generate overall recommendation
        overall_score = quality_assessment.get("combined_quality_score", 
                                              quality_assessment.get("overall_quality_score", 0.5))
        if overall_score >= 0.8:
            suggestions["overall_recommendation"] = "Prompt is high quality and ready for production use."
        elif overall_score >= 0.6:
            suggestions["overall_recommendation"] = "Prompt has good foundation but would benefit from targeted improvements."
        else:
            suggestions["overall_recommendation"] = "Prompt needs significant improvement before production use."
        
        return {
            "prompt": prompt,
            "user_goals": user_goals,
            "quality_score": overall_score,
            "suggestions": suggestions,
            "quality_assessment": quality_assessment,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)