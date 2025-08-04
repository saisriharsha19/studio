
'use server';

import type { GenerateInitialPromptOutput } from '@/ai/flows/generate-initial-prompt';
import type { EvaluateAndIteratePromptOutput } from '@/ai/flows/evaluate-and-iterate-prompt';
import type { GeneratePromptSuggestionsOutput } from '@/ai/flows/get-prompt-suggestions';
import { db } from '@/lib/db';
import type { Prompt } from '@/hooks/use-prompts';
import { revalidatePath } from 'next/cache';

const BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
};

// --- Task-based API Calls ---

export type TaskCreationResponse = {
  task_id: string;
  status_url: string;
};

export async function handleGenerateInitialPrompt(input: { user_needs: string }): Promise<TaskCreationResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/prompts/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to start generation task.');
    }
    return await response.json();
  } catch (error) {
    console.error('Error in handleGenerateInitialPrompt:', error);
    throw new Error(`An error occurred while starting the generation task: ${getErrorMessage(error)}`);
  }
}

export async function handleEvaluatePrompt(input: { prompt: string; user_needs: string; }): Promise<TaskCreationResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/prompts/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to start evaluation task.');
    }
    return await response.json();
  } catch (error) {
    console.error('Error in handleEvaluatePrompt:', error);
    throw new Error(`An error occurred while starting the evaluation task: ${getErrorMessage(error)}`);
  }
}

export async function handleGetPromptSuggestions(input: { current_prompt: string; user_comments?: string }): Promise<TaskCreationResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/prompts/suggest-improvements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to start suggestion task.');
    }
    return await response.json();
  } catch (error) {
    console.error('Error in handleGetPromptSuggestions:', error);
    throw new Error(`An error occurred while starting the suggestion task: ${getErrorMessage(error)}`);
  }
}

// This function is kept for conceptual mapping, but the backend doesn't have a direct "iterate" endpoint.
// Iteration is now: get suggestions -> user selects -> client-side prompt update -> re-evaluate.
// We'll return a dummy successful task for now to avoid breaking the UI flow.
export async function handleIterateOnPrompt(input: { currentPrompt: string; userComments: string; }): Promise<{ newPrompt: string }> {
  console.warn("handleIterateOnPrompt is a client-side operation now and should be refactored.");
  // This would be handled client-side by applying suggestions.
  // We return a simple object to satisfy the call.
  return { newPrompt: input.currentPrompt };
}


export type TaskStatusResponse = {
  task_id: string;
  task_type: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY';
  created_at: string;
  completed_at?: string;
  error_message?: string;
  result?: GenerateInitialPromptOutput | EvaluateAndIteratePromptOutput | GeneratePromptSuggestionsOutput;
};

export async function getTaskResult(status_url: string): Promise<TaskStatusResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}${status_url}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Failed to get task status from ${status_url}.`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching task result from ${status_url}:`, error);
    // Return a synthetic error response to be handled by the client
    return {
      task_id: status_url.split('/').pop() || 'unknown',
      task_type: 'unknown',
      status: 'FAILURE',
      created_at: new Date().toISOString(),
      error_message: getErrorMessage(error),
    };
  }
}


// --- Database Actions ---
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
      if (p.tags && typeof p.tags === 'string' && p.tags.startsWith('[')) {
          try {
              parsedTags = JSON.parse(p.tags);
          } catch (e) {
              // Ignore parse errors for old data
          }
      } else if (Array.isArray(p.tags)) {
        parsedTags = p.tags;
      }
      return {
        ...p,
        isStarredByUser: !!p.isstarredbyuser,
        stars: Number(p.stars),
        tags: parsedTags,
        summary: p.summary || p.tags,
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
  
      // The new backend has a dedicated endpoint for this
      const response = await fetch(`${BACKEND_URL}/prompts/analyze-and-tag`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt_text: promptText }),
      });
  
      if (!response.ok) {
          throw new Error('Failed to analyze prompt for tags and summary.');
      }
  
      const taskResponse: TaskCreationResponse = await response.json();
      let analysisResult: any;
  
      // Poll for the result of the analysis task
      for (let i = 0; i < 10; i++) { // Poll for max 20 seconds
          await new Promise(res => setTimeout(res, 2000));
          const statusRes = await fetch(`${BACKEND_URL}${taskResponse.status_url}`);
          const statusData = await statusRes.json();
          if (statusData.status === 'SUCCESS') {
              analysisResult = statusData.result;
              break;
          } else if (statusData.status === 'FAILURE') {
              throw new Error('Analysis task failed.');
          }
      }
  
      if (!analysisResult) {
          throw new Error('Analysis task timed out.');
      }
  
      const newPromptData = {
        id: crypto.randomUUID(),
        userId: userId,
        text: promptText,
        createdAt: new Date().toISOString(),
        summary: analysisResult.summary,
        tags: JSON.stringify(analysisResult.tags),
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
          tags: analysisResult.tags,
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
