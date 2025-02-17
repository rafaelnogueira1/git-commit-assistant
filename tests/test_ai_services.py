import unittest
from unittest.mock import patch, MagicMock
from git_commit_assistant.ai_services import (
    GeminiService,
    OpenAIService,
    ClaudeService,
    DeepseekService
)

class TestAIServices(unittest.TestCase):
    def setUp(self):
        self.diff_content = "test diff"
        self.files_changed = "test.txt"
        self.expected_response = {
            "type": "feat",
            "scope": "core",
            "description": "test commit",
            "detailed_description": "- Added test feature",
            "breaking_change": False,
            "breaking_description": ""
        }

    def test_gemini_service(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"- Added test feature","breaking_change":false,"breaking_description":""}'
                        }]
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            service = GeminiService("test_key")
            result = service.analyze_changes(self.diff_content, self.files_changed)
            
            self.assertEqual(result, self.expected_response)

    def test_openai_service(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"- Added test feature","breaking_change":false,"breaking_description":""}'
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            service = OpenAIService("test_key")
            result = service.analyze_changes(self.diff_content, self.files_changed)
            
            self.assertEqual(result, self.expected_response)

    def test_claude_service(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "content": [{
                    "text": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"- Added test feature","breaking_change":false,"breaking_description":""}'
                }]
            }
            mock_post.return_value = mock_response
            
            service = ClaudeService("test_key")
            result = service.analyze_changes(self.diff_content, self.files_changed)
            
            self.assertEqual(result, self.expected_response)

    def test_deepseek_service(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"- Added test feature","breaking_change":false,"breaking_description":""}'
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            service = DeepseekService("test_key")
            result = service.analyze_changes(self.diff_content, self.files_changed)
            
            self.assertEqual(result, self.expected_response)

    def test_service_error_handling(self):
        services = [
            GeminiService("test_key"),
            OpenAIService("test_key"),
            ClaudeService("test_key"),
            DeepseekService("test_key")
        ]
        
        for service in services:
            with patch("requests.post", side_effect=Exception("API Error")):
                result = service.analyze_changes(self.diff_content, self.files_changed)
                self.assertEqual(result["type"], "feat")
                self.assertEqual(result["scope"], "core")

    def test_service_invalid_json(self):
        invalid_responses = {
            GeminiService: {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": "invalid json"
                        }]
                    }
                }]
            },
            OpenAIService: {
                "choices": [{
                    "message": {
                        "content": "invalid json"
                    }
                }]
            },
            ClaudeService: {
                "content": [{
                    "text": "invalid json"
                }]
            },
            DeepseekService: {
                "choices": [{
                    "message": {
                        "content": "invalid json"
                    }
                }]
            }
        }
        
        for ServiceClass, mock_response in invalid_responses.items():
            with patch("requests.post") as mock_post:
                mock_post_response = MagicMock()
                mock_post_response.json.return_value = mock_response
                mock_post.return_value = mock_post_response
                
                service = ServiceClass("test_key")
                result = service.analyze_changes(self.diff_content, self.files_changed)
                
                self.assertEqual(result["type"], "feat")
                self.assertEqual(result["scope"], "core") 