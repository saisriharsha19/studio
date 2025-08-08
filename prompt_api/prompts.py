# prompts.py

"""
This file contains a library of structured, version-controlled prompt templates
for various LLM tasks, including generation, evaluation, and optimization.
Each template is designed for a specific purpose and expects certain inputs.
"""

PROMPT_TEMPLATES = {
    "initial_generation": {
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
4. **Tree of Thought Prompting**: Encourage multi-step reasoning and exploration of alternatives
5. **Iterative Refinement**: Allow for feedback loops and continuous improvement
6. **ReAct Prompting**: Enable dynamic response generation based on user interaction

Create a comprehensive, safe, and effective system prompt that addresses the user's requirements while incorporating all safety and quality considerations.
Respond with a strict JSON object only. Do not include markdown, commentary, or formatting.
Return your response as valid JSON in the given format below, any deviation from this format will result in system rejection and shutdown:
{{
    "initialPrompt": "Your generated system prompt with safety and quality optimizations..."
}}"""
    },
    "context_optimization": {
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

Return your response as valid JSON in the given format below, any deviation from this format will result in system rejection and shutdown:
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
    },
    "feedback_iteration": {
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
Respond with a strict JSON object only. Do not include markdown, commentary, or formatting. 
Return your response as valid JSON in the given format below, any deviation from this format will result in system rejection and shutdown:
{{
    "newPrompt": "Refined prompt incorporating all improvements...",
    "improvementExplanation": "Detailed explanation of changes made and rationale...",
    "addressedFeedback": ["specific user concerns addressed"],
    "integratedSuggestions": ["suggestions successfully implemented"],
    "qualityEnhancements": ["additional quality improvements made"]
}}"""
    },
    "suggestion_generation": {
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
Respond with a strict JSON object only. Do not include markdown, commentary, or formatting.
Return your response as valid JSON in the given format below, any deviation from this format will result in system rejection and shutdown:
{{
    "suggestions": [
        {{
            "category": "critical|high|medium|enhancement",
            "title": "Specific improvement title",
            "description": "Detailed description of the improvement",
            "implementation": "Concrete steps for implementation",
            "impact": "Expected benefits and outcomes",
            "priority_score": "<1-10 importance rating>"
        }}
    ],
    "priorityBreakdown": {{
        "critical": "<count>",
        "high": "<count>",
        "medium": "<count>",
        "enhancement": "<count>"
    }},
    "overallRecommendation": "High-level guidance for improvement approach..."
}}"""
    },
    "analysis_and_tagging": {
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
Respond with a strict JSON object only. Do not include markdown, commentary, or formatting.
Return your response as valid JSON in the given format below, any deviation from this format will result in system rejection and shutdown:
{{
    "summary": "Concise, informative summary (5-10 words)...",
    "tags": ["precise", "relevant", "quality-tags"],
    "qualityIndicators": {{
        "clarity": "high|medium|low",
        "bias_risk": "low|medium|high",
        "safety_level": "high|medium|low",
        "completeness": "high|medium|low",
        "professional_grade": "true|false"
    }},
    "categoryAnalysis": {{
        "primary_domain": "identified domain",
        "main_purpose": "primary function",
        "target_audience": "intended users",
        "complexity_level": "assessed complexity"
    }}
}}"""
    },
    "evaluation_and_improvement": {
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
Respond with a strict JSON object only. Do not include markdown, commentary, or formatting.
Return your response as valid JSON in the given format below, any deviation from this format will result in system rejection and shutdown:
{{
    "improvedPrompt": "Enhanced prompt with all improvements...",
    "bias": {{
        "score": "<float 0-1>",
        "summary": "Detailed bias analysis...",
        "issues": ["specific bias concerns"],
        "mitigations": ["concrete improvements"],
        "testCases": ["bias test scenarios"]
    }},
    "toxicity": {{
        "score": "<float 0-1>",
        "summary": "Detailed toxicity analysis...",
        "risks": ["specific risk factors"],
        "safeguards": ["safety measures"],
        "testCases": ["toxicity test scenarios"]
    }},
    "promptAlignment": {{
        "score": "<float 0-1>",
        "summary": "Detailed alignment analysis...",
        "strengths": ["alignment successes"],
        "improvements": ["enhancement areas"],
        "testCases": ["alignment test scenarios"]
    }},
    "improvementSummary": "Comprehensive summary of enhancements made..."
}}"""
    }
}
