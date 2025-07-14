
'use server';
/**
 * @fileOverview A flow to scrape and extract text content from a given URL by calling an external crawler API.
 * 
 * - scrapeUrl - A function that handles the web scraping process.
 * - ScrapeUrlInput - The input type for the scrapeUrl function.
 * - ScrapeUrlOutput - The return type for the scrapeUrl function.
 */
import { ai } from '@/ai/genkit';
import { z } from 'genkit';

const ScrapeUrlInputSchema = z.object({
  url: z.string().url('Please provide a valid URL.'),
  sitemapUrl: z.string().url().optional().describe('Direct URL to a sitemap.xml file.'),
  includeSubdomains: z.boolean().optional().default(false).describe('Whether to automatically discover and scrape subdomains'),
  maxSubdomains: z.number().int().min(1).max(50).optional().default(10).describe('Maximum number of subdomains to scrape (1-50)'),
});

export type ScrapeUrlInput = z.infer<typeof ScrapeUrlInputSchema>;

const SubdomainResultSchema = z.object({
  subdomain: z.string(),
  content: z.string(),
  summary: z.string().optional(),
  error: z.string().optional(),
});

const ScrapeUrlOutputSchema = z.object({
  content: z.string().describe('The extracted text content from the URL.'),
  summary: z.string().optional().describe('An AI-generated summary of the main content.'),
  subdomains: z.array(SubdomainResultSchema).optional().describe('Content from discovered subdomains if includeSubdomains is true'),
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
  async ({ url, includeSubdomains, maxSubdomains, sitemapUrl }) => {
    const crawlerApiUrl = process.env.CRAWLER_API_URL;
    if (!crawlerApiUrl) {
        throw new Error('Crawler API URL is not configured. Please set CRAWLER_API_URL in your environment variables.');
    }
    
    try {
        const payload = {
            base_url: url,
            max_subdomains: includeSubdomains ? maxSubdomains : 0,
            max_pages: 1, // The external API is page-oriented, we want the content for the main URL.
            prefer_sitemap: !!sitemapUrl,
            sitemap_override: sitemapUrl,
        };

        const response = await fetch(crawlerApiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(60000), // 60-second timeout for the crawl
        });

        if (!response.ok) {
            const errorBody = await response.text();
            throw new Error(`Crawler API request failed with status ${response.status}: ${errorBody}`);
        }

        const result = await response.json();
        
        const mainResult = result.results?.[0];
        
        if (!mainResult) {
            throw new Error('Crawler API returned no results for the main URL.');
        }

        let combinedSubdomainContent = '';
        if (includeSubdomains && result.subdomains_results) {
            combinedSubdomainContent = result.subdomains_results
                .map((sub: any) => `--- Subdomain: ${sub.subdomain} ---\nContent: ${sub.content}\nSummary: ${sub.summary || 'N/A'}`)
                .join('\n\n');
        }

        const mainContent = mainResult.content || '';
        const fullContent = [mainContent, combinedSubdomainContent].filter(Boolean).join('\n\n');

        // The external API returns a more complex structure, so we adapt it to our expected output.
        // We'll combine all subdomain content into the main `content` field.
        return {
            content: fullContent,
            summary: mainResult.summary,
            // The `subdomains` field in our output can be structured if needed,
            // but for now, we combine it for simplicity.
            subdomains: result.subdomains_results || [],
        };

    } catch (error: any) {
        console.error(`Error calling crawler API for ${url}:`, error);
        if (error.name === 'TimeoutError') {
             throw new Error('The request to the crawler service timed out after 60 seconds.');
        }
        throw new Error(`Failed to process URL via crawler service. Reason: ${error.message}`);
    }
  }
);
