
'use client';

import { useState } from 'react';
import type { Prompt } from '@/hooks/use-prompts';
import { useLibrary } from '@/hooks/use-library';
import { Button, buttonVariants } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Clipboard, Check, Search, Star, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Input } from './ui/input';
import { Skeleton } from './ui/skeleton';
import { useAuth } from '@/hooks/use-auth';
import { cn } from '@/lib/utils';
import { Badge } from './ui/badge';
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from './ui/tooltip';

function PromptCardSkeleton() {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <Skeleton className="h-5 w-3/4" />
      </CardHeader>
      <CardContent className="flex flex-col flex-grow min-h-0">
        <div className="flex flex-wrap gap-1.5 pb-4 flex-shrink-0">
            <Skeleton className="h-5 w-14 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <div className="flex-grow min-h-0 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between pt-2 flex-shrink-0">
        <Skeleton className="h-5 w-24" />
        <div className="flex items-center">
          <Skeleton className="h-8 w-12" />
          <Skeleton className="h-8 w-8" />
        </div>
      </CardFooter>
    </Card>
  );
}

export function LibraryClient() {
  const { libraryPrompts, toggleStar, isLoading, deleteLibraryPrompt } = useLibrary();
  const { isAuthenticated, isAdmin } = useAuth();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewingPrompt, setViewingPrompt] = useState<Prompt | null>(null);
  const { toast } = useToast();

  const copyToClipboard = (prompt: Prompt) => {
    navigator.clipboard.writeText(prompt.text);
    setCopiedId(prompt.id);
    toast({ title: 'Copied!', description: 'Prompt copied to clipboard.' });
    setTimeout(() => setCopiedId(null), 2000);
  };
  
  const filteredPrompts = libraryPrompts.filter(prompt => {
    const query = searchQuery.toLowerCase();
    const textMatch = prompt.text.toLowerCase().includes(query);
    const summaryMatch = prompt.summary?.toLowerCase().includes(query);
    const tagsMatch = prompt.tags?.some(tag => tag.toLowerCase().includes(query));
    return textMatch || summaryMatch || tagsMatch;
  });

  return (
    <TooltipProvider>
        <Dialog open={!!viewingPrompt} onOpenChange={(isOpen) => !isOpen && setViewingPrompt(null)}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle>{viewingPrompt?.summary || 'Prompt Details'}</DialogTitle>
                    <DialogDescription>
                        Full content of the selected prompt. You can copy it from here.
                    </DialogDescription>
                </DialogHeader>
                <div className="relative">
                    <ScrollArea className="h-96 w-full rounded-md border bg-muted/50 p-4">
                        <p className="text-sm text-foreground whitespace-pre-wrap">
                            {viewingPrompt?.text}
                        </p>
                    </ScrollArea>
                    {viewingPrompt && (
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="absolute top-3 right-3 h-8 w-8 bg-muted/80 hover:bg-muted"
                                    onClick={() => copyToClipboard(viewingPrompt)}
                                    aria-label="Copy prompt"
                                >
                                    {copiedId === viewingPrompt.id ? <Check className="text-primary" /> : <Clipboard />}
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                                <p>Copy prompt</p>
                            </TooltipContent>
                        </Tooltip>
                    )}
                </div>
            </DialogContent>
        </Dialog>

      <div className="container mx-auto max-w-7xl py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="rounded-lg bg-muted p-6">
            <div className='flex items-center gap-3 sm:gap-4'>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-6 w-6 shrink-0 text-primary sm:h-8 sm:w-8"
                aria-hidden="true"
              >
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
              <div>
                <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Prompt Library</h1>
                <p className="text-sm text-muted-foreground">
                  A public collection of curated prompts submitted by the community.
                </p>
              </div>
            </div>
          </div>
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input 
              placeholder="Search library..."
              aria-label="Search prompt library"
              className="h-11 w-full rounded-full border-transparent bg-muted pl-12 pr-4 transition-colors focus:bg-background focus:ring-2 focus:ring-ring"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <ScrollArea className="h-full">
          {isLoading ? (
            <ul className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => <li key={i}><PromptCardSkeleton /></li>)}
            </ul>
          ) : filteredPrompts.length > 0 ? (
            <ul className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredPrompts.map((prompt) => {
                  const needsExpansion = prompt.text.length > 250;

                  return (
                      <li key={prompt.id}>
                          <Card className="flex flex-col">
                              <CardHeader>
                                  <CardTitle>
                                      {prompt.summary || 'No summary available.'}
                                  </CardTitle>
                              </CardHeader>
                              
                              <CardContent className="flex flex-col flex-grow min-h-0">
                                  {prompt.tags && prompt.tags.length > 0 && (
                                      <ul className="flex flex-wrap gap-1.5 pb-4 flex-shrink-0" aria-label="Prompt tags">
                                          {prompt.tags.map((tag, index) => (
                                              <li key={index}>
                                                <Badge variant="secondary" className="font-normal">
                                                    {tag}
                                                </Badge>
                                              </li>
                                          ))}
                                      </ul>
                                  )}
                                  <div className="flex-grow min-h-0 flex flex-col justify-center">
                                    <p className="text-sm text-foreground/80 line-clamp-6">
                                        {prompt.text}
                                    </p>
                                  </div>
                              </CardContent>
                              
                              <CardFooter className="flex items-center justify-between pt-2 mt-auto flex-shrink-0">
                                <Button
                                    variant="link"
                                    className={cn("text-sm font-medium p-0 h-auto", !needsExpansion && "invisible")}
                                    onClick={() => setViewingPrompt(prompt)}
                                >
                                    Show more
                                </Button>
                                  
                                  <div className='flex items-center'>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Button 
                                            variant="ghost" 
                                            className="flex items-center gap-1.5 px-2 text-sm text-muted-foreground" 
                                            onClick={() => toggleStar(prompt.id)} 
                                            disabled={!isAuthenticated}
                                            aria-label={prompt.isStarredByUser ? "Un-star this prompt" : "Star this prompt"}
                                          >
                                              <Star className={cn("h-4 w-4 transition-colors", prompt.isStarredByUser && "fill-yellow-400 text-yellow-400")} />
                                              {prompt.stars ?? 0}
                                          </Button>
                                        </TooltipTrigger>
                                        <TooltipContent>
                                          <p>{prompt.isStarredByUser ? "Un-star prompt" : "Star prompt"}</p>
                                        </TooltipContent>
                                      </Tooltip>

                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Button
                                              variant="ghost"
                                              size="icon"
                                              onClick={() => copyToClipboard(prompt)}
                                              aria-label="Copy prompt"
                                          >
                                              {copiedId === prompt.id ? (
                                              <Check className="h-4 w-4 text-primary" />
                                              ) : (
                                              <Clipboard className="h-4 w-4" />
                                              )}
                                          </Button>
                                        </TooltipTrigger>
                                        <TooltipContent>
                                          <p>Copy prompt</p>
                                        </TooltipContent>
                                      </Tooltip>

                                      {isAdmin && (
                                          <AlertDialog>
                                            <Tooltip>
                                              <TooltipTrigger asChild>
                                                <AlertDialogTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="group" aria-label="Delete prompt">
                                                        <Trash2 className="h-4 w-4 text-muted-foreground group-hover:text-destructive" />
                                                    </Button>
                                                </AlertDialogTrigger>
                                              </TooltipTrigger>
                                              <TooltipContent>
                                                <p>Delete prompt</p>
                                              </TooltipContent>
                                            </Tooltip>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                                                <AlertDialogDescription>
                                                    This action cannot be undone. This will permanently delete this prompt from the public library.
                                                </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                <AlertDialogAction onClick={() => deleteLibraryPrompt(prompt.id)} className={cn(buttonVariants({variant: 'destructive'}))}>
                                                    Delete
                                                </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                          </AlertDialog>
                                      )}
                                  </div>
                              </CardFooter>
                          </Card>
                      </li>
                  );
              })}
            </ul>
          ) : (
            <div role="region" aria-labelledby="empty-library-heading" className="flex h-[50vh] flex-col items-center justify-center rounded-lg border-2 border-dashed">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mb-4 h-16 w-16 text-muted-foreground"
                aria-hidden="true"
              >
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
              <h2 id="empty-library-heading" className="text-2xl font-semibold">Library is Empty</h2>
              <p className="mt-2 text-muted-foreground">
                {searchQuery ? "No prompts match your search." : "Be the first to add a prompt to the public library!"}
              </p>
            </div>
          )}
        </ScrollArea>
      </div>
    </TooltipProvider>
  );
}
