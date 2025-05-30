#!/usr/bin/env python3
"""
Apify Actor Runner - Run and retrieve results from Apify actors
Supports two modes:
1. Retrieve results from existing run ID
2. Create new run and get results
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configure logging
def setup_logger(debug: bool = False) -> logging.Logger:
    """Setup logger with configurable debug level"""
    logger = logging.getLogger('apify_runner')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler with formatting
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

class ApifyActorRunner:
    """Class to handle Apify actor runs and result retrieval"""
    
    def __init__(self, api_token: str, debug: bool = False):
        self.api_token = api_token
        self.base_url = "https://api.apify.com/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        self.logger = setup_logger(debug)
        
    def get_run_info(self, run_id: str) -> Dict[str, Any]:
        """Get information about a specific run"""
        url = f"{self.base_url}/actor-runs/{run_id}"
        
        self.logger.info(f"Fetching run info for ID: {run_id}")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            self.logger.error(f"Failed to get run info: {response.status_code} - {response.text}")
            raise Exception(f"Failed to get run info: {response.text}")
            
        return response.json()["data"]
    
    def get_dataset_items(self, dataset_id: str, format: str = "json") -> Any:
        """Get items from a dataset"""
        url = f"{self.base_url}/datasets/{dataset_id}/items"
        params = {"format": format}
        
        self.logger.info(f"Fetching dataset items from ID: {dataset_id}")
        response = requests.get(url, params=params, headers=self.headers)
        
        if response.status_code != 200:
            self.logger.error(f"Failed to get dataset items: {response.status_code} - {response.text}")
            raise Exception(f"Failed to get dataset items: {response.text}")
            
        if format == "json":
            return response.json()
        else:
            return response.text
    
    def get_key_value_store_record(self, store_id: str, key: str) -> Any:
        """Get a record from key-value store"""
        url = f"{self.base_url}/key-value-stores/{store_id}/records/{key}"
        
        self.logger.info(f"Fetching key-value store record: {key} from store: {store_id}")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            self.logger.debug(f"Key-value store record '{key}' not found (this is often normal)")
            return None
            
        return response.text
    
    def run_actor(self, actor_id: str, input_data: Dict[str, Any], wait_for_finish: bool = True) -> Dict[str, Any]:
        """Run an actor with given input"""
        url = f"{self.base_url}/acts/{actor_id}/runs"
        
        self.logger.info(f"Starting actor: {actor_id}")
        self.logger.debug(f"Input data: {json.dumps(input_data, indent=2)}")
        
        response = requests.post(url, json=input_data, headers=self.headers)
        
        if response.status_code not in [200, 201]:
            self.logger.error(f"Failed to start actor: {response.status_code} - {response.text}")
            raise Exception(f"Failed to start actor: {response.text}")
            
        run_data = response.json()["data"]
        run_id = run_data["id"]
        self.logger.info(f"Actor run started with ID: {run_id}")
        
        if wait_for_finish:
            return self.wait_for_run_completion(run_id)
        else:
            return run_data
    
    def wait_for_run_completion(self, run_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a run to complete"""
        start_time = time.time()
        
        while True:
            run_info = self.get_run_info(run_id)
            status = run_info["status"]
            
            if status in ["SUCCEEDED", "FAILED", "ABORTED"]:
                self.logger.info(f"Run completed with status: {status}")
                if status == "FAILED":
                    self.logger.error(f"Run failed: {run_info.get('statusMessage', 'Unknown error')}")
                return run_info
            
            elapsed = time.time() - start_time
            if elapsed > timeout:
                self.logger.error(f"Timeout waiting for run completion after {timeout} seconds")
                raise TimeoutError(f"Run did not complete within {timeout} seconds")
            
            self.logger.debug(f"Run status: {status} - waiting... ({elapsed:.1f}s elapsed)")
            time.sleep(5)  # Check every 5 seconds
    
    def get_run_results(self, run_id: str) -> Dict[str, Any]:
        """Get all results from a run"""
        self.logger.info(f"Retrieving results for run ID: {run_id}")
        
        # Get run info
        run_info = self.get_run_info(run_id)
        
        results = {
            "run_id": run_id,
            "status": run_info["status"],
            "started_at": run_info["startedAt"],
            "finished_at": run_info.get("finishedAt"),
            "duration_seconds": run_info["stats"].get("runTimeSecs"),
            "dataset_id": run_info.get("defaultDatasetId"),
            "key_value_store_id": run_info.get("defaultKeyValueStoreId"),
            "data": {}
        }
        
        # Get dataset items if available
        if results["dataset_id"]:
            try:
                dataset_items = self.get_dataset_items(results["dataset_id"])
                results["data"]["dataset_items"] = dataset_items
                self.logger.info(f"Retrieved {len(dataset_items)} items from dataset")
                
                # Extract markdown content from dataset items
                markdown_contents = []
                for item in dataset_items:
                    if "markdown" in item:
                        markdown_contents.append(item["markdown"])
                    elif "text" in item:
                        # Fallback to text field if markdown not available
                        markdown_contents.append(item["text"])
                
                if markdown_contents:
                    # Combine all markdown content
                    results["data"]["markdown"] = "\n\n---\n\n".join(markdown_contents)
                    self.logger.info(f"Extracted markdown content from {len(markdown_contents)} dataset items")
                    
            except Exception as e:
                self.logger.warning(f"Could not retrieve dataset items: {e}")
        
        # Try to get additional data from key-value store (optional)
        if results["key_value_store_id"]:
            try:
                # Common keys for website-content-crawler
                for key in ["OUTPUT", "markdown", "results"]:
                    record = self.get_key_value_store_record(results["key_value_store_id"], key)
                    if record:
                        results["data"][f"kvstore_{key}"] = record
                        self.logger.info(f"Retrieved '{key}' from key-value store")
            except Exception as e:
                self.logger.debug(f"Could not retrieve key-value store records: {e}")
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "output"):
        """Save results to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = results["run_id"]
        
        # Save metadata
        metadata_file = os.path.join(output_dir, f"{run_id}_{timestamp}_metadata.json")
        with open(metadata_file, "w") as f:
            metadata = {k: v for k, v in results.items() if k != "data"}
            json.dump(metadata, f, indent=2)
        self.logger.info(f"Saved metadata to: {metadata_file}")
        
        # Save data
        if results.get("data"):
            for key, value in results["data"].items():
                if value:
                    if key == "dataset_items" and isinstance(value, list):
                        # Save dataset items as JSON
                        data_file = os.path.join(output_dir, f"{run_id}_{timestamp}_dataset.json")
                        with open(data_file, "w") as f:
                            json.dump(value, f, indent=2)
                        self.logger.info(f"Saved dataset to: {data_file}")
                    elif key == "markdown" or "markdown" in key.lower():
                        # Save markdown content
                        md_file = os.path.join(output_dir, f"{run_id}_{timestamp}_content.md")
                        with open(md_file, "w") as f:
                            f.write(value)
                        self.logger.info(f"Saved markdown to: {md_file}")
                    else:
                        # Save other text content
                        ext = "txt" if isinstance(value, str) else "json"
                        data_file = os.path.join(output_dir, f"{run_id}_{timestamp}_{key}.{ext}")
                        with open(data_file, "w") as f:
                            if isinstance(value, str):
                                f.write(value)
                            else:
                                json.dump(value, f, indent=2)
                        self.logger.info(f"Saved {key} to: {data_file}")

def main():
    parser = argparse.ArgumentParser(description="Apify Actor Runner - Run and retrieve results from Apify actors")
    parser.add_argument("mode", choices=["get", "run"], help="Mode: 'get' existing run results or 'run' new actor")
    parser.add_argument("--run-id", help="Run ID (required for 'get' mode)")
    parser.add_argument("--url", help="URL to crawl (required for 'run' mode)")
    parser.add_argument("--actor-id", default="apify~website-content-crawler", help="Actor ID (default: apify~website-content-crawler)")
    parser.add_argument("--config-file", help="JSON file with actor configuration")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for run completion (run mode only)")
    
    args = parser.parse_args()
    
    # Get API token from environment
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        print("Error: APIFY_API_TOKEN not found in environment variables")
        print("Please set it using: export APIFY_API_TOKEN=your_token_here")
        print("Or create a .env file with: APIFY_API_TOKEN=your_token_here")
        sys.exit(1)
    
    # Initialize runner
    runner = ApifyActorRunner(api_token, debug=args.debug)
    
    try:
        if args.mode == "get":
            # Get existing run results
            if not args.run_id:
                print("Error: --run-id is required for 'get' mode")
                sys.exit(1)
            
            results = runner.get_run_results(args.run_id)
            runner.save_results(results, args.output_dir)
            
        elif args.mode == "run":
            # Run new actor
            if not args.url:
                print("Error: --url is required for 'run' mode")
                sys.exit(1)
            
            # Load configuration
            if args.config_file:
                with open(args.config_file, "r") as f:
                    config = json.load(f)
            else:
                # Use default configuration based on your example
                config = {
                    "startUrls": [{"url": args.url, "method": "GET"}],
                    "crawlerType": "playwright:adaptive",
                    "saveMarkdown": True,
                    "saveHtml": False,
                    "saveScreenshots": False,
                    "maxCrawlPages": 1,  # Just crawl the single URL
                    "proxyConfiguration": {"useApifyProxy": True},
                    "removeElementsCssSelector": "nav, footer, script, style, noscript, svg",
                    "readableTextCharThreshold": 100,
                    "htmlTransformer": "readableText"
                }
            
            # Run actor
            run_info = runner.run_actor(args.actor_id, config, wait_for_finish=not args.no_wait)
            
            if not args.no_wait:
                # Get and save results
                results = runner.get_run_results(run_info["id"])
                runner.save_results(results, args.output_dir)
            else:
                print(f"Run started with ID: {run_info['id']}")
                print(f"Check status at: https://console.apify.com/view/runs/{run_info['id']}")
    
    except Exception as e:
        runner.logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 