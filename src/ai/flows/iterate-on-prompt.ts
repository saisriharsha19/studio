'use server';

/**
 * @fileOverview A flow to iterate and refine a prompt based on user feedback.
 *
 * - iterateOnPrompt - A function that suggests improvements for a prompt.
 * - IterateOnPromptInput - The input type for the iterateOnPrompt function.
 * - IterateOnPromptOutput - The return type for the iterateOnPrompt function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const IterateOnPromptInputSchema = z.object({
  currentPrompt: z.string().describe('The current system prompt to be improved.'),
  userComments: z.string().describe('User feedback and comments on what to change.'),
});
export type IterateOnPromptInput = z.infer<typeof IterateOnPromptInputSchema>;

const IterateOnPromptOutputSchema = z.object({
  suggestions: z.array(z.string()).describe('A list of suggestions or blurbs on how the prompt could be improved.'),
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
  prompt: `You are an AI assistant that helps users refine system prompts. The user will provide their current prompt and some comments on how they want to improve it.

Your task is to:
1.  Analyze the current prompt and the user's comments.
2.  Provide a list of concrete suggestions (blurbs) for how the prompt could be improved to meet the user's goals.
3.  Generate a new, refined system prompt that incorporates the user's feedback.

Current Prompt:
{{{currentPrompt}}}

User Comments:
"{{{userComments}}}"

Based on the comments, provide improvement suggestions and a new prompt.`,
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
