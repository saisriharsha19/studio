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

const iterateOnPromptFlow = ai.defineFlow(
  {
    name: 'iterateOnPromptFlow',
    inputSchema: IterateOnPromptInputSchema,
    outputSchema: IterateOnPromptOutputSchema,
  },
  async (input) => {
    const suggestionsText = input.selectedSuggestions.map(s => `- ${s}`).join('\n');
    const fullPrompt = `You are an AI assistant that helps users refine system prompts. The user will provide their current prompt, some manual comments, and a list of AI-generated suggestions they have selected.

Your task is to generate a new, refined system prompt that incorporates the user's manual feedback and the selected suggestions.

Current Prompt:
${input.currentPrompt}

User's Manual Comments:
"${input.userComments}"

User's Selected AI Suggestions to Apply:
${suggestionsText}

Generate the new, improved system prompt.

Respond with a single, valid JSON object containing one key: "newPrompt". The value should be the newly generated, refined system prompt as a string. Do not include any extra commentary or markdown formatting.`;

    const response = await fetch(`${process.env.UFL_AI_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.UFL_AI_API_KEY}`,
        },
        body: JSON.stringify({
            model: 'llama-3.3-70b-instruct',
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
        return IterateOnPromptOutputSchema.parse(parsedContent);
    } catch (e: any) {
        console.error("Failed to parse LLM response:", e, "Raw content:", content);
        throw new Error(`Failed to parse LLM response as JSON: ${e.message}`);
    }
  }
);
