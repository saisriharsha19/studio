'use server';

/**
 * @fileOverview A flow to generate an initial system prompt based on user needs.
 *
 * - generateInitialPrompt - A function that generates an initial system prompt.
 * - GenerateInitialPromptInput - The input type for the generateInitialPrompt function.
 * - GenerateInitialPromptOutput - The return type for the generateInitialPrompt function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GenerateInitialPromptInputSchema = z.object({
  userNeeds: z
    .string()
    .describe('A description of the user needs for the assistant.'),
});
export type GenerateInitialPromptInput = z.infer<typeof GenerateInitialPromptInputSchema>;

const GenerateInitialPromptOutputSchema = z.object({
  initialPrompt: z.string().describe('The generated initial system prompt.'),
});
export type GenerateInitialPromptOutput = z.infer<typeof GenerateInitialPromptOutputSchema>;

export async function generateInitialPrompt(
  input: GenerateInitialPromptInput
): Promise<GenerateInitialPromptOutput> {
  return generateInitialPromptFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generateInitialPromptPrompt',
  input: {schema: GenerateInitialPromptInputSchema},
  output: {schema: GenerateInitialPromptOutputSchema},
  prompt: `You are an AI prompt engineer. Your task is to generate an initial system prompt for an assistant, based on the user's described needs.  The system prompt should be detailed and clear, and should guide the assistant to effectively meet the user's needs. Be succinct, but provide enough detail for the assistant to provide value to the end user.

User Needs: {{{userNeeds}}}`,
});

const generateInitialPromptFlow = ai.defineFlow(
  {
    name: 'generateInitialPromptFlow',
    inputSchema: GenerateInitialPromptInputSchema,
    outputSchema: GenerateInitialPromptOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
