'use server';

/**
 * @fileOverview A flow to generate a summary and tags for a given prompt.
 *
 * - generatePromptTags - A function that generates metadata.
 * - GeneratePromptMetadataInput - The input type for the function.
 * - GeneratePromptMetadataOutput - The return type for the function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GeneratePromptMetadataInputSchema = z.object({
  promptText: z.string().describe('The prompt text to analyze.'),
});
export type GeneratePromptMetadataInput = z.infer<typeof GeneratePromptMetadataInputSchema>;

const GeneratePromptMetadataOutputSchema = z.object({
  summary: z.string().describe("A brief, one-sentence summary of the prompt's purpose."),
  tags: z.array(z.string()).describe("A list of 2-4 relevant keywords (tags) for searching and filtering. Tags should be lowercase and one or two words max.")
});
export type GeneratePromptMetadataOutput = z.infer<typeof GeneratePromptMetadataOutputSchema>;

// Function name kept for compatibility with actions.ts
export async function generatePromptTags(
  input: GeneratePromptMetadataInput
): Promise<GeneratePromptMetadataOutput> {
  return generatePromptMetadataFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generatePromptMetadataPrompt',
  input: {schema: GeneratePromptMetadataInputSchema},
  output: {schema: GeneratePromptMetadataOutputSchema},
  prompt: `Analyze the following system prompt.
  
Your task is to generate two things:
1.  A brief, one-sentence summary that explains what the prompt is used for.
2.  A list of 2-4 relevant keywords (tags) for searching and filtering. Tags should be lowercase and one or two words at most.

Prompt to analyze:
"{{{promptText}}}"

Return the response in the required JSON format.`,
});

const generatePromptMetadataFlow = ai.defineFlow(
  {
    name: 'generatePromptMetadataFlow',
    inputSchema: GeneratePromptMetadataInputSchema,
    outputSchema: GeneratePromptMetadataOutputSchema,
  },
  async (input) => {
    const { output } = await prompt(input);
    return { 
        summary: output?.summary || 'No summary generated.',
        tags: output?.tags || []
    };
  }
);
