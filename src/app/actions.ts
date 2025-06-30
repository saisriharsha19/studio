
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

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    // Genkit/Google AI errors often have more details in the 'cause' property
    const cause = (error as any).cause;
    if (cause && typeof cause.message === 'string') {
      return cause.message;
    }
    return error.message;
  }
  return String(error);
};

export async function handleGenerateInitialPrompt(input: GenerateInitialPromptInput): Promise<GenerateInitialPromptOutput> {
  try {
    const output = await generateInitialPrompt(input);
    if (!output) {
      throw new Error('No output received from AI.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleGenerateInitialPrompt:', error);
    throw new Error(`An error occurred while generating the prompt: ${getErrorMessage(error)}`);
  }
}

export async function handleEvaluateAndIterate(input: EvaluateAndIteratePromptInput): Promise<EvaluateAndIteratePromptOutput> {
  try {
    const output = await evaluateAndIteratePrompt(input);
    if (!output) {
      throw new Error('No output received from AI.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleEvaluateAndIterate:', error);
    throw new Error(`An error occurred while evaluating the prompt: ${getErrorMessage(error)}`);
  }
}

export async function handleOptimizeWithContext(input: OptimizePromptWithContextInput): Promise<OptimizePromptWithContextOutput> {
  try {
    const output = await optimizePromptWithContext(input);
    if (!output) {
      throw new Error('No output received from AI.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleOptimizeWithContext:', error);
    throw new Error(`An error occurred while optimizing the prompt: ${getErrorMessage(error)}`);
  }
}

export async function handleGetPromptSuggestions(input: GeneratePromptSuggestionsInput): Promise<GeneratePromptSuggestionsOutput> {
    try {
      const output = await generatePromptSuggestions(input);
      if (!output) {
        throw new Error('No output received from AI.');
      }
      return output;
    } catch (error) {
      console.error('Error in handleGetPromptSuggestions:', error);
      throw new Error(`An error occurred while generating suggestions: ${getErrorMessage(error)}`);
    }
  }

export async function handleIterateOnPrompt(input: IterateOnPromptInput): Promise<IterateOnPromptOutput> {
  try {
    const output = await iterateOnPrompt(input);
    if (!output) {
      throw new Error('No output received from AI.');
    }
    return output;
  } catch (error) {
    console.error('Error in handleIterateOnPrompt:', error);
    throw new Error(`An error occurred while iterating on the prompt: ${getErrorMessage(error)}`);
  }
}

// --- History Actions (prompts table) ---
const MAX_HISTORY_PROMPTS_PER_USER = 20;

export async function getHistoryPromptsFromDB(userId: string): Promise<Prompt[]> {
  if (!userId) return [];
  try {
    const stmt = db.prepare('SELECT * FROM prompts WHERE userId = ? ORDER BY createdAt DESC');
    const prompts = stmt.all(userId) as Prompt[];
    return prompts;
  } catch (error) {
    console.error('Failed to get history prompts:', error);
    return [];
  }
}

export async function addHistoryPromptToDB(promptText: string, userId: string): Promise<Prompt> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const countStmt = db.prepare('SELECT COUNT(*) as count FROM prompts WHERE userId = ?');
    const { count } = countStmt.get(userId) as { count: number };

    if (count >= MAX_HISTORY_PROMPTS_PER_USER) {
      // If limit is reached, delete the oldest prompt
      const oldestStmt = db.prepare('DELETE FROM prompts WHERE id = (SELECT id FROM prompts WHERE userId = ? ORDER BY createdAt ASC LIMIT 1)');
      oldestStmt.run(userId);
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
    revalidatePath('/history');
    return newPrompt;
  } catch (error: any) {
    console.error('Failed to add prompt to history:', error);
    throw new Error(error.message || 'Failed to save prompt to history.');
  }
}

export async function deleteHistoryPromptFromDB(id: string, userId: string): Promise<{ success: boolean }> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const stmt = db.prepare('DELETE FROM prompts WHERE id = ? AND userId = ?');
    const result = stmt.run(id, userId);
    revalidatePath('/history');
    if (result.changes === 0) {
      throw new Error("Prompt not found or you don't have permission to delete it.");
    }
    return { success: true };
  } catch (error: any) {
    console.error('Failed to delete prompt from history:', error);
    throw new Error(error.message || 'Failed to delete prompt from history.');
  }
}


// --- Library Actions (library_prompts table) ---
export async function getLibraryPromptsFromDB(): Promise<Prompt[]> {
  try {
    const stmt = db.prepare('SELECT * FROM library_prompts ORDER BY createdAt DESC');
    const prompts = stmt.all() as Prompt[];
    return prompts;
  } catch (error) {
    console.error('Failed to get library prompts:', error);
    return [];
  }
}

export async function addLibraryPromptToDB(promptText: string, userId: string): Promise<Prompt> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    // Avoid adding duplicates to the public library
    const existsStmt = db.prepare('SELECT 1 FROM library_prompts WHERE text = ?');
    const exists = existsStmt.get(promptText);
    if (exists) {
        throw new Error('This prompt is already in the library.');
    }

    const newPrompt: Prompt = {
      id: crypto.randomUUID(),
      userId: userId,
      text: promptText,
      createdAt: new Date().toISOString(),
    };

    const stmt = db.prepare(
      'INSERT INTO library_prompts (id, userId, text, createdAt) VALUES (?, ?, ?, ?)'
    );
    stmt.run(newPrompt.id, newPrompt.userId, newPrompt.text, newPrompt.createdAt);
    revalidatePath('/library');
    return newPrompt;
  } catch (error: any) {
    console.error('Failed to add prompt to library:', error);
    throw new Error(error.message || 'Failed to save prompt to library.');
  }
}

export async function deleteLibraryPromptFromDB(id: string, userId: string): Promise<{ success: boolean }> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const stmt = db.prepare('DELETE FROM library_prompts WHERE id = ? AND userId = ?');
    const result = stmt.run(id, userId);
    revalidatePath('/library');
    if (result.changes === 0) {
      throw new Error("Prompt not found or you don't have permission to delete it.");
    }
    return { success: true };
  } catch (error: any) {
    console.error('Failed to delete prompt from library:', error);
    throw new Error(error.message || 'Failed to delete prompt from library.');
  }
}
