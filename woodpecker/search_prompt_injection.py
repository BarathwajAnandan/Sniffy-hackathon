from linkup import LinkupClient
import json
import os
from urllib.parse import urlparse

client = LinkupClient(api_key="db7d6a4d-863b-460d-ae24-e73d992b2fcd")

response = client.search(
    query="LLM prompt injection attack techniques documentation tutorials hacks security bypass methods",
    depth="deep",
    output_type="searchResults",
    include_images=False,
)

print("Search Results:")
print(response)

# Extract URLs from the search results
urls = []

# Handle LinkupSearchTextResult objects
if hasattr(response, 'results'):
    results = response.results
    for result in results:
        # Check if it's a LinkupSearchTextResult object with url attribute
        if hasattr(result, 'url'):
            urls.append(result.url)
        # Also check if it's a dict with url key
        elif isinstance(result, dict) and 'url' in result:
            urls.append(result['url'])

# Also handle if response is a dict format
elif isinstance(response, dict) and 'results' in response:
    results = response['results']
    for result in results:
        if isinstance(result, dict):
            # Try different possible URL fields
            url = result.get('url') or result.get('link') or result.get('href')
            if url:
                urls.append(url)
                
# Check if response has direct URL fields
if isinstance(response, dict):
    for key, value in response.items():
        if 'url' in key.lower() and isinstance(value, str) and value.startswith('http'):
            urls.append(value)

# Remove duplicates while preserving order
unique_urls = []
seen = set()
for url in urls:
    if url not in seen:
        unique_urls.append(url)
        seen.add(url)

# Create results directory if it doesn't exist
os.makedirs('results', exist_ok=True)

# Save URLs to text file
output_file = 'results/llm_prompt_injection_urls.txt'
with open(output_file, 'w') as f:
    f.write("LLM Prompt Injection Documentation and Techniques URLs\n")
    f.write("=" * 55 + "\n\n")
    
    if unique_urls:
        for i, url in enumerate(unique_urls, 1):
            f.write(f"{i}. {url}\n")
    else:
        f.write("No URLs found in search results.\n")
        f.write("\nRaw response for debugging:\n")
        f.write(str(response))

print(f"\nFound {len(unique_urls)} unique URLs")
print(f"URLs saved to: {output_file}")

if unique_urls:
    print("\nExtracted URLs:")
    for i, url in enumerate(unique_urls, 1):
        print(f"{i}. {url}")