import {genkit} from 'genkit';
import {openai} from '@genkit-ai/openai';

const uflAI = openai({
  apiKey: process.env.UFL_AI_API_KEY,
  baseURL: process.env.UFL_AI_BASE_URL,
});

export const ai = genkit({
  plugins: [uflAI],
  model: 'openai/gpt-4o',
});
