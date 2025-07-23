# deepeval_integration.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import logging
from datetime import datetime
import json

# DeepEval imports
from deepeval import evaluate
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    HallucinationMetric,
    BiasMetric,
    ToxicityMetric,
    SummarizationMetric,
    GEval
)

# Import your existing modules
from utils import retry_on_failure, extract_json_from_text, validate_response_against_schema
from prompt_templates import template_manager

logger = logging.getLogger(__name__)

# Custom DeepEval LLM class to integrate with your UFL AI API
class UFLDeepEvalLLM(DeepEvalBaseLLM):
    def __init__(self, call_ufl_api_func, model_name="llama-3.3-70b-instruct"):
        self.call_ufl_api_func = call_ufl_api_func
        self.model_name = model_name

    def load_model(self):
        """Load model - not needed for API-based models"""
        return self

    def generate(self, prompt: str) -> str:
        """Generate response using your existing UFL AI API call"""
        try:
            # Since your call_ufl_api is async, we need to handle it properly
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new loop
                import asyncio
                result = asyncio.run_coroutine_threadsafe(
                    self.call_ufl_api_func(prompt), loop
                ).result()
            else:
                result = loop.run_until_complete(self.call_ufl_api_func(prompt))
            
            # Extract the response content
            if isinstance(result, dict):
                # If it's a JSON response, convert to string
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"

    async def a_generate(self, prompt: str) -> str:
        """Async generate method"""
        try:
            result = await self.call_ufl_api_func(prompt)
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"

    def get_model_name(self):
        return self.model_name

# Pydantic models for DeepEval requests
class TestCaseRequest(BaseModel):
    input: str
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    context: Optional[List[str]] = None
    retrieval_context: Optional[List[str]] = None

class EvaluationRequest(BaseModel):
    test_cases: List[TestCaseRequest]
    metrics: List[str]  # List of metric names to evaluate
    template_name: Optional[str] = None  # Optional template to use for generation

class CustomMetricRequest(BaseModel):
    name: str
    criteria: str
    evaluation_steps: List[str]
    test_cases: List[TestCaseRequest]

# Available metrics mapping
AVAILABLE_METRICS = {
    "answer_relevancy": AnswerRelevancyMetric,
    "faithfulness": FaithfulnessMetric,
    "contextual_precision": ContextualPrecisionMetric,
    "contextual_recall": ContextualRecallMetric,
    "hallucination": HallucinationMetric,
    "bias": BiasMetric,
    "toxicity": ToxicityMetric,
    "summarization": SummarizationMetric,
}

class DeepEvalService:
    def __init__(self, call_ufl_api_func):
        self.ufl_llm = UFLDeepEvalLLM(call_ufl_api_func)
        self.evaluation_history = []

    def create_test_cases(self, test_case_requests: List[TestCaseRequest]) -> List[LLMTestCase]:
        """Convert request test cases to DeepEval test cases"""
        test_cases = []
        for req in test_case_requests:
            test_case = LLMTestCase(
                input=req.input,
                actual_output=req.actual_output,
                expected_output=req.expected_output,
                context=req.context,
                retrieval_context=req.retrieval_context
            )
            test_cases.append(test_case)
        return test_cases

    def initialize_metrics(self, metric_names: List[str]) -> List[Any]:
        """Initialize metrics based on names"""
        metrics = []
        for metric_name in metric_names:
            if metric_name in AVAILABLE_METRICS:
                metric_class = AVAILABLE_METRICS[metric_name]
                
                # Initialize metric with custom LLM
                if metric_name in ["answer_relevancy", "faithfulness", "hallucination", "bias", "toxicity"]:
                    metric = metric_class(model=self.ufl_llm)
                elif metric_name in ["contextual_precision", "contextual_recall"]:
                    metric = metric_class(model=self.ufl_llm)
                else:
                    metric = metric_class()
                
                metrics.append(metric)
            else:
                logger.warning(f"Unknown metric: {metric_name}")
        
        return metrics

    def create_custom_metric(self, name: str, criteria: str, evaluation_steps: List[str]) -> GEval:
        """Create a custom G-Eval metric"""
        return GEval(
            name=name,
            criteria=criteria,
            evaluation_steps=evaluation_steps,
            model=self.ufl_llm
        )

    async def evaluate_test_cases(self, test_cases: List[LLMTestCase], metrics: List[Any]) -> Dict[str, Any]:
        """Evaluate test cases with specified metrics"""
        try:
            # Run evaluation
            results = evaluate(test_cases, metrics)
            
            # Process results
            evaluation_results = {
                "overall_score": 0,
                "metric_scores": {},
                "test_case_results": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Calculate overall score and metric scores
            total_score = 0
            metric_count = 0
            
            for test_case in results.test_results:
                case_result = {
                    "input": test_case.input,
                    "actual_output": test_case.actual_output,
                    "success": test_case.success,
                    "metrics_metadata": []
                }
                
                for metric_metadata in test_case.metrics_metadata:
                    metric_result = {
                        "metric": metric_metadata.metric,
                        "score": metric_metadata.score,
                        "reason": metric_metadata.reason,
                        "success": metric_metadata.success
                    }
                    case_result["metrics_metadata"].append(metric_result)
                    
                    # Add to overall calculations
                    if metric_metadata.success and metric_metadata.score is not None:
                        total_score += metric_metadata.score
                        metric_count += 1
                        
                        # Track individual metric scores
                        metric_name = metric_metadata.metric
                        if metric_name not in evaluation_results["metric_scores"]:
                            evaluation_results["metric_scores"][metric_name] = []
                        evaluation_results["metric_scores"][metric_name].append(metric_metadata.score)
                
                evaluation_results["test_case_results"].append(case_result)
            
            # Calculate averages
            if metric_count > 0:
                evaluation_results["overall_score"] = total_score / metric_count
            
            for metric_name, scores in evaluation_results["metric_scores"].items():
                if scores:
                    evaluation_results["metric_scores"][metric_name] = {
                        "average": sum(scores) / len(scores),
                        "scores": scores,
                        "count": len(scores)
                    }
            
            # Store in history
            self.evaluation_history.append(evaluation_results)
            
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            raise Exception(f"Evaluation failed: {str(e)}")

# Add DeepEval endpoints to your existing FastAPI app
def add_deepeval_endpoints(app: FastAPI, call_ufl_api_func):
    """Add DeepEval endpoints to the existing FastAPI app"""
    
    deepeval_service = DeepEvalService(call_ufl_api_func)
    
    @app.get("/deepeval/metrics")
    async def list_available_metrics():
        """List all available DeepEval metrics"""
        return {
            "available_metrics": list(AVAILABLE_METRICS.keys()),
            "descriptions": {
                "answer_relevancy": "Measures how relevant the answer is to the given input",
                "faithfulness": "Measures factual consistency of the answer against the given context",
                "contextual_precision": "Measures how relevant the retrieved contexts are to the question",
                "contextual_recall": "Measures the extent of context retrieval for a given question",
                "hallucination": "Measures the extent of hallucination in the answer",
                "bias": "Measures the degree of bias in the answer",
                "toxicity": "Measures the toxicity level of the answer",
                "summarization": "Measures the quality of text summarization"
            }
        }
    
    @app.post("/deepeval/evaluate")
    async def evaluate_with_deepeval(request: EvaluationRequest):
        """Evaluate test cases using DeepEval metrics"""
        try:
            # Create test cases
            test_cases = deepeval_service.create_test_cases(request.test_cases)
            
            # If actual_output is not provided but template is specified, generate outputs
            if request.template_name and any(tc.actual_output is None for tc in request.test_cases):
                for i, (test_case, req) in enumerate(zip(test_cases, request.test_cases)):
                    if req.actual_output is None:
                        # Generate output using specified template
                        rendered_prompt = template_manager.render_template(
                            request.template_name,
                            userInput=req.input,
                            context=req.context or [],
                            retrievalContext=req.retrieval_context or []
                        )
                        
                        if rendered_prompt:
                            result = await call_ufl_api_func(rendered_prompt)
                            if isinstance(result, dict):
                                test_case.actual_output = json.dumps(result, indent=2)
                            else:
                                test_case.actual_output = str(result)
            
            # Initialize metrics
            metrics = deepeval_service.initialize_metrics(request.metrics)
            
            if not metrics:
                raise HTTPException(status_code=400, detail="No valid metrics specified")
            
            # Evaluate
            results = await deepeval_service.evaluate_test_cases(test_cases, metrics)
            
            return results
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/deepeval/custom-metric")
    async def evaluate_custom_metric(request: CustomMetricRequest):
        """Evaluate using a custom G-Eval metric"""
        try:
            # Create test cases
            test_cases = deepeval_service.create_test_cases(request.test_cases)
            
            # Create custom metric
            custom_metric = deepeval_service.create_custom_metric(
                request.name,
                request.criteria,
                request.evaluation_steps
            )
            
            # Evaluate
            results = await deepeval_service.evaluate_test_cases(test_cases, [custom_metric])
            
            return results
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/deepeval/batch-evaluate")
    async def batch_evaluate_prompts(
        user_needs: str,
        test_inputs: List[str],
        expected_outputs: Optional[List[str]] = None,
        contexts: Optional[List[List[str]]] = None,
        metrics: List[str] = ["answer_relevancy", "faithfulness"]
    ):
        """Batch evaluate multiple prompts against test inputs"""
        try:
            results = {}
            
            # Get available prompt templates
            available_templates = list(template_manager.templates.keys())
            
            # Test each template
            for template_name in available_templates:
                if template_name in ["generate_initial_prompt", "evaluate_and_iterate_prompt"]:
                    continue  # Skip meta-templates
                
                test_case_requests = []
                
                for i, test_input in enumerate(test_inputs):
                    # Generate output using current template
                    try:
                        rendered_prompt = template_manager.render_template(
                            template_name,
                            userNeeds=user_needs,
                            userInput=test_input,
                            context=contexts[i] if contexts and i < len(contexts) else []
                        )
                        
                        if not rendered_prompt:
                            continue
                        
                        result = await call_ufl_api_func(rendered_prompt)
                        actual_output = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                        
                        test_case_req = TestCaseRequest(
                            input=test_input,
                            actual_output=actual_output,
                            expected_output=expected_outputs[i] if expected_outputs and i < len(expected_outputs) else None,
                            context=contexts[i] if contexts and i < len(contexts) else None
                        )
                        
                        test_case_requests.append(test_case_req)
                        
                    except Exception as e:
                        logger.error(f"Error testing template {template_name} with input {i}: {e}")
                        continue
                
                if test_case_requests:
                    # Evaluate this template
                    evaluation_request = EvaluationRequest(
                        test_cases=test_case_requests,
                        metrics=metrics
                    )
                    
                    template_results = await evaluate_with_deepeval(evaluation_request)
                    results[template_name] = template_results
            
            return {
                "batch_evaluation": results,
                "summary": {
                    "templates_tested": len(results),
                    "best_template": max(results.keys(), key=lambda k: results[k]["overall_score"]) if results else None,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/deepeval/history")
    async def get_evaluation_history():
        """Get evaluation history"""
        return {
            "history": deepeval_service.evaluation_history,
            "count": len(deepeval_service.evaluation_history)
        }
    
    @app.post("/deepeval/prompt-optimization")
    async def optimize_prompt_with_deepeval(
        initial_prompt: str,
        test_cases: List[TestCaseRequest],
        target_metrics: List[str] = ["answer_relevancy", "faithfulness"],
        optimization_iterations: int = 3
    ):
        """Optimize a prompt using DeepEval feedback"""
        try:
            optimization_history = []
            current_prompt = initial_prompt
            
            for iteration in range(optimization_iterations):
                # Generate test case outputs with current prompt
                test_cases_with_outputs = []
                for test_case_req in test_cases:
                    try:
                        # Use the prompt directly or with a simple template
                        full_prompt = f"{current_prompt}\n\nInput: {test_case_req.input}"
                        if test_case_req.context:
                            full_prompt += f"\nContext: {'; '.join(test_case_req.context)}"
                        
                        result = await call_ufl_api_func(full_prompt)
                        actual_output = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                        
                        test_case_req.actual_output = actual_output
                        test_cases_with_outputs.append(test_case_req)
                        
                    except Exception as e:
                        logger.error(f"Error generating output for test case: {e}")
                        continue
                
                if not test_cases_with_outputs:
                    break
                
                # Evaluate current prompt
                evaluation_request = EvaluationRequest(
                    test_cases=test_cases_with_outputs,
                    metrics=target_metrics
                )
                
                evaluation_results = await evaluate_with_deepeval(evaluation_request)
                
                # Analyze results and generate improvement suggestions
                improvement_prompt = f"""
                Current prompt: {current_prompt}
                
                Evaluation results:
                - Overall score: {evaluation_results['overall_score']}
                - Metric scores: {json.dumps(evaluation_results['metric_scores'], indent=2)}
                
                Based on these evaluation results, suggest 3 specific improvements to the prompt to increase the scores for: {', '.join(target_metrics)}
                
                Focus on:
                1. Clarity and specificity
                2. Reducing hallucinations
                3. Improving relevance
                
                Return your response as a JSON object with:
                {{
                    "improvedPrompt": "the improved version of the prompt",
                    "improvements": ["list of specific improvements made"],
                    "reasoning": "explanation of why these improvements should help"
                }}
                """
                
                improvement_result = await call_ufl_api_func(improvement_prompt)
                
                optimization_history.append({
                    "iteration": iteration + 1,
                    "prompt": current_prompt,
                    "evaluation_results": evaluation_results,
                    "improvements": improvement_result
                })
                
                # Update prompt for next iteration
                if isinstance(improvement_result, dict) and "improvedPrompt" in improvement_result:
                    current_prompt = improvement_result["improvedPrompt"]
                
            return {
                "optimization_history": optimization_history,
                "final_prompt": current_prompt,
                "initial_prompt": initial_prompt,
                "iterations": len(optimization_history)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# Example of how to integrate with your existing app.py
"""
# In your app.py, after creating the FastAPI app:

from deepeval_integration import add_deepeval_endpoints

# Add DeepEval endpoints
add_deepeval_endpoints(app, call_ufl_api)

# Your existing endpoints remain unchanged
"""