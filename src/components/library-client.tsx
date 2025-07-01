
'use client';

import { useState } from 'react';
import type { Prompt } from '@/hooks/use-prompts';
import { useLibrary } from '@/hooks/use-library';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Clipboard, Check, Library, Search, Star } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';
import { Input } from './ui/input';
import { Skeleton } from './ui/skeleton';
import { useAuth } from '@/hooks/use-auth';
import { cn } from '@/lib/utils';
import { Badge } from './ui/badge';

function PromptCardSkeleton() {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/3 mt-2" />
      </CardHeader>
      <CardContent className="flex-grow space-y-4">
        <div className="flex flex-wrap gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between gap-2">
        <Skeleton className="h-8 w-12" />
        <Skeleton className="h-8 w-8 rounded-full" />
      </CardFooter>
    </Card>
  );
}

export function LibraryClient() {
  const { libraryPrompts, toggleStar, isLoading } = useLibrary();
  const { isAuthenticated } = useAuth();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIds, setExpandedIds] = useState(new Set<string>());
  const { toast } = useToast();

  const toggleExpanded = (id: string) => {
    setExpandedIds(prev => {
        const newSet = new Set(prev);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        return newSet;
    });
  };

  const copyToClipboard = (prompt: Prompt) => {
    navigator.clipboard.writeText(prompt.text);
    setCopiedId(prompt.id);
    toast({ title: 'Copied!', description: 'Prompt copied to clipboard.' });
    setTimeout(() => setCopiedId(null), 2000);
  };
  
  const filteredPrompts = libraryPrompts.filter(prompt => {
    const query = searchQuery.toLowerCase();
    const textMatch = prompt.text.toLowerCase().includes(query);
    const tagMatch = prompt.tags?.some(tag => tag.toLowerCase().includes(query));
    return textMatch || tagMatch;
  });

  const getPromptTitle = (text: string) => {
    const words = text.split(' ');
    const title = words.slice(0, 8).join(' ');
    return words.length > 8 ? `${title}...` : title;
  };
  
  return (
    <div className="container mx-auto max-w-7xl py-8 px-4 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className='flex items-center gap-3'>
          <Library className="h-8 w-8" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Prompt Library</h1>
            <p className="text-muted-foreground">
              A public collection of curated prompts submitted by the community.
            </p>
          </div>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <Input 
            placeholder="Search library..."
            className="h-11 w-full rounded-full border-transparent bg-muted pl-12 pr-4 transition-colors focus:bg-background focus:ring-2 focus:ring-ring"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <ScrollArea className="h-full">
        {isLoading ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => <PromptCardSkeleton key={i} />)}
          </div>
        ) : filteredPrompts.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredPrompts.map((prompt) => (
              <Card key={prompt.id} className="flex flex-col">
                <CardHeader>
                  <CardTitle className="text-lg leading-snug">
                    {getPromptTitle(prompt.text)}
                  </CardTitle>
                  <CardDescription>
                    Saved{' '}
                    {formatDistanceToNow(new Date(prompt.createdAt), {
                      addSuffix: true,
                    })}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow space-y-4">
                  {prompt.tags && prompt.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {prompt.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="font-normal">{tag}</Badge>
                      ))}
                    </div>
                  )}
                  <div>
                    {expandedIds.has(prompt.id) ? (
                      <ScrollArea className="h-32 w-full rounded-md border p-3">
                         <p className="text-sm text-foreground/80 whitespace-pre-wrap">
                            {prompt.text}
                        </p>
                      </ScrollArea>
                    ) : (
                      <p className="text-sm text-foreground/80 line-clamp-4">
                          {prompt.text}
                      </p>
                    )}
                    {prompt.text.length > 200 && (
                        <button onClick={() => toggleExpanded(prompt.id)} className="text-sm font-medium text-primary hover:underline mt-2">
                            {expandedIds.has(prompt.id) ? "Show less" : "Show more"}
                        </button>
                    )}
                  </div>
                </CardContent>
                <CardFooter className="mt-auto flex items-center justify-between gap-2 pt-4">
                  <Button variant="ghost" className="flex items-center gap-1.5 px-2 text-sm text-muted-foreground" onClick={() => toggleStar(prompt.id)} disabled={!isAuthenticated}>
                    <Star className={cn("h-4 w-4 transition-colors", prompt.isStarredByUser && "fill-yellow-400 text-yellow-400")} />
                    {prompt.stars ?? 0}
                  </Button>

                  <div className='flex items-center'>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => copyToClipboard(prompt)}
                    >
                      {copiedId === prompt.id ? (
                        <Check className="h-4 w-4 text-primary" />
                      ) : (
                        <Clipboard className="h-4 w-4" />
                      )}
                      <span className="sr-only">Copy</span>
                    </Button>
                  </div>
                </CardFooter>
              </Card>
            ))}
          </div>
        ) : (
          <div className="flex h-[50vh] flex-col items-center justify-center rounded-lg border-2 border-dashed">
            <Library className="mb-4 h-16 w-16 text-muted-foreground" />
            <h2 className="text-2xl font-semibold">Library is Empty</h2>
            <p className="mt-2 text-muted-foreground">
              {searchQuery ? "No prompts match your search." : "Be the first to add a prompt to the public library!"}
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
