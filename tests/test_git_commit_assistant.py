import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from git import Repo
from git.exc import InvalidGitRepositoryError
from git_commit_assistant.main import GitCommitAssistant

class TestGitCommitAssistant(unittest.TestCase):
    def setUp(self):
        self.original_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        
        self.api_key = "test_api_key"
        os.environ["GEMINI_API_KEY"] = self.api_key
        
        self.repo = Repo.init(self.temp_dir)
        with open(os.path.join(self.temp_dir, "test.txt"), "w") as f:
            f.write("test content")
        self.repo.index.add(["test.txt"])
        self.repo.index.commit("Initial commit")
        
        self.assistant = GitCommitAssistant({"service": "gemini", "api_key": self.api_key})
        self.assistant.repo = self.repo

    def tearDown(self):
        os.chdir(self.original_dir)
        self.repo.close()
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_init_with_valid_repo(self):
        config = {"service": "gemini", "api_key": self.api_key}
        assistant = GitCommitAssistant(config)
        self.assertIsNotNone(assistant.repo)
        self.assertEqual(assistant.config, config)

    def test_init_with_invalid_repo(self):
        invalid_dir = tempfile.mkdtemp()
        os.chdir(invalid_dir)
        try:
            with patch("git_commit_assistant.main.Repo") as mock_repo:
                mock_repo.side_effect = InvalidGitRepositoryError()
                with self.assertRaises(SystemExit):
                    GitCommitAssistant({"service": "gemini", "api_key": self.api_key})
        finally:
            os.chdir(self.temp_dir)
            import shutil
            shutil.rmtree(invalid_dir)

    def test_has_commits(self):
        self.assertTrue(self.assistant._has_commits())

    def test_has_no_commits(self):
        empty_dir = tempfile.mkdtemp()
        os.chdir(empty_dir)
        try:
            empty_repo = Repo.init(empty_dir)
            self.assistant.repo = empty_repo
            self.assertFalse(self.assistant._has_commits())
        finally:
            os.chdir(self.temp_dir)
            import shutil
            shutil.rmtree(empty_dir)

    def test_has_changes_with_modifications(self):
        with open(os.path.join(self.temp_dir, "test.txt"), "a") as f:
            f.write("\nmore content")
        self.assertTrue(self.assistant._has_changes())

    def test_has_no_changes(self):
        self.assertFalse(self.assistant._has_changes())

    def test_has_staged_changes(self):
        with open(os.path.join(self.temp_dir, "test.txt"), "a") as f:
            f.write("\nmore content")
        self.repo.index.add(["test.txt"])
        self.assertTrue(self.assistant.has_staged_changes())

    def test_validate_branch_protected(self):
        master = self.repo.create_head("master")
        self.repo.head.reference = master
        
        with patch("rich.prompt.Confirm.ask", return_value=True):
            self.assistant.validate_branch()

    def test_validate_branch_not_protected(self):
        feature = self.repo.create_head("feature")
        self.repo.head.reference = feature
        
        self.assistant.validate_branch()  # Não deve levantar exceção

    def test_validate_branch_protected_rejected(self):
        master = self.repo.create_head("master")
        self.repo.head.reference = master
        
        with patch("rich.prompt.Confirm.ask", return_value=False):
            with self.assertRaises(SystemExit):
                self.assistant.validate_branch()

    def test_format_commit_message_simple(self):
        details = {
            "type": "feat",
            "scope": "core",
            "description": "add new feature",
            "detailed_description": "",
            "breaking_change": False,
            "breaking_description": ""
        }
        
        message = self.assistant.format_commit_message(details)
        self.assertIn("feat(core): add new feature", message)

    def test_format_commit_message_breaking(self):
        details = {
            "type": "feat",
            "scope": "core",
            "description": "add new feature",
            "detailed_description": "- Added X\n- Changed Y",
            "breaking_change": True,
            "breaking_description": "This breaks Z"
        }
        
        message = self.assistant.format_commit_message(details)
        self.assertIn("feat!(core):", message)
        self.assertIn("BREAKING CHANGE:", message)

    @patch("requests.post")
    def test_analyze_changes(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"","breaking_change":false}'
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = self.assistant.analyze_changes("diff content", "test.txt")
        self.assertEqual(result["type"], "feat")
        self.assertEqual(result["scope"], "core")

    def test_analyze_changes_error(self):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("API Error")
            result = self.assistant.analyze_changes("diff content", "test.txt")
            self.assertEqual(result["type"], "feat")
            self.assertEqual(result["scope"], "core")

    def test_analyze_changes_invalid_response(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"invalid": "response"}
            mock_post.return_value = mock_response
            
            result = self.assistant.analyze_changes("diff content", "test.txt")
            self.assertEqual(result["type"], "feat")
            self.assertEqual(result["scope"], "core")

    def test_analyze_changes_invalid_json(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": "invalid json"
                        }]
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            result = self.assistant.analyze_changes("diff content", "test.txt")
            self.assertEqual(result["type"], "feat")
            self.assertEqual(result["scope"], "core")

    def test_get_commit_details(self):
        with patch("requests.post") as mock_post, \
             patch("rich.prompt.IntPrompt.ask", return_value=1), \
             patch("rich.prompt.Confirm.ask", return_value=True):
            
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"","breaking_change":false}'
                        }]
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            details = self.assistant.get_commit_details("test.txt", "diff content", force=True)
            self.assertEqual(details["type"], "feat")
            self.assertEqual(details["scope"], "core")
            self.assertEqual(details["description"], "test commit")

    def test_commit_changes(self):
        message = "test: commit message"
        self.assistant.commit_changes(message, push=False)
        
        latest_commit = self.repo.head.commit
        self.assertEqual(latest_commit.message, message)

    def test_commit_with_push(self):
        message = "test: commit with push"
        with patch("git.remote.Remote.exists", return_value=True), \
             patch("git.remote.Remote.push") as mock_push:
            self.assistant.commit_changes(message, push=True)
            mock_push.assert_called_once()
            latest_commit = self.repo.head.commit
            self.assertEqual(latest_commit.message, message)

    def test_show_file_status(self):
        with open(os.path.join(self.temp_dir, "test.txt"), "a") as f:
            f.write("\nmore content")
        self.repo.index.add(["test.txt"])
        
        has_changes = self.assistant.show_file_status()
        self.assertTrue(has_changes)

    def test_select_commit_type(self):
        with patch("rich.prompt.IntPrompt.ask", return_value=1), \
             patch("rich.prompt.Confirm.ask", return_value=False):
            commit_type, is_breaking = self.assistant.select_commit_type("feat")
            self.assertEqual(commit_type, "feat")
            self.assertFalse(is_breaking)

    def test_select_commit_type_breaking(self):
        with patch("rich.prompt.IntPrompt.ask", return_value=1), \
             patch("rich.prompt.Confirm.ask", return_value=True):
            commit_type, is_breaking = self.assistant.select_commit_type("feat")
            self.assertEqual(commit_type, "feat")
            self.assertTrue(is_breaking)

    def test_select_scope(self):
        with patch("rich.prompt.IntPrompt.ask", return_value=1):
            scope = self.assistant.select_scope()
            self.assertEqual(scope, "core")

    def test_find_git_root_valid(self):
        git_root = self.assistant._find_git_root()
        self.assertEqual(os.path.realpath(git_root), os.path.realpath(self.temp_dir))

    def test_find_git_root_invalid(self):
        invalid_dir = tempfile.mkdtemp()
        os.chdir(invalid_dir)
        try:
            with patch("sys.exit") as mock_exit:
                assistant = GitCommitAssistant({"service": "gemini", "api_key": self.api_key})
                mock_exit.assert_called_once_with(1)
        finally:
            os.chdir(self.temp_dir)
            import shutil
            shutil.rmtree(invalid_dir)

    def test_show_file_status_with_staged_changes(self):
        with open(os.path.join(self.temp_dir, "test.txt"), "a") as f:
            f.write("\nmore content")
        self.repo.index.add(["test.txt"])
        
        has_changes = self.assistant.show_file_status()
        self.assertTrue(has_changes)

    def test_show_file_status_with_modified_files(self):
        with open(os.path.join(self.temp_dir, "test.txt"), "a") as f:
            f.write("\nmore content")
        
        has_changes = self.assistant.show_file_status()
        self.assertTrue(has_changes)

    def test_show_file_status_with_untracked_files(self):
        with open(os.path.join(self.temp_dir, "untracked.txt"), "w") as f:
            f.write("untracked content")
        
        has_changes = self.assistant.show_file_status()
        self.assertTrue(has_changes)

    def test_show_file_status_with_no_changes(self):
        has_changes = self.assistant.show_file_status()
        self.assertFalse(has_changes)

    def test_git_operation_error(self):
        def failing_operation():
            raise Exception("Git operation failed")
        
        with self.assertRaises(Exception) as context:
            self.assistant._git_operation(failing_operation)
        self.assertEqual(str(context.exception), "Git operation failed")

    def test_show_file_status_with_diff_error(self):
        with open(os.path.join(self.temp_dir, "test.txt"), "a") as f:
            f.write("\nmore content")
        self.repo.index.add(["test.txt"])
        
        # Create a mock Git object
        mock_git = MagicMock()
        mock_git.diff.side_effect = Exception("Diff failed")
        
        # Create a mock IndexFile object
        mock_index = MagicMock()
        mock_index.diff.return_value = []
        mock_index.untracked_files = []
        
        # Create a mock Repo object
        mock_repo = MagicMock()
        mock_repo.git = mock_git
        mock_repo.index = mock_index
        mock_repo.untracked_files = []
        
        # Replace the repo in the assistant
        self.assistant.repo = mock_repo
        
        with patch.object(self.assistant.console, "print"):
            has_changes = self.assistant.show_file_status()
            self.assertFalse(has_changes)

    def test_select_commit_type_keyboard_interrupt(self):
        with patch("rich.prompt.IntPrompt.ask", side_effect=KeyboardInterrupt), \
             patch("sys.exit") as mock_exit:
            self.assistant.select_commit_type("feat")
            mock_exit.assert_called_once_with(0)

    def test_select_scope_keyboard_interrupt(self):
        with patch("rich.prompt.IntPrompt.ask", side_effect=KeyboardInterrupt), \
             patch("sys.exit") as mock_exit:
            self.assistant.select_scope()
            mock_exit.assert_called_once_with(0)

    def test_get_commit_details_keyboard_interrupt(self):
        with patch("requests.post") as mock_post, \
             patch.object(self.assistant, "select_commit_type", side_effect=KeyboardInterrupt), \
             patch("sys.exit") as mock_exit:
            
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"type":"feat","scope":"core","description":"test commit","detailed_description":"","breaking_change":false,"breaking_description":""}'
                        }]
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            with self.assertRaises(KeyboardInterrupt):
                self.assistant.get_commit_details("test.txt", "diff content")

    def test_analyze_changes_with_empty_diff(self):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"type":"feat","scope":"core","description":"update test.txt","detailed_description":"","breaking_change":false,"breaking_description":""}'
                        }]
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            result = self.assistant.analyze_changes("", "test.txt")
            self.assertEqual(result["description"], "update test.txt")

    def test_analyze_changes_with_long_diff(self):
        long_diff = "diff" * 1000  # Create a long diff content
        result = self.assistant.analyze_changes(long_diff, "test.txt")
        self.assertEqual(result["type"], "feat")
        self.assertEqual(result["scope"], "core")

if __name__ == "__main__":
    unittest.main() 