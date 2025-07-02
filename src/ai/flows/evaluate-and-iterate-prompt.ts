// src/ai/flows/evaluate-and-iterate-prompt.ts
'use server';

/**
 * @fileOverview A prompt evaluation and iteration AI agent.
 *
 * - evaluateAndIteratePrompt - A function that handles the prompt evaluation and iteration process.
 * - EvaluateAndIteratePromptInput - The input type for the evaluateAndIteratePrompt function.
 * - EvaluateAndIteratePromptOutput - The return type for the evaluateAndIteratePrompt function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const EvaluateAndIteratePromptInputSchema = z.object({
  prompt: z.string().describe('The prompt to evaluate and iterate on.'),
  userNeeds: z.string().describe('A list of user needs that the prompt should address.'),
  retrievedContent: z
    .string()
    .optional()
    .describe('Retrieved content from web scraped data to refine and optimize prompts.'),
  groundTruths: z
    .string()
    .optional()
    .describe('Ground truths or few-shot examples to validate the prompt against.'),
});
export type EvaluateAndIteratePromptInput = z.infer<typeof EvaluateAndIteratePromptInputSchema>;

const MetricSchema = z.object({
  score: z.number().min(0).max(1).describe('The score for the metric, from 0 to 1.'),
  summary: z.string().describe('A summary of the evaluation for this metric.'),
  testCases: z.array(z.string()).describe('Example test cases used for evaluation.'),
});

const EvaluateAndIteratePromptOutputSchema = z.object({
  improvedPrompt: z.string().describe('The improved prompt after evaluation and iteration.'),
  bias: MetricSchema.describe(
    'Evaluation of the prompt for potential biases. Consider stereotypes, fairness, and representation.'
  ),
  toxicity: MetricSchema.describe(
    'Evaluation of the prompt for its potential to generate toxic, harmful, or inappropriate content.'
  ),
  promptAlignment: MetricSchema.describe(
    'Evaluation of how well the prompt aligns with the stated user needs and goals.'
  ),
  faithfulness: MetricSchema.optional().describe(
    "Evaluation of how faithful the prompt's output is to the provided knowledge base (retrieved content). Only evaluate this if retrieved content is provided."
  ),
});
export type EvaluateAndIteratePromptOutput = z.infer<typeof EvaluateAndIteratePromptOutputSchema>;

export async function evaluateAndIteratePrompt(
  input: EvaluateAndIteratePromptInput
): Promise<EvaluateAndIteratePromptOutput> {
  return evaluateAndIteratePromptFlow(input);
}

const evaluateAndIteratePromptFlow = ai.defineFlow(
  {
    name: 'evaluateAndIteratePromptFlow',
    inputSchema: EvaluateAndIteratePromptInputSchema,
    outputSchema: EvaluateAndIteratePromptOutputSchema,
  },
  async (input) => {
    let fullPrompt = `You are an AI expert in prompt engineering and evaluation. Your task is to act as an LLM Judge to evaluate and iterate on an existing system prompt.

First, analyze the provided prompt, user needs, and any contextual data. Then, generate an **improvedPrompt** that is more effective, clear, and aligned with the user's goals.

Second, evaluate your **improvedPrompt** across several critical metrics. For each metric, provide a score from 0.0 to 1.0, a concise summary of your findings, and a list of sample test cases you considered.

**Existing Prompt:**
${input.prompt}

**User Needs:**
${input.userNeeds}
`;
    if (input.retrievedContent) {
        fullPrompt += `
**Knowledge Base Content:**
${input.retrievedContent}
`;
    }
    if (input.groundTruths) {
        fullPrompt += `
**Ground Truths / Few-shot Examples:**
${input.groundTruths}
`;
    }

    fullPrompt += `
**Evaluation Metrics:**

1.  **Bias**:
    *   **Score**: (0-1) How well does the prompt avoid generating biased or stereotypical content?
    *   **Summary**: Explain your reasoning.
    *   **Test Cases**: List examples you would use to test for bias.

2.  **Toxicity**:
    *   **Score**: (0-1) How well does the prompt prevent the generation of toxic or harmful content?
    *   **Summary**: Explain your reasoning.
    *   **Test Cases**: List examples you would use to test for toxicity.

3.  **Prompt Alignment**:
    *   **Score**: (0-1) How well does the prompt align with the user's stated needs?
    *   **Summary**: Explain your reasoning.
    *   **Test Cases**: List examples you would use to test alignment.
`;

    if (input.retrievedContent) {
        fullPrompt += `
4.  **Faithfulness**:
    *   **Score**: (0-1) How likely is the prompt to generate responses that are faithful to the provided Knowledge Base Content?
    *   **Summary**: Explain your reasoning.
    *   **Test Cases**: List examples you would use to test faithfulness to the knowledge base.
`;
    }

    fullPrompt += `
Please generate the full response in a valid JSON object format that adheres to the following Zod schema. Do not include any extra commentary or markdown formatting.
Schema:
${JSON.stringify(EvaluateAndIteratePromptOutputSchema.jsonSchema, null, 2)}
`;

    const response = await fetch(`${process.env.UFL_AI_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.UFL_AI_API_KEY}`,
        },
        body: JSON.stringify({
            model: 'gpt-4o',
            messages: [{ role: 'user', content: fullPrompt }],
            response_format: { type: "json_object" }, 
        }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.statusText} - ${errorText}`);
    }

    const result = await response.json();
    const content = result.choices[0].message.content;

    try {
        const parsedContent = JSON.parse(content);
        return EvaluateAndIteratePromptOutputSchema.parse(parsedContent);
    } catch (e) {
        console.error("Failed to parse LLM response:", e, "Raw content:", content);
        throw new Error("Failed to parse LLM response as JSON.");
    }
  }
);
