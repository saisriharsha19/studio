#!/usr/bin/env python3
"""
Enhanced Resource-Efficient Web Crawler with Sitemap Discovery
A lightweight web crawler that prioritizes sitemap discovery before manual crawling
"""

import asyncio
import aiohttp
import json
import time
import hashlib
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass, asdict
from typing import Set, List, Dict, Optional
from pathlib import Path
import logging
from datetime import datetime
import re
import sys
from collections import deque
import validators
import gc
import psutil

# Lightweight libraries for content extraction and processing
from bs4 import BeautifulSoup
import trafilatura
from transformers import pipeline
import torch
import aiofiles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CrawlResult:
    """Data structure for crawled page results"""
    url: str
    title: str
    content: str
    summary: str
    metadata: Dict
    crawl_time: str
    content_hash: str
    word_count: int
    links: List[str]
    error: Optional[str] = None

class ResourceMonitor:
    """Monitor and manage resource usage"""
    
    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_mb = max_memory_mb
        self.start_time = time.time()
        self.processed_urls = 0
        
    def check_memory_usage(self) -> bool:
        """Check if memory usage is within limits"""
        try:
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            return memory_mb < self.max_memory_mb
        except:
            return True
    
    def get_stats(self) -> Dict:
        """Get current resource usage statistics"""
        try:
            process = psutil.Process()
            runtime = time.time() - self.start_time
            return {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'runtime_seconds': runtime,
                'urls_processed': self.processed_urls,
                'urls_per_second': self.processed_urls / runtime if runtime > 0 else 0
            }
        except:
            return {'error': 'Unable to get stats'}

class ContentSummarizer:
    """Lightweight content summarization"""
    
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.model_name = model_name
        self.summarizer = None
        self.max_input_length = 1024
        self.max_output_length = 150
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the summarization model with memory optimization"""
        try:
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                tokenizer=self.model_name,
                framework="pt",
                device=-1,  # Use CPU
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            logger.info(f"Initialized summarization model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize summarization model: {e}")
            self.summarizer = None
    
    def summarize_content(self, content: str) -> str:
        """Generate summary of content with fallback options"""
        if not content or len(content.strip()) < 100:
            return content.strip()
        
        try:
            if self.summarizer:
                cleaned_content = self._clean_content(content)
                if len(cleaned_content) > self.max_input_length:
                    cleaned_content = cleaned_content[:self.max_input_length]
                
                result = self.summarizer(
                    cleaned_content,
                    max_length=self.max_output_length,
                    min_length=50,
                    do_sample=False,
                    truncation=True
                )
                return result[0]['summary_text']
            else:
                return self._extractive_summary(content)
                
        except Exception as e:
            logger.warning(f"Summarization failed: {e}")
            return self._extractive_summary(content)
    
    def _clean_content(self, content: str) -> str:
        """Clean content for summarization"""
        content = re.sub(r'\s+', ' ', content.strip())
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        content = re.sub(r'\S+@\S+', '', content)
        return content
    
    def _extractive_summary(self, content: str, max_sentences: int = 3) -> str:
        """Simple extractive summarization as fallback"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if len(sentences) <= max_sentences:
            return '. '.join(sentences)
        
        scored_sentences = []
        for i, sentence in enumerate(sentences[:10]):
            score = (10 - i) + len(sentence.split()) / 10
            scored_sentences.append((score, sentence))
        
        top_sentences = sorted(scored_sentences, reverse=True)[:max_sentences]
        top_sentences = sorted(top_sentences, key=lambda x: sentences.index(x[1]))
        
        return '. '.join([s[1] for s in top_sentences])

class SitemapDiscovery:
    """Handles sitemap discovery and parsing"""
    
    def __init__(self, base_url: str, max_pages: int = 100):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.discovered_urls: Set[str] = set()
        self.sitemap_locations: List[str] = []
        self._generate_sitemap_locations()
    
    def _generate_sitemap_locations(self):
        """Generate list of potential sitemap locations"""
        base = self.base_url
        domain = self.domain
        
        # Remove www for alternative checking
        alt_domain = domain.replace('www.', '') if domain.startswith('www.') else f'www.{domain}'
        
        self.sitemap_locations = [
            f"{base}/sitemap.xml",
            f"{base}/sitemap_index.xml",
            f"{base}/sitemap/sitemap.xml",
            f"{base}/sitemaps/sitemap.xml",
            f"{base}/sitemap/index.xml",
            f"{base}/sitemap-index.xml",
            f"{base}/wp-sitemap.xml",
            f"{base}/post-sitemap.xml",
            f"{base}/page-sitemap.xml",
            f"{base}/product-sitemap.xml",
            f"{base}/category-sitemap.xml",
            f"{base}/news-sitemap.xml",
            f"{base}/image-sitemap.xml",
            f"{base}/video-sitemap.xml",
            f"{base}/feeds/posts/sitemap.xml",
            f"{base}/atom.xml",
            f"{base}/rss.xml",
            f"{base}/feed.xml",
            f"{base}/feed/",
            f"{base}/rss/",
            f"https://{alt_domain}/sitemap.xml",
            f"https://{alt_domain}/sitemap_index.xml",
        ]
    
    async def discover_sitemaps(self, session: aiohttp.ClientSession) -> Set[str]:
        """Main method to discover and parse all sitemaps"""
        logger.info("Starting sitemap discovery...")
        
        # Step 1: Check robots.txt for sitemap declarations
        await self._check_robots_txt(session)
        
        # Step 2: Try each potential sitemap location
        for sitemap_url in self.sitemap_locations:
            try:
                urls = await self._fetch_and_parse_sitemap(session, sitemap_url)
                if urls:
                    self.discovered_urls.update(urls)
                    logger.info(f"Found {len(urls)} URLs in sitemap: {sitemap_url}")
                    
                    # Stop if we have enough URLs
                    if len(self.discovered_urls) >= self.max_pages:
                        break
                        
            except Exception as e:
                logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")
                continue
        
        logger.info(f"Sitemap discovery complete. Found {len(self.discovered_urls)} URLs")
        return self.discovered_urls
    
    async def _check_robots_txt(self, session: aiohttp.ClientSession):
        """Check robots.txt for sitemap declarations"""
        robots_url = f"{self.base_url}/robots.txt"
        
        try:
            async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    
                    for line in robots_content.split('\n'):
                        line = line.strip()
                        if line.lower().startswith('sitemap:'):
                            sitemap_url = line.split(':', 1)[1].strip()
                            if sitemap_url not in self.sitemap_locations:
                                self.sitemap_locations.append(sitemap_url)
                                logger.info(f"Found sitemap in robots.txt: {sitemap_url}")
                                
        except Exception as e:
            logger.debug(f"Failed to check robots.txt: {e}")
    
    async def _fetch_and_parse_sitemap(self, session: aiohttp.ClientSession, sitemap_url: str) -> Set[str]:
        """Fetch and parse a sitemap"""
        try:
            async with session.get(sitemap_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return set()
                
                content_type = response.headers.get('content-type', '').lower()
                content = await response.text()
                
                # Determine content type and parse accordingly
                if self._is_xml_content(content_type, content):
                    return await self._parse_xml_sitemap(session, content, sitemap_url)
                elif self._is_html_content(content_type, content):
                    return self._parse_html_sitemap(content, sitemap_url)
                else:
                    logger.debug(f"Unknown content type for {sitemap_url}: {content_type}")
                    return set()
                    
        except Exception as e:
            logger.debug(f"Error fetching sitemap {sitemap_url}: {e}")
            return set()
    
    def _is_xml_content(self, content_type: str, content: str) -> bool:
        """Check if content is XML"""
        return ('xml' in content_type or 
                content.strip().startswith('<?xml') or 
                '<urlset' in content or 
                '<sitemapindex' in content or
                '<rss' in content or
                '<feed' in content)
    
    def _is_html_content(self, content_type: str, content: str) -> bool:
        """Check if content is HTML"""
        return ('html' in content_type or 
                content.strip().startswith('<!DOCTYPE') or 
                '<html' in content)
    
    async def _parse_xml_sitemap(self, session: aiohttp.ClientSession, content: str, base_url: str) -> Set[str]:
        """Parse XML sitemap content"""
        urls = set()
        
        try:
            root = ET.fromstring(content)
            
            # Handle sitemap index
            if root.tag.endswith('sitemapindex') or 'sitemapindex' in root.tag:
                logger.info(f"Processing sitemap index: {base_url}")
                
                # Find all sitemap references
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc_elem = sitemap.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text:
                        nested_sitemap_url = loc_elem.text.strip()
                        if nested_sitemap_url:
                            nested_urls = await self._fetch_and_parse_sitemap(session, nested_sitemap_url)
                            urls.update(nested_urls)
                            
                            if len(urls) >= self.max_pages:
                                break
            
            # Handle regular sitemap
            elif root.tag.endswith('urlset') or 'urlset' in root.tag:
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc_elem = url_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text:
                        url = loc_elem.text.strip()
                        if url and self._is_valid_url(url):
                            urls.add(url)
                            
                            if len(urls) >= self.max_pages:
                                break
            
            # Handle RSS/Atom feeds
            elif 'rss' in root.tag.lower() or 'feed' in root.tag.lower():
                # RSS items
                for item in root.findall('.//item'):
                    link_elem = item.find('link')
                    if link_elem is not None and link_elem.text:
                        url = link_elem.text.strip()
                        if self._is_valid_url(url):
                            urls.add(url)
                
                # Atom entries
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    link_elem = entry.find('.//{http://www.w3.org/2005/Atom}link')
                    if link_elem is not None:
                        url = link_elem.get('href')
                        if url and self._is_valid_url(url):
                            urls.add(url)
                            
        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML sitemap {base_url}: {e}")
            
        return urls
    
    def _parse_html_sitemap(self, content: str, sitemap_url: str) -> Set[str]:
        """Parse HTML sitemap page"""
        urls = set()
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(sitemap_url, href)
                
                if self._is_valid_url(full_url):
                    urls.add(full_url)
                    
                    if len(urls) >= self.max_pages:
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to parse HTML sitemap {sitemap_url}: {e}")
            
        return urls
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and should be crawled"""
        if not url:
            return False
            
        try:
            parsed = urlparse(url)
            
            # Must have valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be from same domain or subdomain
            if not (parsed.netloc == self.domain or 
                    parsed.netloc.endswith(f'.{self.domain}') or
                    self.domain.endswith(f'.{parsed.netloc}')):
                return False
            
            # Skip unwanted file extensions
            if re.search(r'\.(pdf|jpg|jpeg|png|gif|zip|exe|doc|docx|mp4|mp3|avi|wmv|css|js|ico|woff|woff2|ttf|eot|svg)$', 
                        parsed.path.lower()):
                return False
            
            # Skip unwanted paths
            unwanted_paths = ['/admin', '/login', '/wp-admin', '/wp-login', '/dashboard', 
                            '/account', '/user', '/profile', '/settings', '/config',
                            '/api/', '/ajax/', '/json/', '/xml/', '/search?', '/filter?',
                            '/sort?', '/tag/', '/category/', '/author/', '/date/']
            
            for unwanted in unwanted_paths:
                if unwanted in parsed.path.lower():
                    return False
            
            return True
            
        except Exception:
            return False

class EnhancedWebCrawler:
    """Enhanced web crawler with sitemap discovery"""
    
    def __init__(self, 
                 base_url: str,
                 max_subdomains: int = 5,
                 max_pages_per_domain: int = 100,
                 max_concurrent: int = 10,
                 delay_between_requests: float = 1.0,
                 output_file: str = "crawled_content.json",
                 max_memory_mb: int = 5000,
                 prefer_sitemap: bool = True):
        
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_subdomains = max_subdomains
        self.max_pages_per_domain = max_pages_per_domain
        self.max_concurrent = max_concurrent
        self.delay_between_requests = delay_between_requests
        self.output_file = output_file
        self.prefer_sitemap = prefer_sitemap
        
        # Initialize components
        self.resource_monitor = ResourceMonitor(max_memory_mb)
        self.summarizer = ContentSummarizer()
        self.sitemap_discovery = SitemapDiscovery(base_url, max_pages_per_domain)
        
        # State management
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.url_queue: deque = deque()
        self.discovered_subdomains: Set[str] = set()
        self.results: List[CrawlResult] = []
        self.sitemap_urls: Set[str] = set()
        self.crawl_method = "unknown"
        
        # Rate limiting
        self.last_request_time = {}
        self.robots_cache = {}
        
        # Session configuration
        self.session_config = {
            'timeout': aiohttp.ClientTimeout(total=15, connect=5),
            'headers': {
                'User-Agent': 'EnhancedWebCrawler/1.0 (+https://example.com/bot)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
    
    async def crawl(self) -> List[CrawlResult]:
        """Main crawling method"""
        logger.info(f"Starting enhanced crawl of {self.base_url}")
        logger.info(f"Max subdomains: {self.max_subdomains}, Max pages: {self.max_pages_per_domain}")
        logger.info(f"Prefer sitemap: {self.prefer_sitemap}")
        
        async with aiohttp.ClientSession(**self.session_config) as session:
            # Step 1: Try sitemap discovery first
            if self.prefer_sitemap:
                self.sitemap_urls = await self.sitemap_discovery.discover_sitemaps(session)
                
                if self.sitemap_urls:
                    logger.info(f"Using sitemap-based crawling with {len(self.sitemap_urls)} URLs")
                    self.crawl_method = "sitemap"
                    
                    # Add sitemap URLs to queue
                    for url in list(self.sitemap_urls)[:self.max_pages_per_domain]:
                        self.url_queue.append(url)
                else:
                    logger.info("No sitemap found, falling back to manual crawling")
                    self.crawl_method = "manual"
                    await self._setup_manual_crawling(session)
            else:
                logger.info("Manual crawling mode")
                self.crawl_method = "manual"
                await self._setup_manual_crawling(session)
            
            # Step 2: Process URLs with concurrent control
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            while self.url_queue and len(self.results) < self.max_pages_per_domain:
                # Memory check
                if not self.resource_monitor.check_memory_usage():
                    logger.warning("Memory limit reached, stopping crawl")
                    break
                
                # Process batch of URLs
                batch_size = min(self.max_concurrent, len(self.url_queue))
                batch_urls = [self.url_queue.popleft() for _ in range(batch_size)]
                
                if not batch_urls:
                    break
                
                # Create and execute tasks
                tasks = [self._crawl_url(session, semaphore, url) for url in batch_urls]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Add discovered URLs for manual crawling
                if self.crawl_method == "manual":
                    for result in batch_results:
                        if isinstance(result, CrawlResult) and result.links:
                            self._add_discovered_urls(result.links)
                
                # Rate limiting
                await asyncio.sleep(self.delay_between_requests)
                
                # Periodic cleanup
                if len(self.results) % 20 == 0:
                    await self._cleanup_memory()
        
        # Save results
        await self._save_results()
        
        logger.info(f"Crawl completed using {self.crawl_method} method")
        logger.info(f"Processed {len(self.results)} pages")
        logger.info(f"Resource stats: {self.resource_monitor.get_stats()}")
        
        return self.results
    
    async def _setup_manual_crawling(self, session: aiohttp.ClientSession):
        """Setup manual crawling with subdomain discovery"""
        self.url_queue.append(self.base_url)
        
        # Discover subdomains
        await self._discover_subdomains(session)
        
        # Add subdomain URLs to queue
        for subdomain_url in self.discovered_subdomains:
            self.url_queue.append(subdomain_url)
    
    async def _discover_subdomains(self, session: aiohttp.ClientSession):
        """Discover subdomains of the base domain"""
        logger.info("Discovering subdomains...")
        
        common_subdomains = [
            'www', 'blog', 'shop', 'store', 'api', 'app', 'support',
            'help', 'docs', 'forum', 'community', 'news', 'mail',
            'static', 'assets', 'cdn', 'media', 'images'
        ]
        
        base_domain = self.domain.replace('www.', '') if self.domain.startswith('www.') else self.domain
        discovered_count = 0
        
        for subdomain in common_subdomains:
            if discovered_count >= self.max_subdomains:
                break
                
            subdomain_url = f"https://{subdomain}.{base_domain}"
            
            # Skip if same as base domain
            if subdomain_url == self.base_url:
                continue
                
            try:
                async with session.head(subdomain_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        self.discovered_subdomains.add(subdomain_url)
                        discovered_count += 1
                        logger.info(f"Discovered subdomain: {subdomain_url}")
                        
            except Exception:
                continue
        
        logger.info(f"Discovered {discovered_count} subdomains")
    
    async def _crawl_url(self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, url: str) -> Optional[CrawlResult]:
        """Crawl a single URL"""
        async with semaphore:
            if url in self.visited_urls or url in self.failed_urls:
                return None
            
            self.visited_urls.add(url)
            
            # Check robots.txt
            if not await self._check_robots_txt(session, url):
                return None
            
            # Rate limiting
            domain = urlparse(url).netloc
            if domain in self.last_request_time:
                time_since_last = time.time() - self.last_request_time[domain]
                if time_since_last < self.delay_between_requests:
                    await asyncio.sleep(self.delay_between_requests - time_since_last)
            
            try:
                self.last_request_time[domain] = time.time()
                
                async with session.get(url) as response:
                    if response.status != 200:
                        self.failed_urls.add(url)
                        return None
                    
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        return None
                    
                    html_content = await response.text()
                    
                    # Extract content
                    extracted_content = trafilatura.extract(
                        html_content,
                        include_comments=False,
                        include_tables=True,
                        include_images=False,
                        include_links=False,
                        deduplicate=True,
                        favor_precision=True
                    )
                    
                    if not extracted_content or len(extracted_content.strip()) < 100:
                        return None
                    
                    # Parse for metadata and links
                    soup = BeautifulSoup(html_content, 'html.parser')
                    title = soup.find('title')
                    title_text = title.text.strip() if title else urlparse(url).path
                    
                    # Extract links
                    links = self._extract_links(soup, url)
                    
                    # Generate summary
                    summary = self.summarizer.summarize_content(extracted_content)
                    
                    # Create result
                    result = CrawlResult(
                        url=url,
                        title=title_text,
                        content=extracted_content[:2000],  # Limit content size
                        summary=summary,
                        metadata={
                            'domain': domain,
                            'status_code': response.status,
                            'content_type': content_type,
                            'content_length': len(extracted_content),
                            'crawl_method': self.crawl_method
                        },
                        crawl_time=datetime.now().isoformat(),
                        content_hash=hashlib.md5(extracted_content.encode()).hexdigest(),
                        word_count=len(extracted_content.split()),
                        links=links[:10]
                    )
                    
                    self.results.append(result)
                    self.resource_monitor.processed_urls += 1
                    
                    logger.info(f"Crawled: {url} ({len(extracted_content)} chars)")
                    return result
                    
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                self.failed_urls.add(url)
                return None
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract relevant links from HTML"""
        links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include same domain links
            link_domain = urlparse(full_url).netloc
            if (link_domain == base_domain or 
                link_domain.endswith(f'.{base_domain}') or
                base_domain.endswith(f'.{link_domain}')):
                
                # Filter unwanted file types
                if not re.search(r'\.(pdf|jpg|jpeg|png|gif|zip|exe|doc|docx|mp4|mp3|avi|wmv|css|js|ico)$', 
                                full_url, re.I):
                    links.append(full_url)
        
        return list(set(links))
    
    def _add_discovered_urls(self, urls: List[str]):
        """Add discovered URLs to queue"""
        for url in urls:
            if (url not in self.visited_urls and 
                url not in self.failed_urls and 
                len(self.url_queue) < 1000):
                self.url_queue.append(url)
    
    async def _check_robots_txt(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Check robots.txt compliance"""
        domain = urlparse(url).netloc
        
        if domain not in self.robots_cache:
            robots_url = f"https://{domain}/robots.txt"
            try:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        robots_content = await response.text()
                        # Simple robots.txt check - in production, use proper parser
                        if f"User-agent: *" in robots_content and f"Disallow: /" in robots_content:
                            self.robots_cache[domain] = False
                        else:
                            self.robots_cache[domain] = True
                    else:
                        self.robots_cache[domain] = True
            except Exception:
                self.robots_cache[domain] = True
        
        return self.robots_cache[domain]
    
    async def _cleanup_memory(self):
        """Cleanup memory periodically"""
        gc.collect()
        await asyncio.sleep(0.1)  # Allow cleanup to complete
    
    async def _save_results(self):
        """Save results to JSON file"""
        try:
            serializable_results = [asdict(result) for result in self.results]
            
            output = {
                'metadata': {
                    'crawl_time': datetime.now().isoformat(),
                    'base_url': self.base_url,
                    'total_pages': len(self.results),
                    'discovered_subdomains': list(self.discovered_subdomains),
                    'sitemap_urls_found': len(self.sitemap_urls),
                    'crawl_method': self.crawl_method,
                    'resource_stats': self.resource_monitor.get_stats()
                },
                'sitemap_urls': list(self.sitemap_urls) if self.sitemap_urls else [],
                'results': serializable_results
            }
            
            async with aiofiles.open(self.output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(output, indent=2, ensure_ascii=False))
            
            logger.info(f"Results saved to {self.output_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Web Crawler with Sitemap Discovery")
    parser.add_argument('base_url', help='Base URL to crawl')
    parser.add_argument('--max-subdomains', type=int, default=5, help='Maximum number of subdomains to discover')
    parser.add_argument('--max-pages', type=int, default=100, help='Maximum pages per domain')
    parser.add_argument('--max-concurrent', type=int, default=10, help='Maximum concurrent requests')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--output', default='crawled_content.json', help='Output JSON file')
    parser.add_argument('--max-memory', type=int, default=500, help='Maximum memory usage (MB)')
    parser.add_argument('--prefer-sitemap', action='store_true', default=True, 
                        help='Prefer sitemap over manual crawling (default: True)')
    parser.add_argument('--manual-only', action='store_true', 
                        help='Skip sitemap discovery and use manual crawling only')
    
    args = parser.parse_args()
    
    # Validate URL
    if not validators.url(args.base_url):
        logger.error("Invalid base URL provided")
        sys.exit(1)
    
    # Handle manual-only flag
    prefer_sitemap = args.prefer_sitemap and not args.manual_only
    
    # Create crawler
    crawler = EnhancedWebCrawler(
        base_url=args.base_url,
        max_subdomains=args.max_subdomains,
        max_pages_per_domain=args.max_pages,
        max_concurrent=args.max_concurrent,
        delay_between_requests=args.delay,
        output_file=args.output,
        max_memory_mb=args.max_memory,
        prefer_sitemap=prefer_sitemap
    )
    
    # Start crawling
    try:
        results = await crawler.crawl()
        logger.info(f"Crawling completed successfully. {len(results)} pages processed.")
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"CRAWLING SUMMARY")
        print(f"{'='*60}")
        print(f"Base URL: {args.base_url}")
        print(f"Pages processed: {len(results)}")
        print(f"Subdomains discovered: {len(crawler.discovered_subdomains)}")
        print(f"Sitemap URLs found: {len(crawler.sitemap_urls)}")
        print(f"Crawl method: {crawler.crawl_method.title()}")
        print(f"Output file: {args.output}")
        print(f"Resource stats: {crawler.resource_monitor.get_stats()}")
        
        # Show sample results
        if results:
            print(f"\nSample results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result.title[:50]}...")
                print(f"     URL: {result.url}")
                print(f"     Summary: {result.summary[:100]}...")
                print(f"     Word count: {result.word_count}")
                print()
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Required packages
    required_packages = [
        'aiohttp',
        'beautifulsoup4',
        'trafilatura',
        'transformers',
        'torch',
        'psutil',
        'aiofiles',
        'validators'
    ]
    
    print("Enhanced Web Crawler with Sitemap Discovery")
    print("=" * 50)
    print("\nRequired packages:")
    print("pip install " + " ".join(required_packages))
    print("\nUsage Examples:")
    print("# Sitemap-first crawling (recommended):")
    print("python crawler.py https://example.com")
    print("\n# Manual crawling only:")
    print("python crawler.py https://example.com --manual-only")
    print("\n# Advanced configuration:")
    print("python crawler.py https://example.com --max-subdomains 3 --max-pages 50 --delay 2.0")
    print("\n# High-performance crawling:")
    print("python crawler.py https://example.com --max-concurrent 20 --max-memory 1000")
    print("\nFeatures:")
    print("✓ Intelligent sitemap discovery (20+ locations)")
    print("✓ XML sitemap and sitemap index parsing")
    print("✓ HTML sitemap page parsing")
    print("✓ RSS/Atom feed parsing")
    print("✓ Robots.txt compliance checking")
    print("✓ Resource-efficient crawling")
    print("✓ AI-powered content summarization")
    print("✓ Subdomain discovery")
    print("✓ Comprehensive JSON output")
    print("\nStarting crawler...")
    print("=" * 50)
    
    asyncio.run(main())