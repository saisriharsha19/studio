
'use server';

/**
 * @fileOverview A flow to scrape and extract text content from a given URL.
 * 
 * - scrapeUrl - A function that handles the web scraping process.
 * - ScrapeUrlInput - The input type for the scrapeUrl function.
 * - ScrapeUrlOutput - The return type for the scrapeUrl function.
 */

import { ai } from '@/ai/genkit';
import { z } from 'genkit';

const ScrapeUrlInputSchema = z.object({
  url: z.string().url('Please provide a valid URL.'),
});
export type ScrapeUrlInput = z.infer<typeof ScrapeUrlInputSchema>;

const ScrapeUrlOutputSchema = z.object({
  content: z.string().describe('The extracted text content from the URL.'),
});
export type ScrapeUrlOutput = z.infer<typeof ScrapeUrlOutputSchema>;

export async function scrapeUrl(input: ScrapeUrlInput): Promise<ScrapeUrlOutput> {
  return scrapeUrlFlow(input);
}

const scrapeUrlFlow = ai.defineFlow(
  {
    name: 'scrapeUrlFlow',
    inputSchema: ScrapeUrlInputSchema,
    outputSchema: ScrapeUrlOutputSchema,
  },
  async ({ url }) => {
    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch URL: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      let textContent = '';

      if (contentType && (contentType.includes('text/html') || contentType.includes('text/plain'))) {
        const body = await response.text();
        // Basic text extraction: remove script/style tags, then all other HTML tags, then clean up whitespace.
        textContent = body
          .replace(/<style[^>]*>.*<\/style>/gs, '')
          .replace(/<script[^>]*>.*<\/script>/gs, '')
          .replace(/<[^>]*>/g, '')
          .replace(/\s\s+/g, ' ')
          .trim();
      } else {
        throw new Error(`Unsupported content type: ${contentType}. Only text/html and text/plain are supported.`);
      }

      if (!textContent) {
        throw new Error('Could not extract any text content from the URL.');
      }
      
      return { content: textContent };

    } catch (error: any) {
      console.error(`Error in scrapeUrlFlow for ${url}:`, error);
      // Re-throw with a more user-friendly message
      throw new Error(`Failed to process URL. Reason: ${error.message}`);
    }
  }
);
