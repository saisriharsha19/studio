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

const optimizePromptWithContextFlow = ai.defineFlow(
  {
    name: 'optimizePromptWithContextFlow',
    inputSchema: OptimizePromptWithContextInputSchema,
    outputSchema: OptimizePromptWithContextOutputSchema,
  },
  async (input) => {
    const fullPrompt = `You are an AI prompt optimizer. Analyze the retrieved content and ground truths to refine the given prompt, ensuring it aligns with the contextual information and improves the accuracy and relevance of the assistant's responses.

Original Prompt: ${input.prompt}

Retrieved Content: ${input.retrievedContent}

Ground Truths: ${input.groundTruths}

Based on the retrieved content and ground truths, provide an optimized prompt and explain your reasoning for the changes.

Respond with a single, valid JSON object with two keys: "optimizedPrompt" (the new prompt) and "reasoning" (your explanation). Do not include any extra commentary or markdown formatting.`;
    
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL;
    if (!pythonBackendUrl) {
      throw new Error('PYTHON_BACKEND_URL is not configured.');
    }

    const response = await fetch(`${pythonBackendUrl}/optimize-prompt-with-context`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: fullPrompt }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request to Python backend failed: ${response.statusText} - ${errorText}`);
    }

    const content = await response.json();

    try {
        return OptimizePromptWithContextOutputSchema.parse(content);
    } catch (e: any) {
        console.error("Failed to parse response from Python backend:", e, "Raw content:", content);
        throw new Error(`Failed to parse response from Python backend as JSON: ${e.message}`);
    }
  }
);
