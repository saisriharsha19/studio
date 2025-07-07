
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
  sitemapUrl: z.string().url().optional().describe('Direct URL to a sitemap.xml file.'),
  includeSubdomains: z.boolean().optional().default(false).describe('Whether to automatically discover and scrape subdomains'),
  maxSubdomains: z.number().int().min(1).max(50).optional().default(10).describe('Maximum number of subdomains to scrape (1-50)'),
});

export type ScrapeUrlInput = z.infer<typeof ScrapeUrlInputSchema>;

const ScrapeUrlOutputSchema = z.object({
  content: z.string().describe('The extracted text content from the URL.'),
  subdomains: z.array(z.object({
    subdomain: z.string(),
    content: z.string(),
    error: z.string().optional(),
  })).optional().describe('Content from discovered subdomains if includeSubdomains is true'),
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
    let attempts = 0;
    const maxAttempts = 3;
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
    
    while (attempts < maxAttempts) {
      try {
        attempts++;
        
        // Normalize URL to handle subdomains and various formats
        const normalizedUrl = normalizeUrl(url);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        const response = await fetch(normalizedUrl, {
          headers: {
            'User-Agent': getUserAgent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
          },
          signal: controller.signal,
          redirect: 'follow',
          mode: 'cors',
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          if (response.status === 429) {
            // Rate limited, wait and retry
            await delay(Math.pow(2, attempts) * 1000);
            continue;
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type') || '';
        let textContent = '';
        
        if (isTextContent(contentType)) {
          const body = await response.text();
          textContent = extractTextContent(body, contentType);
        } else {
          throw new Error(`Unsupported content type: ${contentType}. Only HTML and text content are supported.`);
        }
        
        if (!textContent || textContent.trim().length === 0) {
          throw new Error('Could not extract any meaningful text content from the URL.');
        }
        
        let result: ScrapeUrlOutput = { content: textContent };
        
        // Handle subdomain discovery if requested
        if (includeSubdomains) {
          const subdomainResults = await discoverFromSitemap(normalizedUrl, maxSubdomains || 10, sitemapUrl);
          result.subdomains = subdomainResults;
        }
        
        return result;
        
      } catch (error: any) {
        console.error(`Error in scrapeUrlFlow for ${url} (attempt ${attempts}):`, error);
        
        if (attempts >= maxAttempts) {
          // Final attempt failed, throw with user-friendly message
          if (error.name === 'AbortError') {
            throw new Error('Request timed out. The URL may be taking too long to respond.');
          } else if (error.message.includes('fetch')) {
            throw new Error('Network error. Please check the URL and try again.');
          } else {
            throw new Error(`Failed to process URL after ${maxAttempts} attempts. Reason: ${error.message}`);
          }
        }
        
        // Wait before retrying (exponential backoff)
        await delay(Math.pow(2, attempts) * 1000);
      }
    }
    
    throw new Error('Unexpected error: maximum attempts reached without proper error handling.');
  }
);

/**
 * Discovers subdomains and URLs from sitemap
 */
async function discoverFromSitemap(originalUrl: string, maxSubdomains: number = 10, directSitemapUrl?: string): Promise<Array<{subdomain: string, content: string, error?: string}>> {
  const urlObj = new URL(originalUrl);
  const baseDomain = urlObj.hostname;
  const sitemapUrlsToProbe: string[] = [];

  if (directSitemapUrl) {
    sitemapUrlsToProbe.push(directSitemapUrl);
  } else {
    // Check for sitemaps on both root and www domains to improve reliability
    const potentialBases = new Set<string>();
    potentialBases.add(`${urlObj.protocol}//${baseDomain}`);
    if (baseDomain.startsWith('www.')) {
      potentialBases.add(`${urlObj.protocol}//${baseDomain.replace('www.', '')}`);
    } else {
      potentialBases.add(`${urlObj.protocol}//www.${baseDomain}`);
    }

    const sitemapLocations = [
      '/robots.txt', // Check robots.txt first, as it often points to the correct sitemap
      '/sitemap.xml',
      '/sitemap_index.xml',
      '/sitemaps.xml',
      '/sitemap/sitemap.xml',
    ];

    potentialBases.forEach(base => {
      sitemapLocations.forEach(loc => {
        sitemapUrlsToProbe.push(base + loc);
      });
    });
  }
  
  const discoveredUrls = new Set<string>();
  
  // Try to find sitemaps
  for (const sitemapUrl of sitemapUrlsToProbe) {
    try {
      const urls = await extractUrlsFromSitemap(sitemapUrl);
      urls.forEach(url => discoveredUrls.add(url));
    } catch (error) {
      // It's normal for many of these to fail (e.g., 404), so we continue silently.
      continue;
    }
  }
  
  // Group URLs by subdomain
  const subdomainGroups = new Map<string, string[]>();
  
  for (const url of discoveredUrls) {
    try {
      const urlObj = new URL(url);
      const hostname = urlObj.hostname;
      
      if (!subdomainGroups.has(hostname)) {
        subdomainGroups.set(hostname, []);
      }
      subdomainGroups.get(hostname)!.push(url);
    } catch (error) {
      // Skip invalid URLs
      continue;
    }
  }
  
  // Scrape representative pages from each subdomain (limited by maxSubdomains)
  const results = [];
  const maxConcurrent = 3;
  const subdomains = Array.from(subdomainGroups.keys()).slice(0, maxSubdomains);
  
  for (let i = 0; i < subdomains.length; i += maxConcurrent) {
    const batch = subdomains.slice(i, i + maxConcurrent);
    const promises = batch.map(async (subdomain) => {
      const urls = subdomainGroups.get(subdomain) || [];
      // Take first few URLs from each subdomain (prioritize homepage if available)
      const urlsToScrape = urls
        .sort((a, b) => {
          if (a.endsWith('/') && !b.endsWith('/')) return -1;
          if (!a.endsWith('/') && b.endsWith('/')) return 1;
          return a.length - b.length;
        })
        .slice(0, 3); // Max 3 URLs per subdomain
      
      let combinedContent = '';
      let errors = [];
      
      for (const url of urlsToScrape) {
        try {
          const content = await scrapeUrlWithoutSubdomains(url);
          combinedContent += content.content + '\n\n---\n\n';
        } catch (error: any) {
          errors.push(`${url}: ${error.message}`);
        }
      }
      
      return {
        subdomain: subdomain,
        content: combinedContent.trim(),
        error: errors.length > 0 ? errors.join('; ') : undefined,
      };
    });
    
    const batchResults = await Promise.allSettled(promises);
    
    for (const result of batchResults) {
      if (result.status === 'fulfilled') {
        results.push(result.value);
      }
    }
    
    // Small delay between batches
    if (i + maxConcurrent < subdomains.length) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  
  return results.filter(result => result.content.trim().length > 0 || result.error);
}

/**
 * Extracts URLs from sitemap XML or robots.txt
 */
async function extractUrlsFromSitemap(sitemapUrl: string): Promise<string[]> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  
  try {
    const response = await fetch(sitemapUrl, {
      headers: {
        'User-Agent': getUserAgent(),
        'Accept': 'application/xml,text/xml,text/plain,*/*',
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const content = await response.text();
    const urls = new Set<string>();
    
    if (sitemapUrl.includes('robots.txt')) {
      // Extract sitemap URLs from robots.txt
      const sitemapMatches = content.match(/^Sitemap:\s*(.+)$/gim);
      if (sitemapMatches) {
        for (const match of sitemapMatches) {
          const sitemapUrlFromRobots = match.replace(/^Sitemap:\s*/i, '').trim();
          try {
            const nestedUrls = await extractUrlsFromSitemap(sitemapUrlFromRobots);
            nestedUrls.forEach(url => urls.add(url));
          } catch (error) {
            // Continue with other sitemaps
            continue;
          }
        }
      }
    } else {
      // Parse XML sitemap
      // Extract <loc> tags for URLs
      const locMatches = content.match(/<loc>(.*?)<\/loc>/gi);
      if (locMatches) {
        for (const match of locMatches) {
          const url = match.replace(/<\/?loc>/gi, '').trim();
          if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
            urls.add(url);
          }
        }
      }
      
      // Handle sitemap index files - look for nested sitemaps
      const sitemapMatches = content.match(/<sitemap>[\s\S]*?<\/sitemap>/gi);
      if (sitemapMatches) {
        for (const sitemapBlock of sitemapMatches) {
          const locMatch = sitemapBlock.match(/<loc>(.*?)<\/loc>/i);
          if (locMatch) {
            const nestedSitemapUrl = locMatch[1].trim();
            try {
              const nestedUrls = await extractUrlsFromSitemap(nestedSitemapUrl);
              nestedUrls.forEach(url => urls.add(url));
            } catch (error) {
              // Continue with other sitemaps
              continue;
            }
          }
        }
      }
    }
    
    return Array.from(urls);
    
  } catch (error: any) {
    throw new Error(`Failed to fetch sitemap: ${error.message}`);
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Scrapes a URL without triggering subdomain discovery (internal use)
 */
async function scrapeUrlWithoutSubdomains(url: string): Promise<{content: string}> {
  let attempts = 0;
  const maxAttempts = 2; // Fewer attempts for subdomains
  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
  
  while (attempts < maxAttempts) {
    try {
      attempts++;
      
      const normalizedUrl = normalizeUrl(url);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // Shorter timeout for subdomains
      
      const response = await fetch(normalizedUrl, {
        headers: {
          'User-Agent': getUserAgent(),
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'DNT': '1',
          'Connection': 'keep-alive',
        },
        signal: controller.signal,
        redirect: 'follow',
        mode: 'cors',
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const contentType = response.headers.get('content-type') || '';
      let textContent = '';
      
      if (isTextContent(contentType)) {
        const body = await response.text();
        textContent = extractTextContent(body, contentType);
      } else {
        throw new Error(`Unsupported content type: ${contentType}`);
      }
      
      return { content: textContent };
      
    } catch (error: any) {
      if (attempts >= maxAttempts) {
        throw error;
      }
      await delay(500); // Shorter delay for subdomains
    }
  }
  
  throw new Error('Max attempts reached');
}



/**
 * Normalizes URL to handle various formats and subdomains
 */
function normalizeUrl(url: string): string {
  try {
    // Handle URLs without protocol
    if (!url.match(/^https?:\/\//)) {
      url = `https://${url}`;
    }
    
    const urlObj = new URL(url);
    
    // Ensure we can handle subdomains (they're already included in hostname)
    // Just validate the URL structure
    if (!urlObj.hostname) {
      throw new Error('Invalid hostname');
    }
    
    return urlObj.toString();
  } catch (error) {
    throw new Error(`Invalid URL format: ${url}`);
  }
}

/**
 * Returns a varied user agent to avoid detection
 */
function getUserAgent(): string {
  const userAgents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
  ];
  
  return userAgents[Math.floor(Math.random() * userAgents.length)];
}

/**
 * Checks if content type is text-based
 */
function isTextContent(contentType: string): boolean {
  const textTypes = [
    'text/html',
    'text/plain',
    'text/xml',
    'application/xhtml+xml',
    'application/xml',
    'text/css',
    'text/javascript',
    'application/javascript',
    'application/json',
    'text/markdown',
  ];
  
  return textTypes.some(type => contentType.toLowerCase().includes(type));
}

/**
 * Extracts and cleans text content from various content types
 */
function extractTextContent(body: string, contentType: string): string {
  let textContent = '';
  
  if (contentType.includes('text/html') || contentType.includes('application/xhtml+xml')) {
    // Enhanced HTML text extraction
    textContent = body
      // Remove scripts and styles with their content
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      // Remove comments
      .replace(/<!--[\s\S]*?-->/g, '')
      // Remove common non-content elements
      .replace(/<(nav|header|footer|aside|menu)[^>]*>[\s\S]*?<\/\1>/gi, '')
      // Replace common block elements with newlines
      .replace(/<(div|p|br|hr|h[1-6]|li|tr|td|th)[^>]*>/gi, '\n')
      // Remove all remaining HTML tags
      .replace(/<[^>]*>/g, '')
      // Decode common HTML entities
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&apos;/g, "'")
      // Clean up whitespace
      .replace(/\n\s*\n/g, '\n') // Remove empty lines
      .replace(/[ \t]+/g, ' ') // Normalize spaces
      .replace(/\n /g, '\n') // Remove leading spaces after newlines
      .trim();
  } else if (contentType.includes('application/json')) {
    // For JSON, try to extract readable text values
    try {
      const jsonObj = JSON.parse(body);
      textContent = extractTextFromJson(jsonObj);
    } catch {
      textContent = body;
    }
  } else {
    // For plain text and other text types
    textContent = body
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/\t/g, '    ')
      .trim();
  }
  
  return textContent;
}

/**
 * Recursively extracts text content from JSON objects
 */
function extractTextFromJson(obj: any): string {
  if (typeof obj === 'string') {
    return obj;
  } else if (typeof obj === 'number' || typeof obj === 'boolean') {
    return String(obj);
  } else if (Array.isArray(obj)) {
    return obj.map(item => extractTextFromJson(item)).join(' ');
  } else if (obj && typeof obj === 'object') {
    return Object.values(obj).map(value => extractTextFromJson(value)).join(' ');
  }
  return '';
}

    