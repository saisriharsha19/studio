'use client';

import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { useToast } from './use-toast';

export type Prompt = {
  id: string;
  text: string;
  createdAt: string;
};

type PromptContextType = {
  prompts: Prompt[];
  addPrompt: (text: string) => void;
  deletePrompt: (id: string) => void;
};

const PromptContext = createContext<PromptContextType | undefined>(undefined);

const PROMPTS_STORAGE_KEY = 'prompt-library';

export function PromptProvider({ children }: { children: ReactNode }) {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const { toast } = useToast();

  useEffect(() => {
    try {
      const storedPrompts = localStorage.getItem(PROMPTS_STORAGE_KEY);
      if (storedPrompts) {
        setPrompts(JSON.parse(storedPrompts));
      }
    } catch (error) {
      console.error('Failed to load prompts from local storage', error);
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(PROMPTS_STORAGE_KEY, JSON.stringify(prompts));
    } catch (error) {
      console.error('Failed to save prompts to local storage', error);
    }
  }, [prompts]);

  const addPrompt = (text: string) => {
    if (!text.trim()) return;
    
    // Avoid adding duplicates
    if (prompts.length > 0 && prompts[0].text === text) {
      return;
    }

    const newPrompt: Prompt = {
      id: new Date().toISOString(),
      text,
      createdAt: new Date().toISOString(),
    };
    setPrompts(prev => [newPrompt, ...prev]);
    toast({
      title: 'Prompt Saved',
      description: 'The new prompt has been added to your library.',
    });
  };

  const deletePrompt = (id: string) => {
    setPrompts(prev => prev.filter(p => p.id !== id));
  };

  return (
    <PromptContext.Provider value={{ prompts, addPrompt, deletePrompt }}>
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
