
'use client';

import { createContext, useContext, useState, ReactNode, useEffect, useCallback } from 'react';
import { useToast } from './use-toast';
import { addLibraryPromptToDB, deleteLibraryPromptFromDB, getLibraryPromptsFromDB } from '@/app/actions';
import { useAuth } from './use-auth';
import type { Prompt } from './use-prompts';


type LibraryContextType = {
  libraryPrompts: Prompt[];
  isLoading: boolean;
  addLibraryPrompt: (text: string) => Promise<void>;
  deleteLibraryPrompt: (id: string) => Promise<void>;
};

const LibraryContext = createContext<LibraryContextType | undefined>(undefined);

export function LibraryProvider({ children }: { children: ReactNode }) {
  const [libraryPrompts, setLibraryPrompts] = useState<Prompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();
  const { isAuthenticated, userId } = useAuth();

  useEffect(() => {
    const loadPrompts = async () => {
      if (isAuthenticated && userId) {
        try {
          setIsLoading(true);
          const initialPrompts = await getLibraryPromptsFromDB(userId);
          setLibraryPrompts(initialPrompts);
        } catch (error) {
          console.error('Failed to load prompts from library', error);
          toast({
            variant: 'destructive',
            title: 'Error',
            description: 'Could not load your prompt library.',
          });
        } finally {
          setIsLoading(false);
        }
      } else {
        setLibraryPrompts([]);
        setIsLoading(false);
      }
    };
    loadPrompts();
  }, [isAuthenticated, userId, toast]);

  const addLibraryPrompt = useCallback(async (text: string) => {
    if (!isAuthenticated || !userId) {
      toast({
        variant: 'destructive',
        title: 'Not Logged In',
        description: 'You must be logged in to save prompts to the library.',
      });
      return;
    }
    
    if (!text.trim()) return;
    
    try {
      const newPrompt = await addLibraryPromptToDB(text, userId);
      setLibraryPrompts(prev => [newPrompt, ...prev]);
      toast({
        title: 'Prompt Saved to Library',
        description: 'The new prompt has been added to your library.',
      });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Save to Library Failed',
        description: error.message || 'An error occurred while saving the prompt.',
      });
    }
  }, [isAuthenticated, userId, toast]);

  const deleteLibraryPrompt = useCallback(async (id: string) => {
    if (!isAuthenticated || !userId) {
      toast({
        variant: 'destructive',
        title: 'Not Logged In',
        description: 'You must be logged in to delete prompts from the library.',
      });
      return;
    }

    try {
      await deleteLibraryPromptFromDB(id, userId);
      setLibraryPrompts(prev => prev.filter(p => p.id !== id));
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
    <LibraryContext.Provider value={{ libraryPrompts, addLibraryPrompt, deleteLibraryPrompt, isLoading }}>
      {children}
    </LibraryContext.Provider>
  );
}

export function useLibrary() {
  const context = useContext(LibraryContext);
  if (context === undefined) {
    throw new Error('useLibrary must be used within a LibraryProvider');
  }
  return context;
}
