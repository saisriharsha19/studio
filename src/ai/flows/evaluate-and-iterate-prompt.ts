
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
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL;
    if (!pythonBackendUrl) {
      throw new Error('PYTHON_BACKEND_URL is not configured.');
    }

    // The large system prompt is now stored on the Python backend.
    // We only send the dynamic data.
    const payload = {
      prompt: input.prompt,
      userNeeds: input.userNeeds,
      retrievedContent: input.retrievedContent,
      groundTruths: input.groundTruths,
    };

    const response = await fetch(`${pythonBackendUrl}/evaluate-and-iterate-prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request to Python backend failed: ${response.statusText} - ${errorText}`);
    }

    const content = await response.json();

    try {
        return EvaluateAndIteratePromptOutputSchema.parse(content);
    } catch (e: any) {
        console.error("Failed to parse response from Python backend:", e, "Raw content:", content);
        throw new Error(`Failed to parse response from Python backend as JSON: ${e.message}`);
    }
  }
);
