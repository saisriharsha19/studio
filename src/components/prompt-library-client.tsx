'use client';

import { useState } from 'react';
import { usePrompts, type Prompt } from '@/hooks/use-prompts';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
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
import { ScrollArea } from '@/components/ui/scroll-area';
import { Clipboard, Check, Trash2, Library, Search } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';
import { Input } from './ui/input';

export function PromptLibraryClient() {
  const { prompts, deletePrompt } = usePrompts();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const { toast } = useToast();

  const copyToClipboard = (prompt: Prompt) => {
    navigator.clipboard.writeText(prompt.text);
    setCopiedId(prompt.id);
    toast({ title: 'Copied!', description: 'Prompt copied to clipboard.' });
    setTimeout(() => setCopiedId(null), 2000);
  };
  
  const filteredPrompts = prompts.filter(prompt => 
    prompt.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container mx-auto max-w-7xl py-8">
      <div className="mb-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className='flex items-center gap-3'>
          <Library className="h-8 w-8" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Prompt Library</h1>
            <p className="text-muted-foreground">
              Browse, manage, and reuse your saved prompts.
            </p>
          </div>
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search prompts..."
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <ScrollArea className="h-[calc(100vh-12rem)]">
        {filteredPrompts.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredPrompts.map((prompt) => (
              <Card key={prompt.id} className="flex flex-col">
                <CardHeader>
                  <CardTitle className="text-lg">Prompt</CardTitle>
                  <CardDescription>
                    Saved{' '}
                    {formatDistanceToNow(new Date(prompt.createdAt), {
                      addSuffix: true,
                    })}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow">
                  <p className="line-clamp-6 text-sm text-foreground/80">
                    {prompt.text}
                  </p>
                </CardContent>
                <CardFooter className="flex justify-end gap-2">
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
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <Trash2 className="h-4 w-4 text-destructive" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This action cannot be undone. This will permanently delete this prompt from your library.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => deletePrompt(prompt.id)}>
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>

                </CardFooter>
              </Card>
            ))}
          </div>
        ) : (
          <div className="flex h-[50vh] flex-col items-center justify-center rounded-lg border-2 border-dashed">
            <Library className="mb-4 h-16 w-16 text-muted-foreground" />
            <h2 className="text-2xl font-semibold">Library is Empty</h2>
            <p className="mt-2 text-muted-foreground">
              {searchQuery ? "No prompts match your search." : "Go to the generator to save your first prompt!"}
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
