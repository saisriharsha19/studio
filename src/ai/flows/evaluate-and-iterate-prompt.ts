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

const prompt = ai.definePrompt({
  name: 'evaluateAndIteratePromptPrompt',
  input: {schema: EvaluateAndIteratePromptInputSchema},
  output: {schema: EvaluateAndIteratePromptOutputSchema},
  prompt: `You are an AI expert in prompt engineering and evaluation. Your task is to act as an LLM Judge to evaluate and iterate on an existing system prompt.

First, analyze the provided prompt, user needs, and any contextual data. Then, generate an **improvedPrompt** that is more effective, clear, and aligned with the user's goals.

Second, evaluate your **improvedPrompt** across several critical metrics. For each metric, provide a score from 0.0 to 1.0, a concise summary of your findings, and a list of sample test cases you considered.

**Existing Prompt:**
{{{prompt}}}

**User Needs:**
{{{userNeeds}}}

{{#if retrievedContent}}
**Knowledge Base Content:**
{{{retrievedContent}}}
{{/if}}

{{#if groundTruths}}
**Ground Truths / Few-shot Examples:**
{{{groundTruths}}}
{{/if}}

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

{{#if retrievedContent}}
4.  **Faithfulness**:
    *   **Score**: (0-1) How likely is the prompt to generate responses that are faithful to the provided Knowledge Base Content?
    *   **Summary**: Explain your reasoning.
    *   **Test Cases**: List examples you would use to test faithfulness to the knowledge base.
{{/if}}

Please generate the full response in the required JSON format.
`,
});

const evaluateAndIteratePromptFlow = ai.defineFlow(
  {
    name: 'evaluateAndIteratePromptFlow',
    inputSchema: EvaluateAndIteratePromptInputSchema,
    outputSchema: EvaluateAndIteratePromptOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
