
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
  universityCode: z.string().describe('The code for the university.'),
  userId: z.string().describe('The ID of the user.'),
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

const iterateOnPromptFlow = ai.defineFlow(
  {
    name: 'iterateOnPromptFlow',
    inputSchema: IterateOnPromptInputSchema,
    outputSchema: IterateOnPromptOutputSchema,
  },
  async (input) => {
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL;
    if (!pythonBackendUrl) {
      throw new Error('PYTHON_BACKEND_URL is not configured.');
    }

    const payload = {
        currentPrompt: input.currentPrompt,
        userComments: input.userComments,
        selectedSuggestions: input.selectedSuggestions,
        universityCode: input.universityCode,
        userId: input.userId,
    };

    const response = await fetch(`${pythonBackendUrl}/iterate-on-prompt`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request to Python backend failed: ${response.statusText} - ${errorText}`);
    }

    const content = await response.json();

    try {
        return IterateOnPromptOutputSchema.parse(content);
    } catch (e: any) {
        console.error("Failed to parse response from Python backend:", e, "Raw content:", content);
        throw new Error(`Failed to parse response from Python backend as JSON: ${e.message}`);
    }
  }
);
