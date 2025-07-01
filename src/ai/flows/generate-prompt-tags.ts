'use server';

/**
 * @fileOverview A flow to generate a summary for a given prompt.
 *
 * - generatePromptTags - A function that generates a summary. (Keeping name for compatibility)
 * - GeneratePromptSummaryInput - The input type for the function.
 * - GeneratePromptSummaryOutput - The return type for the function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GeneratePromptSummaryInputSchema = z.object({
  promptText: z.string().describe('The prompt text to analyze.'),
});
export type GeneratePromptSummaryInput = z.infer<typeof GeneratePromptSummaryInputSchema>;

const GeneratePromptSummaryOutputSchema = z.object({
  summary: z.string().describe("A brief, one-sentence summary of the prompt's purpose."),
});
export type GeneratePromptSummaryOutput = z.infer<typeof GeneratePromptSummaryOutputSchema>;

// Function name kept for compatibility with actions.ts
export async function generatePromptTags(
  input: GeneratePromptSummaryInput
): Promise<GeneratePromptSummaryOutput> {
  return generatePromptSummaryFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generatePromptSummaryPrompt',
  input: {schema: GeneratePromptSummaryInputSchema},
  output: {schema: GeneratePromptSummaryOutputSchema},
  prompt: `Analyze the following system prompt and generate a brief, one-sentence summary that explains what it is used for. This summary will be used as a description for the prompt in a library.

Prompt to analyze:
"{{{promptText}}}"

Return the response in the required JSON format, providing the summary in the 'summary' field.`,
});

const generatePromptSummaryFlow = ai.defineFlow(
  {
    name: 'generatePromptSummaryFlow',
    inputSchema: GeneratePromptSummaryInputSchema,
    outputSchema: GeneratePromptSummaryOutputSchema,
  },
  async (input) => {
    const { output } = await prompt(input);
    return { summary: output?.summary || 'No summary generated.' };
  }
);
