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
    
    const response = await fetch(`${process.env.UFL_AI_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.UFL_AI_API_KEY}`,
        },
        body: JSON.stringify({
            model: 'llama-3.1-70b-instruct',
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
        // The model can sometimes wrap the JSON in markdown. Find the first '{' and last '}' to extract the JSON.
        const jsonMatch = content.match(/{[\s\S]*}/);
        if (!jsonMatch) {
          throw new Error('No JSON object found in the response.');
        }
        const jsonString = jsonMatch[0];
        const parsedContent = JSON.parse(jsonString);
        return OptimizePromptWithContextOutputSchema.parse(parsedContent);
    } catch (e: any) {
        console.error("Failed to parse LLM response:", e, "Raw content:", content);
        throw new Error(`Failed to parse LLM response as JSON: ${e.message}`);
    }
  }
);
