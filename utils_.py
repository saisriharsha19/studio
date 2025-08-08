import os
import requests
import json
import time
import logging

# Utility functions
def retry_on_failure(max_retries=3, initial_delay=1, backoff_factor=2):
    """
    Decorator to retry a function on failure with exponential backoff
    
    Args:
        max_retries (int): Maximum number of retry attempts
        initial_delay (float): Initial delay in seconds
        backoff_factor (float): Factor to multiply delay for each retry
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logging.error(f"All {max_retries + 1} attempts failed.")
                        raise last_exception
        return wrapper
    return decorator

def extract_json_from_text(text):
    """
    Extract JSON from text that might contain additional content before or after the JSON
    
    Args:
        text (str): Text that contains JSON somewhere within it
        
    Returns:
        The parsed JSON object or None if no valid JSON is found
    """
    try:
        # First try parsing the entire text as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # If that fails, try to find JSON within the text
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            try:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try with regex to find all potential JSON objects
                import re
                json_pattern = r'({[\s\S]*?})'
                matches = re.findall(json_pattern, text)
                
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
                        
        # If no valid JSON found
        logging.error("No valid JSON found in text")
        return None

def validate_response_against_schema(response, required_keys):
    """
    Validate that a response contains all required keys
    
    Args:
        response (dict): The response dictionary to validate
        required_keys (list): List of required keys
        
    Returns:
        tuple: (is_valid, missing_keys)
    """
    if not isinstance(response, dict):
        return False, ["Response is not a dictionary"]
        
    missing_keys = [key for key in required_keys if key not in response]
    is_valid = len(missing_keys) == 0
    
    return is_valid, missing_keys