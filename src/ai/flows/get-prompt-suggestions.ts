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

const generatePromptSuggestionsFlow = ai.defineFlow(
  {
    name: 'generatePromptSuggestionsFlow',
    inputSchema: GeneratePromptSuggestionsInputSchema,
    outputSchema: GeneratePromptSuggestionsOutputSchema,
  },
  async (input) => {
    let fullPrompt = `You are an AI assistant that helps users refine system prompts. The user will provide their current prompt and optionally some comments on how they want to improve it.

Your task is to analyze the current prompt and provide a list of up to 5 concrete, actionable suggestions for how the prompt could be improved.
- Each suggestion must be concise and under 15 words.
- If user comments are provided, use them to guide your suggestions. If not, provide general improvement suggestions based on prompt engineering best practices.
- Do not generate a new prompt, only provide suggestions.

Current Prompt:
${input.currentPrompt}
`;
    if (input.userComments) {
        fullPrompt += `
User Comments:
"${input.userComments}"
`;
    }

    fullPrompt += `
Now, provide your suggestions based on the above.

Respond with a JSON object of the format: { "suggestions": ["suggestion 1", "suggestion 2", ...] }`;

    const response = await fetch(`${process.env.UFL_AI_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.UFL_AI_API_KEY}`,
        },
        body: JSON.stringify({
            model: 'gpt-4o',
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
        const parsedContent = JSON.parse(content);
        return GeneratePromptSuggestionsOutputSchema.parse(parsedContent);
    } catch (e) {
        console.error("Failed to parse LLM response:", e, "Raw content:", content);
        throw new Error("Failed to parse LLM response as JSON.");
    }
  }
);
