
'use client';

import { createContext, useContext, useState, ReactNode, useEffect, useCallback } from 'react';
import { useToast } from './use-toast';
import { addPromptToDB, deletePromptFromDB, getPromptsFromDB } from '@/app/actions';
import { useAuth } from './use-auth';

export type Prompt = {
  id: string;
  userId: string;
  text: string;
  createdAt: string;
};

type PromptContextType = {
  prompts: Prompt[];
  isLoading: boolean;
  addPrompt: (text: string) => Promise<void>;
  deletePrompt: (id: string) => Promise<void>;
};

const PromptContext = createContext<PromptContextType | undefined>(undefined);

export function PromptProvider({ children }: { children: ReactNode }) {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();
  const { isAuthenticated, userId } = useAuth();

  useEffect(() => {
    const loadPrompts = async () => {
      if (isAuthenticated && userId) {
        try {
          setIsLoading(true);
          const initialPrompts = await getPromptsFromDB(userId);
          setPrompts(initialPrompts);
        } catch (error) {
          console.error('Failed to load prompts from database', error);
          toast({
            variant: 'destructive',
            title: 'Error',
            description: 'Could not load your prompt library.',
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

  const addPrompt = useCallback(async (text: string) => {
    if (!isAuthenticated || !userId) {
      toast({
        variant: 'destructive',
        title: 'Not Logged In',
        description: 'You must be logged in to save prompts.',
      });
      return;
    }
    
    if (!text.trim()) return;
    
    // Avoid adding duplicates based on text
    if (prompts.some(p => p.text === text)) {
      return;
    }

    try {
      const newPrompt = await addPromptToDB(text, userId);
      setPrompts(prev => [newPrompt, ...prev]);
      toast({
        title: 'Prompt Saved',
        description: 'The new prompt has been added to your library.',
      });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Save Failed',
        description: error.message || 'An error occurred while saving the prompt.',
      });
    }
  }, [isAuthenticated, userId, prompts, toast]);

  const deletePrompt = useCallback(async (id: string) => {
    if (!isAuthenticated || !userId) {
      toast({
        variant: 'destructive',
        title: 'Not Logged In',
        description: 'You must be logged in to delete prompts.',
      });
      return;
    }

    try {
      await deletePromptFromDB(id, userId);
      setPrompts(prev => prev.filter(p => p.id !== id));
      toast({
        title: 'Prompt Deleted',
        description: 'The prompt has been removed from your library.',
      });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Delete Failed',
        description: error.message || 'An error occurred while deleting the prompt.',
      });
    }
  }, [isAuthenticated, userId, toast]);

  return (
    <PromptContext.Provider value={{ prompts, addPrompt, deletePrompt, isLoading }}>
      {children}
    </PromptContext.Provider>
  );
}

export function usePrompts() {
  const context = useContext(PromptContext);
  if (context === undefined) {
    throw new Error('usePrompts must be used within a PromptProvider');
  }
  return context;
}
