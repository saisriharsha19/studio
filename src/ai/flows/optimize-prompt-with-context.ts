// src/ai/flows/optimize-prompt-with-context.ts
'use server';
/**
 * @fileOverview This file defines a Genkit flow for optimizing prompts based on context.
 *
 * - optimizePromptWithContext - A function that refines prompts using web-scraped data and ground truths.
 * - OptimizePromptWithContextInput - The input type for the optimizePromptWithContext function.
 * - OptimizePromptWithContextOutput - The return type for the optimizePromptWithContext function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const OptimizePromptWithContextInputSchema = z.object({
  prompt: z.string().describe('The prompt to be optimized.'),
  retrievedContent: z
    .string()
    .describe('The content retrieved from web scraping.'),
  groundTruths: z.string().describe('The ground truths extracted from the content.'),
});

export type OptimizePromptWithContextInput = z.infer<
  typeof OptimizePromptWithContextInputSchema
>;

const OptimizePromptWithContextOutputSchema = z.object({
  optimizedPrompt: z.string().describe('The optimized prompt.'),
  reasoning: z
    .string()
    .describe('The reasoning behind the prompt optimization.'),
});

export type OptimizePromptWithContextOutput = z.infer<
  typeof OptimizePromptWithContextOutputSchema
>;

export async function optimizePromptWithContext(
  input: OptimizePromptWithContextInput
): Promise<OptimizePromptWithContextOutput> {
  return optimizePromptWithContextFlow(input);
}

const prompt = ai.definePrompt({
  name: 'optimizePromptWithContextPrompt',
  input: {schema: OptimizePromptWithContextInputSchema},
  output: {schema: OptimizePromptWithContextOutputSchema},
  prompt: `You are an AI prompt optimizer. Analyze the retrieved content and ground truths to refine the given prompt, ensuring it aligns with the contextual information and improves the accuracy and relevance of the assistant's responses.\n\nOriginal Prompt: {{{prompt}}}\n\nRetrieved Content: {{{retrievedContent}}}\n\nGround Truths: {{{groundTruths}}}\n\nBased on the retrieved content and ground truths, provide an optimized prompt and explain your reasoning for the changes.\n\nOptimized Prompt: \nReasoning: `,
});

const optimizePromptWithContextFlow = ai.defineFlow(
  {
    name: 'optimizePromptWithContextFlow',
    inputSchema: OptimizePromptWithContextInputSchema,
    outputSchema: OptimizePromptWithContextOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
