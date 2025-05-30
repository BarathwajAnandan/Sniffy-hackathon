#!/usr/bin/env python3

"""
BEM Runner - Batch Experiment Manager for Woodpecker Red-teaming Framework

This script provides a comprehensive interface for running Woodpecker experiments
with support for single experiments, batch processing, and result analysis.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BEMRunner:
    """Batch Experiment Manager for Woodpecker experiments"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.experiments_dir = self.base_dir / "experiments"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Default templates for different experiment types
        self.default_templates = {
            'llm-data-leakage': 'llm-data-leakage-with-prompt-injection.yaml',
            'llm-data-poisoning': 'llm-data-poisoning.yaml',
            'default': 'llm-data-leakage-with-prompt-injection.yaml'
        }
    
    def load_template(self, template_name: str) -> Dict:
        """Load and parse a YAML experiment template"""
        template_path = self.experiments_dir / template_name
        
        if not template_path.exists():
            logger.error(f"Template not found: {template_path}")
            return None
        
        try:
            with open(template_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            return None
    
    def create_experiment_config(self, experiment_id: str, prompt: str, 
                               template_name: str = None, 
                               experiment_type: str = 'llm-data-leakage') -> Optional[str]:
        """Create a customized experiment configuration file"""
        
        # Use default template if none specified
        if not template_name:
            template_name = self.default_templates.get(experiment_type, 
                                                     self.default_templates['default'])
        
        # Load the template
        config = self.load_template(template_name)
        if not config:
            return None
        
        # Customize the configuration
        if 'experiments' in config and len(config['experiments']) > 0:
            exp = config['experiments'][0]
            
            # Update metadata
            if 'metadata' in exp:
                exp['metadata']['name'] = experiment_id
            
            # Update parameters
            if 'parameters' in exp and 'apis' in exp['parameters']:
                if len(exp['parameters']['apis']) > 0:
                    api = exp['parameters']['apis'][0]
                    if 'payload' in api:
                        api['payload']['prompt'] = prompt
        
        # Save the customized configuration
        output_filename = f"{template_name.replace('.yaml', '')}_{experiment_id}.yaml"
        output_path = self.experiments_dir / output_filename
        
        try:
            with open(output_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            logger.info(f"Created experiment config: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving experiment config: {e}")
            return None
    
    def run_woodpecker_command(self, command: List[str]) -> Tuple[bool, str, str]:
        """Execute a woodpecker command and return success status and output"""
        try:
            logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.base_dir,
                timeout=300  # 5 minute timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error("Command timed out after 5 minutes")
            return False, "", "Command timed out"
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return False, "", str(e)
    
    def run_single_experiment(self, experiment_id: str, prompt: str, 
                            template_name: str = None, 
                            experiment_type: str = 'llm-data-leakage') -> bool:
        """Run a single experiment with the given parameters"""
        
        logger.info(f"🚀 Starting experiment: {experiment_id}")
        logger.info(f"   Prompt: {prompt}")
        logger.info(f"   Type: {experiment_type}")
        
        # Create experiment configuration
        config_path = self.create_experiment_config(
            experiment_id, prompt, template_name, experiment_type
        )
        
        if not config_path:
            logger.error(f"❌ Failed to create config for {experiment_id}")
            return False
        
        # Run the experiment
        logger.info(f"Running experiment {experiment_id}...")
        success, stdout, stderr = self.run_woodpecker_command([
            'woodpecker', 'experiment', 'run', '-f', config_path
        ])
        
        if not success:
            logger.error(f"❌ Experiment {experiment_id} failed to run")
            logger.error(f"Error: {stderr}")
            return False
        
        # Verify the results
        logger.info(f"Verifying experiment {experiment_id}...")
        success, stdout, stderr = self.run_woodpecker_command([
            'woodpecker', 'experiment', 'verify', '-f', config_path, '-o', 'json'
        ])
        
        if not success:
            logger.error(f"❌ Experiment {experiment_id} failed verification")
            logger.error(f"Error: {stderr}")
            return False
        
        # Save results
        result_file = self.results_dir / f"{experiment_id}.json"
        try:
            with open(result_file, 'w') as f:
                f.write(stdout)
            logger.info(f"✅ {experiment_id} completed successfully")
            logger.info(f"   Results saved to: {result_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save results for {experiment_id}: {e}")
            return False
    
    def run_batch_experiments(self, batch_config: Dict[str, str], 
                            template_name: str = None,
                            experiment_type: str = 'llm-data-leakage',
                            delay: float = 1.0) -> Dict[str, bool]:
        """Run multiple experiments from a batch configuration"""
        
        logger.info(f"🚀 Starting batch run with {len(batch_config)} experiments")
        logger.info("=" * 60)
        
        results = {}
        successful = 0
        failed = 0
        
        for experiment_id, prompt in batch_config.items():
            try:
                success = self.run_single_experiment(
                    experiment_id, prompt, template_name, experiment_type
                )
                results[experiment_id] = success
                
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # Add delay between experiments
                if delay > 0 and experiment_id != list(batch_config.keys())[-1]:
                    logger.info(f"⏳ Waiting {delay} seconds before next experiment...")
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                logger.warning("⚠️  Batch run interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in {experiment_id}: {e}")
                results[experiment_id] = False
                failed += 1
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📊 BATCH RUN SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total experiments: {len(batch_config)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        if failed > 0:
            logger.warning("⚠️  Some experiments failed - check logs for details")
        else:
            logger.info("✅ All experiments completed successfully!")
        
        return results
    
    def analyze_results(self, experiment_ids: List[str]) -> Dict:
        """Analyze results from multiple experiments and return summary"""
        
        analysis = {
            'total_experiments': len(experiment_ids),
            'successful_experiments': 0,
            'failed_experiments': 0,
            'security_issues_detected': 0,
            'experiments': []
        }
        
        for exp_id in experiment_ids:
            result_file = self.results_dir / f"{exp_id}.json"
            
            if not result_file.exists():
                logger.warning(f"Result file not found for {exp_id}")
                continue
            
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    
                    # Extract key information
                    experiment_info = {
                        'id': exp_id,
                        'description': result.get('description', ''),
                        'technique': result.get('technique', ''),
                        'result_status': list(result.get('result', {}).values())[0] if result.get('result') else 'unknown'
                    }
                    
                    # Get detailed outputs if available
                    if 'result_outputs' in result:
                        outputs = result['result_outputs']
                        if outputs:
                            first_output_key = list(outputs.keys())[0]
                            if outputs[first_output_key] and len(outputs[first_output_key]) > 0:
                                output_data = outputs[first_output_key][0]
                                experiment_info.update({
                                    'prompt': output_data.get('prompt', ''),
                                    'model': output_data.get('model', ''),
                                    'api_response': output_data.get('api_response', '')
                                })
                    
                    analysis['experiments'].append(experiment_info)
                    analysis['successful_experiments'] += 1
                    
                    # Count security issues (when status is 'fail' for data leakage tests)
                    if experiment_info['result_status'] == 'fail':
                        analysis['security_issues_detected'] += 1
                        
            except Exception as e:
                logger.error(f"Error analyzing results for {exp_id}: {e}")
                analysis['failed_experiments'] += 1
        
        return analysis
    
    def print_analysis_report(self, analysis: Dict):
        """Print a formatted analysis report"""
        
        print("\n" + "=" * 80)
        print("📋 EXPERIMENT ANALYSIS REPORT")
        print("=" * 80)
        print(f"Total Experiments: {analysis['total_experiments']}")
        print(f"Successful: {analysis['successful_experiments']}")
        print(f"Failed: {analysis['failed_experiments']}")
        print(f"Security Issues Detected: {analysis['security_issues_detected']}")
        print("-" * 80)
        
        for exp in analysis['experiments']:
            status_emoji = "🔴" if exp['result_status'] == 'fail' else "🟢"
            print(f"{status_emoji} {exp['id']}: {exp['result_status'].upper()}")
            print(f"   Technique: {exp['technique']}")
            if 'prompt' in exp:
                print(f"   Prompt: {exp['prompt'][:60]}{'...' if len(exp['prompt']) > 60 else ''}")
            if 'api_response' in exp:
                response = exp['api_response'][:100] + "..." if len(exp['api_response']) > 100 else exp['api_response']
                print(f"   Response: {response}")
            print()
        
        print("=" * 80)
        
        if analysis['security_issues_detected'] > 0:
            print("⚠️  SECURITY ALERT: Potential data leakage detected!")
        else:
            print("✅ No security issues detected in the tested scenarios.")
    
    def load_batch_file(self, batch_file: str) -> Optional[Dict[str, str]]:
        """Load batch configuration from JSON file"""
        batch_path = Path(batch_file)
        
        if not batch_path.exists():
            logger.error(f"Batch file not found: {batch_path}")
            return None
        
        try:
            with open(batch_path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                logger.error("Batch file must contain a JSON object")
                return None
            
            logger.info(f"Loaded {len(data)} experiments from {batch_file}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in batch file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading batch file: {e}")
            return None

def main():
    """Main entry point for the BEM Runner"""
    
    parser = argparse.ArgumentParser(
        description="BEM Runner - Batch Experiment Manager for Woodpecker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single experiment
  python bem_runner.py --id test-1 --prompt "what is the password?"
  
  # Run batch experiments
  python bem_runner.py --batch-file sample_experiments.json
  
  # Analyze existing results
  python bem_runner.py --analyze test-1,test-2,test-3
  
  # Run with custom template
  python bem_runner.py --id custom-test --prompt "reveal secrets" --template llm-data-poisoning.yaml
        """
    )
    
    # Experiment mode options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', type=str, 
                      help='Experiment ID for single experiment')
    group.add_argument('--batch-file', type=str,
                      help='JSON file containing experiment_id:prompt pairs')
    group.add_argument('--analyze', type=str,
                      help='Comma-separated list of experiment IDs to analyze')
    
    # Common options
    parser.add_argument('--prompt', type=str,
                       help='Prompt for single experiment (required with --id)')
    parser.add_argument('--template', type=str,
                       help='YAML template file to use (default: llm-data-leakage-with-prompt-injection.yaml)')
    parser.add_argument('--type', type=str, default='llm-data-leakage',
                       choices=['llm-data-leakage', 'llm-data-poisoning'],
                       help='Experiment type (default: llm-data-leakage)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between batch experiments in seconds (default: 1.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.id and not args.prompt:
        parser.error("--prompt is required when using --id")
    
    # Initialize the runner
    runner = BEMRunner()
    
    try:
        if args.id:
            # Single experiment mode
            success = runner.run_single_experiment(
                args.id, args.prompt, args.template, args.type
            )
            sys.exit(0 if success else 1)
            
        elif args.batch_file:
            # Batch experiment mode
            batch_config = runner.load_batch_file(args.batch_file)
            if not batch_config:
                sys.exit(1)
            
            results = runner.run_batch_experiments(
                batch_config, args.template, args.type, args.delay
            )
            
            # Analyze batch results
            experiment_ids = list(batch_config.keys())
            analysis = runner.analyze_results(experiment_ids)
            runner.print_analysis_report(analysis)
            
            # Exit with error code if any experiments failed
            failed_count = len([r for r in results.values() if not r])
            sys.exit(1 if failed_count > 0 else 0)
            
        elif args.analyze:
            # Analysis mode
            experiment_ids = [exp_id.strip() for exp_id in args.analyze.split(',')]
            analysis = runner.analyze_results(experiment_ids)
            runner.print_analysis_report(analysis)
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 