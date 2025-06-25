import { config } from 'dotenv';
config();

import '@/ai/flows/generate-initial-prompt.ts';
import '@/ai/flows/evaluate-and-iterate-prompt.ts';
import '@/ai/flows/optimize-prompt-with-context.ts';