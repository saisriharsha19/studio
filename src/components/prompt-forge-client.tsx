'use client';

import { useState, useTransition } from 'react';
import {
  Bot,
  Loader2,
  Rocket,
  Sparkles,
  Clipboard,
  Check,
  Lightbulb,
  Lock,
  Globe,
  Plus,
  X,
  Upload,
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
  handleOptimizeWithContext,
} from '@/app/actions';
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { useAuth } from '@/hooks/use-auth';
import { Input } from './ui/input';

type LoadingStates = {
  generating: boolean;
  evaluating: boolean;
  optimizing: boolean;
};

export function PromptForgeClient() {
  const { isAuthenticated } = useAuth();
  const [userNeeds, setUserNeeds] = useState('');
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [knowledgeBase, setKnowledgeBase] = useState('');
  const [fewShotExamples, setFewShotExamples] = useState('');
  const [knowledgeBaseUrls, setKnowledgeBaseUrls] = useState(['']);
  const [uploadedFileName, setUploadedFileName] = useState('');


  const [evaluationResult, setEvaluationResult] = useState<{
    improvedPrompt: string;
    relevancyScore: number;
    evaluationSummary: string;
  } | null>(null);

  const [optimizationResult, setOptimizationResult] = useState<{
    optimizedPrompt: string;
    reasoning: string;
  } | null>(null);

  const [isPending, startTransition] = useTransition();
  const [loading, setLoading] = useState<LoadingStates>({
    generating: false,
    evaluating: false,
    optimizing: false,
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
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
    setOptimizationResult(null);
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
  
  const onOptimize = () => {
    if (!currentPrompt || !knowledgeBase || !fewShotExamples) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Prompt, knowledge base, and few-shot examples are required for optimization.',
      });
      return;
    }
    setLoading((prev) => ({ ...prev, optimizing: true }));
    setEvaluationResult(null);
    startTransition(async () => {
      try {
        const result = await handleOptimizeWithContext({
          prompt: currentPrompt,
          retrievedContent: knowledgeBase,
          groundTruths: fewShotExamples,
        });
        setOptimizationResult(result);
        setCurrentPrompt(result.optimizedPrompt);
        toast({ title: 'Success', description: 'Prompt optimized with context.' });
      } catch (error: any) {
        toast({
          variant: 'destructive',
          title: 'Optimization Failed',
          description: error.message,
        });
      } finally {
        setLoading((prev) => ({ ...prev, optimizing: false }));
      }
    });
  };

  const isLoading = isPending || Object.values(loading).some(Boolean);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-3">
        <Card>
          <CardHeader>
            <CardTitle>1. Describe Your Assistant & Provide Knowledge</CardTitle>
            <CardDescription>
              What are the primary goals and functionalities of your AI assistant? You can also provide a knowledge base to ground the assistant.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="user-needs">User Needs</Label>
              <Textarea
                id="user-needs"
                placeholder="e.g., An assistant that helps university students find course information, check deadlines, and book appointments with advisors..."
                value={userNeeds}
                onChange={(e) => setUserNeeds(e.target.value)}
                className="min-h-[120px]"
              />
            </div>
             <div>
              <Label htmlFor="knowledge-base">Knowledge Base</Label>
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
            <Button onClick={onGenerate} disabled={isLoading || loading.generating}>
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
            <CardTitle>2. System Prompt</CardTitle>
            <CardDescription>
              This is the generated system prompt. You can manually edit it before evaluation or optimization.
            </CardDescription>
          </CardHeader>
          <CardContent className="relative">
            <Label htmlFor="system-prompt">Prompt</Label>
            <Textarea
              id="system-prompt"
              placeholder="Your generated or refined prompt will appear here."
              value={currentPrompt}
              onChange={(e) => setCurrentPrompt(e.target.value)}
              className="min-h-[200px] pr-12"
            />
            {currentPrompt && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute bottom-8 right-8"
                onClick={() => copyToClipboard(currentPrompt)}
              >
                {copied ? <Check className="text-primary" /> : <Clipboard />}
              </Button>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. Advanced Tools</CardTitle>
            {!isAuthenticated && (
              <CardDescription>
               Log in to access advanced features like evaluation, optimization, and web scraping.
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
              <div className="space-y-4">
                <div>
                  <Label>Knowledge Base URLs</Label>
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
                  <div className="mt-2 flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addUrlField}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Add URL
                    </Button>
                    <Button variant="outline" onClick={() => toast({ title: "Coming Soon!", description: "Web scraping functionality is not yet implemented."})}>
                        <Globe/>
                        Fetch Content
                    </Button>
                  </div>
                </div>

                <div>
                  <Label htmlFor="file-upload">Or Upload Knowledge File</Label>
                  <div className="mt-2">
                      <Input 
                          id="file-upload" 
                          type="file" 
                          onChange={handleFileChange} 
                          accept=".txt,.md,.json,.csv"
                      />
                  </div>
                  {uploadedFileName && (
                      <p className="mt-2 text-sm text-muted-foreground">
                          Loaded: {uploadedFileName}
                      </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="few-shot-examples">Few-shot Examples</Label>
                  <Textarea
                    id="few-shot-examples"
                    placeholder="e.g., 'The deadline for Fall 2024 registration is August 15th.' or 'Prof. Smith's office is in Room 301.'"
                    value={fewShotExamples}
                    onChange={(e) => setFewShotExamples(e.target.value)}
                    className="min-h-[100px]"
                  />
                </div>
                 <div className="flex flex-col items-start gap-4">
                    <p className="text-sm text-muted-foreground">
                      This information will be used by the LLM Judge to evaluate and score the prompt's effectiveness.
                    </p>
                    <div className="flex gap-4">
                      <Button onClick={onEvaluate} disabled={isLoading || loading.evaluating}>
                        {loading.evaluating ? <Loader2 className="animate-spin" /> : <Bot />}
                        Iterate & Evaluate
                      </Button>
                      <Button onClick={onOptimize} disabled={isLoading || loading.optimizing}>
                        {loading.optimizing ? <Loader2 className="animate-spin" /> : <Lightbulb />}
                        Optimize with Context
                      </Button>
                    </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6 lg:col-span-2">
        <Card className="sticky top-24">
          <CardHeader>
            <CardTitle>Results & Deployment</CardTitle>
            <CardDescription>
              Review the results from the AI evaluation and deploy your agent.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
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

            {loading.optimizing ? <Skeleton className="h-40 w-full" /> : optimizationResult && (
              <Card>
                <CardHeader>
                  <CardTitle>Optimization</CardTitle>
                </CardHeader>
                <CardContent>
                   <p className="text-sm font-medium">Reasoning:</p>
                   <p className="text-sm text-muted-foreground">{optimizationResult.reasoning}</p>
                </CardContent>
              </Card>
            )}

            {!loading.evaluating && !loading.optimizing && !evaluationResult && !optimizationResult && (
              <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center">
                  <p className="text-muted-foreground">Your results will appear here.</p>
              </div>
            )}

          </CardContent>
          <CardFooter>
            <Button
              className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
              disabled={isLoading || !currentPrompt}
              onClick={() => toast({ title: "Onyx Integration", description: "This would trigger agent creation in the Onyx (Danswer) system." })}
            >
              <Rocket />
              Create Agent in Onyx
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
