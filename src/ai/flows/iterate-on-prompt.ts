'use server';

/**
 * @fileOverview A flow to iterate and refine a prompt based on user feedback and selected AI suggestions.
 *
 * - iterateOnPrompt - A function that generates a new, improved prompt.
 * - IterateOnPromptInput - The input type for the iterateOnPrompt function.
 * - IterateOnPromptOutput - The return type for the iterateOnPrompt function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const IterateOnPromptInputSchema = z.object({
  currentPrompt: z.string().describe('The current system prompt to be improved.'),
  userComments: z.string().describe('User feedback and comments on what to change.'),
  selectedSuggestions: z
    .array(z.string())
    .describe('A list of AI-generated suggestions that the user has selected to apply.'),
});
export type IterateOnPromptInput = z.infer<typeof IterateOnPromptInputSchema>;

const IterateOnPromptOutputSchema = z.object({
  newPrompt: z.string().describe('The newly generated, refined system prompt.'),
});
export type IterateOnPromptOutput = z.infer<typeof IterateOnPromptOutputSchema>;

export async function iterateOnPrompt(
  input: IterateOnPromptInput
): Promise<IterateOnPromptOutput> {
  return iterateOnPromptFlow(input);
}

const prompt = ai.definePrompt({
  name: 'iterateOnPromptPrompt',
  input: {schema: IterateOnPromptInputSchema},
  output: {schema: IterateOnPromptOutputSchema},
  prompt: `You are an AI assistant that helps users refine system prompts. The user will provide their current prompt, some manual comments, and a list of AI-generated suggestions they have selected.

Your task is to generate a new, refined system prompt that incorporates the user's manual feedback and the selected suggestions.

Current Prompt:
{{{currentPrompt}}}

User's Manual Comments:
"{{{userComments}}}"

User's Selected AI Suggestions to Apply:
{{#each selectedSuggestions}}
- {{{this}}}
{{/each}}

Generate the new, improved system prompt.`,
});

const iterateOnPromptFlow = ai.defineFlow(
  {
    name: 'iterateOnPromptFlow',
    inputSchema: IterateOnPromptInputSchema,
    outputSchema: IterateOnPromptOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
