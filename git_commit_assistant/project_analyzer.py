import os
import subprocess
import json
from typing import Dict, Any, List

class ProjectAnalyzer:
    """Analyzes project context to generate more accurate prompts"""
    
    DEFAULT_TYPES = [
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
    
    DEFAULT_SCOPES = [
        "core",      # Core functionality
        "ui",        # User Interface
        "api",       # API/Integrations
        "data",      # Data/Models
        "auth",      # Authentication
        "config",    # Configuration
        "test",      # Tests
        "docs"       # Documentation
    ]

    def analyze_project_structure(self, git_root: str) -> Dict[str, Any]:
        """Analyzes project structure to determine its context"""
        context = {
            'language': self._detect_primary_language(git_root),
            'framework': self._detect_framework(git_root),
            'package_manager': self._detect_package_manager(git_root),
            'scopes': self._detect_scopes(git_root),
            'commit_types': self._detect_commit_types(git_root),
            'config': self.load_project_config(git_root)
        }
        return context
    
    def _detect_primary_language(self, git_root: str) -> str:
        """Detects primary language based on file extensions"""
        extensions = {
            '.py': 'Python', 
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.java': 'Java', 
            '.go': 'Go', 
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.cs': 'C#',
            '.cpp': 'C++',
            '.rs': 'Rust'
        }
        
        file_counts = {}
        for root, _, files in os.walk(git_root):
            if '.git' in root or 'node_modules' in root or 'venv' in root:
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    file_counts[ext] = file_counts.get(ext, 0) + 1
        
        if not file_counts:
            return 'Unknown'
        
        most_common_ext = max(file_counts.items(), key=lambda x: x[1])[0]
        return extensions[most_common_ext]
    
    def _detect_framework(self, git_root: str) -> str:
        """Detects framework based on configuration files"""
        framework_files = {
            'requirements.txt': ['Django', 'Flask', 'FastAPI'],
            'package.json': ['Node.js', 'React', 'Vue', 'Angular'],
            'pom.xml': ['Spring'],
            'build.gradle': ['Spring Boot'],
            'go.mod': ['Go'],
            'Gemfile': ['Ruby on Rails'],
            'composer.json': ['Laravel', 'Symfony'],
            '.csproj': ['.NET'],
            'cargo.toml': ['Rust']
        }
        
        for file, frameworks in framework_files.items():
            if os.path.exists(os.path.join(git_root, file)):
                # Detailed analysis of file content
                with open(os.path.join(git_root, file)) as f:
                    content = f.read().lower()
                    for framework in frameworks:
                        if framework.lower() in content:
                            return framework
                return frameworks[0]  # Returns first framework as default
        
        return 'Unknown'
    
    def _detect_package_manager(self, git_root: str) -> str:
        """Detects package manager"""
        package_managers = {
            'package.json': 'npm/yarn',
            'requirements.txt': 'pip',
            'Gemfile': 'bundler',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'composer.json': 'composer',
            'go.mod': 'go modules',
            'cargo.toml': 'cargo'
        }
        
        for file, manager in package_managers.items():
            if os.path.exists(os.path.join(git_root, file)):
                return manager
        
        return 'Unknown'
    
    def _detect_scopes(self, git_root: str) -> List[str]:
        """Detects scopes based on directory structure"""
        scopes = set(self.DEFAULT_SCOPES)
        
        # Add first-level directories as possible scopes
        for item in os.listdir(git_root):
            if os.path.isdir(os.path.join(git_root, item)) and not item.startswith('.'):
                scopes.add(item.lower())
        
        # Load scopes from project configuration
        config = self.load_project_config(git_root)
        if config and 'scopes' in config:
            scopes.update(config['scopes'])
        
        return sorted(list(scopes))

    def _detect_commit_types(self, git_root: str) -> List[Dict[str, str]]:
        """Detects commit types based on project history"""
        commit_types = {t[0]: t[1] for t in self.DEFAULT_TYPES}
        
        try:
            # Analyze last commits to identify patterns
            output = subprocess.check_output(
                ['git', 'log', '--format=%s', '-n', '50'],
                cwd=git_root,
                stderr=subprocess.DEVNULL
            ).decode()
            
            commits = output.split('\n')
            for commit in commits:
                if ':' in commit:
                    type_part = commit.split(':')[0]
                    if '(' in type_part:
                        type_part = type_part.split('(')[0]
                    type_part = type_part.strip()
                    if type_part and type_part not in commit_types:
                        commit_types[type_part] = "Custom type"
        except:
            pass
        
        # Load commit types from project configuration
        config = self.load_project_config(git_root)
        if config and 'commitTypes' in config:
            for ct in config['commitTypes']:
                commit_types[ct['type']] = ct.get('description', 'Custom type')
        
        return [{'type': k, 'description': v} for k, v in commit_types.items()]

    def load_project_config(self, git_root: str) -> Dict[str, Any]:
        """Loads project-specific configuration if it exists"""
        config_files = [
            '.commitrc.json',
            '.commit-assistant.json',
            'commit.config.json'
        ]
        
        for config_file in config_files:
            config_path = os.path.join(git_root, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    continue
        
        return {}

    def _summarize_structure(self, context: Dict[str, Any]) -> str:
        """Summarizes project structure in readable format"""
        parts = []
        
        if context.get('language'):
            parts.append(f"Language: {context['language']}")
        if context.get('framework') and context['framework'] != 'Unknown':
            parts.append(f"Framework: {context['framework']}")
        if context.get('package_manager') and context['package_manager'] != 'Unknown':
            parts.append(f"Package Manager: {context['package_manager']}")
            
        num_scopes = len(context.get('scopes', []))
        num_types = len(context.get('commit_types', []))
        
        parts.append(f"Available Scopes: {num_scopes}")
        parts.append(f"Commit Types: {num_types}")
        
        return " | ".join(parts)

    def generate_adaptive_prompt(self, context: Dict[str, Any], diff_content: str, files_changed: str) -> str:
        """Generates prompt adapted to project context"""
        config = context.get('config', {})
        
        # Get commit types from project config or defaults
        commit_types = config.get('commitTypes', self.DEFAULT_TYPES)
        
        # Convert commit types to string format
        if isinstance(commit_types[0], dict):
            commit_types_str = ", ".join(ct['type'] for ct in commit_types)
        else:
            commit_types_str = ", ".join(ct[0].split()[-1] for ct in commit_types)
        
        # Get scopes from project config only
        scopes = config.get('scopes', self.DEFAULT_SCOPES)
        scopes_str = ", ".join(scopes)
        
        language = context.get('language', 'Unknown')
        framework = context.get('framework', 'Unknown')
        
        return f"""You are a commit analysis expert for a {language}/{framework} project.
        Analyze the following changes and provide a structured response.

        Changed files:
        {files_changed}
        
        Diff content:
        {diff_content}
        
        Project-specific rules:
        1. Use available commit types: {commit_types_str}
        2. Use ONLY these scopes: {scopes_str}
        3. Description should be clear and concise (max 72 chars)
        4. Detailed description should explain the impact of changes
        5. Indicate breaking changes if there are incompatible changes
        
        Consider project context:
        - Primary language: {language}
        - Framework: {framework}
        - Detected structure: {self._summarize_structure(context)}
        
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
        - Return ONLY the JSON object, no additional text
        - The description must be meaningful and specific
        - The detailed_description must be a list of strings
        - Each detail line must start with "- "
        - Include at least 2-3 detail lines
        - Use ONLY the scopes listed above
        """ 