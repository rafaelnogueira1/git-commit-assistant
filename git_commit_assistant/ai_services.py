from abc import ABC, abstractmethod
import requests
from typing import Dict, Optional
import json

class AIService(ABC):
    COMMIT_TYPES = [
        ("feat", "New feature"),
        ("fix", "Bug fix"),
        ("docs", "Documentation"),
        ("style", "Style/formatting"),
        ("refactor", "Code refactoring"),
        ("perf", "Performance"),
        ("test", "Testing"),
        ("chore", "Chores"),
        ("ci", "CI changes")
    ]

    PROMPT_TEMPLATE = """You are a Git commit message analyzer. Analyze the following Git changes and provide a structured response.

        Your task is to create a detailed and meaningful commit message that clearly explains both WHAT changed and WHY.

        Files changed:
        {files_changed}
        
        Diff content:
        {diff_content}
        
        Based on the changes, determine:
        1. Commit type (choose one): {commit_types}
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
        - The description must be meaningful and specific
        - The detailed_description MUST be a list of strings
        - Each detail line MUST start with "- "
        - Include at least 3-4 detail lines
        - Focus on both the technical changes and their impact
        - For the "type" field, use ONLY the type name without emoji
        - Ensure each detail line provides meaningful information
        - Avoid generic descriptions
        - Include specific technical details when relevant"""

    @abstractmethod
    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        """Analyze git changes and suggest commit details."""
        pass

    def _format_prompt(self, diff_content: str, files_changed: str) -> str:
        commit_types = "\n           ".join(f"{t[0]} ({t[1]})" for t in self.COMMIT_TYPES)
        return self.PROMPT_TEMPLATE.format(
            files_changed=files_changed,
            diff_content=diff_content,
            commit_types=commit_types
        )

    def _get_default_response(self) -> Dict:
        return {
            'type': 'chore',  # Most conservative type for fallback
            'scope': 'core',  # Most general scope
            'description': 'update project files',  # Generic but truthful description
            'detailed_description': [
                "- Make changes to project files",
                "- Update code structure",
                "- Ensure code quality standards"
            ],
            'breaking_change': False,  # Conservative assumption
            'breaking_description': ''
        }

    def _parse_ai_response(self, content: str) -> Dict:
        """Parse AI response and ensure it's in the correct format."""
        try:
            # Handle None content
            if content is None:
                print("Received empty response from AI service")
                return self._get_default_response()
                
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
                    print("Failed to parse AI response")
                    return self._get_default_response()
            
            # Validate response structure
            if not isinstance(response, dict):
                print("AI response is not a dictionary")
                return self._get_default_response()
            
            # Ensure all required fields are present with valid values
            if not response.get('type') or not response.get('scope') or not response.get('description'):
                print("Missing required fields in AI response")
                return self._get_default_response()
            
            # Handle detailed_description
            detailed_desc = response.get('detailed_description', [])
            if isinstance(detailed_desc, str):
                detailed_desc = [line.strip() for line in detailed_desc.split('\n') if line and line.strip()]
            
            if not detailed_desc:
                print("Empty detailed_description")
                return self._get_default_response()
            
            # Format detailed_description lines
            response['detailed_description'] = [
                line if line.strip().startswith("- ") else f"- {line.strip()}"
                for line in detailed_desc
                if line and isinstance(line, str) and line.strip()
            ]
            
            if not response['detailed_description']:
                print("No valid lines in detailed_description")
                return self._get_default_response()
            
            # Ensure other fields have default values if missing
            response['breaking_change'] = bool(response.get('breaking_change', False))
            response['breaking_description'] = str(response.get('breaking_description', '')).strip()
            
            # Validate commit type against allowed types
            valid_types = [t[0] for t in self.COMMIT_TYPES]
            if response['type'] not in valid_types:
                print(f"Invalid commit type: {response['type']}")
                response['type'] = 'chore'  # Fallback to most conservative type
            
            # Ensure description is lowercase and concise
            response['description'] = str(response.get('description', '')).lower().strip()
            if len(response['description']) > 72:
                response['description'] = response['description'][:69] + '...'
            
            return response
            
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            return self._get_default_response()

class BaseAPIService(AIService):
    def __init__(self, api_key: str, api_url: str, model: str):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        try:
            if not diff_content and not files_changed:
                print("No changes to analyze")
                return self._get_default_response()

            prompt = self._format_prompt(diff_content, files_changed)
            print(f"\nSending request to {self.__class__.__name__}...")
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=self._get_request_body(prompt)
            )
            
            response.raise_for_status()
            print(f"Got response from {self.__class__.__name__}")
            
            content = self._extract_content(response.json())
            if not content:
                print(f"No content extracted from {self.__class__.__name__} response")
                return self._get_default_response()
                
            print(f"Parsing response from {self.__class__.__name__}")
            result = self._parse_ai_response(content)
            
            # Validate the result
            if result == self._get_default_response():
                print(f"Got default response from {self.__class__.__name__}, retrying...")
                # Try one more time with a more explicit prompt
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=self._get_request_body(prompt, retry=True)
                )
                response.raise_for_status()
                content = self._extract_content(response.json())
                if content:
                    result = self._parse_ai_response(content)
            
            return result
                
        except requests.exceptions.RequestException as e:
            print(f"Network error in {self.__class__.__name__}: {str(e)}")
            return self._get_default_response()
        except Exception as e:
            print(f"Error in {self.__class__.__name__}: {str(e)}")
            return self._get_default_response()

    def _get_request_body(self, prompt: str, retry: bool = False) -> Dict:
        system_content = """You are a Git commit message analyzer. Your task is to analyze git changes and provide a structured commit message that follows conventional commits format.

You MUST return a valid JSON object with the following structure:
{
    "type": "commit_type",
    "scope": "affected_scope",
    "description": "clear description of what changed",
    "detailed_description": [
        "- first detail about why and impact",
        "- second detail about why and impact",
        "- technical details if relevant"
    ],
    "breaking_change": boolean,
    "breaking_description": "if breaking_change is true, explain why"
}

Rules:
1. The response MUST be a valid JSON object
2. The type MUST be one of: feat, fix, docs, style, refactor, perf, test, chore, ci
3. The description MUST be clear, concise, and under 72 characters
4. The detailed_description MUST be a list of strings, each starting with "- "
5. Include at least 3 detailed description lines
6. Focus on both WHAT changed and WHY it changed
7. Be specific and technical, avoid generic descriptions
8. NEVER return a generic response - analyze the actual changes"""

        if retry:
            system_content += """

IMPORTANT: Your previous response was too generic. Please analyze the changes more carefully and provide a specific, detailed response based on the actual changes in the diff content."""

        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

    @abstractmethod
    def _extract_content(self, response_data: Dict) -> str:
        pass

class OpenAIService(BaseAPIService):
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            api_url="https://api.openai.com/v1/chat/completions",
            model="gpt-4"
        )

    def _extract_content(self, response_data: Dict) -> str:
        try:
            return response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (KeyError, IndexError):
            print("Invalid response format from OpenAI")
            return ""

class DeepseekService(BaseAPIService):
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-coder-33b-instruct"
        )

    def _extract_content(self, response_data: Dict) -> str:
        try:
            return response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (KeyError, IndexError):
            print("Invalid response format from Deepseek")
            return ""

class ClaudeService(BaseAPIService):
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            api_url="https://api.anthropic.com/v1/messages",
            model="claude-3-opus-20240229"
        )
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }

    def _extract_content(self, response_data: Dict) -> str:
        try:
            return response_data.get("content", [{}])[0].get("text", "")
        except (KeyError, IndexError):
            print("Invalid response format from Claude")
            return ""

class GeminiService(AIService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.headers = {"Content-Type": "application/json"}

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        try:
            if not diff_content and not files_changed:
                print("No changes to analyze")
                return self._get_default_response()

            prompt = self._format_prompt(diff_content, files_changed)
            print("\nSending request to Gemini API...")
            
            system_content = """You are a Git commit message analyzer. Your task is to analyze git changes and provide a structured commit message that follows conventional commits format.

You MUST return a valid JSON object with the following structure:
{
    "type": "commit_type",
    "scope": "affected_scope",
    "description": "clear description of what changed",
    "detailed_description": [
        "- first detail about why and impact",
        "- second detail about why and impact",
        "- technical details if relevant"
    ],
    "breaking_change": boolean,
    "breaking_description": "if breaking_change is true, explain why"
}

Rules:
1. The response MUST be a valid JSON object
2. The type MUST be one of: feat, fix, docs, style, refactor, perf, test, chore, ci
3. The description MUST be clear, concise, and under 72 characters
4. The detailed_description MUST be a list of strings, each starting with "- "
5. Include at least 3 detailed description lines
6. Focus on both WHAT changed and WHY it changed
7. Be specific and technical, avoid generic descriptions
8. NEVER return a generic response - analyze the actual changes

Analyze these changes:
"""
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=self.headers,
                json={
                    "contents": {
                        "role": "user",
                        "parts": [
                            {"text": system_content},
                            {"text": prompt}
                        ]
                    },
                    "generationConfig": {
                        "temperature": 0.3,
                        "topK": 1,
                        "topP": 0.8,
                        "maxOutputTokens": 1000,
                    }
                }
            )
            
            response.raise_for_status()
            print("Got response from Gemini API")
            
            response_data = response.json()
            
            if "error" in response_data:
                print(f"Error from Gemini API: {response_data['error']}")
                return self._get_default_response()
                
            if "candidates" not in response_data or not response_data["candidates"]:
                print("No candidates in Gemini response")
                return self._get_default_response()
                
            candidate = response_data["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                print("Invalid response structure from Gemini")
                return self._get_default_response()
                
            try:
                content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
                if not content:
                    print("Empty content from Gemini API")
                    return self._get_default_response()
                    
                print("Parsing Gemini response")
                result = self._parse_ai_response(content)
                
                # If we got a default response, try one more time with a more explicit prompt
                if result == self._get_default_response():
                    print("Got default response from Gemini, retrying...")
                    system_content += """

IMPORTANT: Your previous response was too generic. Please analyze the changes more carefully and provide a specific, detailed response based on the actual changes in the diff content."""
                    
                    response = requests.post(
                        f"{self.api_url}?key={self.api_key}",
                        headers=self.headers,
                        json={
                            "contents": {
                                "role": "user",
                                "parts": [
                                    {"text": system_content},
                                    {"text": prompt}
                                ]
                            },
                            "generationConfig": {
                                "temperature": 0.3,
                                "topK": 1,
                                "topP": 0.8,
                                "maxOutputTokens": 1000,
                            }
                        }
                    )
                    
                    response.raise_for_status()
                    response_data = response.json()
                    if "candidates" in response_data and response_data["candidates"]:
                        content = response_data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if content:
                            result = self._parse_ai_response(content)
                
                return result
                
            except (KeyError, IndexError) as e:
                print(f"Invalid response format from Gemini: {str(e)}")
                return self._get_default_response()
                
        except requests.exceptions.RequestException as e:
            print(f"Network error in Gemini service: {str(e)}")
            return self._get_default_response()
        except Exception as e:
            print(f"Error in Gemini service: {str(e)}")
            return self._get_default_response() 