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
import keyring
from .project_analyzer import ProjectAnalyzer

class CredentialsManager:
    """Secure credentials manager using system keyring."""
    
    APP_NAME = "git-commit-assistant"
    
    @staticmethod
    def get_key(service: str) -> Optional[str]:
        """Get API key for service from system keyring."""
        return keyring.get_password(CredentialsManager.APP_NAME, service)
    
    @staticmethod
    def set_key(service: str, api_key: str) -> None:
        """Save API key for service in system keyring."""
        keyring.set_password(CredentialsManager.APP_NAME, service, api_key)
    
    @staticmethod
    def delete_key(service: str) -> None:
        """Delete API key for service from system keyring."""
        try:
            keyring.delete_password(CredentialsManager.APP_NAME, service)
        except keyring.errors.PasswordDeleteError:
            pass

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
        
        # AI service configuration
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
            
            # Initialize project analyzer
            self.project_analyzer = ProjectAnalyzer()
            self.project_context = self.project_analyzer.analyze_project_structure(git_dir)
            
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
            config = self.project_context.get('config', {})
            commit_types = config.get('commitTypes', self.COMMIT_TYPES)
            
            # Convert config format to internal format if needed
            if isinstance(commit_types[0], dict):
                commit_types = [(f"{self.COMMIT_TYPES[i][0].split()[0]} {ct['type']}", ct['description']) 
                              for i, ct in enumerate(commit_types) if i < len(self.COMMIT_TYPES)]
            
            table = Table(title="Commit Types", show_header=True)
            table.add_column("#", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Description", style="yellow")

            for i, (type_emoji, desc) in enumerate(commit_types, 1):
                type_name = type_emoji.split()[-1]  # Get last part after emoji
                if type_name == suggested_type:
                    table.add_row(str(i), f"[bold green]{type_emoji}[/bold green]", desc + " (suggested)")
                else:
                    table.add_row(str(i), type_emoji, desc)

            self.console.print(table)
            
            default_choice = 1
            for i, (type_emoji, _) in enumerate(commit_types, 1):
                if type_emoji.split()[-1] == suggested_type:
                    default_choice = i
                    break
            
            choice = IntPrompt.ask(
                "Select commit type",
                default=default_choice
            )
            
            selected_type = commit_types[choice-1][0].split()[-1]  # Get type without emoji
            is_breaking = Confirm.ask("Is this a breaking change?", default=False)
            
            return selected_type, is_breaking
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)

    def select_scope(self) -> str:
        """Interactive scope selection."""
        try:
            config = self.project_context.get('config', {})
            scopes = config.get('scopes', self.SCOPES)
            
            table = Table(title="Available Scopes", show_header=True)
            table.add_column("#", style="cyan")
            table.add_column("Scope", style="green")
            table.add_column("Description", style="yellow")
            
            suggested_scope = self.current_suggestion.get('scope', 'core').lower() if hasattr(self, 'current_suggestion') else 'core'
            
            for i, scope in enumerate(scopes, 1):
                description = "(suggested)" if scope == suggested_scope else ""
                table.add_row(str(i), f"[{'bold green' if scope == suggested_scope else 'green'}]{scope}[/{'bold green' if scope == suggested_scope else 'green'}]", description)
                
            self.console.print(table)
            
            default_choice = 1
            for i, scope in enumerate(scopes, 1):
                if scope == suggested_scope:
                    default_choice = i
                    break
            
            choice = IntPrompt.ask("Select scope", default=default_choice)
            return scopes[choice-1]
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)

    def get_commit_details(self, files_changed: str, diff_content: str, force: bool = False) -> Dict:
        """Get commit details from AI service or manual input."""
        # First get AI suggestion
        self.current_suggestion = self.analyze_changes(diff_content, files_changed)
        
        # Format suggestion for display
        config = self.project_context.get('config', {})
        commit_types = config.get('commitTypes', self.COMMIT_TYPES)
        
        # Get emoji for commit type
        emoji = next((t[0].split()[0] for t in self.COMMIT_TYPES if t[0].split()[1] == self.current_suggestion.get('type', 'feat')), "🔄")
        
        scope = self.current_suggestion.get('scope', 'core')
        scope = scope.lower() if scope else 'core'
        formatted_suggestion = f"{emoji} {self.current_suggestion.get('type', 'feat')}({scope}): {self.current_suggestion.get('description', '').lower()}"
        
        if self.current_suggestion.get('detailed_description'):
            detailed_lines = []
            if isinstance(self.current_suggestion['detailed_description'], list):
                detailed_lines = self.current_suggestion['detailed_description']
            else:
                detailed_lines = self.current_suggestion['detailed_description'].split('\n')
            
            # Ensure each line starts with "- " and is properly formatted
            formatted_lines = []
            for line in detailed_lines:
                line = line.strip().strip("'\"").lower()
                if line:
                    if not line.startswith("- "):
                        line = f"- {line}"
                    formatted_lines.append(line)
            
            if formatted_lines:
                formatted_suggestion += f"\n\n{'\n'.join(formatted_lines)}"
            
        if self.current_suggestion.get('breaking_change'):
            formatted_suggestion += f"\n\nBREAKING CHANGE: {self.current_suggestion.get('breaking_description', '').lower()}"
        
        # Show the suggestion
        self.console.print("\n[bold blue]AI Suggestion:[/bold blue]")
        self.console.print(Panel(formatted_suggestion, title="Suggested Commit Message", border_style="blue"))
        
        if force:
            return {
                'type': self.current_suggestion.get('type', 'feat'),
                'scope': self.current_suggestion.get('scope', 'core'),
                'description': self.current_suggestion.get('description', '').lower(),
                'detailed_description': formatted_lines if self.current_suggestion.get('detailed_description') else [],
                'breaking_change': self.current_suggestion.get('breaking_change', False),
                'breaking_description': self.current_suggestion.get('breaking_description', '')
            }

        # Let user choose type and scope
        commit_type, is_breaking = self.select_commit_type(self.current_suggestion.get('type', 'feat'))
        scope = self.select_scope()
        
        return {
            'type': commit_type,
            'scope': scope,
            'description': self.current_suggestion.get('description', '').lower(),
            'detailed_description': formatted_lines if self.current_suggestion.get('detailed_description') else [],
            'breaking_change': is_breaking,
            'breaking_description': self.current_suggestion.get('breaking_description', '') if is_breaking else ''
        }

    def analyze_changes(self, diff_content: str, files_changed: str) -> Dict:
        """Analyze changes using AI service with project context."""
        prompt = self.project_analyzer.generate_adaptive_prompt(
            self.project_context,
            diff_content,
            files_changed
        )

        try:
            self.console.print("[cyan]Analyzing changes with AI...[/cyan]")
            response = self.ai_service.analyze_changes(diff_content, files_changed)
            
            if not response or not isinstance(response, dict):
                self.console.print("[yellow]Warning: Invalid response from AI service[/yellow]")
                return self._get_default_commit_details()
            
            # Ensure all required fields are present and valid
            if not response.get('type') or not response.get('scope') or not response.get('description'):
                self.console.print("[yellow]Warning: Missing required fields in AI response[/yellow]")
                return self._get_default_commit_details()
            
            # Ensure detailed_description is a non-empty list
            if not response.get('detailed_description') or not isinstance(response['detailed_description'], list):
                self.console.print("[yellow]Warning: Invalid detailed_description in AI response[/yellow]")
                return self._get_default_commit_details()
            
            # Ensure each line in detailed_description is valid
            valid_lines = [
                line.strip() for line in response['detailed_description']
                if line and isinstance(line, str) and line.strip()
            ]
            
            if not valid_lines:
                self.console.print("[yellow]Warning: No valid lines in detailed_description[/yellow]")
                return self._get_default_commit_details()
            
            response['detailed_description'] = [
                line if line.startswith("- ") else f"- {line}"
                for line in valid_lines
            ]
            
            return response
                
        except Exception as e:
            self.console.print(f"[red]Error analyzing changes: {str(e)}[/red]")
            return self._get_default_commit_details()
    
    def _get_default_commit_details(self) -> Dict:
        """Get default commit details when AI analysis fails."""
        return {
            'type': 'feat',
            'scope': 'core',
            'description': 'update code',
            'detailed_description': [
                "- Added new functionality to improve system capabilities",
                "- Enhanced code structure for better maintainability",
                "- Improved user experience with clearer feedback",
                "- Updated documentation to reflect changes"
            ],
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
                detailed_lines = details['detailed_description']
            else:
                detailed_lines = details['detailed_description'].split('\n')
            
            # Ensure each line starts with "- " and is properly formatted
            formatted_lines = []
            for line in detailed_lines:
                line = line.strip().strip("'\"").lower()
                if line:
                    if not line.startswith("- "):
                        line = f"- {line}"
                    formatted_lines.append(line)
            
            if formatted_lines:
                message += f"\n\n{'\n'.join(formatted_lines)}"
        
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

def configure_ai_service() -> None:
    """Interactive AI service configuration."""
    console = Console()
    
    services = [
        ("gemini", "Google's Gemini Pro - Best for general use"),
        ("openai", "OpenAI's GPT-4 - Most powerful, but expensive"),
        ("claude", "Anthropic's Claude - Great for complex tasks"),
        ("deepseek", "Deepseek Coder - Specialized in code")
    ]
    
    # Format choices for questionary
    choices = [
        f"{service} - {desc}" for service, desc in services
    ]
    
    console.print("\n[bold blue]Available AI Services:[/bold blue]")
    
    # Interactive selection with arrow keys
    selection = questionary.select(
        "Select AI service to configure:",
        choices=choices,
    ).ask()
    
    if not selection:
        sys.exit(0)
        
    selected_service = selection.split(" - ")[0]
    
    # Check for existing key
    current_key = CredentialsManager.get_key(selected_service)
    
    if current_key:
        console.print(f"\n[yellow]Current API key found for {selected_service}[/yellow]")
        if not Confirm.ask("Do you want to update it?", default=False):
            # Save selected service as default even if key is not updated
            with open(os.path.expanduser("~/.gitcommitrc"), "w") as f:
                f.write(f"AI_SERVICE={selected_service}\n")
            console.print(f"[green]✓ {selected_service} set as default service[/green]")
            return
    
    api_key = Prompt.ask("Enter your API key", password=True)
    
    # Save to keyring
    CredentialsManager.set_key(selected_service, api_key)
    
    # Save selected service as default
    with open(os.path.expanduser("~/.gitcommitrc"), "w") as f:
        f.write(f"AI_SERVICE={selected_service}\n")
    
    console.print(f"\n[green]✓ API key securely saved for {selected_service}[/green]")
    console.print(f"[green]✓ {selected_service} set as default service[/green]")

def show_current_config() -> None:
    """Show current AI service configuration."""
    console = Console()
    
    services = {
        'gemini': "Google's Gemini Pro",
        'openai': "OpenAI's GPT-4",
        'claude': "Anthropic's Claude",
        'deepseek': "Deepseek Coder"
    }
    
    # Get current service from config file or default
    current_service = 'gemini'  # Default
    try:
        with open(os.path.expanduser("~/.gitcommitrc")) as f:
            for line in f:
                if line.startswith("AI_SERVICE="):
                    current_service = line.strip().split("=")[1]
                    break
    except FileNotFoundError:
        pass
    
    # Create table
    table = Table(title="Current AI Service Configuration", show_header=True)
    table.add_column("Service", style="cyan")
    table.add_column("Description", style="yellow")
    table.add_column("Status", style="green")
    
    # Add row for current service
    has_key = bool(CredentialsManager.get_key(current_service))
    status = "[green]✓ Configured[/green]" if has_key else "[red]× Not Configured[/red]"
    table.add_row(
        current_service,
        services.get(current_service, "Unknown service"),
        status
    )
    
    console.print(table)
    
    if not has_key:
        console.print("\n[yellow]Run 'gcommit --configure' to set up your API key[/yellow]")

def remove_api_key() -> None:
    """Remove API key for a service."""
    console = Console()
    
    services = [
        ("gemini", "Google's Gemini Pro"),
        ("openai", "OpenAI's GPT-4"),
        ("claude", "Anthropic's Claude"),
        ("deepseek", "Deepseek Coder")
    ]
    
    # Format choices for questionary
    choices = [
        f"{service} - {desc}" for service, desc in services
    ]
    
    console.print("\n[bold blue]Select service to remove API key:[/bold blue]")
    
    # Interactive selection with arrow keys
    selection = questionary.select(
        "Select service:",
        choices=choices,
    ).ask()
    
    if not selection:
        sys.exit(0)
        
    selected_service = selection.split(" - ")[0]
    
    # Check if key exists
    if not CredentialsManager.get_key(selected_service):
        console.print(f"\n[yellow]No API key found for {selected_service}[/yellow]")
        return
    
    if Confirm.ask(f"Are you sure you want to remove the API key for {selected_service}?", default=False):
        CredentialsManager.delete_key(selected_service)
        console.print(f"\n[green]✓ API key removed for {selected_service}[/green]")

def main():
    try:
        parser = argparse.ArgumentParser(description="AI-powered Git commit assistant")
        parser.add_argument("-a", "--add", action="store_true", help="Stage all changes")
        parser.add_argument("-f", "--force", action="store_true", help="Skip intermediate confirmations")
        parser.add_argument("-p", "--push", action="store_true", help="Push after commit")
        parser.add_argument("-s", "--service", choices=['gemini', 'openai', 'claude', 'deepseek'], 
                          help="AI service to use (default: from config or gemini)")
        parser.add_argument("-c", "--configure", action="store_true",
                          help="Configure AI service and API key")
        parser.add_argument("-l", "--list", action="store_true",
                          help="Show current AI service configuration")
        parser.add_argument("-r", "--remove-key", action="store_true",
                          help="Remove API key for a service")
        args = parser.parse_args()

        if args.remove_key:
            remove_api_key()
            sys.exit(0)

        if args.list:
            show_current_config()
            sys.exit(0)

        if args.configure:
            configure_ai_service()
            sys.exit(0)

        # Get service from command line, config file, or default
        service = args.service
        if not service:
            try:
                with open(os.path.expanduser("~/.gitcommitrc")) as f:
                    for line in f:
                        if line.startswith("AI_SERVICE="):
                            service = line.strip().split("=")[1]
                            break
            except FileNotFoundError:
                pass
        service = service or 'gemini'  # Default to gemini if not set

        # Get API key from keyring
        api_key = CredentialsManager.get_key(service)
        if not api_key:
            console = Console()
            console.print(f"[red]Error: No API key found for {service}[/red]")
            console.print("[yellow]Run 'gcommit --configure' to set up your API key[/yellow]")
            sys.exit(1)

        config = {
            'service': service,
            'api_key': api_key
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
        console.print("\n[bold blue]AI Suggested Commit Message:[/bold blue]")
        console.print(Panel(message, title="Suggested Commit Message", border_style="blue"))

        if not args.force:
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