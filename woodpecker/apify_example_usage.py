#!/usr/bin/env python3
"""
Example usage of the ApifyActorRunner class
"""

import os
from dotenv import load_dotenv
from apify_actor_runner import ApifyActorRunner

# Load environment variables
load_dotenv()

def example_get_existing_run():
    """Example: Get results from an existing run"""
    print("=== Example 1: Get Existing Run Results ===")
    
    # Initialize runner
    api_token = os.getenv("APIFY_API_TOKEN")
    runner = ApifyActorRunner(api_token, debug=True)
    
    # Get results from your run
    run_id = "XCO3ZBYQ8I8Ebsq61"
    results = runner.get_run_results(run_id)
    
    # Save results
    runner.save_results(results, "output")
    
    print(f"\nRun Status: {results['status']}")
    print(f"Duration: {results['duration_seconds']} seconds")
    print(f"Dataset ID: {results['dataset_id']}")

def example_run_new_actor():
    """Example: Run a new actor and get results"""
    print("\n=== Example 2: Run New Actor ===")
    
    # Initialize runner
    api_token = os.getenv("APIFY_API_TOKEN")
    runner = ApifyActorRunner(api_token, debug=False)
    
    # Configure the actor
    config = {
        "startUrls": [{"url": "https://example.com", "method": "GET"}],
        "crawlerType": "playwright:adaptive",
        "saveMarkdown": True,
        "saveHtml": False,
        "maxCrawlPages": 1,
        "proxyConfiguration": {"useApifyProxy": True},
        "removeElementsCssSelector": "nav, footer, script, style, noscript, svg",
        "readableTextCharThreshold": 100,
        "htmlTransformer": "readableText"
    }
    
    # Run the actor
    actor_id = "apify~website-content-crawler"
    run_info = runner.run_actor(actor_id, config, wait_for_finish=True)
    
    # Get and save results
    results = runner.get_run_results(run_info["id"])
    runner.save_results(results, "output")
    
    print(f"\nNew Run ID: {run_info['id']}")
    print(f"Status: {run_info['status']}")
    print(f"Console URL: {run_info.get('consoleUrl', 'N/A')}")

def example_run_without_waiting():
    """Example: Start a run without waiting for completion"""
    print("\n=== Example 3: Run Without Waiting ===")
    
    # Initialize runner
    api_token = os.getenv("APIFY_API_TOKEN")
    runner = ApifyActorRunner(api_token, debug=False)
    
    # Simple config
    config = {
        "startUrls": [{"url": "https://example.com", "method": "GET"}],
        "saveMarkdown": True,
        "maxCrawlPages": 1
    }
    
    # Start the run without waiting
    run_info = runner.run_actor("apify~website-content-crawler", config, wait_for_finish=False)
    
    print(f"Run started with ID: {run_info['id']}")
    print(f"Check status at: https://console.apify.com/view/runs/{run_info['id']}")
    print("\nYou can retrieve results later using:")
    print(f"python apify_actor_runner.py get --run-id {run_info['id']}")

if __name__ == "__main__":
    # Make sure API token is set
    if not os.getenv("APIFY_API_TOKEN"):
        print("Error: Please set APIFY_API_TOKEN in your .env file")
        exit(1)
    
    # Run examples
    try:
        example_get_existing_run()
        # Uncomment to run other examples:
        # example_run_new_actor()
        # example_run_without_waiting()
    except Exception as e:
        print(f"Error: {e}") 