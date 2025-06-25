'use server';

/**
 * @fileOverview A flow to generate suggestions for improving a prompt.
 *
 * - generatePromptSuggestions - A function that generates suggestions for a prompt.
 * - GeneratePromptSuggestionsInput - The input type for the function.
 * - GeneratePromptSuggestionsOutput - The return type for the function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GeneratePromptSuggestionsInputSchema = z.object({
  currentPrompt: z.string().describe('The current system prompt to be improved.'),
  userComments: z.string().describe('User feedback and comments on what to change.'),
});
export type GeneratePromptSuggestionsInput = z.infer<typeof GeneratePromptSuggestionsInputSchema>;

const GeneratePromptSuggestionsOutputSchema = z.object({
  suggestions: z.array(z.string()).describe('A list of concrete suggestions on how the prompt could be improved.'),
});
export type GeneratePromptSuggestionsOutput = z.infer<typeof GeneratePromptSuggestionsOutputSchema>;

export async function generatePromptSuggestions(
  input: GeneratePromptSuggestionsInput
): Promise<GeneratePromptSuggestionsOutput> {
  return generatePromptSuggestionsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generatePromptSuggestionsPrompt',
  input: {schema: GeneratePromptSuggestionsInputSchema},
  output: {schema: GeneratePromptSuggestionsOutputSchema},
  prompt: `You are an AI assistant that helps users refine system prompts. The user will provide their current prompt and some comments on how they want to improve it.

Your task is to analyze the current prompt and the user's comments and provide a list of concrete, actionable suggestions (blurbs) for how the prompt could be improved to meet the user's goals. Do not generate a new prompt, only provide suggestions.

Current Prompt:
{{{currentPrompt}}}

User Comments:
"{{{userComments}}}"

Based on the comments, provide improvement suggestions.`,
});

const generatePromptSuggestionsFlow = ai.defineFlow(
  {
    name: 'generatePromptSuggestionsFlow',
    inputSchema: GeneratePromptSuggestionsInputSchema,
    outputSchema: GeneratePromptSuggestionsOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
