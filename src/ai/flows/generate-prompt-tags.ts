
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
  universityCode: z.string().describe('The code for the university.'),
});
export type GeneratePromptMetadataInput = z.infer<typeof GeneratePromptMetadataInputSchema>;

const GeneratePromptMetadataOutputSchema = z.object({
  summary: z.string().describe("A very short, concise summary (around 5-10 words) of the prompt's purpose, to be used as a title."),
  tags: z.array(z.string()).describe("A list of 2-4 relevant keywords (tags) for searching and filtering. Tags should be lowercase and one or two words max."),
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
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL;
    if (!pythonBackendUrl) {
      throw new Error('PYTHON_BACKEND_URL is not configured.');
    }

    const payload = {
        promptText: input.promptText,
        universityCode: input.universityCode,
    };

    const response = await fetch(`${pythonBackendUrl}/generate-prompt-tags`, {
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
        return GeneratePromptMetadataOutputSchema.parse(content);
    } catch (e: any) {
        console.error("Failed to parse response from Python backend:", e, "Raw content:", content);
        throw new Error(`Failed to parse response from Python backend as JSON: ${e.message}`);
    }
  }
);
