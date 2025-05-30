import json
import argparse
import os
import uuid
import re
import base64
import time
from bem._client import BemSDK, APIStatusError
from bem._exceptions import APIConnectionError

def read_text_file(filepath: str) -> str | None:
    """
    Reads the content of a text file containing business document.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return None

def extract_contact_info_with_bem(document_content: str) -> dict | None:
    """
    Uses BEM to extract contact information from a business document.

    Args:
        document_content: The business document text.

    Returns:
        A dictionary with contact information,
        or None if extraction fails.
    """
    sdk_environment = os.environ.get("BEM_ENVIRONMENT", "sandbox")
    print(f"\n--- Extracting Contact Information with BEM API (Environment: {sdk_environment}) ---")
    print("Processing business document...")
    print("Document preview (first 200 chars):")
    print(document_content[:200] + "...\n")

    try:
        # Initialize BEM SDK Client
        client = BemSDK(environment=sdk_environment)
        
        if not client.api_key:
            api_key_env = "BEM_SDK_API_KEY"
            print(f"Error: {api_key_env} environment variable not set.")
            print(f"Please set the {api_key_env} environment variable with your BEM API key.")
            return None

        # Define the extraction prompt for contact information
        extraction_prompt = """
        Please read this business document and extract the company name.
        
        The company name should be at the beginning of the document after "# " or in the title.
        
        Return the company name in this exact JSON format:
        {"company_name": "NAME_FOUND_HERE"}
        
        Example: {"company_name": "TechSolutions Inc."}
        """

        try:
            print("Creating action type config for contact extraction...")
            
            # Step 1: Create action type config with our extraction prompt
            config_response = client.action_type_configs.create(
                body={
                    "name": "simple-company-name-extractor",
                    "actionType": "transform",
                    "prompt": extraction_prompt,
                    "outputSchema": {
                        "type": "object",
                        "title": "Company Name Extraction",
                        "$schema": "http://json-schema.org/draft-07/schema#",
                        "required": ["company_name"],
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "The name of the company found in the document header or title. Look for text after '# ' at the beginning or in titles. Example: 'TechSolutions Inc.'"
                            }
                        }
                    }
                }
            )
            
            # Get config ID
            config_id = None
            if hasattr(config_response, 'action_type_config_id'):
                config_id = config_response.action_type_config_id
            elif hasattr(config_response, 'id'):
                config_id = config_response.id
            
            if not config_id:
                raise Exception("Could not extract config ID from response")
                
            print(f"✅ Created action type config with ID: {config_id}")
            
            # Step 2: Use the config to process our content
            print("Processing document content with BEM...")
            
            # Encode content as base64 (required by BEM API)
            encoded_content = base64.b64encode(document_content.encode('utf-8')).decode('utf-8')
            
            # Try with raw response to see if output is hidden
            print("🔍 Trying .with_raw_response to get full HTTP response...")
            raw_response = client.actions.with_raw_response.create(
                action_type="transform",
                action_type_config_id=config_id,
                actions=[{
                    "reference_id": "contact_extraction_001",
                    "input_content": encoded_content,
                    "input_type": "text"
                }]
            )
            
            print(f"📡 Raw response status: {raw_response.http_response.status_code}")
            print(f"📡 Raw response headers: {dict(raw_response.http_response.headers)}")
            print(f"📡 Raw response content preview: {raw_response.http_response.content[:500]}...")
            
            # Parse the normal response
            response = raw_response.parse()
            print("Successfully called BEM actions API (with raw response)")
            result = parse_bem_response(response, client, document_content)
            if result and len(result) > 0:
                return result
                
        except Exception as e:
            print(f"BEM API approach failed: {e}")
        
        print("No results from BEM")
        return None

    except APIStatusError as e:
        print(f"BEM API Error (Status {e.status_code}): {e.response}")
        return None
    except APIConnectionError as e:
        print(f"BEM Connection Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during BEM interaction: {e}")
        return None
    finally:
        print("--- End of BEM Interaction ---\n")

def poll_bem_action(client: BemSDK, action_id: str, max_wait_seconds: int = 120) -> dict | None:
    """
    Poll BEM action until completion or timeout.
    """
    print(f"🔄 Polling BEM action {action_id}...")
    
    start_time = time.time()
    poll_interval = 5  # Poll every 5 seconds
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # List actions and find our specific action by ID
            response = client.actions.list()
            
            if hasattr(response, 'actions'):
                # Find our action in the list
                target_action = None
                for action in response.actions:
                    if hasattr(action, 'action_id') and action.action_id == action_id:
                        target_action = action
                        break
                
                if target_action:
                    print(f"⏱️  Action status: {target_action.status} (waited {int(time.time() - start_time)}s)")
                    
                    if target_action.status == 'completed':
                        print("✅ BEM action completed successfully!")
                        
                        # Try BEM SDK documentation approaches
                        print("\n🔍 TRYING BEM SDK DOCUMENTATION METHODS:")
                        
                        # 1. Try Pydantic model methods
                        try:
                            if hasattr(target_action, 'to_dict'):
                                action_dict = target_action.to_dict()
                                print(f"✅ to_dict() result: {action_dict}")
                                # Look for output in the dict
                                for key, value in action_dict.items():
                                    if key not in ['inputContent', 'input_content', 'action_id', 'actionID', 'reference_id', 'referenceID', 'action_type_config_id', 'actionTypeConfigID', 'input_type', 'inputType', 'action_type', 'actionType', 'status', 'dryRun']:
                                        if value and isinstance(value, (dict, list, str)) and len(str(value)) > 10:
                                            print(f"🎯 Potential output in to_dict()['{key}']: {value}")
                                            return value
                        except Exception as e:
                            print(f"❌ to_dict() failed: {e}")
                        
                        try:
                            if hasattr(target_action, 'to_json'):
                                action_json = target_action.to_json()
                                print(f"✅ to_json() result: {action_json}")
                                # Try to parse and look for output
                                import json
                                parsed = json.loads(action_json)
                                for key, value in parsed.items():
                                    if key not in ['inputContent', 'input_content', 'action_id', 'actionID', 'reference_id', 'referenceID', 'action_type_config_id', 'actionTypeConfigID', 'input_type', 'inputType', 'action_type', 'actionType', 'status', 'dryRun']:
                                        if value and len(str(value)) > 10:
                                            print(f"🎯 Potential output in to_json()['{key}']: {value}")
                                            return value
                        except Exception as e:
                            print(f"❌ to_json() failed: {e}")
                        
                        # 2. Try model_extra for undocumented fields
                        try:
                            if hasattr(target_action, 'model_extra'):
                                extra_fields = target_action.model_extra
                                print(f"✅ model_extra: {extra_fields}")
                                if extra_fields:
                                    return extra_fields
                        except Exception as e:
                            print(f"❌ model_extra failed: {e}")
                        
                        # 3. Try direct field access with common output names
                        output_field_names = [
                            'result', 'output', 'extracted_data', 'output_content', 'data', 
                            'response', 'content', 'transformed_content', 'processed_data',
                            'extraction_result', 'transform_result', 'analysis_result'
                        ]
                        
                        for field_name in output_field_names:
                            try:
                                if hasattr(target_action, field_name):
                                    field_value = getattr(target_action, field_name)
                                    if field_value:
                                        print(f"✅ Found non-empty field '{field_name}': {field_value}")
                                        return field_value
                                    else:
                                        print(f"🔍 Found empty field '{field_name}': {field_value}")
                            except Exception as e:
                                print(f"❌ Error accessing field '{field_name}': {e}")
                        
                        # 4. Last resort: check ALL attributes for anything that looks like output
                        print("\n🔍 Checking ALL attributes for potential output:")
                        all_attrs = dir(target_action)
                        for attr in all_attrs:
                            if not attr.startswith('_') and attr not in [
                                'action_id', 'action_type', 'action_type_config_id', 'input_content', 
                                'input_type', 'reference_id', 'status', 'construct', 'copy', 'dict', 
                                'from_orm', 'json', 'model_computed_fields', 'model_config', 
                                'model_construct', 'model_copy', 'model_dump', 'model_dump_json', 
                                'model_extra', 'model_fields', 'model_fields_set', 'model_json_schema', 
                                'model_parametrized_name', 'model_post_init', 'model_rebuild', 
                                'model_validate', 'model_validate_json', 'model_validate_strings', 
                                'parse_file', 'parse_obj', 'parse_raw', 'schema', 'schema_json', 
                                'to_dict', 'to_json', 'update_forward_refs', 'validate'
                            ]:
                                try:
                                    attr_value = getattr(target_action, attr)
                                    if attr_value and not callable(attr_value):
                                        print(f"🎯 Found attribute '{attr}': {type(attr_value)} = {attr_value}")
                                        if isinstance(attr_value, (dict, list)) and len(str(attr_value)) > 20:
                                            return attr_value
                                except Exception as e:
                                    print(f"❌ Error accessing attribute '{attr}': {e}")
                        
                        print("❌ No output found even with BEM SDK documentation methods!")
                        return None
                    elif target_action.status == 'failed':
                        error_msg = getattr(target_action, 'error', 'Unknown error')
                        print(f"❌ BEM action failed: {error_msg}")
                        return None
                        
                    elif target_action.status == 'pending':
                        # Still processing, continue polling
                        time.sleep(poll_interval)
                        continue
                    else:
                        print(f"🔍 Unknown status '{target_action.status}', continuing to poll...")
                        time.sleep(poll_interval)
                        continue
                else:
                    print(f"❌ Action {action_id} not found in actions list")
                    return None
            else:
                print("❌ No actions field in response")
                return None
                
        except Exception as e:
            print(f"⚠️  Error polling action: {e}")
            time.sleep(poll_interval)
            continue
    
    print(f"⏰ Polling timeout after {max_wait_seconds}s")
    return None

def parse_bem_response(response, client: BemSDK = None, document_content: str = None) -> dict | None:
    """
    Parse the response from BEM API to extract the contact information.
    """
    try:
        print(f"🔍 BEM Response type: {type(response)}")
        print(f"🔍 BEM Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        
        if hasattr(response, '__dict__'):
            print(f"🔍 BEM Response dict: {response.__dict__}")
        
        # Try the original expected fields
        if hasattr(response, 'extracted_data') and response.extracted_data:
            print("✅ Found extracted_data field")
            return response.extracted_data
        elif hasattr(response, 'result') and response.result:
            print("✅ Found result field")
            return response.result
        elif hasattr(response, 'actions') and response.actions:
            print("✅ Found actions field")
            # Check each action for results
            for action in response.actions:
                print(f"🔍 Action ID: {action.action_id}")
                print(f"🔍 Action Status: {action.status}")
                
                if action.status == 'pending':
                    print("⏳ BEM action is still processing. Starting polling...")
                    print("💡 This may take 1-2 minutes for complex analysis...")
                    if client:
                        # Poll for completion with 2 minute timeout
                        polling_result = poll_bem_action(client, action.action_id, max_wait_seconds=120)
                        if polling_result:
                            return polling_result
                        else:
                            print("⏰ BEM processing timed out or failed")
                            return None
                    else:
                        print("❌ No client provided for polling")
                    return None
                elif action.status == 'completed':
                    print("✅ BEM action completed successfully!")
                    
                    # Try BEM SDK documentation approaches
                    print("\n🔍 TRYING BEM SDK DOCUMENTATION METHODS:")
                    
                    # 1. Try Pydantic model methods
                    try:
                        if hasattr(action, 'to_dict'):
                            action_dict = action.to_dict()
                            print(f"✅ to_dict() result: {action_dict}")
                            # Look for output in the dict
                            for key, value in action_dict.items():
                                if key not in ['inputContent', 'input_content', 'action_id', 'actionID', 'reference_id', 'referenceID', 'action_type_config_id', 'actionTypeConfigID', 'input_type', 'inputType', 'action_type', 'actionType', 'status', 'dryRun']:
                                    if value and isinstance(value, (dict, list, str)) and len(str(value)) > 10:
                                        print(f"🎯 Potential output in to_dict()['{key}']: {value}")
                                        return value
                    except Exception as e:
                        print(f"❌ to_dict() failed: {e}")
                    
                    try:
                        if hasattr(action, 'to_json'):
                            action_json = action.to_json()
                            print(f"✅ to_json() result: {action_json}")
                            # Try to parse and look for output
                            import json
                            parsed = json.loads(action_json)
                            for key, value in parsed.items():
                                if key not in ['inputContent', 'input_content', 'action_id', 'actionID', 'reference_id', 'referenceID', 'action_type_config_id', 'actionTypeConfigID', 'input_type', 'inputType', 'action_type', 'actionType', 'status', 'dryRun']:
                                    if value and len(str(value)) > 10:
                                        print(f"🎯 Potential output in to_json()['{key}']: {value}")
                                        return value
                    except Exception as e:
                        print(f"❌ to_json() failed: {e}")
                    
                    # 2. Try model_extra for undocumented fields
                    try:
                        if hasattr(action, 'model_extra'):
                            extra_fields = action.model_extra
                            print(f"✅ model_extra: {extra_fields}")
                            if extra_fields:
                                return extra_fields
                    except Exception as e:
                        print(f"❌ model_extra failed: {e}")
                    
                    # 3. Try direct field access with common output names
                    output_field_names = [
                        'result', 'output', 'extracted_data', 'output_content', 'data', 
                        'response', 'content', 'transformed_content', 'processed_data',
                        'extraction_result', 'transform_result', 'analysis_result'
                    ]
                    
                    for field_name in output_field_names:
                        try:
                            if hasattr(action, field_name):
                                field_value = getattr(action, field_name)
                                if field_value:
                                    print(f"✅ Found non-empty field '{field_name}': {field_value}")
                                    return field_value
                                else:
                                    print(f"🔍 Found empty field '{field_name}': {field_value}")
                        except Exception as e:
                            print(f"❌ Error accessing field '{field_name}': {e}")
                    
                    # 4. Last resort: check ALL attributes for anything that looks like output
                    print("\n🔍 Checking ALL attributes for potential output:")
                    all_attrs = dir(action)
                    for attr in all_attrs:
                        if not attr.startswith('_') and attr not in [
                            'action_id', 'action_type', 'action_type_config_id', 'input_content', 
                            'input_type', 'reference_id', 'status', 'construct', 'copy', 'dict', 
                            'from_orm', 'json', 'model_computed_fields', 'model_config', 
                            'model_construct', 'model_copy', 'model_dump', 'model_dump_json', 
                            'model_extra', 'model_fields', 'model_fields_set', 'model_json_schema', 
                            'model_parametrized_name', 'model_post_init', 'model_rebuild', 
                            'model_validate', 'model_validate_json', 'model_validate_strings', 
                            'parse_file', 'parse_obj', 'parse_raw', 'schema', 'schema_json', 
                            'to_dict', 'to_json', 'update_forward_refs', 'validate'
                        ]:
                            try:
                                attr_value = getattr(action, attr)
                                if attr_value and not callable(attr_value):
                                    print(f"🎯 Found attribute '{attr}': {type(attr_value)} = {attr_value}")
                                    if isinstance(attr_value, (dict, list)) and len(str(attr_value)) > 20:
                                        return attr_value
                            except Exception as e:
                                print(f"❌ Error accessing attribute '{attr}': {e}")
                    
                    print("❌ No output found even with BEM SDK documentation methods!")
                    return None
                elif action.status == 'failed':
                    print(f"❌ BEM action failed: {getattr(action, 'error', 'Unknown error')}")
                    return None
                else:
                    print(f"🔍 Unknown action status: {action.status}")
            return None
        else:
            print("❌ BEM response doesn't contain expected data structure")
            print(f"🔍 Full response: {response}")
            return None
    except Exception as e:
        print(f"Error parsing BEM response: {e}")
        return None

def save_contact_info_to_json(contact_dict: dict, output_file: str = None) -> None:
    """
    Save the extracted contact information to a JSON file or print to console.
    """
    json_output = json.dumps(contact_dict, indent=2, ensure_ascii=False)
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"✅ Successfully saved contact information to: {output_file}")
        except Exception as e:
            print(f"Error writing to file {output_file}: {e}")
            print("\n📄 Contact Information JSON (console output):")
            print(json_output)
    else:
        print("\n📄 Extracted Contact Information JSON:")
        print(json_output)

def main():
    """
    Main function to extract contact information from business documents.
    """
    parser = argparse.ArgumentParser(
        description="Extract contact information from business documents using BEM AI"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the text file containing the business document"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        help="Optional: Path to save the JSON output. If not provided, prints to console.",
        default=None
    )

    args = parser.parse_args()

    print("📇 Business Contact Information Extractor")
    print("=" * 50)
    print(f"📖 Reading document from: {args.input_file}")

    # Read the input document
    document_content = read_text_file(args.input_file)
    if document_content is None:
        print("❌ Failed to read input file. Exiting.")
        return

    # Extract contact information using BEM
    contact_info = extract_contact_info_with_bem(document_content)
    
    if contact_info and len(contact_info) > 0:
        print(f"✅ Successfully extracted contact information")
        save_contact_info_to_json(contact_info, args.output_file)
    else:
        print("❌ No contact information could be extracted from the document.")
        print("💡 This could mean:")
        print("   • The document doesn't contain contact information")
        print("   • BEM API configuration needs adjustment")
        print("   • The content format is different than expected")

if __name__ == "__main__":
    main() 