# prompt_templates.py
"""
Enhanced module for managing prompt templates with DSPy integration and DeepEval optimization.
Refactored for cleaner code and precise context-aware template management.
"""

import os
import json
import logging
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

class DSPyPromptTemplateManager:
    """Enhanced manager for prompt templates with precise optimization and context awareness"""
    
    def __init__(self, templates_dir=None):
        """Initialize the template manager with enhanced tracking"""
        if templates_dir is None:
            self.templates_dir = Path(__file__).parent / 'templates'
        else:
            self.templates_dir = Path(templates_dir)
            
        self.templates_dir.mkdir(exist_ok=True)
        
        # Core template storage
        self.templates = {}
        
        # Optimization storage
        self.dspy_optimized_templates = {}
        self.deepeval_optimized_templates = {}
        
        # Enhanced analytics
        self.template_usage = {}
        self.template_metrics = {}
        self.context_patterns = {}
        
        # Load all templates and optimizations
        self._load_templates()
        self._load_optimizations()
        self._create_enhanced_default_templates()
    
    def _load_templates(self):
        """Load all template files with enhanced error handling"""
        try:
            for template_file in self.templates_dir.glob('*.json'):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        template_name = template_file.stem
                        self.templates[template_name] = template_data
                        
                        # Initialize enhanced usage tracking
                        self._initialize_template_tracking(template_name)
                        
                    logger.info(f"Loaded template: {template_name}")
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning templates directory: {str(e)}")
    
    def _initialize_template_tracking(self, template_name: str):
        """Initialize comprehensive template tracking"""
        self.template_usage[template_name] = {
            "usage_count": 0,
            "last_used": None,
            "success_rate": 1.0,
            "average_response_time": 0.0,
            "context_usage": {},
            "deepeval_scores": {
                "bias": [],
                "toxicity": [],
                "relevance": [],
                "coherence": [],
                "faithfulness": [],
                "overall": []
            },
            "quality_trend": [],
            "optimization_history": []
        }
    
    def _load_optimizations(self):
        """Load existing optimizations from disk"""
        self._load_dspy_optimizations()
        self._load_deepeval_optimizations()
    
    def _create_enhanced_default_templates(self):
        """Create enhanced default templates with DeepEval optimization focus"""
        default_templates = {
            "generate_initial_prompt": {
                "description": "Generate initial system prompt with enhanced safety and quality focus",
                "version": "2.1",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "context_aware": True,
                "template": """You are an expert prompt engineer specializing in creating safe, unbiased, and high-quality system prompts. Your task is to generate an effective system prompt that meets user requirements while maintaining the highest standards for safety, bias mitigation, and response quality.

User Requirements: {userNeeds}

{deepevalContext}

ENHANCED PROMPT CREATION FRAMEWORK:

**SAFETY-FIRST APPROACH:**
1. **Bias Prevention**: Ensure inclusive language, diverse perspectives, avoid demographic assumptions
2. **Toxicity Prevention**: Include explicit safety guardrails, content boundaries, harm prevention
3. **Ethical Guidelines**: Embed responsible AI practices, respect for all users, fairness principles

**QUALITY OPTIMIZATION:**
1. **Clarity & Specificity**: Clear instructions, unambiguous language, specific expectations
2. **Context Integration**: Relevant background, appropriate constraints, domain-specific knowledge
3. **Output Specification**: Precise format requirements, quality standards, validation criteria

**ADVANCED TECHNIQUES:**
1. **Layered Prompting**: Separate system rules from task constraints
2. **Self-Verification**: Include quality checks and error prevention
3. **Adaptive Responses**: Handle edge cases and uncertainty appropriately

Create a comprehensive, safe, and effective system prompt that addresses the user's requirements while incorporating all safety and quality considerations.

Return your response as JSON:
{{
    "initialPrompt": "Your generated system prompt with safety and quality optimizations..."
}}"""
            },
            
            "evaluate_and_iterate_prompt": {
                "description": "Evaluate and improve prompts with comprehensive DeepEval-driven analysis",
                "version": "2.1",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "context_aware": True,
                "template": """You are an expert prompt evaluation specialist with deep expertise in AI safety, bias detection, and quality optimization. Analyze the given prompt and provide comprehensive evaluation with precise improvements.

**CURRENT PROMPT:**
{prompt}

**USER REQUIREMENTS:**
{userNeeds}

{retrievedContentSection}
{groundTruthsSection}
{deepevalContext}

**COMPREHENSIVE EVALUATION FRAMEWORK:**

**1. BIAS ASSESSMENT (Critical Priority)**
- **Scoring**: 0.0 = No bias, 1.0 = Severe bias
- **Analysis Areas**: Language inclusivity, demographic neutrality, assumption identification
- **Test Framework**: Design specific test cases for bias detection
- **Mitigation**: Provide concrete bias reduction strategies

**2. TOXICITY ASSESSMENT (Critical Priority)**
- **Scoring**: 0.0 = Safe, 1.0 = High toxicity risk
- **Analysis Areas**: Harmful content potential, safety boundary effectiveness
- **Risk Evaluation**: Identify specific toxicity vectors
- **Prevention**: Design comprehensive safety measures

**3. PROMPT ALIGNMENT (Quality Priority)**
- **Scoring**: 0.0 = Misaligned, 1.0 = Perfect alignment
- **Analysis Areas**: Requirement fulfillment, objective clarity, constraint implementation
- **Optimization**: Enhance alignment through targeted improvements

{faithfulnessSection}

Create an improved version that eliminates identified risks and enhances quality.

Return comprehensive evaluation as JSON:
{{
    "improvedPrompt": "Enhanced prompt with all improvements...",
    "bias": {{
        "score": <float 0-1>,
        "summary": "Detailed bias analysis...",
        "issues": ["specific bias concerns"],
        "mitigations": ["concrete improvements"],
        "testCases": ["bias test scenarios"]
    }},
    "toxicity": {{
        "score": <float 0-1>,
        "summary": "Detailed toxicity analysis...",
        "risks": ["specific risk factors"],
        "safeguards": ["safety measures"],
        "testCases": ["toxicity test scenarios"]
    }},
    "promptAlignment": {{
        "score": <float 0-1>,
        "summary": "Detailed alignment analysis...",
        "strengths": ["alignment successes"],
        "improvements": ["enhancement areas"],
        "testCases": ["alignment test scenarios"]
    }},
    "improvementSummary": "Comprehensive summary of enhancements made..."
}}"""
            },
            
            "iterate_on_prompt": {
                "description": "Iterate prompts with DeepEval feedback integration",
                "version": "2.1",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "context_aware": True,
                "template": """You are an expert prompt refinement specialist. Improve the current prompt by integrating user feedback, selected suggestions, and assessment insights to create an optimized version.

**CURRENT PROMPT:**
{currentPrompt}

**USER FEEDBACK:**
{userComments}

**SELECTED SUGGESTIONS:**
{selectedSuggestions}

{deepevalInsights}

**REFINEMENT STRATEGY:**

**1. FEEDBACK INTEGRATION**
- Analyze user comments for specific improvement areas
- Prioritize user-identified concerns and requirements
- Maintain core functionality while addressing feedback

**2. SUGGESTION IMPLEMENTATION**
- Evaluate selected suggestions for compatibility and impact
- Integrate suggestions that enhance safety and quality
- Avoid changes that compromise existing safeguards

**3. ASSESSMENT-DRIVEN IMPROVEMENTS**
- Address specific issues identified in quality assessments
- Prioritize safety and bias mitigation enhancements
- Implement targeted improvements for identified weaknesses

**ENHANCEMENT PRIORITIES:**
1. **Critical**: Safety, bias, and toxicity improvements
2. **High**: User feedback and alignment issues
3. **Medium**: Quality and effectiveness enhancements

Create an improved prompt that thoughtfully integrates all feedback while maintaining high safety and quality standards.

Return refined prompt as JSON:
{{
    "newPrompt": "Refined prompt incorporating all improvements...",
    "improvementExplanation": "Detailed explanation of changes made and rationale...",
    "addressedFeedback": ["specific user concerns addressed"],
    "integratedSuggestions": ["suggestions successfully implemented"],
    "qualityEnhancements": ["additional quality improvements made"]
}}"""
            },
            
            "generate_prompt_tags": {
                "description": "Generate precise tags with quality and safety indicators",
                "version": "2.1",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "context_aware": True,
                "template": """You are an expert prompt analyzer specializing in categorization, quality assessment, and safety evaluation. Generate comprehensive tags and summary for the given prompt.

**PROMPT TO ANALYZE:**
{promptText}

{targetedContext}

**ANALYSIS FRAMEWORK:**

**1. CONTENT ANALYSIS**
- Purpose and primary function identification
- Domain and application area assessment
- Complexity and sophistication level evaluation
- Use case and audience identification

**2. QUALITY INDICATORS**
- Clarity and specificity assessment
- Structure and organization evaluation
- Completeness and effectiveness analysis
- Professional quality determination

**3. SAFETY EVALUATION**
- Bias risk assessment and identification
- Toxicity potential evaluation
- Safety measure adequacy analysis
- Ethical consideration review

**ENHANCED TAGGING SYSTEM:**
- Domain Tags: business, creative, technical, educational, healthcare, legal, research
- Purpose Tags: analysis, generation, classification, conversation, summarization, evaluation
- Quality Tags: high-quality, well-structured, clear-objectives, needs-improvement, professional-grade
- Safety Tags: bias-safe, safety-verified, inclusive-language, ethical-guidelines, toxicity-safe
- Structure Tags: detailed, concise, step-by-step, formatted-output, examples-included
- Complexity Tags: simple, intermediate, advanced, expert-level, comprehensive
- Audience Tags: general-public, professionals, students, researchers, specialists

Generate 4-8 most relevant tags with quality and safety indicators.

Return analysis as JSON:
{{
    "summary": "Concise, informative summary (5-10 words)...",
    "tags": ["precise", "relevant", "quality-tags"],
    "qualityIndicators": {{
        "clarity": "high|medium|low",
        "bias_risk": "low|medium|high",
        "safety_level": "high|medium|low",
        "completeness": "high|medium|low",
        "professional_grade": true|false
    }},
    "categoryAnalysis": {{
        "primary_domain": "identified domain",
        "main_purpose": "primary function",
        "target_audience": "intended users",
        "complexity_level": "assessed complexity"
    }}
}}"""
            },
            
            "get_prompt_suggestions": {
                "description": "Generate targeted suggestions with assessment-driven priorities",
                "version": "2.1",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "context_aware": True,
                "template": """You are an expert prompt improvement specialist. Analyze the current prompt and provide targeted, actionable suggestions prioritized by assessment insights and user needs.

**CURRENT PROMPT:**
{currentPrompt}

{userCommentsSection}
{targetedContext}

**SUGGESTION GENERATION FRAMEWORK:**

**1. CRITICAL PRIORITY SUGGESTIONS (Safety & Bias)**
- Bias mitigation and inclusive language improvements
- Safety enhancement and toxicity prevention measures
- Ethical guideline implementation and harm prevention
- Demographic neutrality and cultural sensitivity

**2. HIGH PRIORITY SUGGESTIONS (Quality & Alignment)**
- Task clarity and objective specification improvements
- User requirement alignment enhancements
- Output format and structure optimizations
- Constraint definition and boundary setting

**3. MEDIUM PRIORITY SUGGESTIONS (Effectiveness)**
- Example provision and illustration improvements
- Context integration and domain knowledge enhancement
- Error handling and edge case consideration
- Performance optimization and efficiency gains

**SUGGESTION QUALITY STANDARDS:**
- Specific and actionable (not vague advice)
- Implementable within prompt constraints
- Measurably beneficial for quality or safety
- Compatible with existing prompt structure
- Prioritized by impact and importance

Generate 5-8 targeted suggestions with clear implementation guidance.

Return suggestions as JSON:
{{
    "suggestions": [
        {{
            "category": "critical|high|medium|enhancement",
            "title": "Specific improvement title",
            "description": "Detailed description of the improvement",
            "implementation": "Concrete steps for implementation",
            "impact": "Expected benefits and outcomes",
            "priority_score": <1-10 importance rating>
        }}
    ],
    "priorityBreakdown": {{
        "critical": <count>,
        "high": <count>,
        "medium": <count>,
        "enhancement": <count>
    }},
    "overallRecommendation": "High-level guidance for improvement approach..."
}}"""
            },
            
            "optimize_prompt_with_context": {
                "description": "Context-aware optimization with comprehensive quality enhancement",
                "version": "2.1",
                "dspy_compatible": True,
                "deepeval_optimized": True,
                "context_aware": True,
                "template": """You are an expert RAG prompt optimization specialist. Optimize the given prompt using provided context and examples while ensuring comprehensive quality, safety, and faithfulness improvements.

**ORIGINAL PROMPT:**
{prompt}

**KNOWLEDGE BASE CONTENT:**
{retrievedContent}

**GROUND TRUTH EXAMPLES:**
{groundTruths}

{optimizationFocus}

**COMPREHENSIVE OPTIMIZATION FRAMEWORK:**

**1. CONTEXT INTEGRATION OPTIMIZATION**
- **Faithfulness Enhancement**: Ensure strict adherence to knowledge base content
- **Information Synthesis**: Integrate relevant context seamlessly
- **Accuracy Preservation**: Prevent hallucination and information fabrication
- **Source Grounding**: Maintain clear connection to provided content

**2. DOMAIN-SPECIFIC ENHANCEMENT**
- **Terminology Alignment**: Adapt language to domain standards
- **Best Practice Integration**: Incorporate industry-specific guidelines
- **Example Utilization**: Leverage ground truth patterns effectively
- **Consistency Assurance**: Align with provided examples and standards

**3. SAFETY & BIAS OPTIMIZATION**
- **Context Bias Review**: Identify and mitigate contextual bias sources
- **Inclusive Integration**: Ensure diverse representation in context usage
- **Safety Validation**: Verify context doesn't introduce safety risks
- **Ethical Consideration**: Maintain ethical standards in context application

**4. QUALITY & PERFORMANCE ENHANCEMENT**
- **Clarity Optimization**: Improve instruction precision and specificity
- **Structure Enhancement**: Organize content for optimal comprehension
- **Completeness Assurance**: Address all relevant aspects comprehensively
- **Efficiency Optimization**: Streamline for effective performance

**CONTEXT-AWARE ENHANCEMENT PRIORITIES:**
1. **Faithfulness**: Strict adherence to provided information
2. **Safety**: Bias mitigation and toxicity prevention
3. **Quality**: Clarity, structure, and effectiveness
4. **Domain Alignment**: Terminology and best practices
5. **Robustness**: Edge case and error handling

Create an optimized prompt that leverages context effectively while maintaining the highest standards for quality, safety, and faithfulness.

Return optimization as JSON:
{{
    "optimizedPrompt": "Comprehensively optimized prompt with context integration...",
    "reasoning": "Detailed explanation of optimization strategy and changes made...",
    "contextIntegration": {{
        "faithfulness_enhancements": ["specific faithfulness improvements"],
        "domain_adaptations": ["domain-specific optimizations"],
        "safety_considerations": ["safety and bias improvements"],
        "quality_improvements": ["clarity and effectiveness enhancements"]
    }},
    "optimizationMetrics": {{
        "faithfulness_improvement": "expected improvement level",
        "safety_enhancement": "safety upgrade assessment",
        "quality_upgrade": "quality improvement prediction",
        "context_utilization": "context integration effectiveness"
    }}
}}"""
            }
        }
        
        # Save default templates if they don't exist
        for template_name, template_data in default_templates.items():
            template_path = self.templates_dir / f"{template_name}.json"
            if not template_path.exists():
                self.save_template(template_name, template_data)
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name"""
        if template_name in self.templates:
            return self.templates[template_name]
        else:
            logger.warning(f"Template not found: {template_name}")
            return None
    
    def render_template(self, template_name: str, **kwargs) -> Optional[str]:
        """Render template with enhanced context awareness and optimization selection"""
        # Generate context signature for optimization selection
        context_signature = self._generate_context_signature(template_name, **kwargs)
        
        # Select best available template version
        template_text = self._select_optimal_template(template_name, context_signature, **kwargs)
        
        if not template_text:
            return None
        
        # Track usage with context
        self._track_template_usage(template_name, context_signature)
        
        # Render template with context-aware enhancements
        try:
            rendered = self._enhanced_template_render(template_text, **kwargs)
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
    
    def _select_optimal_template(self, template_name: str, context_signature: str, **kwargs) -> Optional[str]:
        """Select the optimal template version based on context and optimization history"""
        # Priority order: DeepEval optimized -> DSPy optimized -> Base template
        
        # Check for context-specific DeepEval optimization
        deepeval_template = self._get_deepeval_optimized_template(template_name, context_signature)
        if deepeval_template:
            return deepeval_template
        
        # Check for context-specific DSPy optimization
        dspy_template = self._get_dspy_optimized_template(template_name, context_signature)
        if dspy_template:
            return dspy_template
        
        # Fall back to base template
        base_template = self.get_template(template_name)
        return base_template.get('template') if base_template else None
    
    def _generate_context_signature(self, template_name: str, **kwargs) -> str:
        """Generate enhanced context signature for optimization selection"""
        context_elements = []
        
        # Key context indicators
        if 'userNeeds' in kwargs:
            context_elements.append(f"needs:{len(kwargs['userNeeds'].split())}")
        if 'retrievedContent' in kwargs and kwargs['retrievedContent']:
            context_elements.append("context:available")
        if 'groundTruths' in kwargs and kwargs['groundTruths']:
            context_elements.append("examples:available")
        if 'userComments' in kwargs and kwargs['userComments']:
            context_elements.append("feedback:available")
        
        # Generate signature hash
        context_string = f"{template_name}:{':'.join(sorted(context_elements))}"
        return hashlib.md5(context_string.encode()).hexdigest()[:8]
    
    def _enhanced_template_render(self, template_text: str, **kwargs) -> str:
        """Enhanced template rendering with context-aware variable handling"""
        # Add default values for optional context variables
        enhanced_kwargs = kwargs.copy()
        
        # Provide defaults for common optional variables
        defaults = {
            'deepevalContext': '',
            'deepevalInsights': '',
            'targetedContext': '',
            'optimizationFocus': '',
            'retrievedContentSection': '',
            'groundTruthsSection': '',
            'faithfulnessSection': '',
            'userCommentsSection': ''
        }
        
        for key, default_value in defaults.items():
            if key not in enhanced_kwargs:
                enhanced_kwargs[key] = default_value
        
        return template_text.format(**enhanced_kwargs)
    
    def _get_deepeval_optimized_template(self, template_name: str, context_signature: str) -> Optional[str]:
        """Get DeepEval-optimized template with enhanced selection logic"""
        if template_name not in self.deepeval_optimized_templates:
            return None
        
        optimizations = self.deepeval_optimized_templates[template_name]
        
        # Look for exact context match first
        if context_signature in optimizations:
            opt_data = optimizations[context_signature]
            self._update_optimization_usage(template_name, "deepeval", context_signature)
            return opt_data["template"]
        
        # Look for general optimization
        if "general" in optimizations:
            opt_data = optimizations["general"]
            self._update_optimization_usage(template_name, "deepeval", "general")
            return opt_data["template"]
        
        return None
    
    def _get_dspy_optimized_template(self, template_name: str, context_signature: str) -> Optional[str]:
        """Get DSPy-optimized template with enhanced selection logic"""
        if template_name not in self.dspy_optimized_templates:
            return None
        
        optimizations = self.dspy_optimized_templates[template_name]
        
        # Similar logic to DeepEval but for DSPy optimizations
        if context_signature in optimizations:
            opt_data = optimizations[context_signature]
            self._update_optimization_usage(template_name, "dspy", context_signature)
            return opt_data["template"]
        
        if "general" in optimizations:
            opt_data = optimizations["general"]
            self._update_optimization_usage(template_name, "dspy", "general")
            return opt_data["template"]
        
        return None
    
    def _update_optimization_usage(self, template_name: str, optimization_type: str, context_key: str):
        """Update optimization usage statistics"""
        optimization_store = (
            self.deepeval_optimized_templates if optimization_type == "deepeval" 
            else self.dspy_optimized_templates
        )
        
        if template_name in optimization_store and context_key in optimization_store[template_name]:
            opt_data = optimization_store[template_name][context_key]
            opt_data["usage_count"] = opt_data.get("usage_count", 0) + 1
            opt_data["last_used"] = time.time()
    
    def _track_template_usage(self, template_name: str, context_signature: str):
        """Enhanced template usage tracking with context awareness"""
        if template_name not in self.template_usage:
            self._initialize_template_tracking(template_name)
        
        usage_data = self.template_usage[template_name]
        usage_data["usage_count"] += 1
        usage_data["last_used"] = time.time()
        
        # Track context usage patterns
        if context_signature not in usage_data["context_usage"]:
            usage_data["context_usage"][context_signature] = 0
        usage_data["context_usage"][context_signature] += 1
        
        # Update global context patterns
        if context_signature not in self.context_patterns:
            self.context_patterns[context_signature] = {"count": 0, "templates": set()}
        self.context_patterns[context_signature]["count"] += 1
        self.context_patterns[context_signature]["templates"].add(template_name)
    
    def _record_template_success(self, template_name: str):
        """Record successful template rendering with enhanced metrics"""
        if template_name in self.template_usage:
            usage_data = self.template_usage[template_name]
            current_rate = usage_data["success_rate"]
            total_uses = usage_data["usage_count"]
            
            # Update success rate using moving average
            new_rate = (current_rate * (total_uses - 1) + 1.0) / total_uses
            usage_data["success_rate"] = new_rate
    
    def _record_template_failure(self, template_name: str):
        """Record failed template rendering with enhanced metrics"""
        if template_name in self.template_usage:
            usage_data = self.template_usage[template_name]
            current_rate = usage_data["success_rate"]
            total_uses = usage_data["usage_count"]
            
            # Update success rate
            new_rate = (current_rate * (total_uses - 1) + 0.0) / total_uses
            usage_data["success_rate"] = new_rate
    
    def save_deepeval_optimized_template(self, template_name: str, optimized_template: str,
                                       context: Optional[Dict[str, Any]] = None,
                                       deepeval_metrics: Optional[Dict[str, float]] = None,
                                       optimization_notes: Optional[str] = None):
        """Save DeepEval-optimized template with enhanced metadata"""
        if template_name not in self.deepeval_optimized_templates:
            self.deepeval_optimized_templates[template_name] = {}
        
        context_key = "general"
        if context:
            context_key = self._generate_context_signature(template_name, **context)
        
        self.deepeval_optimized_templates[template_name][context_key] = {
            "template": optimized_template,
            "created_at": time.time(),
            "context": context or {},
            "deepeval_metrics": deepeval_metrics or {},
            "optimization_notes": optimization_notes or "",
            "usage_count": 0,
            "last_used": None,
            "performance_history": [],
            "version": "2.1"
        }
        
        self._save_deepeval_optimizations()
        logger.info(f"Saved DeepEval optimization for template {template_name} with context {context_key}")
    
    def save_dspy_optimized_template(self, template_name: str, optimized_template: str, 
                                   context: Optional[Dict[str, Any]] = None, 
                                   performance_metrics: Optional[Dict[str, float]] = None):
        """Save DSPy-optimized template with enhanced metadata"""
        if template_name not in self.dspy_optimized_templates:
            self.dspy_optimized_templates[template_name] = {}
        
        context_key = "general"
        if context:
            context_key = self._generate_context_signature(template_name, **context)
        
        self.dspy_optimized_templates[template_name][context_key] = {
            "template": optimized_template,
            "created_at": time.time(),
            "context": context or {},
            "performance_metrics": performance_metrics or {},
            "usage_count": 0,
            "last_used": None,
            "performance_history": [],
            "version": "2.1"
        }
        
        self._save_dspy_optimizations()
        logger.info(f"Saved DSPy optimization for template {template_name} with context {context_key}")
    
    def record_template_deepeval_score(self, template_name: str, metric_name: str, score: float, context_info: Optional[Dict[str, Any]] = None):
        """Record DeepEval score with enhanced context tracking"""
        if template_name in self.template_usage:
            usage_data = self.template_usage[template_name]
            if metric_name in usage_data["deepeval_scores"]:
                score_entry = {
                    "score": score,
                    "timestamp": time.time(),
                    "context": context_info or {}
                }
                usage_data["deepeval_scores"][metric_name].append(score_entry)
                
                # Keep only recent scores (last 100)
                if len(usage_data["deepeval_scores"][metric_name]) > 100:
                    usage_data["deepeval_scores"][metric_name] = usage_data["deepeval_scores"][metric_name][-100:]
    
    def get_template_deepeval_summary(self, template_name: str) -> Dict[str, Any]:
        """Get comprehensive DeepEval performance summary for a template"""
        if template_name not in self.template_usage:
            return {"error": "Template not found"}
        
        usage_data = self.template_usage[template_name]
        deepeval_scores = usage_data["deepeval_scores"]
        
        summary = {
            "template_name": template_name,
            "metrics_summary": {},
            "optimization_recommendations": [],
            "performance_trends": {},
            "quality_assessment": {}
        }
        
        # Analyze each metric
        for metric, scores in deepeval_scores.items():
            if scores:
                score_values = [s["score"] for s in scores]
                
                summary["metrics_summary"][metric] = {
                    "average": sum(score_values) / len(score_values),
                    "latest": score_values[-1],
                    "best": max(score_values) if metric not in ["bias", "toxicity"] else min(score_values),
                    "worst": min(score_values) if metric not in ["bias", "toxicity"] else max(score_values),
                    "count": len(score_values),
                    "trend": self._calculate_score_trend(scores)
                }
                
                # Generate specific recommendations based on scores
                avg_score = summary["metrics_summary"][metric]["average"]
                if metric == "bias" and avg_score > 0.3:
                    summary["optimization_recommendations"].append(f"High bias detected ({avg_score:.2f}) - implement bias mitigation")
                elif metric == "toxicity" and avg_score > 0.2:
                    summary["optimization_recommendations"].append(f"Toxicity risk present ({avg_score:.2f}) - strengthen safety measures")
                elif metric in ["relevance", "coherence", "faithfulness"] and avg_score < 0.7:
                    summary["optimization_recommendations"].append(f"Low {metric} score ({avg_score:.2f}) - optimize for better {metric}")
        
        return summary
    
    def _calculate_score_trend(self, scores: List[Dict[str, Any]]) -> str:
        """Calculate trend for a metric score series"""
        if len(scores) < 3:
            return "insufficient_data"
        
        recent_scores = [s["score"] for s in scores[-5:]]
        older_scores = [s["score"] for s in scores[-10:-5]] if len(scores) >= 10 else [s["score"] for s in scores[:-5]]
        
        if not older_scores:
            return "insufficient_data"
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)
        
        if recent_avg > older_avg + 0.05:
            return "improving"
        elif recent_avg < older_avg - 0.05:
            return "declining"
        else:
            return "stable"
    
    def get_template_analytics(self) -> Dict[str, Any]:
        """Get comprehensive template usage analytics with enhanced insights"""
        analytics = {
            "template_usage": self.template_usage,
            "optimization_analytics": {
                "dspy_optimizations": {
                    name: {
                        "count": len(optimizations),
                        "contexts": list(optimizations.keys()),
                        "total_usage": sum(opt.get("usage_count", 0) for opt in optimizations.values())
                    }
                    for name, optimizations in self.dspy_optimized_templates.items()
                },
                "deepeval_optimizations": {
                    name: {
                        "count": len(optimizations),
                        "contexts": list(optimizations.keys()),
                        "total_usage": sum(opt.get("usage_count", 0) for opt in optimizations.values())
                    }
                    for name, optimizations in self.deepeval_optimized_templates.items()
                }
            },
            "context_analytics": self._analyze_context_patterns_global(),
            "total_templates": len(self.templates),
            "quality_summary": self._generate_enhanced_quality_summary()
        }
        
        return analytics
    
    def _analyze_context_patterns_global(self) -> Dict[str, Any]:
        """Analyze context usage patterns across all templates"""
        context_analysis = {
            "total_patterns": len(self.context_patterns),
            "most_common": [],
            "template_diversity": {}
        }
        
        # Sort patterns by usage frequency
        sorted_patterns = sorted(
            self.context_patterns.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        # Top 10 most common patterns
        context_analysis["most_common"] = [
            {
                "pattern": pattern,
                "count": data["count"],
                "templates": list(data["templates"])
            }
            for pattern, data in sorted_patterns[:10]
        ]
        
        return context_analysis
    
    def _generate_enhanced_quality_summary(self) -> Dict[str, Any]:
        """Generate enhanced quality summary across all templates"""
        quality_summary = {
            "templates_with_deepeval_data": 0,
            "average_scores": {},
            "quality_distribution": {"excellent": 0, "good": 0, "moderate": 0, "poor": 0, "unknown": 0},
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
                        recent_scores = [s["score"] for s in scores[-10:]]
                        avg_score = sum(recent_scores) / len(recent_scores)
                        metric_totals[metric].append(avg_score)
                
                # Determine quality category
                template_summary = self.get_template_deepeval_summary(template_name)
                overall_scores = [s["score"] for s in deepeval_scores.get("overall", [])]
                if overall_scores:
                    avg_overall = sum(overall_scores[-5:]) / len(overall_scores[-5:])
                    if avg_overall >= 0.8:
                        quality_summary["quality_distribution"]["excellent"] += 1
                    elif avg_overall >= 0.6:
                        quality_summary["quality_distribution"]["good"] += 1
                    elif avg_overall >= 0.4:
                        quality_summary["quality_distribution"]["moderate"] += 1
                    else:
                        quality_summary["quality_distribution"]["poor"] += 1
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
        self._load_optimizations()
        self._create_enhanced_default_templates()
        
    def save_template(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """Save a template to disk"""
        try:
            template_path = self.templates_dir / f"{template_name}.json"
            with open(template_path, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Update in-memory cache
            self.templates[template_name] = template_data
            
            # Initialize usage tracking if new template
            if template_name not in self.template_usage:
                self._initialize_template_tracking(template_name)
            
            logger.info(f"Saved template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template {template_name}: {str(e)}")
            return False
    
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
    
    def _save_dspy_optimizations(self):
        """Save DSPy optimizations to disk"""
        try:
            optimizations_file = self.templates_dir / "dspy_optimizations.json"
            with open(optimizations_file, 'w') as f:
                json.dump(self.dspy_optimized_templates, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving DSPy optimizations: {str(e)}")
    
    def _save_deepeval_optimizations(self):
        """Save DeepEval optimizations to disk"""
        try:
            optimizations_file = self.templates_dir / "deepeval_optimizations.json"
            with open(optimizations_file, 'w') as f:
                json.dump(self.deepeval_optimized_templates, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving DeepEval optimizations: {str(e)}")
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available templates with comprehensive metadata"""
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
        """Suggest templates that would benefit from optimization with enhanced DeepEval insights"""
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