
'use client';

import { createContext, useContext, useState, ReactNode, useEffect, useCallback } from 'react';
import { useToast } from './use-toast';
import { addLibraryPromptToDB, getLibraryPromptsFromDB, toggleStarForPrompt, deleteLibraryPromptFromDB } from '@/app/actions';
import { useAuth } from './use-auth';
import type { Prompt } from './use-prompts';


type LibraryContextType = {
  libraryPrompts: Prompt[];
  isLoading: boolean;
  addLibraryPrompt: (text: string) => Promise<void>;
  toggleStar: (id: string) => Promise<void>;
  deleteLibraryPrompt: (id: string) => Promise<void>;
};

const LibraryContext = createContext<LibraryContextType | undefined>(undefined);

export function LibraryProvider({ children }: { children: ReactNode }) {
  const [libraryPrompts, setLibraryPrompts] = useState<Prompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();
  const { isAuthenticated, userId, isAdmin } = useAuth();

  useEffect(() => {
    const loadPrompts = async () => {
      try {
        setIsLoading(true);
        const initialPrompts = await getLibraryPromptsFromDB(userId);
        setLibraryPrompts(initialPrompts);
      } catch (error) {
        console.error('Failed to load prompts from library', error);
        toast({
          variant: 'destructive',
          title: 'Error',
          description: 'Could not load the prompt library.',
        });
      } finally {
        setIsLoading(false);
      }
    };
    loadPrompts();
  }, [toast, userId]);

  const addLibraryPrompt = useCallback(async (text: string) => {
    if (!isAuthenticated || !userId) {
      toast({
        variant: 'destructive',
        title: 'Authentication Required',
        description: 'You must be signed in to add prompts to the public library.',
      });
      return;
    }
    
    if (!text.trim()) return;
    
    try {
      const newPrompt = await addLibraryPromptToDB(text, userId);
      setLibraryPrompts(prev => [newPrompt, ...prev]);
      toast({
        title: 'Prompt Added to Library',
        description: 'The new prompt has been added to the public library.',
      });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Add to Library Failed',
        description: error.message || 'An error occurred while saving the prompt.',
      });
    }
  }, [isAuthenticated, userId, toast]);

  const deleteLibraryPrompt = useCallback(async (id: string) => {
    if (!isAuthenticated || !userId || !isAdmin) {
      toast({
        variant: 'destructive',
        title: 'Permission Denied',
        description: 'You do not have permission to delete library prompts.',
      });
      return;
    }

    const originalPrompts = [...libraryPrompts];
    setLibraryPrompts(prev => prev.filter(p => p.id !== id));

    try {
      await deleteLibraryPromptFromDB(id, userId);
      toast({
        title: 'Prompt Deleted',
        description: 'The prompt has been removed from the library.',
      });
    } catch (error: any) {
      setLibraryPrompts(originalPrompts); // Revert on error
      toast({
        variant: 'destructive',
        title: 'Delete Failed',
        description: error.message || 'An error occurred while deleting the prompt.',
      });
    }
  }, [isAuthenticated, userId, isAdmin, libraryPrompts, toast]);


  const toggleStar = useCallback(async (promptId: string) => {
    if (!isAuthenticated || !userId) {
        toast({ variant: 'destructive', title: 'Please sign in to star prompts.' });
        return;
    }

    // Optimistic update
    setLibraryPrompts(prev =>
      prev.map(p => {
        if (p.id === promptId) {
          const isStarred = p.isStarredByUser;
          const currentStars = p.stars || 0;
          return {
            ...p,
            isStarredByUser: !isStarred,
            stars: isStarred ? currentStars - 1 : currentStars + 1,
          };
        }
        return p;
      })
    );

    try {
        await toggleStarForPrompt(promptId, userId);
    } catch (error: any) {
        toast({
            variant: 'destructive',
            title: 'Error',
            description: error.message,
        });
        // Revert optimistic update on failure
        setLibraryPrompts(prev =>
            prev.map(p => {
                if (p.id === promptId) {
                    const isStarred = p.isStarredByUser;
                    const currentStars = p.stars || 0;
                    return {
                        ...p,
                        isStarredByUser: !isStarred, // Revert the flag
                        stars: isStarred ? currentStars - 1 : currentStars + 1, // Revert the count
                    };
                }
                return p;
            })
        );
    }
  }, [isAuthenticated, userId, toast]);

  return (
    <LibraryContext.Provider value={{ libraryPrompts, addLibraryPrompt, toggleStar, isLoading, deleteLibraryPrompt }}>
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
