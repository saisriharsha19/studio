# Navigator Prompt API - Authentication Guide

## 1. Getting an Authentication Token

### Step 1: Get Available Universities

import requests
import json
from typing import List, Dict
# Get list of available universities
response = requests.get("http://localhost:5000/universities")
universities = response.json()
print("Available universities:", universities)
# Output: [{"code": "ufl", "name": "University of Florida", "domain": "ufl.edu"}, ...]


### Step 2: Create Authentication Token

# Create authentication token
university_code = "ufl"  # Choose from available universities
user_id = "anonymous"  # Your unique user identifier

response = requests.post(
    "http://localhost:5000/auth/token",
    params={
        "university_code": university_code,
        "user_id": user_id
    }
)

if response.status_code == 200:
    token_data = response.json()
    access_token = token_data["access_token"]
    print(f"Access token: {access_token}")
else:
    print(f"Error: {response.status_code} - {response.text}")


### Step 3: Use Token for Authenticated Requests

# Set up headers with Bearer token
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Example: Generate a prompt
prompt_request = {
    "user_needs": "Create a system prompt for a helpful AI assistant that can answer questions about university courses and help students with their academic planning."
}

response = requests.post(
    "http://localhost:5000/prompts/generate",
    headers=headers,
    json=prompt_request
)

if response.status_code == 200:
    result = response.json()
    print("Task queued:", result)
    task_id = result["task_id"]
    
    # Check task result
    task_response = requests.get(
        f"http://localhost:5000/prompts/task/{task_id}",
        headers=headers
    )
    print("Task result:", task_response.json())
else:
    print(f"Error: {response.status_code} - {response.text}")


## 2. Complete Python Client Example

import requests
import time
import json
from typing import Optional, Dict, Any

class NavigatorAPIClient:
    """Navigator Prompt API Client"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.university_code: Optional[str] = None
    
    def authenticate(self, university_code: str, user_id: str) -> bool:
        """Authenticate with the API"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/token",
                params={
                    "university_code": university_code,
                    "user_id": user_id
                }
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.user_id = user_id
                self.university_code = university_code
                print(f"✅ Authenticated as {user_id} at {university_code}")
                return True
            else:
                print(f"❌ Authentication failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_universities(self) -> List[Dict]:
        """Get list of available universities"""
        response = requests.get(f"{self.base_url}/universities")
        return response.json()
    
    def generate_prompt(self, user_needs: str, wait_for_result: bool = True) -> Dict[str, Any]:
        """Generate a prompt"""
        headers = self._get_headers()
        
        response = requests.post(
            f"{self.base_url}/prompts/generate",
            headers=headers,
            json={"user_needs": user_needs}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if wait_for_result:
                return self.wait_for_task(result["task_id"])
            else:
                return result
        else:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")
    
    def wait_for_task(self, task_id: str, max_wait: int = 300) -> Dict[str, Any]:
        """Wait for a task to complete"""
        headers = self._get_headers()
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(
                f"{self.base_url}/prompts/task/{task_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result["status"] == "completed":
                    return result["result"]
                elif result["status"] == "failed":
                    raise Exception(f"Task failed: {result.get('error', 'Unknown error')}")
                else:
                    print(f"⏳ Task {result['status']}... waiting")
                    time.sleep(2)
            else:
                raise Exception(f"Task check failed: {response.text}")
        
        raise Exception(f"Task timed out after {max_wait} seconds")
    
    def save_prompt(self, text: str) -> Dict[str, Any]:
        """Save a prompt to history"""
        headers = self._get_headers()
        
        response = requests.post(
            f"{self.base_url}/prompts/save",
            headers=headers,
            json={"text": text}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Save failed: {response.status_code} - {response.text}")
    
    def get_prompt_history(self, limit: int = 20) -> List[Dict]:
        """Get prompt history"""
        headers = self._get_headers()
        
        response = requests.get(
            f"{self.base_url}/prompts/history",
            headers=headers,
            params={"limit": limit}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"History fetch failed: {response.status_code} - {response.text}")
    
    def evaluate_prompt(self, prompt: str, user_needs: str, wait_for_result: bool = True) -> Dict[str, Any]:
        """Evaluate a prompt"""
        headers = self._get_headers()
        
        response = requests.post(
            f"{self.base_url}/prompts/evaluate",
            headers=headers,
            json={
                "prompt": prompt,
                "user_needs": user_needs
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if wait_for_result:
                return self.wait_for_task(result["task_id"])
            else:
                return result
        else:
            raise Exception(f"Evaluation failed: {response.status_code} - {response.text}")

# Usage Example
if __name__ == "__main__":
    # Initialize client
    client = NavigatorAPIClient()
    
    # Get available universities
    print("Available universities:")
    universities = client.get_universities()
    for uni in universities:
        print(f"  - {uni['name']} ({uni['code']})")
    
    # Authenticate
    success = client.authenticate(
        university_code="ufl",  # Choose your university
        user_id="test_user_123"  # Your user ID
    )
    
    if success:
        # Generate a prompt
        print("\n🔄 Generating prompt...")
        user_needs = "Create a helpful AI assistant for students that can answer questions about course registration and academic planning."
        
        try:
            result = client.generate_prompt(user_needs)
            print(f"✅ Generated prompt: {result['initialPrompt'][:100]}...")
            
            # Save the prompt
            saved = client.save_prompt(result['initialPrompt'])
            print(f"💾 Prompt saved with ID: {saved['id']}")
            
            # Get history
            history = client.get_prompt_history(limit=5)
            print(f"📚 Found {len(history)} prompts in history")
            print(history)
            
        except Exception as e:
            print(f"❌ Error: {e}")