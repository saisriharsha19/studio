
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
import {
  generatePromptSuggestions,
  type GeneratePromptSuggestionsInput,
  type GeneratePromptSuggestionsOutput,
} from '@/ai/flows/get-prompt-suggestions';
import { db } from '@/lib/db';
import type { Prompt } from '@/hooks/use-prompts';
import { revalidatePath } from 'next/cache';


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

export async function handleGetPromptSuggestions(input: GeneratePromptSuggestionsInput): Promise<GeneratePromptSuggestionsOutput> {
    try {
      const output = await generatePromptSuggestions(input);
      if (!output) {
        throw new Error('Failed to generate prompt suggestions.');
      }
      return output;
    } catch (error) {
      console.error('Error in handleGetPromptSuggestions:', error);
      throw new Error('An error occurred while generating suggestions.');
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

const MAX_PROMPTS_PER_USER = 20;

export async function getPromptsFromDB(userId: string): Promise<Prompt[]> {
  if (!userId) return [];
  try {
    const stmt = db.prepare('SELECT * FROM prompts WHERE userId = ? ORDER BY createdAt DESC');
    const prompts = stmt.all(userId) as Prompt[];
    return prompts;
  } catch (error) {
    console.error('Failed to get prompts:', error);
    return [];
  }
}

export async function addPromptToDB(promptText: string, userId: string): Promise<Prompt> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const countStmt = db.prepare('SELECT COUNT(*) as count FROM prompts WHERE userId = ?');
    const { count } = countStmt.get(userId) as { count: number };

    if (count >= MAX_PROMPTS_PER_USER) {
      throw new Error(`You have reached the maximum of ${MAX_PROMPTS_PER_USER} saved prompts.`);
    }

    const newPrompt: Prompt = {
      id: crypto.randomUUID(),
      userId: userId,
      text: promptText,
      createdAt: new Date().toISOString(),
    };

    const stmt = db.prepare(
      'INSERT INTO prompts (id, userId, text, createdAt) VALUES (?, ?, ?, ?)'
    );
    stmt.run(newPrompt.id, newPrompt.userId, newPrompt.text, newPrompt.createdAt);
    revalidatePath('/library');
    return newPrompt;
  } catch (error: any) {
    console.error('Failed to add prompt:', error);
    throw new Error(error.message || 'Failed to save prompt to database.');
  }
}

export async function deletePromptFromDB(id: string, userId: string): Promise<{ success: boolean }> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const stmt = db.prepare('DELETE FROM prompts WHERE id = ? AND userId = ?');
    const result = stmt.run(id, userId);
    revalidatePath('/library');
    if (result.changes === 0) {
      throw new Error("Prompt not found or you don't have permission to delete it.");
    }
    return { success: true };
  } catch (error: any) {
    console.error('Failed to delete prompt:', error);
    throw new Error(error.message || 'Failed to delete prompt from database.');
  }
}
