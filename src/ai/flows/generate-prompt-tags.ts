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
  summary: z.string().describe("A very short, concise summary (around 5-10 words) of the prompt's purpose, to be used as a title."),
  tags: z.array(z.string()).describe("A list of 2-4 relevant keywords (tags) for searching and filtering. Tags should be lowercase and one or two words max.")
});
export type GeneratePromptMetadataOutput = z.infer<typeof GeneratePromptMetadataOutputSchema>;

// Function name kept for compatibility with actions.ts
export async function generatePromptTags(
  input: GeneratePromptMetadataInput
): Promise<GeneratePromptMetadataOutput> {
  return generatePromptMetadataFlow(input);
}

const generatePromptMetadataFlow = ai.defineFlow(
  {
    name: 'generatePromptMetadataFlow',
    inputSchema: GeneratePromptMetadataInputSchema,
    outputSchema: GeneratePromptMetadataOutputSchema,
  },
  async (input) => {
    const fullPrompt = `Analyze the following system prompt.
  
Your task is to generate two things:
1.  A very short, concise summary (around 5-10 words) that explains what the prompt is used for. This will be used as a title.
2.  A list of 2-4 relevant keywords (tags) for searching and filtering. Tags should be lowercase and one or two words at most.

Prompt to analyze:
"${input.promptText}"

Return the response as a single, valid JSON object with two keys: "summary" (a short string) and "tags" (an array of 2-4 strings). Do not include any extra commentary or markdown formatting.
`;

    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL;
    if (!pythonBackendUrl) {
      throw new Error('PYTHON_BACKEND_URL is not configured.');
    }

    const response = await fetch(`${pythonBackendUrl}/generate-prompt-tags`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: fullPrompt }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request to Python backend failed: ${response.statusText} - ${errorText}`);
    }

    const content = await response.json();
    
    try {
        return GeneratePromptMetadataOutputSchema.parse(content);
    } catch (e: any) {
        console.error("Failed to parse response from Python backend:", e, "Raw content:", content);
        throw new Error(`Failed to parse response from Python backend as JSON: ${e.message}`);
    }
  }
);
