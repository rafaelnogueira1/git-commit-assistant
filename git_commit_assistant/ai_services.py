from abc import ABC, abstractmethod
import requests
from typing import Dict, Optional
import json

class AIService(ABC):
    @abstractmethod
    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        """Analyze git changes and suggest commit details."""
        pass

    def _format_prompt(self, diff_content: str, files_changed: str) -> str:
        return f"""You are a Git commit message analyzer. Analyze the following Git changes and provide a structured response.

        Your task is to create a detailed and meaningful commit message that clearly explains both WHAT changed and WHY.

        Files changed:
        {files_changed}
        
        Diff content:
        {diff_content}
        
        Based on the changes, determine:
        1. Commit type (choose one): 
           🚀 feat (New feature)
           🐛 fix (Bug fix)
           📝 docs (Documentation)
           💅 style (Style/formatting)
           ♻️ refactor (Code refactoring)
           ⚡️ perf (Performance)
           🧪 test (Testing)
           🔧 chore (Chores)
           🔄 ci (CI changes)
        2. Most appropriate scope from: core, ui, api, data, auth, config, test, docs
        3. A clear and concise description (max 72 chars) that explains WHAT changed
        4. A detailed description explaining WHY the changes were made and their impact
           - Each line must start with "- "
           - Include technical details when relevant
           - Explain the reasoning behind the changes
           - List all significant modifications
           - Describe the impact and benefits of the changes
           - Include any important implementation details
           - Aim for at least 3-4 detail lines
        5. Whether this is a breaking change (changes that break backward compatibility)
        
        Provide your response in this exact JSON format:
        {{
            "type": "commit_type",
            "scope": "affected_scope",
            "description": "clear description of what changed",
            "detailed_description": [
                "- first detail about why and impact",
                "- second detail about why and impact",
                "- technical details if relevant",
                "- other important information"
            ],
            "breaking_change": boolean,
            "breaking_description": "if breaking_change is true, explain why"
        }}

        Important:
        - Return ONLY the JSON object, no other text or markdown formatting
        - Do not include any headers, titles or sections
        - The description must be meaningful and specific
        - The detailed_description MUST be a list of strings
        - Each detail line MUST start with "- "
        - Include at least 3-4 detail lines
        - Make the description comprehensive but concise
        - Focus on both the technical changes and their impact
        - Do not include any additional formatting or text outside the JSON
        - For the "type" field, use ONLY the type name without emoji (e.g., use "feat" not "🚀 feat")
        - Ensure each detail line provides meaningful information about the changes
        - Avoid generic or vague descriptions
        - Include specific technical details when relevant
        """

    def _get_default_response(self) -> Dict:
        return {
            'type': 'feat',
            'scope': 'core',
            'description': 'test commit',
            'detailed_description': [
                "- Added new functionality to improve system capabilities",
                "- Enhanced code structure for better maintainability",
                "- Improved user experience with clearer feedback",
                "- Updated documentation to reflect changes"
            ],
            'breaking_change': False,
            'breaking_description': ''
        }

    def _parse_ai_response(self, content: str) -> Dict:
        """Parse AI response and ensure it's in the correct format."""
        try:
            # Clean up the response
            content = content.strip()
            
            # Remove any markdown or text formatting
            if "```" in content:
                content = content.split("```")[1] if "```json" in content else content.split("```")[0]
            
            # Remove any headers or sections
            if "**" in content:
                content = content.replace("**", "")
            
            content = content.strip()
            
            # Try parsing as JSON first
            try:
                response = json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, try evaluating as Python dict
                try:
                    response = eval(content)
                except:
                    return self._get_default_response()
            
            # Ensure all required fields are present
            required_fields = ['type', 'scope', 'description', 'detailed_description', 'breaking_change', 'breaking_description']
            if not all(field in response for field in required_fields):
                return self._get_default_response()
            
            # Ensure detailed_description is a list
            if isinstance(response['detailed_description'], str):
                response['detailed_description'] = [response['detailed_description']]
            
            # Ensure each line in detailed_description starts with "- "
            if isinstance(response['detailed_description'], list):
                response['detailed_description'] = [
                    line if line.startswith("- ") else f"- {line}"
                    for line in response['detailed_description']
                ]
            
            return response
            
        except Exception as e:
            return self._get_default_response()

class GeminiService(AIService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.headers = {"Content-Type": "application/json"}

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        try:
            prompt = self._format_prompt(diff_content, files_changed)
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=self.headers,
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "topK": 1,
                        "topP": 0.8,
                    }
                }
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            if "error" in response_data:
                print(f"Error from Gemini API: {response_data['error']}")
                return self._get_default_response()
                
            if "candidates" not in response_data or not response_data["candidates"]:
                print("No candidates in response")
                return self._get_default_response()
                
            candidate = response_data["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                print("Invalid response structure")
                return self._get_default_response()
                
            content = candidate["content"]["parts"][0]["text"]
            return self._parse_ai_response(content)
                
        except Exception as e:
            print(f"Error in Gemini service: {str(e)}")
            return self._get_default_response()

class OpenAIService(AIService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.model = "gpt-4"

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        try:
            prompt = self._format_prompt(diff_content, files_changed)
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a Git commit message analyzer."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )
            
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_ai_response(content)
                
        except Exception as e:
            print(f"Error in OpenAI service: {str(e)}")
            return self._get_default_response()

class ClaudeService(AIService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        self.model = "claude-3-opus-20240229"

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        try:
            prompt = self._format_prompt(diff_content, files_changed)
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3
                }
            )
            
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
            return self._parse_ai_response(content)
                
        except Exception as e:
            print(f"Error in Claude service: {str(e)}")
            return self._get_default_response()

class DeepseekService(AIService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.model = "deepseek-coder-33b-instruct"

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        try:
            prompt = self._format_prompt(diff_content, files_changed)
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a Git commit message analyzer."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )
            
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_ai_response(content)
                
        except Exception as e:
            print(f"Error in Deepseek service: {str(e)}")
            return self._get_default_response() 