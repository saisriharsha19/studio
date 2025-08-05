
'use client';

import { useState, useTransition, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { UploadCloud, FileText, X, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/use-auth';
import { Button } from './ui/button';
import { usePromptForge } from '@/hooks/use-prompt-forge';
import mammoth from 'mammoth';
import pdf from 'pdf-parse/lib/pdf-parse';

// Add pdf-parse to window for browser usage
if (typeof window !== 'undefined') {
  (window as any).pdf = pdf;
}

const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  'text/plain',
  'text/markdown',
];

export function DocumentManager() {
  const { userId, isAuthenticated, login } = useAuth();
  const { setUploadedFileContent, uploadedFileName, setUploadedFileName } = usePromptForge();
  const [isExtracting, setIsExtracting] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const { toast } = useToast();

  const resetState = () => {
    setUploadedFileName('');
    setUploadedFileContent('');
  };

  const handleFileChange = async (selectedFile: File | null) => {
    if (!isAuthenticated) {
        toast({ variant: 'destructive', title: 'Please sign in to use documents.' });
        login();
        return;
    }
    if (!selectedFile) return;

    // --- Validation ---
    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      toast({
        variant: 'destructive',
        title: 'File Too Large',
        description: `The maximum file size is ${MAX_FILE_SIZE_MB}MB.`,
      });
      return;
    }
    if (!ALLOWED_FILE_TYPES.includes(selectedFile.type)) {
      toast({
        variant: 'destructive',
        title: 'Invalid File Type',
        description: 'Please upload a PDF, DOCX, TXT, or MD file.',
      });
      return;
    }
    // --- End Validation ---

    setIsExtracting(true);
    resetState();

    try {
      let textContent = '';
      if (selectedFile.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
        // Handle .docx
        const arrayBuffer = await selectedFile.arrayBuffer();
        const result = await mammoth.extractRawText({ arrayBuffer });
        textContent = result.value;
      } else if (selectedFile.type === 'application/pdf') {
        // Handle .pdf
        const arrayBuffer = await selectedFile.arrayBuffer();
        const data = await pdf(arrayBuffer);
        textContent = data.text;
      } else {
        // Handle .txt, .md
        textContent = await selectedFile.text();
      }

      setUploadedFileContent(textContent);
      setUploadedFileName(selectedFile.name);
      toast({ title: 'Extraction Successful', description: `Extracted content from ${selectedFile.name}.` });

    } catch (error: any) {
      console.error('File extraction error:', error);
      toast({ variant: 'destructive', title: 'Extraction Failed', description: 'Could not read text from the document.' });
      resetState();
    } finally {
      setIsExtracting(false);
    }
  };

  const handleDrop = useCallback((event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      handleFileChange(event.dataTransfer.files[0]);
    }
  }, [isAuthenticated]);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Context & Knowledge</CardTitle>
        <CardDescription>Upload documents to provide context for the assistant.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col">
        <AnimatePresence mode="wait">
          {isExtracting ? (
             <motion.div
                key="loading-view"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-12 text-center"
            >
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="font-semibold">Extracting text...</p>
                <p className="text-xs text-muted-foreground">Please wait while the document is processed.</p>
            </motion.div>
          ) : (
            <motion.div
              key="upload-view"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <label
                htmlFor="file-upload"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-12 text-center transition-colors',
                  isDragOver ? 'border-primary bg-accent' : 'border-border hover:border-primary/50',
                  !isAuthenticated && 'cursor-not-allowed opacity-60'
                )}
              >
                <div className="rounded-full bg-muted p-3">
                    <UploadCloud className="h-8 w-8 text-muted-foreground" />
                </div>
                <p className="font-semibold">
                  <span className="text-primary">Click to upload</span> or drag and drop
                </p>
                <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, or MD (max. 10MB)</p>
              </label>
              <input
                id="file-upload"
                type="file"
                className="sr-only"
                onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                accept={ALLOWED_FILE_TYPES.join(',')}
                disabled={!isAuthenticated || isExtracting}
              />
            </motion.div>
          )}
        </AnimatePresence>

         <div className="space-y-2 pt-6">
            <h4 className="text-sm font-medium">Active Document</h4>
            <div className="flex h-16 items-center justify-center rounded-lg border bg-muted/50 px-4 text-center">
              {uploadedFileName ? (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <FileText className="h-5 w-5 shrink-0 text-primary" />
                  <span className="font-medium truncate flex-1">{uploadedFileName}</span>
                   <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0"
                      onClick={resetState}
                      disabled={isExtracting}
                    >
                      <X className="h-4 w-4" />
                   </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No document context applied.</p>
              )}
            </div>
         </div>
      </CardContent>
    </Card>
  );
}
