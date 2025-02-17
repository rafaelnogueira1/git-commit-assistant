#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from typing import List, Tuple, Dict, Optional
import requests
from rich.console import Console
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.style import Style
from git import Repo
from git.exc import InvalidGitRepositoryError
from pathlib import Path
import questionary
from .ai_services import GeminiService, OpenAIService, ClaudeService, DeepseekService

class GitCommitAssistant:
    COMMIT_TYPES = [
        ("🚀 feat", "New feature"),
        ("🐛 fix", "Bug fix"),
        ("📝 docs", "Documentation"),
        ("💅 style", "Style/formatting"),
        ("♻️ refactor", "Code refactoring"),
        ("⚡️ perf", "Performance"),
        ("🧪 test", "Testing"),
        ("🔧 chore", "Chores"),
        ("🔄 ci", "CI changes")
    ]

    SCOPES = [
        "core",      # Core functionality
        "ui",        # User Interface
        "api",       # API/Integrations
        "data",      # Data/Models
        "auth",      # Authentication
        "config",    # Configuration
        "test",      # Tests
        "docs"       # Documentation
    ]

    def __init__(self, config: Dict[str, str]):
        self.console = Console()
        self.original_cwd = os.getcwd()
        self.config = config
        
        # Configuração do serviço de IA
        service_name = config.get('service', 'gemini').lower()
        service_map = {
            'gemini': (GeminiService, 'GEMINI_API_KEY'),
            'openai': (OpenAIService, 'OPENAI_API_KEY'),
            'claude': (ClaudeService, 'ANTHROPIC_API_KEY'),
            'deepseek': (DeepseekService, 'DEEPSEEK_API_KEY')
        }
        
        if service_name not in service_map:
            self.console.print(f"[red]Error: Unsupported AI service: {service_name}[/red]")
            self.console.print("[yellow]Supported services: " + ", ".join(service_map.keys()) + "[/yellow]")
            sys.exit(1)
        
        ServiceClass, key_name = service_map[service_name]
        api_key = config.get('api_key')
        if not api_key:
            self.console.print(f"[red]Error: Missing API key for {service_name}[/red]")
            self.console.print(f"[yellow]Please set it using: export {key_name}='your-api-key'[/yellow]")
            sys.exit(1)
        
        self.ai_service = ServiceClass(api_key)
        
        try:
            git_dir = self._find_git_root()
            if not git_dir:
                raise InvalidGitRepositoryError("Not a git repository")
            
            # Initialize repo without changing directory
            self.repo = Repo(git_dir, search_parent_directories=True)
            
            # Validate git repository state
            if not self._has_commits():
                raise InvalidGitRepositoryError("Repository has no commits yet")
                
        except InvalidGitRepositoryError as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            sys.exit(1)

    def _find_git_root(self) -> Optional[str]:
        """Find the git repository root from the current directory."""
        try:
            # Use git rev-parse to find the git root
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
        
    def _has_commits(self) -> bool:
        try:
            return self._git_operation(lambda: bool(self.repo.head.commit))
        except:
            return False
            
    def _has_changes(self) -> bool:
        """Check if there are any changes to commit."""
        return self._git_operation(lambda: bool(self.repo.index.diff('HEAD') or 
                   self.repo.index.diff(None) or 
                   self.repo.untracked_files))

    def has_staged_changes(self) -> bool:
        """Check if there are any staged changes."""
        return self._git_operation(lambda: bool(self.repo.index.diff('HEAD')))

    def show_file_status(self) -> bool:
        """Show detailed file status with colors. Returns True if there are changes."""
        has_changes = False

        # Staged files (green)
        staged = self.repo.index.diff('HEAD')
        if staged:
            has_changes = True
            table = Table(title="Staged Changes", show_header=True, header_style="bold green")
            table.add_column("Status", style="bold")
            table.add_column("File")
            table.add_column("Changes", style="dim")
            for item in staged:
                try:
                    diff_stats = self.repo.git.diff('--cached', '--numstat', item.a_path).strip()
                    if diff_stats:
                        insertions, deletions, _ = diff_stats.split()
                        changes = f"{int(insertions) + int(deletions)} {'+'*int(insertions)}{'-'*int(deletions)}"
                        full_stats = self.repo.git.diff('--cached', '--shortstat', item.a_path).strip()
                        if full_stats:
                            changes += f"\n{full_stats}"
                    else:
                        changes = "new file"
                except:
                    changes = "modified"
                table.add_row("✓ Staged", f"[green]{item.a_path}[/green]", changes)
            self.console.print(table)
            self.console.print()

        # Modified files (yellow)
        modified = self.repo.index.diff(None)
        if modified:
            has_changes = True
            table = Table(title="Modified Files", show_header=True, header_style="bold yellow")
            table.add_column("Status", style="bold")
            table.add_column("File")
            table.add_column("Changes", style="dim")
            for item in modified:
                try:
                    diff_stats = self.repo.git.diff('--numstat', item.a_path).strip()
                    if diff_stats:
                        insertions, deletions, _ = diff_stats.split()
                        changes = f"{int(insertions) + int(deletions)} {'+'*int(insertions)}{'-'*int(deletions)}"
                        full_stats = self.repo.git.diff('--shortstat', item.a_path).strip()
                        if full_stats:
                            changes += f"\n{full_stats}"
                    else:
                        changes = "modified"
                except:
                    changes = "modified"
                table.add_row("● Modified", f"[yellow]{item.a_path}[/yellow]", changes)
            self.console.print(table)
            self.console.print()

        # Untracked files (red)
        untracked = self.repo.untracked_files
        if untracked:
            has_changes = True
            table = Table(title="Untracked Files", show_header=True, header_style="bold red")
            table.add_column("Status", style="bold")
            table.add_column("File")
            table.add_column("Changes", style="dim")
            for item in untracked:
                table.add_row("? Untracked", f"[red]{item}[/red]", "new file")
            self.console.print(table)
            self.console.print()

        if not has_changes:
            self.console.print("[yellow]No changes detected in the repository.[/yellow]")

        return has_changes

    def select_commit_type(self, suggested_type: str) -> Tuple[str, bool]:
        """Interactive commit type selection."""
        try:
            table = Table(title="Commit Types", show_header=True)
            table.add_column("#", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Description", style="yellow")

            for i, (type_emoji, desc) in enumerate(self.COMMIT_TYPES, 1):
                type_name = type_emoji.split()[1]
                if type_name == suggested_type:
                    table.add_row(str(i), f"[bold green]{type_emoji}[/bold green]", desc + " (suggested)")
                else:
                    table.add_row(str(i), type_emoji, desc)

            self.console.print(table)
            
            default_choice = 1
            for i, (type_emoji, _) in enumerate(self.COMMIT_TYPES, 1):
                if type_emoji.split()[1] == suggested_type:
                    default_choice = i
                    break
            
            choice = IntPrompt.ask(
                "Select commit type",
                default=default_choice
            )
            
            selected_type = self.COMMIT_TYPES[choice-1][0].split()[1]
            is_breaking = Confirm.ask("Is this a breaking change?", default=False)
            
            return selected_type, is_breaking
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)

    def select_scope(self) -> str:
        """Interactive scope selection."""
        try:
            table = Table(title="Available Scopes", show_header=True)
            table.add_column("#", style="cyan")
            table.add_column("Scope", style="green")
            
            for i, scope in enumerate(self.SCOPES, 1):
                table.add_row(str(i), scope)
                
            self.console.print(table)
            
            choice = IntPrompt.ask("Select scope", default=1)
            return self.SCOPES[choice-1]
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)

    def get_commit_details(self, files_changed: str, diff_content: str, force: bool = False) -> Dict:
        """Get commit details from Gemini API or manual input."""
        # First get AI suggestion
        suggestion = self.analyze_changes(diff_content, files_changed)
        
        # Format suggestion for display
        emoji = next((t[0].split()[0] for t in self.COMMIT_TYPES if t[0].split()[1] == suggestion.get('type', 'feat')), "")
        scope = suggestion.get('scope', 'core')
        scope = scope.lower() if scope else 'core'
        formatted_suggestion = f"{emoji} {suggestion.get('type', 'feat')}({scope}): {suggestion.get('description', '').lower()}"
        
        if suggestion.get('detailed_description'):
            detailed_lines = []
            if isinstance(suggestion['detailed_description'], list):
                detailed_lines = [line.strip().strip("'\"").lower() for line in suggestion['detailed_description']]
            else:
                detailed_lines = [line.strip().strip("'\"").lower() for line in suggestion['detailed_description'].split('\n')]
            formatted_suggestion += f"\n\n{'\n'.join(detailed_lines)}"
            
        if suggestion.get('breaking_change'):
            formatted_suggestion += f"\n\nBREAKING CHANGE: {suggestion.get('breaking_description', '').lower()}"
        
        # Show the suggestion
        self.console.print("\n[bold blue]AI Suggestion:[/bold blue]")
        self.console.print(Panel(formatted_suggestion, title="AI Suggestion"))
        
        if force:
            return {
                'type': suggestion.get('type', 'feat'),
                'scope': suggestion.get('scope', 'core'),
                'description': suggestion.get('description', '').lower(),
                'detailed_description': suggestion.get('detailed_description', ''),
                'breaking_change': suggestion.get('breaking_change', False),
                'breaking_description': suggestion.get('breaking_description', '')
            }

        # Let user choose type and scope
        commit_type, is_breaking = self.select_commit_type(suggestion.get('type', 'feat'))
        scope = self.select_scope()
        
        return {
            'type': commit_type,
            'scope': scope,
            'description': suggestion.get('description', '').lower(),
            'detailed_description': suggestion.get('detailed_description', ''),
            'breaking_change': is_breaking,
            'breaking_description': suggestion.get('breaking_description', '') if is_breaking else ''
        }

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        """Analyze changes using Gemini API."""
        prompt = f"""You are a Git commit message analyzer. Analyze the following Git changes and provide a structured response.
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

        try:
            self.console.print("[cyan]Analyzing changes with AI...[/cyan]")
            response = requests.post(
                f"{self.ai_service.api_url}?key={self.ai_service.api_key}",
                headers=self.ai_service.headers,
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
                
            try:
                import json
                return json.loads(content)
            except json.JSONDecodeError as e:
                self.console.print(f"[yellow]Warning: Failed to parse AI response as JSON: {str(e)}[/yellow]")
                
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]API Error: {str(e)}[/red]")
        except Exception as e:
            self.console.print(f"[red]Unexpected error: {str(e)}[/red]")
        
        # Return default values if anything fails
        return {
            'type': 'feat',
            'scope': 'core',
            'description': '',
            'detailed_description': '',
            'breaking_change': False,
            'breaking_description': ''
        }

    def validate_branch(self, force: bool = False) -> None:
        """Validate current branch."""
        protected_branches = ["main", "master", "dev", "develop"]
        current = self.repo.active_branch.name
        
        if current in protected_branches:
            warning = Panel(
                f"[yellow]Warning: You are committing directly to {current} branch[/yellow]",
                title="Branch Warning"
            )
            self.console.print(warning)
            
            # Always ask for confirmation on protected branches, even with force flag
            if not Confirm.ask("Are you sure you want to commit to this branch?"):
                sys.exit(0)

    def format_commit_message(self, details: Dict) -> str:
        """Format the commit message."""
        # Get emoji for the commit type
        emoji = next((t[0].split()[0] for t in self.COMMIT_TYPES if t[0].split()[1] == details['type']), "")
        
        type_part = f"{details['type']}!" if details['breaking_change'] else details['type']
        
        # Handle scope with proper None checking
        scope = details.get('scope')
        scope = (scope or 'core').lower()  # If scope is None or empty, use 'core'
        
        message = f"{emoji} {type_part}({scope}): {details['description'].lower()}"
        
        if details['detailed_description']:
            # Ensure each line starts with - and is lowercase
            detailed_lines = []
            
            # Handle both string and list inputs
            if isinstance(details['detailed_description'], list):
                lines = details['detailed_description']
            else:
                lines = details['detailed_description'].split('\n')
                
            for line in lines:
                if line.strip():
                    line = line.strip().lower()
                    if not line.startswith('-'):
                        line = f"- {line}"
                    detailed_lines.append(line)
            
            message += f"\n\n{'\n'.join(detailed_lines)}"
        
        if details['breaking_change']:
            breaking_desc = details.get('breaking_description', '')
            message += f"\n\nBREAKING CHANGE: {breaking_desc.lower() if breaking_desc else ''}"
        
        return message

    def commit_changes(self, message: str, push: bool = False) -> None:
        """Commit changes and optionally push."""
        def _do_commit():
            self.repo.index.commit(message)
            self.console.print("[green]Changes committed successfully![/green]")
            
            if push:
                remote = self.repo.remote()
                if not remote.exists():
                    self.console.print("[yellow]No remote repository configured.[/yellow]")
                    return
                
                self.console.print("[cyan]Pushing changes...[/cyan]")
                remote.push()
                self.console.print("[green]Changes pushed successfully![/green]")

        try:
            self._git_operation(_do_commit)
        except Exception as e:
            self.console.print(f"[red]Error during commit/push: {str(e)}[/red]")
            sys.exit(1)

    def _ensure_cwd(self):
        """Ensure we're in the original working directory."""
        if os.getcwd() != self.original_cwd:
            os.chdir(self.original_cwd)

    def _git_operation(self, operation):
        """Execute a git operation and ensure we return to original directory."""
        try:
            result = operation()
            self._ensure_cwd()
            return result
        except Exception as e:
            self._ensure_cwd()
            raise e

def main():
    try:
        parser = argparse.ArgumentParser(description="AI-powered Git commit assistant")
        parser.add_argument("-a", "--add", action="store_true", help="Stage all changes")
        parser.add_argument("-f", "--force", action="store_true", help="Skip intermediate confirmations")
        parser.add_argument("-p", "--push", action="store_true", help="Push after commit")
        parser.add_argument("-s", "--service", choices=['gemini', 'openai', 'claude', 'deepseek'], 
                          default=os.getenv('AI_SERVICE', 'gemini'),
                          help="AI service to use (default: gemini)")
        args = parser.parse_args()

        # Get API keys from environment
        config = {
            'service': args.service,
            'api_key': os.getenv(f"{args.service.upper()}_API_KEY")
        }

        assistant = GitCommitAssistant(config)

        # Stage all changes if requested
        if args.add:
            assistant.repo.git.add(".")

        # Show current status and check for changes
        if not assistant.show_file_status():
            sys.exit(0)

        # Check if there are staged changes
        if not assistant.has_staged_changes():
            console = Console()
            console.print("[red]Error: No staged changes to commit[/red]")
            console.print("[yellow]Use 'git add <file>' to stage changes or run with -a to stage all changes[/yellow]")
            sys.exit(1)

        # Validate current branch
        assistant.validate_branch(args.force)

        # Get git changes
        try:
            files_changed = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only"],
                universal_newlines=True
            )
            diff_content = subprocess.check_output(
                ["git", "diff", "--cached"],
                universal_newlines=True
            )
        except subprocess.CalledProcessError as e:
            console = Console()
            console.print(f"[red]Error getting git diff: {str(e)}[/red]")
            sys.exit(1)

        # Get commit details
        details = assistant.get_commit_details(files_changed, diff_content, args.force)

        # Show final message and confirm
        message = assistant.format_commit_message(details)
        console = Console()
        console.print("\n[bold blue]Final Commit Message:[/bold blue]")
        console.print(Panel(message, title="Commit Message"))

        # Show available actions
        action_table = Table(show_header=True, header_style="bold magenta")
        action_table.add_column("Action", style="cyan")
        action_table.add_column("Description", style="yellow")
        
        action_table.add_row("accept", "Proceed with the commit")
        action_table.add_row("edit", "Modify the commit message")
        action_table.add_row("cancel", "Abort the commit")
        
        console.print("\n[bold blue]Available Actions:[/bold blue]")
        console.print(action_table)

        # Interactive selection with arrow keys
        action = questionary.select(
            "What would you like to do?",
            choices=[
                "accept - Proceed with the commit",
                "edit - Modify the commit message",
                "cancel - Abort the commit"
            ],
            default="accept - Proceed with the commit"
        ).ask()

        if not action or action.startswith("cancel"):
            sys.exit(0)
        elif action.startswith("edit"):
            # Create a temporary file with the commit message
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write(message)
                tmp_path = tmp.name

            # Get git editor from config or default to vim
            try:
                editor = subprocess.check_output(
                    ["git", "config", "--get", "core.editor"],
                    universal_newlines=True
                ).strip()
            except subprocess.CalledProcessError:
                editor = os.getenv('EDITOR', 'vim')

            # Open editor with the temporary file
            try:
                subprocess.call([editor, tmp_path])
                
                # Read the edited message
                with open(tmp_path, 'r') as tmp:
                    message = tmp.read().strip()
                
                # Remove temporary file
                os.unlink(tmp_path)
                
                # Show the final edited message
                console.print("\n[bold blue]Final Edited Message:[/bold blue]")
                console.print(Panel(message, title="Edited Commit Message"))
                
                # Confirm the edited message
                if not Confirm.ask("Proceed with this edited message?", default=True):
                    sys.exit(0)
                    
            except Exception as e:
                console.print(f"[red]Error editing message: {str(e)}[/red]")
                os.unlink(tmp_path)
                sys.exit(1)

        # Commit and push
        assistant.commit_changes(message, args.push)
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)

if __name__ == "__main__":
    main()