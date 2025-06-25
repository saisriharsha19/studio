
'use client';

import { useState, useTransition, useCallback, useEffect, useRef } from 'react';
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
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
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { useAuth } from '@/hooks/use-auth';
import { Input } from './ui/input';
import { cn } from '@/lib/utils';

type LoadingStates = {
  generating: boolean;
  evaluating: boolean;
  iterating: boolean;
};

export function PromptForgeClient() {
  const { isAuthenticated } = useAuth();
  const [userNeeds, setUserNeeds] = useState('');
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [promptsGenerated, setPromptsGenerated] = useState(0);
  const [knowledgeBase, setKnowledgeBase] = useState('');
  const [fewShotExamples, setFewShotExamples] = useState('');
  const [knowledgeBaseUrls, setKnowledgeBaseUrls] = useState(['']);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [iterationComments, setIterationComments] = useState('');
  
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const suggestionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [evaluationResult, setEvaluationResult] = useState<{
    improvedPrompt: string;
    relevancyScore: number;
    evaluationSummary: string;
  } | null>(null);

  const [isPending, startTransition] = useTransition();
  const [loading, setLoading] = useState<LoadingStates>({
    generating: false,
    evaluating: false,
    iterating: false,
  });

  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

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

    setUploadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
        const content = event.target?.result as string;
        setKnowledgeBase(prev => 
            prev 
            ? `${prev}\n\n--- From file: ${file.name} ---\n${content}`
            : `--- From file: ${file.name} ---\n${content}`
        );
        toast({
            title: "File Loaded",
            description: `Content from ${file.name} has been added to the knowledge base.`
        });
    };
    reader.onerror = () => {
        toast({
            variant: 'destructive',
            title: 'Error',
            description: 'Failed to read the file.',
        });
        setUploadedFileName('');
    };
    reader.readAsText(file);
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
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
  }, [currentPrompt, iterationComments, toast]);

  useEffect(() => {
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
  }, [currentPrompt, iterationComments, getSuggestions, promptsGenerated]);

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
    if (!currentPrompt || !userNeeds || !knowledgeBase || !fewShotExamples) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'All fields are required for evaluation.',
      });
      return;
    }
    setLoading((prev) => ({ ...prev, evaluating: true }));
    startTransition(async () => {
      try {
        const result = await handleEvaluateAndIterate({
          prompt: currentPrompt,
          userNeeds,
          retrievedContent: knowledgeBase,
          groundTruths: fewShotExamples,
        });
        setEvaluationResult(result);
        setCurrentPrompt(result.improvedPrompt);
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

  const isLoading = isPending || Object.values(loading).some(Boolean);

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-5">
      <div className="space-y-10 lg:col-span-3">
        <Card>
          <CardHeader>
            <CardTitle>Describe Your Assistant</CardTitle>
            <CardDescription>
              What are the primary goals and functionalities of your AI assistant? You can also provide a knowledge base to ground the assistant.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <Label htmlFor="user-needs" className="mb-2 block">User Needs</Label>
              <Textarea
                id="user-needs"
                placeholder="e.g., An assistant that helps university students find course information, check deadlines, and book appointments with advisors..."
                value={userNeeds}
                onChange={(e) => setUserNeeds(e.target.value)}
                className="min-h-[120px]"
              />
            </div>
             <div>
              <Label htmlFor="knowledge-base" className="mb-2 block">Knowledge Base</Label>
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
            <Button onClick={onGenerate} disabled={isLoading || loading.generating || promptsGenerated > 0}>
              {loading.generating ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Sparkles />
              )}
              Generate Initial Prompt
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Prompt</CardTitle>
            <CardDescription>
              This is the generated system prompt. You can manually edit it before evaluation or optimization.
            </CardDescription>
          </CardHeader>
          <CardContent className="relative">
            <Label htmlFor="system-prompt" className="mb-2 block">Prompt</Label>
            <Textarea
              id="system-prompt"
              placeholder="Your generated or refined prompt will appear here."
              value={currentPrompt}
              onChange={(e) => setCurrentPrompt(e.target.value)}
              className="min-h-[200px] pr-12 pb-8"
            />
            {currentPrompt && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute bottom-5 right-2"
                onClick={() => copyToClipboard(currentPrompt)}
              >
                {copied ? <Check className="text-primary" /> : <Clipboard />}
              </Button>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Advanced Tools</CardTitle>
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
              <div className="space-y-6">
                <div>
                  <Label className="mb-2 block">Knowledge Base URLs</Label>
                  <div className="space-y-2">
                    {knowledgeBaseUrls.map((url, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <Input
                          id={`knowledge-base-url-${index}`}
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
                            <span className="sr-only">Remove URL</span>
                          </Button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addUrlField}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Add URL
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => toast({ title: "Coming Soon!", description: "Web scraping functionality is not yet implemented."})}>
                        <Globe/>
                        Fetch Content
                    </Button>
                  </div>
                </div>

                <div>
                  <Label htmlFor="file-upload" className="mb-2 block">Upload Knowledge File</Label>
                    <Label 
                      htmlFor="file-upload" 
                      className={cn(
                          "mt-2 flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted",
                          isDragging ? "border-primary bg-muted" : "border-border"
                      )}
                      onDragEnter={handleDragEnter}
                      onDragLeave={handleDragLeave}
                      onDragOver={handleDragOver}
                      onDrop={handleDrop}
                    >
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                          <Upload className="w-8 h-8 mb-4 text-muted-foreground" />
                          <p className="mb-2 text-sm text-muted-foreground">
                              <span className="font-semibold">Click to upload</span> or drag and drop
                          </p>
                          <p className="text-xs text-muted-foreground">TXT, MD, JSON, or CSV</p>
                      </div>
                      <Input 
                          id="file-upload" 
                          type="file" 
                          className="hidden" 
                          onChange={handleFileChange} 
                          accept=".txt,.md,.json,.csv"
                      />
                  </Label>
                  {uploadedFileName && (
                      <p className="mt-2 text-sm text-muted-foreground">
                          Loaded: {uploadedFileName}
                      </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="few-shot-examples" className="mb-2 block">Few-shot Examples</Label>
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
                      <Button onClick={onEvaluate} disabled={isLoading || loading.evaluating}>
                        {loading.evaluating ? <Loader2 className="animate-spin" /> : <Bot />}
                        Iterate &amp; Evaluate
                      </Button>
                    </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-10 lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>Prompt Refinement</CardTitle>
            <CardDescription>
              Provide feedback on the current prompt to get AI-generated suggestions for improvement.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {(loadingSuggestions || suggestions.length > 0) && (
              <div className="mb-6 rounded-md border bg-muted/50 p-4">
                <p className="mb-4 text-sm font-medium">AI Suggestions:</p>
                {loadingSuggestions ? (
                  <div className="flex flex-wrap gap-2">
                    <Skeleton className="h-7 w-24 rounded-full" />
                    <Skeleton className="h-7 w-32 rounded-full" />
                    <Skeleton className="h-7 w-28 rounded-full" />
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {suggestions.map((suggestion, index) => (
                      <Badge
                        key={index}
                        variant={selectedSuggestions.includes(suggestion) ? 'default' : 'secondary'}
                        onClick={() => handleSuggestionToggle(suggestion)}
                        className="cursor-pointer items-center transition-all hover:opacity-80 text-sm px-3 py-1"
                      >
                        {selectedSuggestions.includes(suggestion) && (
                          <Check className="mr-1.5 h-4 w-4" />
                        )}
                        {suggestion}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div>
              <Label htmlFor="iteration-comments" className="mb-2 block">Your Feedback &amp; Comments</Label>
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
          </CardFooter>
        </Card>

        {isAuthenticated ? (
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Evaluation &amp; Deployment</CardTitle>
              <CardDescription>
                Review the results from our AI evaluator and deploy your agent.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {loading.evaluating ? <Skeleton className="h-40 w-full" /> : evaluationResult && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Evaluation</span>
                      <Badge variant={evaluationResult.relevancyScore > 0.7 ? "default" : "destructive"}>
                        Score: {Math.round(evaluationResult.relevancyScore * 100)}%
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm font-medium">Summary:</p>
                    <p className="text-sm text-muted-foreground">{evaluationResult.evaluationSummary}</p>
                  </CardContent>
                </Card>
              )}

              {!loading.evaluating && !evaluationResult && (
                <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center">
                    <p className="text-muted-foreground">Your evaluation results will appear here.</p>
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button
                className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                disabled={isLoading || !currentPrompt}
                onClick={() => toast({ title: "Onyx Integration", description: "This would trigger agent creation in the Onyx (Danswer) system." })}
              >
                <Rocket />
                Create NaviGator Assistant 
              </Button>
              <Button
                className="w-full text-accent-foreground hover:bg-accent/90"
                disabled={isLoading || !currentPrompt}
                onClick={() => toast({ title: "Onyx Integration", description: "This would trigger agent creation in the Onyx (Danswer) system." })}
              >
                <Upload />
                Upload to Prompt Library 
              </Button>
              <Button
                className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
                disabled={isLoading || !currentPrompt}
                onClick={() => toast({ title: "Coming Soon!", description: "This would import the prompt into the NaviGator Builder." })}
              >
                <Import />
                Import to NaviGator Builder
              </Button>
            </CardFooter>
          </Card>
        ) : (
          <Card>
            <CardHeader>
                <CardTitle>Evaluation &amp; Deployment</CardTitle>
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
  );
}
