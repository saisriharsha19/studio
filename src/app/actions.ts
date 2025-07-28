
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
    type GeneratePromptMetadataInput,
    type GeneratePromptMetadataOutput,
} from '@/ai/flows/generate-prompt-tags';
import {
    scrapeUrl,
    type ScrapeUrlInput,
    type ScrapeUrlOutput
} from '@/ai/flows/scrape-url-flow';
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

async function handleGeneratePromptTags(input: GeneratePromptMetadataInput): Promise<GeneratePromptMetadataOutput> {
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
          return { summary: "Could not generate summary.", tags: [] };
      }
      throw new Error(`An error occurred while generating metadata: ${getErrorMessage(error)}`);
    }
}

export async function handleScrapeUrl(input: ScrapeUrlInput): Promise<ScrapeUrlOutput> {
    try {
      const output = await scrapeUrl(input);
      if (!output) {
        throw new Error('No content received from URL.');
      }
      return output;
    } catch (error) {
      console.error('Error in handleScrapeUrl:', error);
      throw new Error(`An error occurred while scraping the URL: ${getErrorMessage(error)}`);
    }
}


// --- History Actions (prompts table) ---
const MAX_HISTORY_PROMPTS_PER_USER = 20;

export async function getHistoryPromptsFromDB(userId: string): Promise<Prompt[]> {
  if (!userId) return [];
  try {
    const sql = 'SELECT * FROM prompts WHERE userId = ? ORDER BY createdAt DESC';
    const prompts = await db.query<Prompt>(sql, [userId]);
    return prompts;
  } catch (error) {
    console.error('Failed to get history prompts:', error);
    return [];
  }
}

export async function addHistoryPromptToDB(promptText: string, userId: string): Promise<Prompt> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const countSql = 'SELECT COUNT(*) as count FROM prompts WHERE userId = ?';
    const countResult = await db.query<{ count: number | string }>(countSql, [userId]);
    const count = Number(countResult[0]?.count || 0);

    if (count >= MAX_HISTORY_PROMPTS_PER_USER) {
      const oldestSql = 'DELETE FROM prompts WHERE id = (SELECT id FROM prompts WHERE userId = ? ORDER BY createdAt ASC LIMIT 1)';
      await db.run(oldestSql, [userId]);
    }

    const newPrompt: Prompt = {
      id: crypto.randomUUID(),
      userId: userId,
      text: promptText,
      createdAt: new Date().toISOString(),
    };

    const insertSql = 'INSERT INTO prompts (id, userId, text, createdAt) VALUES (?, ?, ?, ?)';
    await db.run(insertSql, [newPrompt.id, newPrompt.userId, newPrompt.text, newPrompt.createdAt]);
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
    const sql = 'DELETE FROM prompts WHERE id = ? AND userId = ?';
    const result = await db.run(sql, [id, userId]);
    revalidatePath('/history');
    if (result.rowCount === 0) {
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
        lp.summary,
        lp.tags,
        COUNT(ps.promptId) as stars,
        ${userId ? `(SELECT 1 FROM prompt_stars WHERE promptId = lp.id AND userId = ?) as isStarredByUser` : '0 as isStarredByUser'}
      FROM library_prompts lp
      LEFT JOIN prompt_stars ps ON lp.id = ps.promptId
      GROUP BY lp.id
      ORDER BY stars DESC, lp.createdAt DESC
    `;
    const params = userId ? [userId] : [];
    const results = await db.query<any>(sql, params);

    return results.map((p: any) => {
      let parsedTags: string[] = [];
      // Check if tags is a JSON string before parsing
      if (p.tags && typeof p.tags === 'string' && p.tags.startsWith('[')) {
          try {
              parsedTags = JSON.parse(p.tags);
          } catch (e) {
              // Ignore parse errors for old data
          }
      } else if (Array.isArray(p.tags)) {
        // Postgres might return it as an array directly
        parsedTags = p.tags;
      }
      return {
        ...p,
        isStarredByUser: !!p.isstarredbyuser, // Postgres returns lowercase
        stars: Number(p.stars),
        tags: parsedTags,
        summary: p.summary || p.tags, // Fallback for old data
      };
    });
  } catch (error) {
    console.error('Failed to get library prompts:', error);
    return [];
  }
}

export async function addLibraryPromptToDB(promptText: string, userId: string): Promise<Prompt> {
  if (!userId) throw new Error('User not authenticated.');

  try {
    const existsSql = 'SELECT 1 FROM library_prompts WHERE text = ?';
    const existingPrompts = await db.query(existsSql, [promptText]);
    if (existingPrompts.length > 0) {
        throw new Error('This prompt is already in the library.');
    }

    const { summary, tags } = await handleGeneratePromptTags({ promptText, universityCode: 'ufl' });

    const newPromptData = {
      id: crypto.randomUUID(),
      userId: userId,
      text: promptText,
      createdAt: new Date().toISOString(),
      summary: summary,
      tags: JSON.stringify(tags),
    };

    const insertSql = 'INSERT INTO library_prompts (id, userId, text, createdAt, summary, tags) VALUES (?, ?, ?, ?, ?, ?)';
    await db.run(insertSql, [newPromptData.id, newPromptData.userId, newPromptData.text, newPromptData.createdAt, newPromptData.summary, newPromptData.tags]);
    
    revalidatePath('/library');
    
    return {
        id: newPromptData.id,
        userId: newPromptData.userId,
        text: newPromptData.text,
        createdAt: newPromptData.createdAt,
        summary: newPromptData.summary,
        tags: tags,
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
  
  const isAdmin = userId === 'mock-user-123';
  if (!isAdmin) {
    throw new Error('You do not have permission to delete library prompts.');
  }

  try {
    const sql = 'DELETE FROM library_prompts WHERE id = ?';
    const result = await db.run(sql, [promptId]);
    
    if (result.rowCount === 0) {
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
    const selectSql = 'SELECT 1 FROM prompt_stars WHERE promptId = ? AND userId = ?';
    const existingStars = await db.query(selectSql, [promptId, userId]);
    const isStarred = existingStars.length > 0;

    if (isStarred) {
      const deleteSql = 'DELETE FROM prompt_stars WHERE promptId = ? AND userId = ?';
      await db.run(deleteSql, [promptId, userId]);
    } else {
      const insertSql = 'INSERT INTO prompt_stars (promptId, userId) VALUES (?, ?)';
      await db.run(insertSql, [promptId, userId]);
    }
    
    revalidatePath('/library');
    return { success: true };
  } catch (error: any) {
     console.error('Failed to toggle star for prompt:', error);
    throw new Error(error.message || 'Failed to toggle star for prompt.');
  }
}
