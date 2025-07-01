'use server';

/**
 * @fileOverview A flow to generate tags for a given prompt.
 *
 * - generatePromptTags - A function that generates tags.
 * - GeneratePromptTagsInput - The input type for the function.
 * - GeneratePromptTagsOutput - The return type for the function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GeneratePromptTagsInputSchema = z.object({
  promptText: z.string().describe('The prompt text to analyze.'),
});
export type GeneratePromptTagsInput = z.infer<typeof GeneratePromptTagsInputSchema>;

const GeneratePromptTagsOutputSchema = z.object({
  tags: z.array(z.string()).describe('A list of up to 5 relevant, one-to-two-word tags.'),
});
export type GeneratePromptTagsOutput = z.infer<typeof GeneratePromptTagsOutputSchema>;

export async function generatePromptTags(
  input: GeneratePromptTagsInput
): Promise<GeneratePromptTagsOutput> {
  return generatePromptTagsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generatePromptTagsPrompt',
  input: {schema: GeneratePromptTagsInputSchema},
  output: {schema: GeneratePromptTagsOutputSchema},
  prompt: `Analyze the following system prompt and generate up to 5 relevant, concise, one-to-two-word tags that describe its purpose or domain.

Examples of good tags: "customer service", "code generation", "education", "student-facing", "data analysis", "creative writing".

Do not use generic tags like "assistant" or "prompt". Focus on the specific task.

For example, for a prompt about creative story writing, the output should be: {"tags": ["creative writing", "storytelling"]}

Prompt to analyze:
"{{{promptText}}}"

Return the response in the required JSON format.`,
});

const generatePromptTagsFlow = ai.defineFlow(
  {
    name: 'generatePromptTagsFlow',
    inputSchema: GeneratePromptTagsInputSchema,
    outputSchema: GeneratePromptTagsOutputSchema,
  },
  async (input) => {
    const { output } = await prompt(input);
    // Be defensive. If the model doesn't return what we expect, return an empty array.
    if (output?.tags && Array.isArray(output.tags)) {
      return {
        tags: output.tags.slice(0, 5).map((tag) => String(tag).toLowerCase()),
      };
    }
    return { tags: [] };
  }
);
