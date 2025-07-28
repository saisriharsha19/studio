# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import requests
import json
import time
import logging
from dotenv import load_dotenv
from utils import retry_on_failure, extract_json_from_text, validate_response_against_schema
from prompt_templates import template_manager
from deepeval import evaluate
from deepeval.metrics import BiasMetric, ToxicityMetric, AnswerRelevancyMetric, FaithfulnessMetric
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

app = FastAPI()

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure API settings from environment variables
UFL_AI_API_KEY = os.getenv("UFL_AI_API_KEY")
UFL_AI_BASE_URL = os.getenv("UFL_AI_BASE_URL")
UFL_AI_MODEL = os.getenv("UFL_AI_MODEL", "llama-3.3-70b-instruct")

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

@retry_on_failure(max_retries=3, initial_delay=1, backoff_factor=2)
def call_ufl_api(prompt, endpoint_name=None):
    """
    Helper function to call the UFL AI API with retry logic
    
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
        
        response = requests.post(f"{UFL_AI_BASE_URL}/chat/completions", headers=headers, json=data)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        result = response.json()
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
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise Exception(f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "model": UFL_AI_MODEL,
        "template_count": len(template_manager.templates)
    }

@app.post("/generate-initial-prompt")
def generate_initial_prompt(request: UserNeedsRequest):
    """Generate an initial system prompt based on user needs"""
    try:
        # Get the template and render it with the user needs
        template = template_manager.render_template(
            "generate_initial_prompt",
            userNeeds=request.userNeeds
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = call_ufl_api(template, "generate-initial-prompt")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Custom LLM for DeepEval
class UFL_AI_LLM(DeepEvalBaseLLM):
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def load_model(self):
        return self

    def generate(self, prompt: str) -> str:
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = requests.post(f"{self.base_url}/chat/completions", headers=self.headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self):
        return self.model

@app.post("/evaluate-and-iterate-prompt")
def evaluate_and_iterate_prompt(request: EvaluatePromptRequest):
    """Evaluate and iterate on a prompt based on user needs and optional content"""
    try:
        # Step 1: Generate the improved prompt
        retrievedContentSection = f"\n**Knowledge Base Content:**\n{request.retrievedContent}\n" if request.retrievedContent else ""
        groundTruthsSection = f"\n**Ground Truths / Few-shot Examples:**\n{request.groundTruths}\n" if request.groundTruths else ""

        template = template_manager.render_template(
            "evaluate_and_iterate_prompt",
            prompt=request.prompt,
            userNeeds=request.userNeeds,
            retrievedContentSection=retrievedContentSection,
            groundTruthsSection=groundTruthsSection
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")

        improved_prompt_response = call_ufl_api(template, "generate-initial-prompt")
        improved_prompt = improved_prompt_response.get("initialPrompt")

        if not improved_prompt:
            raise HTTPException(status_code=500, detail="Failed to generate improved prompt")

        # Step 2: Evaluate the improved prompt using deepeval
        custom_model = UFL_AI_LLM(model=UFL_AI_MODEL, api_key=UFL_AI_API_KEY, base_url=UFL_AI_BASE_URL)

        test_case = LLMTestCase(
            input=request.userNeeds,
            actual_output=improved_prompt,
            retrieval_context=[request.retrievedContent] if request.retrievedContent else None,
            context=[request.groundTruths] if request.groundTruths else None
        )

        metrics = [
            BiasMetric(threshold=0.5, model=custom_model),
            ToxicityMetric(threshold=0.5, model=custom_model),
            AnswerRelevancyMetric(threshold=0.5, model=custom_model)
        ]
        if request.retrievedContent:
            metrics.append(FaithfulnessMetric(threshold=0.5, model=custom_model))

        evaluation_results = evaluate(test_cases=[test_case], metrics=metrics)

        # Format the results
        results = {"improvedPrompt": improved_prompt}
        for metric in evaluation_results[0].metrics:
            metric_name = metric.__class__.__name__.replace("Metric", "").lower()
            if metric_name == "answerrelevancy":
                metric_name = "promptAlignment"

            results[metric_name] = {
                "score": metric.score,
                "summary": metric.reason,
                "testCases": [] # deepeval doesn't expose test cases in the same way
            }
        
        return results

    except Exception as e:
        logger.error(f"Error in evaluate_and_iterate_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/iterate-on-prompt")
def iterate_on_prompt(request: IteratePromptRequest):
    """Iterate and refine a prompt based on user feedback and selected suggestions"""
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
        result = call_ufl_api(template, "iterate-on-prompt")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-prompt-tags")
def generate_prompt_tags(request: PromptTagsRequest):
    """Generate a summary and tags for a given prompt"""
    try:
        # Get the template and render it with the data
        template = template_manager.render_template(
            "generate_prompt_tags",
            promptText=request.promptText
        )
        
        if not template:
            raise HTTPException(status_code=500, detail="Template not found or rendering failed")
        
        # Call the AI API with the rendered template
        result = call_ufl_api(template, "generate-prompt-tags")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-prompt-suggestions")
def get_prompt_suggestions(request: PromptSuggestionsRequest):
    """Generate suggestions for improving a prompt"""
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
        result = call_ufl_api(template, "get-prompt-suggestions")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize-prompt-with-context")
def optimize_prompt_with_context(request: OptimizePromptRequest):
    """Optimize a prompt using retrieved content and ground truths"""
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
        result = call_ufl_api(template, "optimize-prompt-with-context")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Template management endpoints
@app.get("/templates")
def list_templates():
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
def get_template(template_name: str):
    """Get a specific template by name"""
    try:
        template_data = template_manager.get_template(template_name)
        if not template_data:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        return template_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/templates/{template_name}")
def update_template(template_name: str, request: TemplateUpdateRequest):
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
def reload_templates():
    """Reload all templates from disk"""
    try:
        template_manager.reload_templates()
        return {"message": "Templates reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/render-template/{template_name}")
def render_template_endpoint(template_name: str, request: dict):
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