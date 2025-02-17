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
        Focus on understanding the changes and suggesting appropriate commit details.

        Files changed:
        {files_changed}
        
        Diff content:
        {diff_content}
        
        Based on the changes, determine:
        1. Commit type (choose one): feat, fix, docs, style, refactor, perf, test, chore, ci
        2. Most appropriate scope from: core, ui, api, data, auth, config, test, docs
        3. A clear and concise description (max 72 chars)
        4. A detailed description explaining the changes (start each item with '- ')
        5. Whether this is a breaking change
        
        Provide your response in this exact JSON format:
        {{
            "type": "commit_type",
            "scope": "affected_scope",
            "description": "short_description",
            "detailed_description": "detailed_changes",
            "breaking_change": boolean,
            "breaking_description": "description if breaking"
        }}

        Important: Return ONLY the JSON object, no other text or explanation.
        Make sure the JSON is valid and properly formatted.
        Ensure each line in detailed_description starts with '- '.
        """

    def _get_default_response(self) -> Dict:
        return {
            'type': 'feat',
            'scope': 'core',
            'description': '',
            'detailed_description': '',
            'breaking_change': False,
            'breaking_description': ''
        }

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
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            # Clean up the response and try to parse it
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content)
                
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
            
            # Clean up the response and try to parse it
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content)
                
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
            
            # Clean up the response and try to parse it
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content)
                
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
            
            # Clean up the response and try to parse it
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content)
                
        except Exception as e:
            print(f"Error in Deepseek service: {str(e)}")
            return self._get_default_response() 