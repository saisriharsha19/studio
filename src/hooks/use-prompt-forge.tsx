
'use client';

import type { EvaluateAndIteratePromptOutput } from '@/ai/flows/evaluate-and-iterate-prompt';
import { createContext, useContext, useState, ReactNode, Dispatch, SetStateAction, useEffect } from 'react';

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
  sitemapUrl: string;
  setSitemapUrl: Dispatch<SetStateAction<string>>;
  includeSubdomains: boolean;
  setIncludeSubdomains: Dispatch<SetStateAction<boolean>>;
  maxSubdomains: number;
  setMaxSubdomains: Dispatch<SetStateAction<number>>;
  maxPages: number;
  setMaxPages: Dispatch<SetStateAction<number>>;
  preferSitemap: boolean;
  setPreferSitemap: Dispatch<SetStateAction<boolean>>;
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
  const [sitemapUrl, setSitemapUrl] = useState('');
  const [includeSubdomains, setIncludeSubdomains] = useState(false);
  const [maxSubdomains, setMaxSubdomains] = useState(10);
  const [maxPages, setMaxPages] = useState(100);
  const [preferSitemap, setPreferSitemap] = useState(true);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [iterationComments, setIterationComments] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([]);
  const [evaluationResult, setEvaluationResult] = useState<EvaluateAndIteratePromptOutput | null>(null);

  // Effect to append document context to the prompt
  useEffect(() => {
    if (uploadedFileContent) {
      const contextBlock = `\n\n--- [DOCUMENT CONTEXT] ---\n${uploadedFileContent}`;
      
      setCurrentPrompt(prevPrompt => {
        // Remove old context block if it exists to prevent duplication
        const oldContextIndex = prevPrompt.indexOf('\n\n--- [DOCUMENT CONTEXT] ---');
        const basePrompt = oldContextIndex !== -1 ? prevPrompt.substring(0, oldContextIndex) : prevPrompt;
        return basePrompt + contextBlock;
      });
    }
  }, [uploadedFileContent, setCurrentPrompt]);


  const value = {
    userNeeds, setUserNeeds,
    currentPrompt, setCurrentPrompt,
    promptsGenerated, setPromptsGenerated,
    knowledgeBase, setKnowledgeBase,
    uploadedFileContent, setUploadedFileContent,
    fewShotExamples, setFewShotExamples,
    scrapeUrl, setScrapeUrl,
    sitemapUrl, setSitemapUrl,
    includeSubdomains, setIncludeSubdomains,
    maxSubdomains, setMaxSubdomains,
    maxPages, setMaxPages,
    preferSitemap, setPreferSitemap,
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

    