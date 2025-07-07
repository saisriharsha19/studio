
'use client';

import { useState, useTransition, useCallback, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  Bot,
  Loader2,
  Rocket,
  Sparkles,
  Clipboard,
  Check,
  Wrench,
  Lock,
  Globe,
  Plus,
  X,
  Upload,
  Import,
  Lightbulb,
  RotateCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import {
  handleGenerateInitialPrompt,
  handleEvaluateAndIterate,
  handleIterateOnPrompt,
  handleGetPromptSuggestions,
} from '@/app/actions';
import { Badge, badgeVariants } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { useAuth } from '@/hooks/use-auth';
import { Input } from './ui/input';
import { cn } from '@/lib/utils';
import { type EvaluateAndIteratePromptOutput } from '@/ai/flows/evaluate-and-iterate-prompt';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { usePromptHistory } from '@/hooks/use-prompts';
import { usePromptForge } from '@/hooks/use-prompt-forge';
import { useLibrary } from '@/hooks/use-library';

type LoadingStates = {
  generating: boolean;
  evaluating: boolean;
  iterating: boolean;
};

export function PromptForgeClient() {
  const { isAuthenticated } = useAuth();
  const { addPrompt } = usePromptHistory();
  const { addLibraryPrompt } = useLibrary();
  const { toast } = useToast();

  const {
    userNeeds, setUserNeeds,
    currentPrompt, setCurrentPrompt,
    promptsGenerated, setPromptsGenerated,
    knowledgeBase, setKnowledgeBase,
    uploadedFileContent, setUploadedFileContent,
    fewShotExamples, setFewShotExamples,
    knowledgeBaseUrls, setKnowledgeBaseUrls,
    uploadedFileName, setUploadedFileName,
    iterationComments, setIterationComments,
    suggestions, setSuggestions,
    selectedSuggestions, setSelectedSuggestions,
    evaluationResult, setEvaluationResult
  } = usePromptForge();

  const [isDragging, setIsDragging] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const suggestionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isInitialMount = useRef(true);

  const [isPending, startTransition] = useTransition();
  const [loading, setLoading] = useState<LoadingStates>({
    generating: false,
    evaluating: false,
    iterating: false,
  });

  const [copied, setCopied] = useState(false);

  const containerVariants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
    },
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleUrlChange = (index: number, value: string) => {
    const newUrls = [...knowledgeBaseUrls];
    newUrls[index] = value;
    setKnowledgeBaseUrls(newUrls);
  };

  const addUrlField = () => {
    setKnowledgeBaseUrls([...knowledgeBaseUrls, '']);
  };

  const removeUrlField = (index: number) => {
    const newUrls = knowledgeBaseUrls.filter((_, i) => i !== index);
    setKnowledgeBaseUrls(newUrls);
  };

  const processFile = (file: File) => {
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
        const content = event.target?.result as string;
        setUploadedFileContent(content);
        setUploadedFileName(file.name);
        toast({
            title: "File Loaded",
            description: `${file.name} is ready to be used for evaluation.`
        });
    };
    reader.onerror = () => {
        toast({
            variant: 'destructive',
            title: 'Error',
            description: 'Failed to read the file.',
        });
        setUploadedFileName('');
        setUploadedFileContent('');
    };
    reader.readAsText(file);
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    setUploadedFileName('');
    setUploadedFileContent('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragEnter = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  };

  const onGenerate = () => {
    if (!userNeeds) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Please describe your assistant needs first.',
      });
      return;
    }
    setLoading((prev) => ({ ...prev, generating: true }));
    startTransition(async () => {
      try {
        const result = await handleGenerateInitialPrompt({ userNeeds });
        setCurrentPrompt(result.initialPrompt);
        setPromptsGenerated(prev => prev + 1);
        if (isAuthenticated) {
          addPrompt(result.initialPrompt);
        }
        toast({ title: 'Success', description: 'Initial prompt generated.' });
      } catch (error: any) {
        toast({
          variant: 'destructive',
          title: 'Generation Failed',
          description: error.message,
        });
      } finally {
        setLoading((prev) => ({ ...prev, generating: false }));
      }
    });
  };
  
  const handleSuggestionToggle = (suggestion: string) => {
    setSelectedSuggestions(prev =>
      prev.includes(suggestion)
        ? prev.filter(s => s !== suggestion)
        : [...prev, suggestion]
    );
  };

  const getSuggestions = useCallback(() => {
    if (!currentPrompt) {
      return;
    }

    setLoadingSuggestions(true);
    startTransition(async () => {
      try {
        const result = await handleGetPromptSuggestions({
          currentPrompt,
          userComments: iterationComments,
        });
        setSuggestions(result.suggestions);
      } catch (error: any) {
        toast({
          variant: 'destructive',
          title: 'Suggestion Generation Failed',
          description: error.message,
        });
      } finally {
        setLoadingSuggestions(false);
      }
    });
  }, [currentPrompt, iterationComments, toast, setSuggestions]);

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    if (suggestionTimeoutRef.current) {
      clearTimeout(suggestionTimeoutRef.current);
    }
    
    if (promptsGenerated > 0 || currentPrompt) {
      suggestionTimeoutRef.current = setTimeout(() => {
        getSuggestions();
      }, 1000); 
    } else {
        setSuggestions([]);
    }

    return () => {
      if (suggestionTimeoutRef.current) {
        clearTimeout(suggestionTimeoutRef.current);
      }
    };
  }, [currentPrompt, iterationComments, getSuggestions, promptsGenerated, setSuggestions]);

  const onIterate = () => {
    if (!currentPrompt || (!iterationComments && selectedSuggestions.length === 0)) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Please provide feedback or select suggestions before refining.',
      });
      return;
    }
    setLoading((prev) => ({ ...prev, iterating: true }));
    setEvaluationResult(null);
    setSuggestions([]); 
    startTransition(async () => {
      try {
        const result = await handleIterateOnPrompt({
          currentPrompt,
          userComments: iterationComments,
          selectedSuggestions,
        });
        setCurrentPrompt(result.newPrompt);
        if (isAuthenticated) {
          addPrompt(result.newPrompt);
        }
        setIterationComments(''); 
        setSelectedSuggestions([]);
        toast({ title: 'Success', description: 'Prompt refined with your feedback.' });
      } catch (error: any) {
        toast({
          variant: 'destructive',
          title: 'Refinement Failed',
          description: error.message,
        });
      } finally {
        setLoading((prev) => ({ ...prev, iterating: false }));
      }
    });
  };

  const onEvaluate = () => {
    if (!currentPrompt || !userNeeds) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'A prompt and user needs are required for evaluation.',
      });
      return;
    }
    setLoading((prev) => ({ ...prev, evaluating: true }));
    startTransition(async () => {
      try {
        const combinedKnowledge = [knowledgeBase, uploadedFileContent].filter(Boolean).join('\n\n');
        const result = await handleEvaluateAndIterate({
          prompt: currentPrompt,
          userNeeds,
          retrievedContent: combinedKnowledge,
          groundTruths: fewShotExamples,
        });
        setEvaluationResult(result);
        setCurrentPrompt(result.improvedPrompt);
        if (isAuthenticated) {
          addPrompt(result.improvedPrompt);
        }
        toast({ title: 'Success', description: 'Prompt evaluated and improved.' });
      } catch (error: any) {
        toast({
          variant: 'destructive',
          title: 'Evaluation Failed',
          description: error.message,
        });
      } finally {
        setLoading((prev) => ({ ...prev, evaluating: false }));
      }
    });
  };

  const onUploadToLibrary = () => {
    if (!currentPrompt) {
        toast({
            variant: 'destructive',
            title: 'Error',
            description: 'There is no prompt to upload.',
        });
        return;
    }
    addLibraryPrompt(currentPrompt);
  };

  const handleCreateAssistant = () => {
    if (!currentPrompt) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Please generate a prompt first.',
      });
      return;
    }
    navigator.clipboard.writeText(currentPrompt);
    window.open('https://assistant.ai.it.ufl.edu/admin/indexing/status', '_blank', 'noopener,noreferrer');
    toast({
      title: 'Prompt Copied & Portal Opened',
      description: 'The link requires authorization and sign-in.',
    });
  };

  const isLoading = isPending || Object.values(loading).some(Boolean);

  return (
    <TooltipProvider>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-5">
        <div className="space-y-12 lg:col-span-3">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-medium leading-snug">Describe Your Assistant</h2>
              <CardDescription>
                What are the primary goals and functionalities of your AI assistant? You can also provide a knowledge base to ground the assistant.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-10">
              <div className="space-y-4">
                <Label htmlFor="user-needs" className="text-base">User Needs</Label>
                <Textarea
                  id="user-needs"
                  placeholder="e.g., An assistant that helps university students find course information, check deadlines, and book appointments with advisors..."
                  value={userNeeds}
                  onChange={(e) => setUserNeeds(e.target.value)}
                  className="min-h-[120px]"
                />
              </div>
               <div className="space-y-4">
                <Label htmlFor="knowledge-base" className="text-base">Knowledge Base (Optional)</Label>
                <Textarea
                  id="knowledge-base"
                  placeholder="Paste relevant web-scraped data, FAQs, or knowledge base articles here."
                  value={knowledgeBase}
                  onChange={(e) => setKnowledgeBase(e.target.value)}
                  className="min-h-[150px]"
                />
              </div>
            </CardContent>
            <CardFooter>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={onGenerate} disabled={isLoading || loading.generating}>
                    {loading.generating ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <Sparkles />
                    )}
                    {promptsGenerated === 0 ? 'Generate Initial Prompt' : 'Regenerate Initial Prompt'}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Generate a new prompt based on your needs.</p>
                </TooltipContent>
              </Tooltip>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-medium leading-snug">System Prompt</h2>
              <CardDescription>
                This is the generated system prompt. You can manually edit it before evaluation or optimization.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Label htmlFor="system-prompt" className="text-base">Prompt</Label>
              <div className="relative">
                <Textarea
                  id="system-prompt"
                  placeholder="Your generated or refined prompt will appear here."
                  value={currentPrompt}
                  onChange={(e) => setCurrentPrompt(e.target.value)}
                  className="min-h-[200px] pr-12 pb-12"
                />
                {currentPrompt && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute bottom-2 right-2"
                        onClick={() => copyToClipboard(currentPrompt)}
                        aria-label="Copy generated prompt"
                      >
                        {copied ? <Check className="text-primary" /> : <Clipboard />}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Copy prompt</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-medium leading-snug">Advanced Tools</h2>
              {!isAuthenticated && (
                <CardDescription>
                 Log in to access advanced features.
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              {!isAuthenticated ? (
                 <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center">
                    <Lock className="h-10 w-10 text-muted-foreground" />
                    <p className="mt-4 text-muted-foreground">Please log in to use advanced tools.</p>
                </div>
              ) : (
                <div className="space-y-10">
                  <div className="space-y-4">
                    <Label className="text-base">Knowledge Base URLs (Optional)</Label>
                    <div className="space-y-2">
                      {knowledgeBaseUrls.map((url, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <Input
                            id={`knowledge-base-url-${index}`}
                            aria-label={`Knowledge base URL ${index + 1}`}
                            placeholder="https://example.com/knowledge"
                            value={url}
                            onChange={(e) => handleUrlChange(index, e.target.value)}
                          />
                          {knowledgeBaseUrls.length > 1 ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => removeUrlField(index)}
                              className="shrink-0"
                            >
                              <X className="h-4 w-4" />
                              <span className="sr-only">Remove URL {index + 1}</span>
                            </Button>
                          ) : null}
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={addUrlField}
                          >
                            <Plus className="mr-2 h-4 w-4" />
                            Add URL
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Add another URL field for the knowledge base.</p>
                        </TooltipContent>
                      </Tooltip>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="outline" size="sm" onClick={() => toast({ title: "Coming Soon!", description: "Web scraping functionality is not yet implemented."})} aria-disabled="true">
                              <Globe className="mr-2 h-4 w-4"/>
                              Fetch Content
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Scrape content from URLs for the knowledge base.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <Label htmlFor="file-upload" className="text-base">Upload Knowledge File (Optional)</Label>
                      <Label 
                        htmlFor="file-upload" 
                        className={cn(
                            "flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted",
                            isDragging ? "border-primary bg-muted" : "border-border"
                        )}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                      >
                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                            <Upload className="w-8 h-8 mb-4 text-muted-foreground" aria-hidden="true" />
                            <p className="mb-2 text-sm text-muted-foreground">
                                <span className="font-semibold">Click to upload</span> or drag and drop
                            </p>
                            <p className="text-xs text-muted-foreground">TXT, MD, JSON, or CSV</p>
                        </div>
                        <Input 
                            ref={fileInputRef}
                            id="file-upload" 
                            type="file" 
                            className="hidden" 
                            onChange={handleFileChange} 
                            accept=".txt,.md,.json,.csv"
                        />
                    </Label>
                    {uploadedFileName && (
                      <div className="mt-2 flex items-center justify-between rounded-lg border bg-muted/50 px-3 py-2">
                        <p className="truncate pr-4 text-sm text-muted-foreground">
                          {uploadedFileName}
                        </p>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={handleRemoveFile}
                          className="h-6 w-6 shrink-0"
                        >
                          <X className="h-4 w-4" />
                          <span className="sr-only">Remove file</span>
                        </Button>
                      </div>
                    )}
                  </div>

                  <div className="space-y-4">
                    <Label htmlFor="few-shot-examples" className="text-base">Few-shot Examples (Optional)</Label>
                    <Textarea
                      id="few-shot-examples"
                      placeholder="e.g., 'The deadline for Fall 2024 registration is August 15th.' or 'Prof. Smith's office is in Room 301.'"
                      value={fewShotExamples}
                      onChange={(e) => setFewShotExamples(e.target.value)}
                      className="min-h-[100px]"
                    />
                  </div>
                   <div className="flex flex-col items-start gap-4 pt-2">
                      <p className="text-sm text-muted-foreground">
                        This information will be used by the LLM Judge to evaluate and score the prompt's effectiveness.
                      </p>
                      <div className="flex gap-4">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button onClick={onEvaluate} disabled={isLoading || loading.evaluating}>
                              {loading.evaluating ? <Loader2 className="animate-spin" /> : <Bot />}
                              Iterate &amp; Evaluate
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Use AI to evaluate and improve the prompt with context.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-24 space-y-10">
            <Card>
              <CardHeader>
                <h2 className="text-lg font-medium leading-snug">Prompt Refinement</h2>
                <CardDescription>
                  Provide feedback on the current prompt to get AI-generated suggestions for improvement.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {(loadingSuggestions || suggestions.length > 0) && (
                  <div className="mb-6 rounded-md border bg-muted/50 p-4">
                    <div className="mb-4 flex items-center justify-between">
                      <p className="flex items-center text-sm font-medium">
                        <Lightbulb className="mr-2 h-5 w-5" />
                        AI Suggestions:
                      </p>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={getSuggestions}
                            disabled={loadingSuggestions}
                            className="h-6 w-6"
                            aria-label="Regenerate AI suggestions"
                          >
                            <RotateCw
                              className={`h-4 w-4 ${
                                loadingSuggestions ? 'animate-spin' : ''
                              }`}
                            />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Regenerate AI suggestions</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    {loadingSuggestions ? (
                      <div className="flex flex-wrap gap-2">
                        <Skeleton className="h-7 w-24 rounded-full" />
                        <Skeleton className="h-7 w-32 rounded-full" />
                        <Skeleton className="h-7 w-28 rounded-full" />
                      </div>
                    ) : (
                      <motion.div
                        className="flex flex-wrap gap-2"
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                      >
                        {suggestions.map((suggestion, index) => (
                          <motion.div key={index} variants={itemVariants}>
                            <button
                              type="button"
                              onClick={() => handleSuggestionToggle(suggestion)}
                              aria-pressed={selectedSuggestions.includes(suggestion)}
                              className={cn(badgeVariants({ variant: selectedSuggestions.includes(suggestion) ? 'default' : 'secondary' }), "cursor-pointer items-center transition-all hover:opacity-80 text-xs px-3 py-1 font-normal")}
                            >
                              {selectedSuggestions.includes(suggestion) && (
                                <Check className="mr-1.5 h-4 w-4" />
                              )}
                              {suggestion}
                            </button>
                          </motion.div>
                        ))}
                      </motion.div>
                    )}
                  </div>
                )}
                <div className="space-y-4">
                  <Label htmlFor="iteration-comments" className="text-base">Your Feedback &amp; Comments</Label>
                  <Textarea
                    id="iteration-comments"
                    placeholder="e.g., 'Make it more concise' or 'Add a rule to always ask for the user's name.'"
                    value={iterationComments}
                    onChange={(e) => setIterationComments(e.target.value)}
                    className="min-h-[100px]"
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={onIterate}
                      disabled={
                        isLoading ||
                        loading.iterating ||
                        !currentPrompt ||
                        (!iterationComments && selectedSuggestions.length === 0)
                      }
                    >
                      {loading.iterating ? <Loader2 className="animate-spin" /> : <Wrench />}
                      Refine with AI
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Refine the prompt using your feedback & suggestions.</p>
                  </TooltipContent>
                </Tooltip>
              </CardFooter>
            </Card>

            {isAuthenticated ? (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-medium leading-snug">Evaluation &amp; Deployment</h2>
                  <CardDescription>
                    Review the results from our AI evaluator and deploy your agent.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div aria-live="polite" aria-atomic="true">
                    {loading.evaluating ? (
                      <Skeleton className="h-40 w-full" />
                    ) : evaluationResult ? (
                      <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="bias">
                          <AccordionTrigger>
                            <div className="flex w-full items-center justify-between pr-4">
                              <span>Bias</span>
                              <Badge
                                variant={
                                  evaluationResult.bias.score > 0.7
                                    ? 'default'
                                    : 'destructive'
                                }
                              >
                                Score: {Math.round(evaluationResult.bias.score * 100)}%
                              </Badge>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="space-y-4 px-1">
                            <div>
                              <p className="text-sm font-medium">Summary:</p>
                              <p className="text-sm text-muted-foreground">
                                {evaluationResult.bias.summary}
                              </p>
                            </div>
                            <div>
                              <p className="text-sm font-medium">Test Cases:</p>
                              <ul className="list-disc pl-5 text-sm text-muted-foreground">
                                {evaluationResult.bias.testCases.map((tc, i) => (
                                  <li key={i}>{tc}</li>
                                ))}
                              </ul>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                        <AccordionItem value="toxicity">
                          <AccordionTrigger>
                            <div className="flex w-full items-center justify-between pr-4">
                              <span>Toxicity</span>
                              <Badge
                                variant={
                                  evaluationResult.toxicity.score > 0.7
                                    ? 'default'
                                    : 'destructive'
                                }
                              >
                                Score: {Math.round(evaluationResult.toxicity.score * 100)}%
                              </Badge>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="space-y-4 px-1">
                            <div>
                              <p className="text-sm font-medium">Summary:</p>
                              <p className="text-sm text-muted-foreground">
                                {evaluationResult.toxicity.summary}
                              </p>
                            </div>
                            <div>
                              <p className="text-sm font-medium">Test Cases:</p>
                              <ul className="list-disc pl-5 text-sm text-muted-foreground">
                                {evaluationResult.toxicity.testCases.map((tc, i) => (
                                  <li key={i}>{tc}</li>
                                ))}
                              </ul>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                        <AccordionItem value="alignment">
                          <AccordionTrigger>
                            <div className="flex w-full items-center justify-between pr-4">
                              <span>Prompt Alignment</span>
                              <Badge
                                variant={
                                  evaluationResult.promptAlignment.score > 0.7
                                    ? 'default'
                                    : 'destructive'
                                }
                              >
                                Score: {Math.round(evaluationResult.promptAlignment.score * 100)}%
                              </Badge>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="space-y-4 px-1">
                            <div>
                              <p className="text-sm font-medium">Summary:</p>
                              <p className="text-sm text-muted-foreground">
                                {evaluationResult.promptAlignment.summary}
                              </p>
                            </div>
                            <div>
                              <p className="text-sm font-medium">Test Cases:</p>
                              <ul className="list-disc pl-5 text-sm text-muted-foreground">
                                {evaluationResult.promptAlignment.testCases.map(
                                  (tc, i) => (
                                    <li key={i}>{tc}</li>
                                  )
                                )}
                              </ul>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                        {evaluationResult.faithfulness && (
                          <AccordionItem value="faithfulness">
                            <AccordionTrigger>
                              <div className="flex w-full items-center justify-between pr-4">
                                <span>Faithfulness</span>
                                <Badge
                                  variant={
                                    evaluationResult.faithfulness.score > 0.7
                                      ? 'default'
                                      : 'destructive'
                                  }
                                >
                                  Score: {Math.round(evaluationResult.faithfulness.score * 100)}%
                                </Badge>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-4 px-1">
                              <div>
                                <p className="text-sm font-medium">Summary:</p>
                                <p className="text-sm text-muted-foreground">
                                  {evaluationResult.faithfulness.summary}
                                </p>
                              </div>
                              <div>
                                <p className="text-sm font-medium">Test Cases:</p>
                                <ul className="list-disc pl-5 text-sm text-muted-foreground">
                                  {evaluationResult.faithfulness.testCases.map(
                                    (tc, i) => (
                                      <li key={i}>{tc}</li>
                                    )
                                  )}
                                </ul>
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        )}
                      </Accordion>
                    ) : (
                      <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center">
                          <p className="text-muted-foreground">Your evaluation results will appear here.</p>
                      </div>
                    )}
                  </div>
                </CardContent>
                <CardFooter className="flex flex-col gap-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                        disabled={isLoading || !currentPrompt}
                        onClick={handleCreateAssistant}
                      >
                        <Rocket />
                        Create NaviGator Assistant
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Copies the prompt and opens the NaviGator Assistant portal.</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                        disabled={isLoading || !currentPrompt}
                        onClick={onUploadToLibrary}
                      >
                        <Upload />
                        Upload to Prompt Library 
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Share this prompt with the community by adding it to the public library.</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                        disabled={isLoading || !currentPrompt}
                        onClick={() => toast({ title: "Coming Soon!", description: "This would import the prompt into the NaviGator Builder." })}
                      >
                        <Import />
                        Import to NaviGator Builder
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Open this prompt in the NaviGator Builder for further customization.</p>
                    </TooltipContent>
                  </Tooltip>
                </CardFooter>
              </Card>
            ) : (
              <Card>
                <CardHeader>
                    <h2 className="text-lg font-medium leading-snug">Evaluation &amp; Deployment</h2>
                    <CardDescription>
                        Log in to view evaluation results and deploy your agent.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center">
                        <Lock className="h-10 w-10 text-muted-foreground" />
                        <p className="mt-4 text-muted-foreground">Please log in to use these tools.</p>
                    </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
