
'use client';

import { createContext, useContext, useState, ReactNode, useEffect, useCallback } from 'react';
import { useToast } from './use-toast';
import { deleteHistoryPromptFromDB, getHistoryPromptsFromDB } from '@/app/actions';
import { useAuth } from './use-auth';

export type Prompt = {
  id: string;
  userId: string;
  text: string;
  createdAt: string;
  // Library-specific fields
  stars?: number;
  summary?: string;
  tags?: string[];
  isStarredByUser?: boolean;
};

export type LibrarySubmission = {
    id: string;
    prompt_text: string;
    user_id: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    submitted_at: string;
    admin_notes?: string;
};


type PromptHistoryContextType = {
  prompts: Prompt[];
  isLoading: boolean;
  deletePrompt: (id: string) => Promise<void>;
};

const PromptHistoryContext = createContext<PromptHistoryContextType | undefined>(undefined);

export function PromptHistoryProvider({ children }: { children: ReactNode }) {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();
  const { isAuthenticated, userId, isAdmin } = useAuth();

  useEffect(() => {
    const loadPrompts = async () => {
      if (isAuthenticated && userId) {
        try {
          setIsLoading(true);
          const initialPrompts = await getHistoryPromptsFromDB(userId);
          setPrompts(initialPrompts);
        } catch (error) {
          console.error('Failed to load prompts from history', error);
          toast({
            variant: 'destructive',
            title: 'Error',
            description: 'Could not load your prompt history.',
          });
        } finally {
          setIsLoading(false);
        }
      } else {
        setPrompts([]);
        setIsLoading(false);
      }
    };
    loadPrompts();
  }, [isAuthenticated, userId, toast]);


  const deletePrompt = useCallback(async (id: string) => {
    if (!isAuthenticated || !userId) {
      toast({
        variant: 'destructive',
        title: 'Not Logged In',
        description: 'You must be logged in to delete prompts from history.',
      });
      return;
    }
    
    if (!isAdmin) {
      toast({
        variant: 'destructive',
        title: 'Permission Denied',
        description: 'Only admins can delete prompts from history.',
      });
      return;
    }

    try {
      await deleteHistoryPromptFromDB(id, userId);
      setPrompts(prev => prev.filter(p => p.id !== id));
      toast({
        title: 'Prompt Deleted',
        description: 'The prompt has been removed from the user\'s history.',
      });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Delete Failed',
        description: error.message || 'An error occurred while deleting the prompt.',
      });
    }
  }, [isAuthenticated, userId, toast, isAdmin]);

  return (
    <PromptHistoryContext.Provider value={{ prompts, deletePrompt, isLoading }}>
      {children}
    </PromptHistoryContext.Provider>
  );
}

export function usePromptHistory() {
  const context = useContext(PromptHistoryContext);
  if (context === undefined) {
    throw new Error('usePromptHistory must be used within a PromptHistoryProvider');
  }
  return context;
}

    