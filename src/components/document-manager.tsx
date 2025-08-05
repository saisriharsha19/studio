
'use client';

import { useState, useTransition, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { UploadCloud, FileText, X, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { handleUploadDocument } from '@/app/actions';
import { useAuth } from '@/hooks/use-auth';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { usePromptForge } from '@/hooks/use-prompt-forge';

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
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isPending, startTransition] = useTransition();
  const { toast } = useToast();

  const handleFileChange = (selectedFile: File | null) => {
    if (selectedFile) {
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
      setFile(selectedFile);
    }
  };

  const handleDrop = useCallback((event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      handleFileChange(event.dataTransfer.files[0]);
    }
  }, []);

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

  const onUpload = () => {
    if (!file || !userId) {
      if (!isAuthenticated) {
        toast({ variant: 'destructive', title: 'Please sign in to upload documents.' });
        login();
      } else {
        toast({ variant: 'destructive', title: 'No file selected.' });
      }
      return;
    }

    setIsUploading(true);
    setUploadProgress(0); // Reset progress

    const formData = new FormData();
    formData.append('document', file);

    startTransition(async () => {
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 5, 95));
      }, 200);

      try {
        const result = await handleUploadDocument(userId, formData);
        clearInterval(progressInterval);
        setUploadProgress(100);

        if (result.success && result.content && result.filename) {
          toast({ title: 'Upload Successful', description: result.message });
          setUploadedFileContent(result.content);
          setUploadedFileName(result.filename);
        } else {
          toast({ variant: 'destructive', title: 'Upload Failed', description: result.message });
          setUploadProgress(0);
        }
      } catch (error: any) {
        clearInterval(progressInterval);
        setUploadProgress(0);
        toast({ variant: 'destructive', title: 'Upload Error', description: error.message });
      } finally {
        setTimeout(() => {
          setIsUploading(false);
          setFile(null); 
        }, 1000);
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Context & Knowledge</CardTitle>
        <CardDescription>Upload documents to provide context for the assistant.</CardDescription>
      </CardHeader>
      <CardContent>
        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="file-view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <div className="flex items-center gap-3 rounded-lg border bg-muted/50 p-3">
                <FileText className="h-6 w-6 shrink-0 text-primary" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-sm">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  onClick={() => setFile(null)}
                  disabled={isUploading}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {isUploading ? (
                 <Progress value={uploadProgress} className="w-full h-2" />
              ) : (
                <Button className="w-full" onClick={onUpload} disabled={isPending || !isAuthenticated}>
                  {isPending ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <UploadCloud />
                  )}
                  Upload Document
                </Button>
              )}
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
                  isDragOver ? 'border-primary bg-accent' : 'border-border hover:border-primary/50'
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
                disabled={isPending}
              />
            </motion.div>
          )}
        </AnimatePresence>

         <div className="space-y-2 pt-6">
            <h4 className="text-sm font-medium">Active Document</h4>
            <div className="flex h-16 items-center justify-center rounded-lg border-2 border-dashed text-center">
              {uploadedFileName ? (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <FileText className="h-5 w-5 shrink-0 text-primary" />
                  <span className="font-medium">{uploadedFileName}</span>
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

    