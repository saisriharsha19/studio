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

const generateInitialPromptFlow = ai.defineFlow(
  {
    name: 'generateInitialPromptFlow',
    inputSchema: GenerateInitialPromptInputSchema,
    outputSchema: GenerateInitialPromptOutputSchema,
  },
  async (input) => {
    const fullPrompt = `You are an expert AI prompt architect. Your role is to construct a robust system prompt for an assistant, tailored precisely to the user’s stated goals. The prompt must include detailed, unambiguous instructions that not only align with the user’s needs but also embed strong behavioral guardrails to ensure safety, consistency, and ethical responses.

Your prompt should:

Leverage advanced prompt engineering techniques such as Chain-of-Thought, Tree-of-Thought, ReAct, Self-Reflection, and more.

Incorporate clear role definitions, tone settings, task boundaries, and refusal criteria.

Include alignment safeguards to prevent hallucination, off-topic generation, harmful content, or ethical breaches.

Avoid user requests with dangerous, unethical, harmful, over task boundaries and avoid with I'm unable to generate prompt with some explanation.

Be optimized for clarity, brevity, and modular adaptability across domains and use cases.

Craft the system prompt as if it were to be deployed in production-grade AI systems serving high-stakes applications.


User Needs: ${input.userNeeds}

Respond with a single, valid JSON object containing one key: "initialPrompt". The value should be the generated system prompt as a string. Do not include any extra commentary or markdown formatting.`;

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
        return GenerateInitialPromptOutputSchema.parse(parsedContent);
    } catch (e: any) {
        console.error("Failed to parse LLM response:", e, "Raw content:", content);
        throw new Error(`Failed to parse LLM response as JSON: ${e.message}`);
    }
  }
);
