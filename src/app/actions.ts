
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
import {
    generatePromptTags,
    type GeneratePromptSummaryInput,
    type GeneratePromptSummaryOutput,
} from '@/ai/flows/generate-prompt-tags';
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

async function handleGeneratePromptTags(input: GeneratePromptSummaryInput): Promise<GeneratePromptSummaryOutput> {
    try {
      const output = await generatePromptTags(input);
      if (!output) {
        throw new Error('No output received from AI.');
      }
      return output;
    } catch (error: any) {
      console.error('Error in handleGeneratePromptTags:', error);
       // Ensure a valid structure is always returned
      if (error.message && error.message.includes('JSON')) {
          return { summary: "Could not generate summary." };
      }
      throw new Error(`An error occurred while generating summary: ${getErrorMessage(error)}`);
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
export async function getLibraryPromptsFromDB(userId: string | null): Promise<Prompt[]> {
  try {
    // This query is more complex. It fetches prompts, counts stars, and checks if the current user has starred it.
    const sql = `
      SELECT
        lp.id,
        lp.userId,
        lp.text,
        lp.createdAt,
        lp.tags as summary,
        COUNT(ps.promptId) as stars,
        ${userId ? `(SELECT 1 FROM prompt_stars WHERE promptId = lp.id AND userId = ?) as isStarredByUser` : '0 as isStarredByUser'}
      FROM library_prompts lp
      LEFT JOIN prompt_stars ps ON lp.id = ps.promptId
      GROUP BY lp.id
      ORDER BY stars DESC, lp.createdAt DESC
    `;
    const stmt = db.prepare(sql);
    const results = userId ? stmt.all(userId) : stmt.all();

    return results.map((p: any) => ({
      ...p,
      isStarredByUser: !!p.isStarredByUser,
    }));
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

    const { summary } = await handleGeneratePromptTags({ promptText });

    const newPromptData = {
      id: crypto.randomUUID(),
      userId: userId,
      text: promptText,
      createdAt: new Date().toISOString(),
      tags: summary, // Storing summary in 'tags' column
    };

    const stmt = db.prepare(
      'INSERT INTO library_prompts (id, userId, text, createdAt, tags) VALUES (@id, @userId, @text, @createdAt, @tags)'
    );
    stmt.run(newPromptData);
    
    revalidatePath('/library');
    
    // Return a fully formed Prompt object, matching getLibraryPromptsFromDB
    return {
        id: newPromptData.id,
        userId: newPromptData.userId,
        text: newPromptData.text,
        createdAt: newPromptData.createdAt,
        summary: newPromptData.tags,
        stars: 0,
        isStarredByUser: false,
    };
  } catch (error: any) {
    console.error('Failed to add prompt to library:', error);
    throw new Error(error.message || 'Failed to save prompt to library.');
  }
}

export async function deleteLibraryPromptFromDB(promptId: string, userId: string): Promise<{ success: boolean }> {
  if (!userId) throw new Error('User not authenticated.');
  
  // In a real app, you'd have a proper role check. Here, we'll use the mock admin ID.
  const isAdmin = userId === 'mock-user-123';
  if (!isAdmin) {
    throw new Error('You do not have permission to delete library prompts.');
  }

  try {
    // The ON DELETE CASCADE in the schema will handle deleting from prompt_stars
    const stmt = db.prepare('DELETE FROM library_prompts WHERE id = ?');
    const result = stmt.run(promptId);
    
    if (result.changes === 0) {
      throw new Error("Prompt not found.");
    }

    revalidatePath('/library');
    return { success: true };
  } catch (error: any) {
    console.error('Failed to delete prompt from library:', error);
    throw new Error(error.message || 'Failed to delete prompt from library.');
  }
}

export async function toggleStarForPrompt(promptId: string, userId: string): Promise<{ success: boolean }> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const existingStarStmt = db.prepare('SELECT 1 FROM prompt_stars WHERE promptId = ? AND userId = ?');
    const existingStar = existingStarStmt.get(promptId, userId);

    if (existingStar) {
      // User has already starred, so unstar it.
      const deleteStmt = db.prepare('DELETE FROM prompt_stars WHERE promptId = ? AND userId = ?');
      deleteStmt.run(promptId, userId);
    } else {
      // User has not starred, so star it.
      const insertStmt = db.prepare('INSERT INTO prompt_stars (promptId, userId) VALUES (?, ?)');
      insertStmt.run(promptId, userId);
    }
    
    revalidatePath('/library');
    return { success: true };
  } catch (error: any) {
     console.error('Failed to toggle star for prompt:', error);
    throw new Error(error.message || 'Failed to toggle star for prompt.');
  }
}
