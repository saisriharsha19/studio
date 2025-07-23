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
from utils import retry_on_failure, extract_json_from_text, validate_response_against_schema
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "model": UFL_AI_MODEL,
        "template_count": len(template_manager.templates)
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
        
        # Cache the result
        set_cache(cache_key, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Template management endpoints
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)