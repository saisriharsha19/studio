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

    const response = await fetch(`${process.env.UFL_AI_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.UFL_AI_API_KEY}`,
        },
        body: JSON.stringify({
            model: 'llama-3.1-70b-instruct',
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
        return GeneratePromptMetadataOutputSchema.parse(parsedContent);
    } catch (e: any) {
        console.error("Failed to parse LLM response:", e, "Raw content:", content);
        throw new Error(`Failed to parse LLM response as JSON: ${e.message}`);
    }
  }
);
