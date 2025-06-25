
'use server';

import { 
  generateInitialPrompt, 
  type GenerateInitialPromptInput, 
  type GenerateInitialPromptOutput 
} from '@/ai/flows/generate-initial-prompt';
import { 
  evaluateAndIteratePrompt, 
  type EvaluateAndIteratePromptInput, 
  type EvaluateAndIteratePromptOutput 
} from '@/ai/flows/evaluate-and-iterate-prompt';
import { 
  optimizePromptWithContext, 
  type OptimizePromptWithContextInput, 
  type OptimizePromptWithContextOutput 
} from '@/ai/flows/optimize-prompt-with-context';
import {
  iterateOnPrompt,
  type IterateOnPromptInput,
  type IterateOnPromptOutput,
} from '@/ai/flows/iterate-on-prompt';


export async function handleGenerateInitialPrompt(input: GenerateInitialPromptInput): Promise<GenerateInitialPromptOutput> {
  try {
    const output = await generateInitialPrompt(input);
    if (!output) {
      throw new Error('Failed to generate initial prompt.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleGenerateInitialPrompt:', error);
    throw new Error('An error occurred while generating the prompt.');
  }
}

export async function handleEvaluateAndIterate(input: EvaluateAndIteratePromptInput): Promise<EvaluateAndIteratePromptOutput> {
  try {
    const output = await evaluateAndIteratePrompt(input);
    if (!output) {
      throw new Error('Failed to evaluate and iterate prompt.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleEvaluateAndIterate:', error);
    throw new Error('An error occurred while evaluating the prompt.');
  }
}

export async function handleOptimizeWithContext(input: OptimizePromptWithContextInput): Promise<OptimizePromptWithContextOutput> {
  try {
    const output = await optimizePromptWithContext(input);
    if (!output) {
      throw new Error('Failed to optimize prompt with context.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleOptimizeWithContext:', error);
    throw new Error('An error occurred while optimizing the prompt.');
  }
}

export async function handleIterateOnPrompt(input: IterateOnPromptInput): Promise<IterateOnPromptOutput> {
  try {
    const output = await iterateOnPrompt(input);
    if (!output) {
      throw new Error('Failed to iterate on prompt.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleIterateOnPrompt:', error);
    throw new Error('An error occurred while iterating on the prompt.');
  }
}
