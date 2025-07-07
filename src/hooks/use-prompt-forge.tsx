'use client';

import type { EvaluateAndIteratePromptOutput } from '@/ai/flows/evaluate-and-iterate-prompt';
import { createContext, useContext, useState, ReactNode, Dispatch, SetStateAction } from 'react';

type PromptForgeContextType = {
  userNeeds: string;
  setUserNeeds: Dispatch<SetStateAction<string>>;
  currentPrompt: string;
  setCurrentPrompt: Dispatch<SetStateAction<string>>;
  promptsGenerated: number;
  setPromptsGenerated: Dispatch<SetStateAction<number>>;
  knowledgeBase: string;
  setKnowledgeBase: Dispatch<SetStateAction<string>>;
  uploadedFileContent: string;
  setUploadedFileContent: Dispatch<SetStateAction<string>>;
  fewShotExamples: string;
  setFewShotExamples: Dispatch<SetStateAction<string>>;
  scrapeUrl: string;
  setScrapeUrl: Dispatch<SetStateAction<string>>;
  uploadedFileName: string;
  setUploadedFileName: Dispatch<SetStateAction<string>>;
  iterationComments: string;
  setIterationComments: Dispatch<SetStateAction<string>>;
  suggestions: string[];
  setSuggestions: Dispatch<SetStateAction<string[]>>;
  selectedSuggestions: string[];
  setSelectedSuggestions: Dispatch<SetStateAction<string[]>>;
  evaluationResult: EvaluateAndIteratePromptOutput | null;
  setEvaluationResult: Dispatch<SetStateAction<EvaluateAndIteratePromptOutput | null>>;
};

const PromptForgeContext = createContext<PromptForgeContextType | undefined>(undefined);

export function PromptForgeProvider({ children }: { children: ReactNode }) {
  const [userNeeds, setUserNeeds] = useState('');
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [promptsGenerated, setPromptsGenerated] = useState(0);
  const [knowledgeBase, setKnowledgeBase] = useState('');
  const [uploadedFileContent, setUploadedFileContent] = useState('');
  const [fewShotExamples, setFewShotExamples] = useState('');
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [iterationComments, setIterationComments] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([]);
  const [evaluationResult, setEvaluationResult] = useState<EvaluateAndIteratePromptOutput | null>(null);

  const value = {
    userNeeds, setUserNeeds,
    currentPrompt, setCurrentPrompt,
    promptsGenerated, setPromptsGenerated,
    knowledgeBase, setKnowledgeBase,
    uploadedFileContent, setUploadedFileContent,
    fewShotExamples, setFewShotExamples,
    scrapeUrl, setScrapeUrl,
    uploadedFileName, setUploadedFileName,
    iterationComments, setIterationComments,
    suggestions, setSuggestions,
    selectedSuggestions, setSelectedSuggestions,
    evaluationResult, setEvaluationResult
  };
  
  return (
    <PromptForgeContext.Provider value={value}>
      {children}
    </PromptForgeContext.Provider>
  );
}

export function usePromptForge() {
  const context = useContext(PromptForgeContext);
  if (context === undefined) {
    throw new Error('usePromptForge must be used within a PromptForgeProvider');
  }
  return context;
}
