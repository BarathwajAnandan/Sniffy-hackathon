#!/usr/bin/env python3
"""
Apify Batch Runner - Read URLs from file and scrape them automatically
"""

import os
import sys
import json
import time
import logging
import re
from typing import List
from urllib.parse import urlparse
from dotenv import load_dotenv
from apify_actor_runner import ApifyActorRunner

# Load environment variables
load_dotenv()

def extract_domain_name(url: str) -> str:
    """Extract clean domain name from URL for filename"""
    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    # Remove special characters and replace with underscores
    domain = re.sub(r'[^\w\-.]', '_', domain)
    return domain

def read_urls_from_file(file_path: str, max_urls: int = None) -> List[str]:
    """Read URLs from text file and return list"""
    urls = []
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return urls
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        # Skip empty lines and headers
        if not line or line.startswith('=') or 'URLs' in line:
            continue
        
        # Extract URL from numbered list format (e.g., "1. https://...")
        if line[0].isdigit() and '. ' in line:
            url = line.split('. ', 1)[1]
            urls.append(url)
    
    if max_urls:
        urls = urls[:max_urls]
    
    return urls

def save_markdown_results(content: str, domain: str, output_dir: str):
    """Save markdown content with domain name as filename"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with domain name
    filename = f"{domain}_content.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Saved markdown content to: {filepath}")

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Configuration
    urls_file = "results/llm_prompt_injection_urls.txt"
    output_dir = "results/apify"
    max_urls = 2  # Process only first 2 URLs for testing
    
    # Get API token
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        print("Error: APIFY_API_TOKEN not found in environment variables")
        sys.exit(1)
    
    # Read URLs from file
    print(f"Reading URLs from: {urls_file}")
    urls = read_urls_from_file(urls_file, max_urls)
    
    if not urls:
        print("No URLs found to process")
        sys.exit(1)
    
    print(f"Found {len(urls)} URLs to process:")
    for i, url in enumerate(urls, 1):
        print(f"{i}. {url}")
    
    # Initialize Apify runner
    runner = ApifyActorRunner(api_token, debug=True)
    
    # Process each URL
    for i, url in enumerate(urls, 1):
        domain = extract_domain_name(url)
        print(f"\n{'='*60}")
        print(f"Processing URL {i}/{len(urls)}: {url}")
        print(f"Domain: {domain}")
        print(f"{'='*60}")
        
        try:
            # Configure the actor
            config = {
                "startUrls": [{"url": url, "method": "GET"}],
                "crawlerType": "playwright:adaptive",
                "saveMarkdown": True,
                "saveHtml": False,
                "saveScreenshots": False,
                "maxCrawlPages": 1,
                "proxyConfiguration": {"useApifyProxy": True},
                "removeElementsCssSelector": "nav, footer, script, style, noscript, svg",
                "readableTextCharThreshold": 100,
                "htmlTransformer": "readableText"
            }
            
            # Run the actor
            actor_id = "apify~website-content-crawler"
            print(f"Starting Apify actor for {domain}...")
            run_info = runner.run_actor(actor_id, config, wait_for_finish=True)
            
            # Get results
            print(f"Retrieving results for {domain}...")
            results = runner.get_run_results(run_info["id"])
            
            # Extract and save markdown content
            if results.get("data", {}).get("markdown"):
                markdown_content = results["data"]["markdown"]
                
                # Add metadata header to markdown
                header = f"""# {domain.replace('_', '.')} - LLM Prompt Injection Documentation

**Source URL:** {url}
**Scraped on:** {time.strftime("%Y-%m-%d %H:%M:%S")}
**Run ID:** {run_info["id"]}

---

"""
                full_content = header + markdown_content
                save_markdown_results(full_content, domain, output_dir)
                
                print(f"✅ Successfully processed {domain}")
            else:
                print(f"⚠️  No markdown content found for {domain}")
            
            # Small delay between requests
            if i < len(urls):
                print("Waiting 5 seconds before next request...")
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Error processing {url}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("Batch processing completed!")
    print(f"Results saved to: {output_dir}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 