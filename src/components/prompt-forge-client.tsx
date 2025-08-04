
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
  Clock,
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
  handleEvaluatePrompt,
  handleGetPromptSuggestions,
  getTaskResult,
  type TaskStatusResponse,
} from '@/app/actions';
import { Badge, badgeVariants } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { useAuth } from '@/hooks/use-auth';
import { Input } from './ui/input';
import { cn } from '@/lib/utils';
import type { EvaluateAndIteratePromptOutput } from '@/ai/flows/evaluate-and-iterate-prompt';
import type { GeneratePromptSuggestionsOutput } from '@/ai/flows/get-prompt-suggestions';
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
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';

type ActionType = 'generate' | 'evaluate' | 'suggest' | 'iterate' | 'scrape' | null;

type LoadingState = {
  inProgress: boolean;
  action: ActionType;
  statusText: string;
};

// Helper to format metric names for display
const formatMetricName = (name: string) => {
  return name.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase());
};

export function PromptForgeClient() {
  const { isAuthenticated, userId } = useAuth();
  const { addPrompt } = usePromptHistory();
  const { addLibraryPrompt } = useLibrary();
  const { toast } = useToast();

  const {
    userNeeds, setUserNeeds,
    currentPrompt, setCurrentPrompt,
    knowledgeBase, setKnowledgeBase,
    uploadedFileContent, setUploadedFileContent,
    fewShotExamples, setFewShotExamples,
    uploadedFileName, setUploadedFileName,
    iterationComments, setIterationComments,
    suggestions, setSuggestions,
    selectedSuggestions, setSelectedSuggestions,
    evaluationResult, setEvaluationResult
  } = usePromptForge();

  const [loadingState, setLoadingState] = useState<LoadingState>({
    inProgress: false,
    action: null,
    statusText: '',
  });

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

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

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  const pollTaskStatus = (status_url: string, actionType: ActionType) => {
    stopPolling(); // Stop any existing polling

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const task: TaskStatusResponse = await getTaskResult(status_url);

        if (task.status === 'SUCCESS') {
          stopPolling();
          setLoadingState({ inProgress: false, action: null, statusText: 'Completed!' });
          toast({ title: 'Success', description: `${actionType} task completed.` });

          // Handle the result based on the action type
          if (actionType === 'generate' && task.result) {
            const result = task.result as any;
            setCurrentPrompt(result.initial_prompt);
            if (isAuthenticated) addPrompt(result.initial_prompt);
          } else if (actionType === 'evaluate' && task.result) {
            const result = task.result as EvaluateAndIteratePromptOutput;
            setEvaluationResult(result);
            setCurrentPrompt(result.improved_prompt); // The backend now returns an improved prompt
            if (isAuthenticated) addPrompt(result.improved_prompt);
          } else if (actionType === 'suggest' && task.result) {
            const result = task.result as GeneratePromptSuggestionsOutput;
            setSuggestions(result.map(s => s.description));
          }

        } else if (task.status === 'FAILURE') {
          stopPolling();
          setLoadingState({ inProgress: false, action: null, statusText: 'Failed!' });
          toast({ variant: 'destructive', title: 'Task Failed', description: task.error_message || 'An unknown error occurred.' });
        } else if (task.status === 'PENDING' || task.status === 'STARTED') {
          setLoadingState(prev => ({ ...prev, statusText: `Processing... (${task.status.toLowerCase()})` }));
        }
      } catch (error) {
        stopPolling();
        setLoadingState({ inProgress: false, action: null, statusText: 'Error!' });
        toast({ variant: 'destructive', title: 'Polling Error', description: getErrorMessage(error) });
      }
    }, 3000); // Poll every 3 seconds
  };

  useEffect(() => {
    // Cleanup polling on component unmount
    return () => stopPolling();
  }, []);
  
  const onGenerate = async () => {
    if (!userNeeds) {
      toast({ variant: 'destructive', title: 'Error', description: 'Please describe your assistant needs first.' });
      return;
    }
    setLoadingState({ inProgress: true, action: 'generate', statusText: 'Starting generation task...' });
    try {
      const task = await handleGenerateInitialPrompt({ user_needs: userNeeds });
      setLoadingState(prev => ({ ...prev, statusText: 'Task initiated, awaiting result...' }));
      pollTaskStatus(task.status_url, 'generate');
    } catch (error) {
      setLoadingState({ inProgress: false, action: null, statusText: 'Failed to start task.' });
      toast({ variant: 'destructive', title: 'Generation Failed', description: getErrorMessage(error) });
    }
  };

  const onEvaluate = async () => {
    if (!currentPrompt || !userNeeds) {
      toast({ variant: 'destructive', title: 'Error', description: 'A prompt and user needs are required for evaluation.' });
      return;
    }
    setLoadingState({ inProgress: true, action: 'evaluate', statusText: 'Starting evaluation task...' });
    setEvaluationResult(null); // Clear previous results
    try {
      const task = await handleEvaluatePrompt({ prompt: currentPrompt, user_needs: userNeeds });
      setLoadingState(prev => ({ ...prev, statusText: 'Task initiated, awaiting evaluation...' }));
      pollTaskStatus(task.status_url, 'evaluate');
    } catch (error) {
      setLoadingState({ inProgress: false, action: null, statusText: 'Failed to start task.' });
      toast({ variant: 'destructive', title: 'Evaluation Failed', description: getErrorMessage(error) });
    }
  };

  const getSuggestions = useCallback(async () => {
    if (!currentPrompt) return;

    setLoadingState({ inProgress: true, action: 'suggest', statusText: 'Getting suggestions...' });
    try {
      const task = await handleGetPromptSuggestions({
        current_prompt: currentPrompt,
        user_comments: iterationComments,
      });
      setLoadingState(prev => ({ ...prev, statusText: 'Task initiated, awaiting suggestions...' }));
      pollTaskStatus(task.status_url, 'suggest');
    } catch (error) {
      setLoadingState({ inProgress: false, action: null, statusText: 'Failed to get suggestions.' });
      toast({ variant: 'destructive', title: 'Suggestion Failed', description: getErrorMessage(error) });
    }
  }, [currentPrompt, iterationComments]);

  // The new backend has no dedicated "iterate" endpoint.
  // Iteration is now a client-side concept: apply suggestions to the current prompt text.
  const onIterate = () => {
    if (!currentPrompt || (!iterationComments && selectedSuggestions.length === 0)) {
      toast({ variant: 'destructive', title: 'Error', description: 'Please provide feedback or select suggestions before refining.' });
      return;
    }
    
    // Simulate an iteration by just appending comments/suggestions to the prompt for re-evaluation.
    // A more sophisticated implementation might try to intelligently merge them.
    const feedbackText = `
---
USER FEEDBACK FOR REFINEMENT:
Comments: ${iterationComments}
Selected Suggestions:
- ${selectedSuggestions.join('\n- ')}
---
    `;
    setCurrentPrompt(prev => `${prev}\n${feedbackText}`);
    setIterationComments('');
    setSelectedSuggestions([]);
    setSuggestions([]);
    toast({ title: 'Feedback Applied', description: 'Your feedback has been added to the prompt. You can now re-evaluate it.' });
  };
  
  const handleSuggestionToggle = (suggestion: string) => {
    setSelectedSuggestions(prev =>
      prev.includes(suggestion)
        ? prev.filter(s => s !== suggestion)
        : [...prev, suggestion]
    );
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
    if (!userId) {
        toast({ variant: 'destructive', title: 'Authentication Error', description: 'You must be logged in to upload to the library.'});
        return;
    }
    addLibraryPrompt(currentPrompt);
  };

  const handleCreateAssistant = () => {
    if (!currentPrompt) {
      toast({ variant: 'destructive', title: 'Error', description: 'Please generate a prompt first.' });
      return;
    }

    navigator.clipboard.writeText(currentPrompt);
    window.open('https://assistant.ai.it.ufl.edu/admin/assistants/new', '_blank', 'noopener,noreferrer');
    
    toast({
      title: 'Prompt Copied!',
      description: 'The prompt has been copied. Please paste it into the portal.',
      duration: 5000,
    });
  };
  
  return (
    <TooltipProvider>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-5 lg:gap-12">
        <div className="space-y-12 lg:col-span-3">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-medium leading-snug">Describe Your Assistant</h2>
              <CardDescription>
                What are the primary goals and functionalities of your AI assistant?
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
                  disabled={loadingState.inProgress}
                />
              </div>
            </CardContent>
            <CardFooter>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={onGenerate} disabled={loadingState.inProgress || !userNeeds}>
                    {loadingState.inProgress && loadingState.action === 'generate' ? <Loader2 className="animate-spin" /> : <Sparkles />}
                    Generate Initial Prompt
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
                This is the generated system prompt. You can manually edit it before evaluation or refinement.
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
                  className="min-h-[200px] pr-12"
                  disabled={loadingState.inProgress}
                />
                {currentPrompt && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute top-3 right-3 h-8 w-8"
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
            <CardFooter>
                <Button onClick={onEvaluate} disabled={loadingState.inProgress || !currentPrompt || !userNeeds}>
                    {loadingState.inProgress && loadingState.action === 'evaluate' ? <Loader2 className="animate-spin" /> : <Bot />}
                    Evaluate Prompt
                </Button>
            </CardFooter>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-24 space-y-10">
            {loadingState.inProgress && (
              <Card className="border-primary">
                <CardHeader className="flex-row items-center gap-4 space-y-0">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <div>
                    <h2 className="text-lg font-medium capitalize leading-snug">{loadingState.action} in Progress</h2>
                    <CardDescription className="mt-1.5">{loadingState.statusText}</CardDescription>
                  </div>
                </CardHeader>
              </Card>
            )}

            <Card>
              <CardHeader>
                <h2 className="text-lg font-medium leading-snug">Prompt Refinement</h2>
                <CardDescription>
                  Provide feedback on the current prompt to get AI-generated suggestions for improvement.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
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
                          disabled={loadingState.inProgress || !currentPrompt}
                          className="h-6 w-6"
                          aria-label="Regenerate AI suggestions"
                        >
                          <RotateCw
                            className={cn('h-4 w-4', loadingState.inProgress && loadingState.action === 'suggest' && 'animate-spin')}
                          />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Get AI suggestions</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  {suggestions.length > 0 ? (
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
                  ) : (
                    <p className="text-sm text-muted-foreground">Click the refresh icon to get suggestions.</p>
                  )}
                </div>
                
                <div className="space-y-4">
                  <Label htmlFor="iteration-comments" className="text-base">Your Feedback &amp; Comments</Label>
                  <Textarea
                    id="iteration-comments"
                    placeholder="e.g., 'Make it more concise' or 'Add a rule to always ask for the user's name.'"
                    value={iterationComments}
                    onChange={(e) => setIterationComments(e.target.value)}
                    className="min-h-[100px]"
                    disabled={loadingState.inProgress}
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={onIterate}
                      disabled={loadingState.inProgress || !currentPrompt || (!iterationComments && selectedSuggestions.length === 0)}
                    >
                      <Wrench />
                      Apply Feedback to Prompt
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Applies your feedback to the prompt text for re-evaluation.</p>
                  </TooltipContent>
                </Tooltip>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="text-lg font-medium leading-snug">Evaluation &amp; Deployment</h2>
                <CardDescription>
                  Review the results from our AI evaluator and deploy your agent.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div aria-live="polite" aria-atomic="true">
                  {evaluationResult ? (
                    <Accordion type="single" collapsible className="w-full" defaultValue='promptAlignment'>
                      {Object.entries(evaluationResult).map(([key, value]) => {
                        if (typeof value !== 'object' || value === null || !('score' in value)) return null;
                        
                        const metric = value as { score: number | null; summary: string | null };
                        const score = metric.score;

                        return (
                          <AccordionItem value={key} key={key}>
                            <AccordionTrigger>
                              <div className="flex w-full items-center justify-between pr-4">
                                <span>{formatMetricName(key)}</span>
                                {typeof score === 'number' ? (
                                  <Badge variant={score > 0.7 ? 'default' : score > 0.4 ? 'secondary' : 'destructive'}>
                                    {Math.round(score * 100)}%
                                  </Badge>
                                ) : (
                                  <Badge variant="secondary">N/A</Badge>
                                )}
                              </div>
                            </AccordionTrigger>
                            <AccordionContent className="space-y-4 px-1">
                              {metric.summary && (
                                <div>
                                  <p className="text-sm font-medium">Summary:</p>
                                  <p className="text-sm text-muted-foreground">
                                    {metric.summary}
                                  </p>
                                </div>
                              )}
                            </AccordionContent>
                          </AccordionItem>
                        );
                      })}
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
                      disabled={loadingState.inProgress || !currentPrompt}
                      onClick={handleCreateAssistant}
                    >
                      <Rocket />
                      Create NaviGator Assistant
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Copies prompt and opens the NaviGator Assistant portal.</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                      disabled={loadingState.inProgress || !currentPrompt}
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
              </CardFooter>
            </Card>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
