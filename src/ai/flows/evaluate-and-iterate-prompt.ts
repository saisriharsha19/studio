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
    .describe('Retrieved content from web scraped data to refine and optimize prompts.'),
  groundTruths: z
    .string()
    .describe('Ground truths discovered from the retrieved content to validate the prompt.'),
});
export type EvaluateAndIteratePromptInput = z.infer<typeof EvaluateAndIteratePromptInputSchema>;

const EvaluateAndIteratePromptOutputSchema = z.object({
  improvedPrompt: z.string().describe('The improved prompt after evaluation and iteration.'),
  relevancyScore: z.number().describe('The relevancy score of the improved prompt (0-1).'),
  evaluationSummary: z
    .string()
    .describe('A summary of the evaluation process and improvements made.'),
});
export type EvaluateAndIteratePromptOutput = z.infer<typeof EvaluateAndIteratePromptOutputSchema>;

export async function evaluateAndIteratePrompt(input: EvaluateAndIteratePromptInput): Promise<
  EvaluateAndIteratePromptOutput
> {
  return evaluateAndIteratePromptFlow(input);
}

const prompt = ai.definePrompt({
  name: 'evaluateAndIteratePromptPrompt',
  input: {schema: EvaluateAndIteratePromptInputSchema},
  output: {schema: EvaluateAndIteratePromptOutputSchema},
  prompt: `You are an AI expert in prompt engineering. Your task is to evaluate and iterate on an existing prompt based on user needs, retrieved content, and ground truths.

Existing Prompt: {{{prompt}}}
User Needs: {{{userNeeds}}}
Retrieved Content: {{{retrievedContent}}}
Ground Truths: {{{groundTruths}}}

Evaluate the prompt for relevancy and effectiveness in addressing the user needs, considering the retrieved content and ground truths. Provide a relevancy score between 0 and 1. Iterate on the prompt to improve its performance. Provide a summary of the evaluation process and improvements made.

Output:
Improved Prompt: 
Relevancy Score: 
Evaluation Summary:`,
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
