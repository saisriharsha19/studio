# prompt_templates.py
"""
Module for managing prompt templates for the prompt engineering backend.
Enhanced with DSPy integration and DeepEval optimization for better prompt management.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
import hashlib
import time

logger = logging.getLogger(__name__)

class DSPyPromptTemplateManager:
    """
    Enhanced manager for loading and retrieving prompt templates with DSPy and DeepEval integration
    """
    
    def __init__(self, templates_dir=None):
        """
        Initialize the prompt template manager
        
        Args:
            templates_dir (str, optional): Directory containing template files
        """
        if templates_dir is None:
            # Default to 'templates' directory in the same folder as this file
            self.templates_dir = Path(__file__).parent / 'templates'
        else:
            self.templates_dir = Path(templates_dir)
            
        # Create templates directory if it doesn't exist
        self.templates_dir.mkdir(exist_ok=True)
        
        # Templates cache
        self.templates = {}
        
        # DSPy-optimized templates cache
        self.dspy_optimized_templates = {}
        
        # DeepEval-optimized templates cache
        self.deepeval_optimized_templates = {}
        
        # Template usage analytics
        self.template_usage = {}
        
        # Template performance metrics including DeepEval scores
        self.template_metrics = {}
        
        # Load all templates
        self._load_templates()
        self._create_default_templates()
    
    def _load_templates(self):
        """Load all template files from the templates directory"""
        try:
            for template_file in self.templates_dir.glob('*.json'):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        template_name = template_file.stem
                        self.templates[template_name] = template_data
                        
                        # Initialize usage tracking
                        self.template_usage[template_name] = {
                            "usage_count": 0,
                            "last_used": None,
                            "success_rate": 1.0,
                            "average_response_time": 0.0,
                            "deepeval_scores": {
                                "bias": [],
                                "toxicity": [],
                                "relevance": [],
                                "coherence": [],
                                "faithfulness": [],
                                "overall": []
                            }
                        }
                        
                    logger.info(f"Loaded template: {template_name}")
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning templates directory: {str(e)}")
    
    def _create_default_templates(self):
        """Create default templates if they don't exist - Enhanced with DeepEval considerations"""
        default_templates = {
            "generate_initial_prompt": {
                "description": "Generate an initial system prompt based on user needs with DeepEval optimization",
                "version": "2.0",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "template": """You are an expert prompt engineer with deep knowledge of bias mitigation, toxicity prevention, and response quality optimization. Your task is to create an effective, safe, and unbiased system prompt based on the user's requirements.

User Requirements: {userNeeds}

Guidelines for creating the prompt (with emphasis on safety and quality):
1. **Clarity and Specificity**: Be specific and clear about the desired behavior while avoiding ambiguous language that could lead to misinterpretation
2. **Bias Mitigation**: Ensure the prompt encourages fair, inclusive, and unbiased responses across all demographics and perspectives
3. **Toxicity Prevention**: Include explicit safeguards against generating harmful, toxic, or offensive content
4. **Context and Constraints**: Include relevant context and constraints that promote helpful and appropriate responses
5. **Output Format**: Specify the expected output format clearly to ensure consistency
6. **Edge Case Handling**: Consider and address potential edge cases and problematic scenarios
7. **Ethical Guidelines**: Embed ethical considerations and responsible AI practices

Safety and Quality Checklist:
- Does the prompt encourage respectful treatment of all individuals and groups?
- Are there clear boundaries preventing harmful or inappropriate outputs?
- Does the prompt promote factual accuracy and discourage misinformation?
- Is the language inclusive and accessible?
- Are there safeguards against generating biased or discriminatory content?

Create a well-structured, safe, and effective system prompt that will help achieve the user's goals while maintaining high ethical standards. Return your response as JSON with the key "initialPrompt".

Example format:
{{
    "initialPrompt": "Your generated system prompt here with safety and quality considerations..."
}}"""
            },
            
            "evaluate_and_iterate_prompt": {
                "description": "Evaluate and improve a prompt with comprehensive DeepEval metrics",
                "version": "2.0", 
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "template": """You are an expert prompt evaluator with specialized knowledge in AI safety, bias detection, toxicity prevention, and prompt optimization. Analyze the given prompt against the user requirements and provide detailed evaluation and improvements using comprehensive quality metrics.

**Current Prompt:**
{prompt}

**User Requirements:**
{userNeeds}

{retrievedContentSection}

{groundTruthsSection}

**Comprehensive Evaluation Criteria:**

1. **Bias Assessment**:
   * **Score**: (0-1) How likely is the prompt to generate biased responses across different demographics, perspectives, and contexts?
   * **Analysis**: Identify specific language, examples, or structures that could introduce bias
   * **Mitigation**: Suggest specific modifications to reduce bias potential
   * **Test Cases**: Provide examples to test for various types of bias (gender, racial, age, cultural, etc.)

2. **Toxicity Assessment**:
   * **Score**: (0-1) How likely is the prompt to generate toxic, harmful, or inappropriate content?
   * **Risk Factors**: Identify elements that could trigger toxic responses
   * **Safeguards**: Recommend explicit safety measures and content filtering approaches
   * **Edge Cases**: Consider scenarios where the prompt might fail safety checks

3. **Prompt Alignment**:
   * **Score**: (0-1) How well does the prompt align with user requirements and intended outcomes?
   * **Goal Clarity**: Assess how clearly the prompt communicates the desired task
   * **Constraint Adherence**: Evaluate how well the prompt enforces necessary constraints
   * **Output Consistency**: Determine likelihood of consistent, expected outputs

4. **Relevance and Coherence**:
   * **Relevance Score**: (0-1) How well does the prompt ensure responses stay relevant to the task?
   * **Coherence Score**: (0-1) How likely is the prompt to generate logically coherent responses?
   * **Structure Quality**: Assess the logical flow and organization of the prompt

{faithfulnessSection}

5. **Overall Quality Assessment**:
   * Consider readability, clarity, completeness, and practical usability
   * Evaluate potential for misinterpretation or unintended behaviors
   * Assess scalability and robustness across different use cases

**Improved Prompt:**
Provide an enhanced version of the prompt that addresses ALL identified issues, incorporates safety measures, reduces bias potential, prevents toxicity, and improves overall quality and alignment.

**Improvement Summary:**
Provide a clear summary of the key improvements made and why they enhance the prompt's safety, quality, and effectiveness.

Return your response as JSON with keys: "improvedPrompt", "bias", "toxicity", "promptAlignment", and "improvementSummary".

Example format:
{{
    "improvedPrompt": "Enhanced prompt text with comprehensive improvements...",
    "bias": {{"score": 0.1, "summary": "Low bias risk due to inclusive language and diverse examples...", "mitigations": ["specific improvement 1", "specific improvement 2"]}},
    "toxicity": {{"score": 0.05, "summary": "Minimal toxicity risk with explicit safety guardrails...", "safeguards": ["safety measure 1", "safety measure 2"]}},
    "promptAlignment": {{"score": 0.9, "summary": "Strong alignment with requirements through clear objectives and constraints...", "improvements": ["alignment improvement 1", "alignment improvement 2"]}},
    "improvementSummary": "Key improvements include: bias reduction through inclusive language, toxicity prevention via explicit safeguards, enhanced clarity through structured objectives..."
}}"""
            },
            
            "iterate_on_prompt": {
                "description": "Iterate and refine a prompt based on feedback with quality assurance",
                "version": "2.0",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "template": """You are an expert prompt engineer specializing in iterative improvement and quality assurance. Refine the current prompt based on user feedback and selected suggestions while maintaining high standards for safety, bias mitigation, and quality.

**Current Prompt:**
{currentPrompt}

**User Comments:**
{userComments}

**Selected Improvement Suggestions:**
{selectedSuggestions}

**Iterative Improvement Process:**
1. **Feedback Analysis**: Carefully analyze the user feedback to understand concerns and desired improvements
2. **Suggestion Integration**: Evaluate which suggestions align with best practices and user needs
3. **Quality Preservation**: Ensure that improvements don't compromise existing safety measures or quality standards
4. **Bias Review**: Check that changes don't introduce new bias risks or compromise inclusivity
5. **Safety Verification**: Confirm that modifications maintain or improve toxicity prevention measures
6. **Coherence Check**: Ensure the refined prompt maintains logical flow and clarity
7. **Edge Case Consideration**: Account for how changes might affect prompt behavior in edge cases

**Quality Assurance Checklist:**
- Does the refined prompt address the user's specific concerns?
- Are safety and bias mitigation measures preserved or enhanced?
- Is the prompt structure improved without losing clarity?
- Do the changes align with responsible AI practices?
- Will the modifications improve response quality and consistency?

**Improvement Guidelines:**
- Maintain or enhance existing safety guardrails
- Use inclusive and unbiased language throughout
- Ensure clear, actionable instructions
- Preserve the core functionality while addressing feedback
- Add specific constraints or examples where helpful
- Consider potential misuse scenarios and add appropriate safeguards

Create an improved version of the prompt that thoughtfully incorporates the feedback and suggestions while maintaining high quality and safety standards.

Return your response as JSON with the key "newPrompt" and include an explanation of the key improvements made.

Example format:
{{
    "newPrompt": "Your refined prompt text incorporating feedback while maintaining quality standards...",
    "improvementExplanation": "Detailed explanation of how the feedback was addressed and what specific improvements were made..."
}}"""
            },
            
            "generate_prompt_tags": {
                "description": "Generate summary and tags with quality and safety indicators",
                "version": "2.0",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "template": """You are an expert prompt analyzer specializing in categorization, quality assessment, and safety evaluation. Generate a comprehensive summary and relevant tags for the given prompt, including quality and safety indicators.

**Prompt to Analyze:**
{promptText}

**Analysis Instructions:**
1. **Content Analysis**: Examine the prompt's purpose, domain, complexity, and intended use case
2. **Quality Assessment**: Evaluate clarity, specificity, structure, and potential effectiveness
3. **Safety Evaluation**: Assess bias potential, toxicity risk, and ethical considerations
4. **Categorization**: Determine appropriate functional and domain categories
5. **Use Case Identification**: Identify primary and secondary use cases

**Summary Guidelines:**
- Create a clear, informative summary (2-3 sentences)
- Highlight the prompt's main purpose and key characteristics
- Note any significant quality or safety considerations
- Use professional, objective language

**Tagging Categories:**
- **Domain**: (e.g., business, creative, technical, educational, healthcare)
- **Purpose**: (e.g., analysis, generation, classification, conversation, summarization)
- **Style**: (e.g., formal, casual, detailed, concise, creative)
- **Format**: (e.g., json-output, structured, freeform, step-by-step)
- **Complexity**: (e.g., simple, intermediate, advanced, expert-level)
- **Quality**: (e.g., high-quality, needs-improvement, well-structured, clear-objectives)
- **Safety**: (e.g., bias-aware, safety-focused, inclusive-language, ethical-guidelines)
- **Audience**: (e.g., general-public, professionals, students, researchers)

**Quality Indicators to Include:**
- Clarity and specificity level
- Bias risk assessment
- Safety considerations
- Structural quality
- Completeness and effectiveness potential

Return your response as JSON with keys "summary", "tags", and "qualityIndicators".

Example format:
{{
    "summary": "A well-structured prompt for analyzing business data with clear objectives and safety considerations. Designed for professional use with emphasis on unbiased analysis and factual reporting.",
    "tags": ["domain-business", "purpose-analysis", "format-structured", "complexity-intermediate", "quality-high", "safety-bias-aware", "audience-professionals"],
    "qualityIndicators": {{
        "clarity": "high",
        "bias_risk": "low", 
        "safety_level": "high",
        "completeness": "high",
        "effectiveness_potential": "high"
    }}
}}"""
            },
            
            "get_prompt_suggestions": {
                "description": "Generate comprehensive improvement suggestions with safety and quality focus",
                "version": "2.0",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "template": """You are an expert prompt engineer with specialization in prompt optimization, safety enhancement, and quality improvement. Analyze the current prompt and provide specific, actionable improvement suggestions with focus on safety, bias mitigation, and overall quality enhancement.

**Current Prompt:**
{currentPrompt}

{userCommentsSection}

**Comprehensive Analysis Areas:**

1. **Safety and Ethics**:
   - Bias detection and mitigation opportunities
   - Toxicity prevention measures
   - Inclusive language improvements
   - Ethical consideration enhancements

2. **Clarity and Specificity**:
   - Instruction precision and clarity
   - Objective definition improvements
   - Constraint specification enhancements
   - Example provision opportunities

3. **Structure and Organization**:
   - Logical flow optimization
   - Information hierarchy improvements
   - Readability enhancements
   - Format specification clarifications

4. **Completeness and Coverage**:
   - Missing context identification
   - Constraint gap analysis
   - Edge case coverage assessment
   - Error handling improvements

5. **Output Quality Assurance**:
   - Response consistency improvements
   - Quality control measures
   - Validation criteria specification
   - Performance optimization opportunities

6. **User Experience**:
   - Usability enhancements
   - Accessibility improvements
   - Scalability considerations
   - Maintenance and updates

**Suggestion Guidelines:**
- Provide 5-10 specific, actionable improvement suggestions
- Prioritize safety and bias mitigation improvements
- Focus on practical, implementable changes
- Consider both immediate and long-term benefits
- Address the most impactful potential improvements first
- Include specific examples or modifications where helpful

**Suggestion Categories:**
- **Critical**: Essential for safety, bias mitigation, or core functionality
- **Important**: Significant quality or usability improvements
- **Enhancement**: Nice-to-have improvements for optimization

Return your response as JSON with the key "suggestions" containing an array of detailed suggestion objects.

Example format:
{{
    "suggestions": [
        {{
            "category": "critical",
            "title": "Add bias mitigation measures",
            "description": "Include explicit instructions to consider diverse perspectives and avoid demographic assumptions",
            "implementation": "Add: 'Ensure responses are inclusive and consider diverse viewpoints without making assumptions about demographics or backgrounds.'",
            "impact": "Reduces bias risk and improves inclusivity"
        }},
        {{
            "category": "important", 
            "title": "Enhance output format specification",
            "description": "Provide clearer structure for expected response format",
            "implementation": "Add specific formatting requirements and examples",
            "impact": "Improves response consistency and usability"
        }}
    ]
}}"""
            },
            
            "optimize_prompt_with_context": {
                "description": "Optimize prompts using context with comprehensive quality and safety optimization",
                "version": "2.0",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "template": """You are an expert RAG (Retrieval-Augmented Generation) prompt engineer with specialization in context-aware optimization, safety enhancement, and quality assurance. Optimize the given prompt using the provided context and examples while ensuring high standards for bias mitigation, toxicity prevention, and overall quality.

**Original Prompt:**
{prompt}

**Retrieved Content (Knowledge Base):**
{retrievedContent}

**Ground Truth Examples:**
{groundTruths}

**Comprehensive Optimization Objectives:**

1. **Context Integration and Faithfulness**:
   - Ensure responses stay faithful to the retrieved content
   - Integrate relevant context seamlessly
   - Prevent hallucination and information fabrication
   - Maintain accuracy to source material

2. **Domain-Specific Optimization**:
   - Adapt language and terminology to the specific domain
   - Incorporate domain best practices and standards
   - Ensure consistency with provided examples
   - Align with industry or field-specific requirements

3. **Safety and Bias Enhancement**:
   - Review context for potential bias sources
   - Add safeguards against biased interpretation of context
   - Ensure inclusive representation in examples and instructions
   - Prevent amplification of existing biases in source material

4. **Quality and Consistency Assurance**:
   - Improve response consistency with ground truth examples
   - Enhance clarity and specificity for the domain
   - Optimize for the specific use case and context
   - Ensure robust performance across similar scenarios

5. **Edge Case and Error Handling**:
   - Address cases where retrieved content is insufficient
   - Handle conflicting information in context
   - Provide guidance for uncertain or ambiguous situations
   - Include fallback strategies for incomplete context

**Optimization Process:**
1. **Context Analysis**: Examine the retrieved content for key information, potential biases, and quality indicators
2. **Example Integration**: Analyze ground truth examples for patterns, quality standards, and consistency requirements
3. **Prompt Enhancement**: Modify the original prompt to better leverage context while maintaining safety standards
4. **Quality Verification**: Ensure optimizations improve rather than compromise prompt effectiveness
5. **Safety Review**: Confirm that context integration doesn't introduce new bias or safety risks

**Context-Aware Improvements:**
- Integrate specific terminology and concepts from the knowledge base
- Add context-validation instructions to ensure faithfulness
- Include domain-specific constraints and quality criteria
- Provide clear guidance on handling context limitations
- Ensure examples align with the specific domain and use case

**Safety Considerations for Context:**
- Review retrieved content for potential bias or problematic information
- Add explicit instructions to critically evaluate context information
- Include guidelines for handling controversial or sensitive topics in context
- Ensure diverse perspectives are considered when interpreting context

Provide the optimized prompt and detailed reasoning for your changes, focusing on how the modifications improve faithfulness, reduce bias, enhance safety, and increase overall quality.

Return your response as JSON with keys "optimizedPrompt" and "reasoning".

Example format:
{{
    "optimizedPrompt": "Your comprehensively optimized prompt incorporating context, safety measures, and quality enhancements...",
    "reasoning": "Detailed explanation of optimizations made, including context integration strategies, safety improvements, bias mitigation measures, and quality enhancements. Explain how each change improves the prompt's effectiveness and safety."
}}"""
            }
        }
        
        # Save default templates if they don't exist
        for template_name, template_data in default_templates.items():
            template_path = self.templates_dir / f"{template_name}.json"
            if not template_path.exists():
                self.save_template(template_name, template_data)
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by name
        
        Args:
            template_name (str): Name of the template to retrieve
            
        Returns:
            dict: Template data or None if not found
        """
        if template_name in self.templates:
            return self.templates[template_name]
        else:
            logger.warning(f"Template not found: {template_name}")
            return None
    
    def render_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Render a template with the provided variables, prioritizing DeepEval-optimized versions
        
        Args:
            template_name (str): Name of the template to render
            **kwargs: Variables to render in the template
            
        Returns:
            str: Rendered template or None if template not found
        """
        # Check for DeepEval-optimized version first
        deepeval_template = self._get_deepeval_optimized_template(template_name, **kwargs)
        if deepeval_template:
            template_data = {"template": deepeval_template}
        else:
            # Check for DSPy-optimized version
            dspy_template = self._get_dspy_optimized_template(template_name, **kwargs)
            if dspy_template:
                template_data = {"template": dspy_template}
            else:
                # Use base template
                template_data = self.get_template(template_name)
        
        if not template_data or 'template' not in template_data:
            return None
        
        template = template_data['template']
        
        # Track usage
        self._track_template_usage(template_name)
        
        # Simple string formatting for template variables
        try:
            rendered = template.format(**kwargs)
            self._record_template_success(template_name)
            return rendered
        except KeyError as e:
            logger.error(f"Missing variable in template {template_name}: {str(e)}")
            self._record_template_failure(template_name)
            return None
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}")
            self._record_template_failure(template_name)
            return None
    
    def _get_deepeval_optimized_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Get DeepEval-optimized template if available
        
        Args:
            template_name (str): Name of the template
            **kwargs: Template variables for context-specific optimization
            
        Returns:
            str: Optimized template or None if not available
        """
        # Create a context hash for this specific use case
        context_hash = self._generate_context_hash(template_name, **kwargs)
        
        if template_name in self.deepeval_optimized_templates:
            optimized_versions = self.deepeval_optimized_templates[template_name]
            
            # Look for context-specific optimization
            if context_hash in optimized_versions:
                opt_data = optimized_versions[context_hash]
                # Update usage count
                opt_data["usage_count"] = opt_data.get("usage_count", 0) + 1
                opt_data["last_used"] = time.time()
                return opt_data["template"]
            
            # Fall back to general optimization if available
            if "general" in optimized_versions:
                opt_data = optimized_versions["general"]
                opt_data["usage_count"] = opt_data.get("usage_count", 0) + 1
                opt_data["last_used"] = time.time()
                return opt_data["template"]
        
        return None
    
    def _get_dspy_optimized_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Get DSPy-optimized template if available
        
        Args:
            template_name (str): Name of the template
            **kwargs: Template variables for context-specific optimization
            
        Returns:
            str: Optimized template or None if not available
        """
        # Create a context hash for this specific use case
        context_hash = self._generate_context_hash(template_name, **kwargs)
        
        if template_name in self.dspy_optimized_templates:
            optimized_versions = self.dspy_optimized_templates[template_name]
            
            # Look for context-specific optimization
            if context_hash in optimized_versions:
                opt_data = optimized_versions[context_hash]
                opt_data["usage_count"] = opt_data.get("usage_count", 0) + 1
                opt_data["last_used"] = time.time()
                return opt_data["template"]
            
            # Fall back to general optimization if available
            if "general" in optimized_versions:
                opt_data = optimized_versions["general"]
                opt_data["usage_count"] = opt_data.get("usage_count", 0) + 1
                opt_data["last_used"] = time.time()
                return opt_data["template"]
        
        return None
    
    def _generate_context_hash(self, template_name: str, **kwargs) -> str:
        """Generate a hash for the template context"""
        # Create a simplified context signature
        context_keys = sorted(kwargs.keys())
        context_signature = f"{template_name}:{':'.join(context_keys)}"
        return hashlib.md5(context_signature.encode()).hexdigest()[:8]
    
    def save_deepeval_optimized_template(self, template_name: str, optimized_template: str,
                                       context: Optional[Dict[str, Any]] = None,
                                       deepeval_metrics: Optional[Dict[str, float]] = None,
                                       optimization_notes: Optional[str] = None):
        """
        Save a DeepEval-optimized template
        
        Args:
            template_name (str): Name of the base template
            optimized_template (str): The optimized template text
            context (dict, optional): Context for which this optimization applies
            deepeval_metrics (dict, optional): DeepEval metrics that drove the optimization
            optimization_notes (str, optional): Notes about the optimization process
        """
        if template_name not in self.deepeval_optimized_templates:
            self.deepeval_optimized_templates[template_name] = {}
        
        context_key = "general"
        if context:
            context_key = self._generate_context_hash(template_name, **context)
        
        self.deepeval_optimized_templates[template_name][context_key] = {
            "template": optimized_template,
            "created_at": time.time(),
            "context": context or {},
            "deepeval_metrics": deepeval_metrics or {},
            "optimization_notes": optimization_notes or "",
            "usage_count": 0,
            "last_used": None,
            "performance_history": []
        }
        
        # Save to disk
        self._save_deepeval_optimizations()
        
        logger.info(f"Saved DeepEval optimization for template {template_name} with context {context_key}")
    
    def save_dspy_optimized_template(self, template_name: str, optimized_template: str, 
                                   context: Optional[Dict[str, Any]] = None, 
                                   performance_metrics: Optional[Dict[str, float]] = None):
        """
        Save a DSPy-optimized template
        
        Args:
            template_name (str): Name of the base template
            optimized_template (str): The optimized template text
            context (dict, optional): Context for which this optimization applies
            performance_metrics (dict, optional): Performance metrics for this optimization
        """
        if template_name not in self.dspy_optimized_templates:
            self.dspy_optimized_templates[template_name] = {}
        
        context_key = "general"
        if context:
            context_key = self._generate_context_hash(template_name, **context)
        
        self.dspy_optimized_templates[template_name][context_key] = {
            "template": optimized_template,
            "created_at": time.time(),
            "context": context or {},
            "performance_metrics": performance_metrics or {},
            "usage_count": 0,
            "last_used": None
        }
        
        # Save to disk
        self._save_dspy_optimizations()
        
        logger.info(f"Saved DSPy optimization for template {template_name} with context {context_key}")
    
    def record_template_deepeval_score(self, template_name: str, metric_name: str, score: float):
        """
        Record a DeepEval score for a template
        
        Args:
            template_name (str): Name of the template
            metric_name (str): Name of the metric (bias, toxicity, relevance, etc.)
            score (float): The score value
        """
        if template_name in self.template_usage:
            usage_data = self.template_usage[template_name]
            if metric_name in usage_data["deepeval_scores"]:
                usage_data["deepeval_scores"][metric_name].append({
                    "score": score,
                    "timestamp": time.time()
                })
                
                # Keep only recent scores (last 100)
                if len(usage_data["deepeval_scores"][metric_name]) > 100:
                    usage_data["deepeval_scores"][metric_name] = usage_data["deepeval_scores"][metric_name][-100:]
    
    def get_template_deepeval_summary(self, template_name: str) -> Dict[str, Any]:
        """
        Get DeepEval performance summary for a template
        
        Args:
            template_name (str): Name of the template
            
        Returns:
            dict: DeepEval performance summary
        """
        if template_name not in self.template_usage:
            return {"error": "Template not found"}
        
        usage_data = self.template_usage[template_name]
        deepeval_scores = usage_data["deepeval_scores"]
        
        summary = {
            "template_name": template_name,
            "metrics_summary": {},
            "optimization_recommendations": [],
            "performance_trends": {}
        }
        
        for metric, scores in deepeval_scores.items():
            if scores:
                score_values = [s["score"] for s in scores]
                summary["metrics_summary"][metric] = {
                    "average": sum(score_values) / len(score_values),
                    "latest": score_values[-1],
                    "best": max(score_values) if metric not in ["bias", "toxicity"] else min(score_values),
                    "worst": min(score_values) if metric not in ["bias", "toxicity"] else max(score_values),
                    "count": len(score_values),
                    "trend": self._calculate_trend(score_values)
                }
                
                # Generate recommendations based on scores
                avg_score = summary["metrics_summary"][metric]["average"]
                if metric == "bias" and avg_score > 0.3:
                    summary["optimization_recommendations"].append(f"High bias detected (avg: {avg_score:.2f}) - consider bias mitigation optimization")
                elif metric == "toxicity" and avg_score > 0.2:
                    summary["optimization_recommendations"].append(f"Toxicity risk detected (avg: {avg_score:.2f}) - implement safety enhancements")
                elif metric in ["relevance", "coherence", "faithfulness"] and avg_score < 0.7:
                    summary["optimization_recommendations"].append(f"Low {metric} score (avg: {avg_score:.2f}) - optimize for better {metric}")
        
        return summary
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate trend direction for scores"""
        if len(scores) < 3:
            return "insufficient_data"
        
        recent_avg = sum(scores[-5:]) / len(scores[-5:])
        older_avg = sum(scores[:-5]) / len(scores[:-5]) if len(scores) > 5 else sum(scores[:-2]) / len(scores[:-2])
        
        if recent_avg > older_avg * 1.05:
            return "improving"
        elif recent_avg < older_avg * 0.95:
            return "declining"
        else:
            return "stable"
    
    def _save_deepeval_optimizations(self):
        """Save DeepEval optimizations to disk"""
        try:
            optimizations_file = self.templates_dir / "deepeval_optimizations.json"
            with open(optimizations_file, 'w') as f:
                json.dump(self.deepeval_optimized_templates, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving DeepEval optimizations: {str(e)}")
    
    def _save_dspy_optimizations(self):
        """Save DSPy optimizations to disk"""
        try:
            optimizations_file = self.templates_dir / "dspy_optimizations.json"
            with open(optimizations_file, 'w') as f:
                json.dump(self.dspy_optimized_templates, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving DSPy optimizations: {str(e)}")
    
    def _load_deepeval_optimizations(self):
        """Load DeepEval optimizations from disk"""
        try:
            optimizations_file = self.templates_dir / "deepeval_optimizations.json"
            if optimizations_file.exists():
                with open(optimizations_file, 'r') as f:
                    self.deepeval_optimized_templates = json.load(f)
                logger.info("Loaded DeepEval optimizations from disk")
        except Exception as e:
            logger.error(f"Error loading DeepEval optimizations: {str(e)}")
    
    def _load_dspy_optimizations(self):
        """Load DSPy optimizations from disk"""
        try:
            optimizations_file = self.templates_dir / "dspy_optimizations.json"
            if optimizations_file.exists():
                with open(optimizations_file, 'r') as f:
                    self.dspy_optimized_templates = json.load(f)
                logger.info("Loaded DSPy optimizations from disk")
        except Exception as e:
            logger.error(f"Error loading DSPy optimizations: {str(e)}")
    
    def _track_template_usage(self, template_name: str):
        """Track template usage for analytics"""
        if template_name not in self.template_usage:
            self.template_usage[template_name] = {
                "usage_count": 0,
                "last_used": None,
                "success_rate": 1.0,
                "average_response_time": 0.0,
                "deepeval_scores": {
                    "bias": [],
                    "toxicity": [],
                    "relevance": [],
                    "coherence": [],
                    "faithfulness": [],
                    "overall": []
                }
            }
        
        self.template_usage[template_name]["usage_count"] += 1
        self.template_usage[template_name]["last_used"] = time.time()
    
    def _record_template_success(self, template_name: str):
        """Record successful template rendering"""
        if template_name in self.template_usage:
            current_rate = self.template_usage[template_name]["success_rate"]
            total_uses = self.template_usage[template_name]["usage_count"]
            
            # Update success rate using moving average
            new_rate = (current_rate * (total_uses - 1) + 1.0) / total_uses
            self.template_usage[template_name]["success_rate"] = new_rate
    
    def _record_template_failure(self, template_name: str):
        """Record failed template rendering"""
        if template_name in self.template_usage:
            current_rate = self.template_usage[template_name]["success_rate"]
            total_uses = self.template_usage[template_name]["usage_count"]
            
            # Update success rate using moving average
            new_rate = (current_rate * (total_uses - 1) + 0.0) / total_uses
            self.template_usage[template_name]["success_rate"] = new_rate
    
    def get_template_analytics(self) -> Dict[str, Any]:
        """Get comprehensive template usage analytics including DeepEval metrics"""
        analytics = {
            "template_usage": self.template_usage,
            "dspy_optimizations": {
                name: len(optimizations) 
                for name, optimizations in self.dspy_optimized_templates.items()
            },
            "deepeval_optimizations": {
                name: len(optimizations)
                for name, optimizations in self.deepeval_optimized_templates.items()
            },
            "total_templates": len(self.templates),
            "quality_summary": self._generate_quality_summary()
        }
        
        return analytics
    
    def _generate_quality_summary(self) -> Dict[str, Any]:
        """Generate overall quality summary across all templates"""
        quality_summary = {
            "templates_with_deepeval_data": 0,
            "average_scores": {},
            "quality_distribution": {"high": 0, "medium": 0, "low": 0, "unknown": 0},
            "optimization_opportunities": []
        }
        
        metric_totals = {"bias": [], "toxicity": [], "relevance": [], "coherence": [], "faithfulness": [], "overall": []}
        
        for template_name, usage_data in self.template_usage.items():
            deepeval_scores = usage_data.get("deepeval_scores", {})
            has_scores = any(scores for scores in deepeval_scores.values())
            
            if has_scores:
                quality_summary["templates_with_deepeval_data"] += 1
                
                # Collect scores for averaging
                for metric, scores in deepeval_scores.items():
                    if scores:
                        recent_scores = [s["score"] for s in scores[-10:]]  # Last 10 scores
                        avg_score = sum(recent_scores) / len(recent_scores)
                        metric_totals[metric].append(avg_score)
                
                # Determine quality category
                overall_scores = [s["score"] for s in deepeval_scores.get("overall", [])]
                if overall_scores:
                    avg_overall = sum(overall_scores[-5:]) / len(overall_scores[-5:])  # Last 5 scores
                    if avg_overall >= 0.8:
                        quality_summary["quality_distribution"]["high"] += 1
                    elif avg_overall >= 0.6:
                        quality_summary["quality_distribution"]["medium"] += 1
                    else:
                        quality_summary["quality_distribution"]["low"] += 1
                else:
                    quality_summary["quality_distribution"]["unknown"] += 1
        
        # Calculate average scores across all templates
        for metric, scores in metric_totals.items():
            if scores:
                quality_summary["average_scores"][metric] = sum(scores) / len(scores)
        
        # Generate optimization opportunities
        if quality_summary["average_scores"]:
            if quality_summary["average_scores"].get("bias", 0) > 0.3:
                quality_summary["optimization_opportunities"].append("System-wide bias reduction needed")
            if quality_summary["average_scores"].get("toxicity", 0) > 0.2:
                quality_summary["optimization_opportunities"].append("Enhanced safety measures recommended")
            if quality_summary["average_scores"].get("relevance", 1) < 0.7:
                quality_summary["optimization_opportunities"].append("Relevance optimization opportunities identified")
        
        return quality_summary
    
    def reload_templates(self):
        """Reload all templates from disk"""
        self.templates = {}
        self._load_templates()
        self._load_dspy_optimizations()
        self._load_deepeval_optimizations()
        self._create_default_templates()
        
    def save_template(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """
        Save a template to disk
        
        Args:
            template_name (str): Name of the template
            template_data (dict): Template data to save
            
        Returns:
            bool: Success or failure
        """
        try:
            template_path = self.templates_dir / f"{template_name}.json"
            with open(template_path, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Update in-memory cache
            self.templates[template_name] = template_data
            
            # Initialize usage tracking if new template
            if template_name not in self.template_usage:
                self.template_usage[template_name] = {
                    "usage_count": 0,
                    "last_used": None,
                    "success_rate": 1.0,
                    "average_response_time": 0.0,
                    "deepeval_scores": {
                        "bias": [],
                        "toxicity": [],
                        "relevance": [],
                        "coherence": [],
                        "faithfulness": [],
                        "overall": []
                    }
                }
            
            logger.info(f"Saved template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template {template_name}: {str(e)}")
            return False
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available templates with comprehensive metadata
        
        Returns:
            dict: Dictionary of template names and their metadata
        """
        templates_info = {}
        
        for name, template_data in self.templates.items():
            usage_stats = self.template_usage.get(name, {})
            deepeval_summary = self.get_template_deepeval_summary(name)
            
            templates_info[name] = {
                "description": template_data.get("description", "No description"),
                "version": template_data.get("version", "1.0"),
                "dspy_compatible": template_data.get("dspy_compatible", False),
                "deepeval_optimized": template_data.get("deepeval_optimized", False),
                "usage_stats": usage_stats,
                "has_dspy_optimizations": name in self.dspy_optimized_templates,
                "has_deepeval_optimizations": name in self.deepeval_optimized_templates,
                "dspy_optimization_count": len(self.dspy_optimized_templates.get(name, {})),
                "deepeval_optimization_count": len(self.deepeval_optimized_templates.get(name, {})),
                "deepeval_summary": deepeval_summary if "error" not in deepeval_summary else None,
                "quality_recommendation": self._get_template_quality_recommendation(name, deepeval_summary)
            }
        
        return templates_info
    
    def _get_template_quality_recommendation(self, template_name: str, deepeval_summary: Dict[str, Any]) -> str:
        """Get quality-based recommendation for template"""
        if "error" in deepeval_summary:
            return "No quality data available - consider running DeepEval assessment"
        
        metrics = deepeval_summary.get("metrics_summary", {})
        recommendations = deepeval_summary.get("optimization_recommendations", [])
        
        if recommendations:
            return f"Optimization needed: {recommendations[0]}"
        
        # Check overall quality
        overall_metric = metrics.get("overall", {})
        if overall_metric and overall_metric.get("average", 0) >= 0.8:
            return "High quality template - performing well"
        elif overall_metric and overall_metric.get("average", 0) >= 0.6:
            return "Good quality template - minor optimizations possible"
        elif overall_metric:
            return "Quality improvements needed - consider optimization"
        else:
            return "Insufficient quality data - run more evaluations"
    
    def suggest_optimization_candidates(self) -> List[Dict[str, Any]]:
        """
        Suggest templates that would benefit from optimization with enhanced DeepEval insights
        
        Returns:
            list: List of optimization candidates with detailed reasoning
        """
        candidates = []
        
        for template_name, stats in self.template_usage.items():
            score = 0
            reasons = []
            deepeval_summary = self.get_template_deepeval_summary(template_name)
            
            # High usage templates are good candidates
            if stats.get("usage_count", 0) > 50:
                score += 2
                reasons.append("High usage frequency")
            
            # Low success rate templates need optimization
            if stats.get("success_rate", 1.0) < 0.9:
                score += 3
                reasons.append("Low success rate")
            
            # Templates without optimizations
            if template_name not in self.dspy_optimized_templates and template_name not in self.deepeval_optimized_templates:
                score += 2
                reasons.append("No optimizations available")
            
            # DeepEval-based scoring
            if "error" not in deepeval_summary:
                metrics = deepeval_summary.get("metrics_summary", {})
                
                # High bias or toxicity
                if metrics.get("bias", {}).get("average", 0) > 0.3:
                    score += 4
                    reasons.append("High bias detected")
                if metrics.get("toxicity", {}).get("average", 0) > 0.2:
                    score += 4
                    reasons.append("Toxicity risk detected")
                
                # Low quality metrics
                for metric in ["relevance", "coherence", "faithfulness"]:
                    if metrics.get(metric, {}).get("average", 1) < 0.7:
                        score += 2
                        reasons.append(f"Low {metric} score")
                
                # Declining trends
                for metric, data in metrics.items():
                    if data.get("trend") == "declining":
                        score += 1
                        reasons.append(f"Declining {metric} trend")
            
            if score >= 3:  # Threshold for recommendation
                priority = "high" if score >= 6 else "medium" if score >= 4 else "low"
                candidates.append({
                    "template_name": template_name,
                    "optimization_score": score,
                    "priority": priority,
                    "reasons": reasons,
                    "current_stats": stats,
                    "deepeval_summary": deepeval_summary if "error" not in deepeval_summary else None,
                    "recommended_optimization": self._get_recommended_optimization_type(reasons)
                })
        
        # Sort by optimization score and priority
        candidates.sort(key=lambda x: (x["optimization_score"], x["priority"] == "high"), reverse=True)
        return candidates
    
    def _get_recommended_optimization_type(self, reasons: List[str]) -> str:
        """Determine the recommended optimization type based on reasons"""
        if any("bias" in reason.lower() or "toxicity" in reason.lower() for reason in reasons):
            return "DeepEval Safety Optimization"
        elif any("success rate" in reason.lower() for reason in reasons):
            return "DSPy Performance Optimization"
        elif any("usage" in reason.lower() for reason in reasons):
            return "Comprehensive Optimization (DSPy + DeepEval)"
        else:
            return "General Quality Optimization"

# Initialize a global template manager instance
template_manager = DSPyPromptTemplateManager()

# Load any existing optimizations on startup
template_manager._load_dspy_optimizations()
template_manager._load_deepeval_optimizations()