#!/usr/bin/env python3
"""
Simple Website Scraper for RAG Applications
-------------------------------------------
Extracts content from websites in a format ready for RAG pipelines.
"""

import requests
from bs4 import BeautifulSoup
import json
import argparse
from urllib.parse import urlparse, urljoin
import sys
from collections import deque

def scrape_website(url, max_pages=20, max_depth=2, output_file="scraped_content.json"):
    """
    Scrape website content using BeautifulSoup
    
    Args:
        url (str): URL of the website to scrape
        max_pages (int): Maximum number of pages to scrape
        max_depth (int): Maximum link depth to follow
        output_file (str): Output JSON file path
    """
    # Setup
    parsed_url = urlparse(url)
    base_domain = parsed_url.netloc
    
    # Queue for BFS traversal (url, depth)
    queue = deque([(url, 0)])
    visited = set([url])
    results = []
    
    # Process pages
    while queue and len(results) < max_pages:
        current_url, depth = queue.popleft()
        
        try:
            print(f"Scraping page {len(results)+1}/{max_pages}: {current_url}")
            
            # Get page content
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(current_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = extract_title(soup)
            
            # Extract date
            date = extract_date(soup)
            
            # Extract content
            content = extract_content(soup)
            
            # Add to results
            page_data = {
                "title": title,
                "date": date,
                "link": current_url,
                "content": content
            }
            results.append(page_data)
            
            # Find and queue new links if not at max depth
            if depth < max_depth and len(results) < max_pages:
                for link in soup.find_all('a', href=True):
                    # Get absolute URL
                    next_url = urljoin(current_url, link['href'])
                    
                    # Skip non-HTTP URLs
                    if not next_url.startswith(('http://', 'https://')):
                        continue
                    
                    # Parse URL
                    parsed_next = urlparse(next_url)
                    
                    # Skip fragments and queries, just get the path
                    clean_url = f"{parsed_next.scheme}://{parsed_next.netloc}{parsed_next.path}"
                    
                    # Skip if already visited
                    if clean_url in visited:
                        continue
                    
                    # Skip if not same domain (exact match, no subdomains)
                    if parsed_next.netloc != base_domain:
                        continue
                    
                    # Skip common file types
                    if any(clean_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif']):
                        continue
                    
                    # Add to queue
                    visited.add(clean_url)
                    queue.append((clean_url, depth + 1))
        
        except Exception as e:
            print(f"Error processing {current_url}: {str(e)}")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Scraped {len(results)} pages")
    print(f"Results saved to {output_file}")
    return results

def extract_title(soup):
    """Extract the page title"""
    title = None
    if soup.find('h1'):
        title = soup.find('h1').get_text().strip()
    elif soup.find('meta', property='og:title'):
        title = soup.find('meta', property='og:title')['content'].strip()
    elif soup.find('title'):
        title = soup.find('title').get_text().strip()
    return title or "Unknown Title"

def extract_date(soup):
    """Extract the publication date"""
    date = None
    date_elements = [
        ('meta', {'property': 'article:published_time'}),
        ('meta', {'name': 'date'}),
        ('meta', {'name': 'publication_date'}),
        ('time', {'class': 'entry-date'})
    ]
    
    for tag, attrs in date_elements:
        element = soup.find(tag, attrs)
        if element:
            if tag == 'meta':
                date = element.get('content')
            else:
                date = element.get_text().strip()
            if date:
                break
    
    return date or "Unknown Date"

def extract_content(soup):
    """Extract the page content as markdown"""
    # Remove unwanted elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
    
    # Try to get the main content
    content = ""
    
    # Try common content containers
    content_container = None
    for selector in ['article', 'main', '.content', '#content', '.post', '.article']:
        container = soup.select_one(selector)
        if container:
            content_container = container
            break
    
    # Use body if no content container found
    if not content_container:
        content_container = soup.body
    
    # Extract paragraphs
    for p in content_container.find_all('p'):
        text = p.get_text().strip()
        if text:
            content += text + "\n\n"
    
    # If no paragraphs, just get text
    if not content.strip():
        content = content_container.get_text().strip()
    
    return content

def main():
    parser = argparse.ArgumentParser(description="Simple website scraper for RAG applications")
    parser.add_argument("url", help="URL of the website to scrape")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum number of pages to scrape")
    parser.add_argument("--max-depth", type=int, default=2, help="Maximum link depth to follow")
    parser.add_argument("--output", default="scraped_content.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    scrape_website(args.url, args.max_pages, args.max_depth, args.output)

if __name__ == "__main__":
    main()