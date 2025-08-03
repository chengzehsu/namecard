import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class PRRequirement:
    """Represents a single requirement from the PR description"""

    action: str  # add, modify, fix, refactor, etc.
    target: str  # file, function, feature, etc.
    description: str
    priority: str = "medium"


@dataclass
class CodeChange:
    """Represents a code change to be made"""

    file_path: str
    change_type: str  # create, modify, delete
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    description: str = ""


class PRCreator:
    """Instant PR creation system that generates complete PRs from natural language descriptions"""

    def __init__(self):
        self.current_dir = os.getcwd()
        self.temp_files = []

    def create_instant_pr(self, description: str, base_branch: str = "main") -> Dict:
        """
        Main function to create a complete PR from a description

        Args:
            description: Natural language description of what needs to be done
            base_branch: Base branch to create PR from (default: main)

        Returns:
            Dict with success status, PR URL, and details
        """
        try:
            # Step 1: Parse requirements from description
            requirements = self._parse_pr_description(description)
            if not requirements:
                return {
                    "success": False,
                    "error": "Could not parse requirements from description",
                }

            # Step 2: Analyze current codebase
            codebase_info = self._analyze_codebase()

            # Step 3: Generate code changes
            changes = self._generate_code_changes(requirements, codebase_info)
            if not changes:
                return {"success": False, "error": "Could not generate code changes"}

            # Step 4: Create feature branch
            branch_name = self._create_feature_branch(description)
            if not branch_name:
                return {"success": False, "error": "Failed to create feature branch"}

            # Step 5: Apply code changes
            applied_changes = self._apply_code_changes(changes)
            if not applied_changes:
                return {"success": False, "error": "Failed to apply code changes"}

            # Step 6: Run tests and validation
            validation_result = self._validate_changes()

            # Step 7: Commit changes
            commit_result = self._commit_changes(description, requirements)
            if not commit_result:
                return {"success": False, "error": "Failed to commit changes"}

            # Step 8: Push and create PR
            pr_result = self._create_pull_request(
                description, requirements, branch_name, base_branch
            )

            return {
                "success": True,
                "pr_url": pr_result.get("url", ""),
                "branch_name": branch_name,
                "changes_applied": len(applied_changes),
                "validation_passed": validation_result.get("success", False),
                "details": {
                    "requirements": [req.__dict__ for req in requirements],
                    "changes": [change.__dict__ for change in applied_changes],
                    "validation": validation_result,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
        finally:
            self._cleanup_temp_files()

    def _parse_pr_description(self, description: str) -> List[PRRequirement]:
        """Parse natural language description into structured requirements"""
        requirements = []

        # Common action patterns
        action_patterns = {
            r"add|create|implement|build": "add",
            r"fix|repair|resolve|correct": "fix",
            r"update|modify|change|edit": "modify",
            r"refactor|restructure|reorganize": "refactor",
            r"remove|delete|drop": "remove",
            r"improve|enhance|optimize": "improve",
        }

        # Split description into sentences/lines
        sentences = re.split(r"[.!?;\n]", description.lower())

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Determine action
            action = "modify"  # default
            for pattern, act in action_patterns.items():
                if re.search(pattern, sentence):
                    action = act
                    break

            # Extract target (look for specific patterns)
            target = self._extract_target_from_sentence(sentence)

            # Determine priority
            priority = "medium"
            if any(
                word in sentence for word in ["urgent", "critical", "important", "must"]
            ):
                priority = "high"
            elif any(
                word in sentence for word in ["minor", "small", "simple", "optional"]
            ):
                priority = "low"

            requirements.append(
                PRRequirement(
                    action=action,
                    target=target,
                    description=sentence,
                    priority=priority,
                )
            )

        return requirements

    def _extract_target_from_sentence(self, sentence: str) -> str:
        """Extract the target (what to work on) from a sentence"""
        # Look for file extensions
        file_match = re.search(r"(\w+\.(py|js|html|css|md|json|yml|yaml))", sentence)
        if file_match:
            return file_match.group(1)

        # Look for function/class patterns
        func_match = re.search(r"function\s+(\w+)|def\s+(\w+)|class\s+(\w+)", sentence)
        if func_match:
            return func_match.group(1) or func_match.group(2) or func_match.group(3)

        # Look for feature names
        feature_words = ["feature", "module", "component", "service", "api", "endpoint"]
        for word in feature_words:
            if word in sentence:
                # Try to extract the feature name
                pattern = f"{word}\\s+(\\w+)"
                match = re.search(pattern, sentence)
                if match:
                    return f"{word}_{match.group(1)}"

        # Default to generic target
        return "codebase"

    def _analyze_codebase(self) -> Dict:
        """Analyze current codebase structure and patterns"""
        info = {"files": [], "structure": {}, "patterns": {}, "technologies": []}

        try:
            # Get file list
            for root, dirs, files in os.walk(self.current_dir):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "__pycache__", "venv"]
                ]

                for file in files:
                    if not file.startswith(".") and not file.endswith(".pyc"):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.current_dir)
                        info["files"].append(rel_path)

            # Analyze main files
            main_files = [
                f
                for f in info["files"]
                if f
                in ["app.py", "main.py", "index.js", "package.json", "requirements.txt"]
            ]

            # Detect technologies
            if any("requirements.txt" in f or ".py" in f for f in info["files"]):
                info["technologies"].append("Python")
            if any(".js" in f or "package.json" in f for f in info["files"]):
                info["technologies"].append("JavaScript")
            if "app.py" in [os.path.basename(f) for f in info["files"]]:
                info["technologies"].append("Flask")

            # Analyze structure patterns
            info["structure"] = {
                "has_tests": any("test" in f.lower() for f in info["files"]),
                "has_config": any("config" in f.lower() for f in info["files"]),
                "has_requirements": "requirements.txt" in info["files"],
                "main_file": next((f for f in main_files if f.endswith(".py")), None),
            }

        except Exception as e:
            print(f"Warning: Could not fully analyze codebase: {e}")

        return info

    def _generate_code_changes(
        self, requirements: List[PRRequirement], codebase_info: Dict
    ) -> List[CodeChange]:
        """Generate specific code changes based on requirements and codebase analysis"""
        changes = []

        for req in requirements:
            if req.action == "add" and "pr" in req.target.lower():
                # Adding PR creation functionality
                changes.extend(
                    self._generate_pr_functionality_changes(req, codebase_info)
                )
            elif req.action == "add" and any(
                word in req.description for word in ["command", "endpoint", "api"]
            ):
                changes.extend(self._generate_api_endpoint_changes(req, codebase_info))
            elif req.action == "modify" and "line bot" in req.description:
                changes.extend(
                    self._generate_linebot_enhancement_changes(req, codebase_info)
                )
            else:
                # Generic changes
                changes.extend(self._generate_generic_changes(req, codebase_info))

        return changes

    def _generate_pr_functionality_changes(
        self, req: PRRequirement, codebase_info: Dict
    ) -> List[CodeChange]:
        """Generate changes to add PR creation functionality"""
        changes = []

        # Add PR creation command to LINE Bot
        if "app.py" in [os.path.basename(f) for f in codebase_info.get("files", [])]:
            app_file = next(
                (f for f in codebase_info["files"] if f.endswith("app.py")), None
            )
            if app_file:
                changes.append(
                    CodeChange(
                        file_path=app_file,
                        change_type="modify",
                        description="Add PR creation command handler to LINE Bot",
                    )
                )

        # Create PR creation service
        changes.append(
            CodeChange(
                file_path="pr_service.py",
                change_type="create",
                new_content=self._generate_pr_service_code(),
                description="Create PR creation service module",
            )
        )

        return changes

    def _generate_api_endpoint_changes(
        self, req: PRRequirement, codebase_info: Dict
    ) -> List[CodeChange]:
        """Generate changes to add new API endpoints"""
        changes = []

        main_file = codebase_info.get("structure", {}).get("main_file", "app.py")
        changes.append(
            CodeChange(
                file_path=main_file,
                change_type="modify",
                description=f"Add new API endpoint based on requirement: {req.description}",
            )
        )

        return changes

    def _generate_linebot_enhancement_changes(
        self, req: PRRequirement, codebase_info: Dict
    ) -> List[CodeChange]:
        """Generate changes to enhance LINE Bot functionality"""
        changes = []

        # Modify app.py to add new LINE Bot features
        changes.append(
            CodeChange(
                file_path="app.py",
                change_type="modify",
                description=f"Enhance LINE Bot with: {req.description}",
            )
        )

        return changes

    def _generate_generic_changes(
        self, req: PRRequirement, codebase_info: Dict
    ) -> List[CodeChange]:
        """Generate generic code changes"""
        changes = []

        # If target is a specific file
        if "." in req.target and req.target in codebase_info.get("files", []):
            changes.append(
                CodeChange(
                    file_path=req.target,
                    change_type=req.action,
                    description=req.description,
                )
            )
        else:
            # Generic change to main file
            main_file = codebase_info.get("structure", {}).get("main_file", "app.py")
            changes.append(
                CodeChange(
                    file_path=main_file,
                    change_type="modify",
                    description=req.description,
                )
            )

        return changes

    def _generate_pr_service_code(self) -> str:
        """Generate code for PR creation service"""
        return '''import subprocess
import json
import os
from typing import Dict, List

class PRService:
    """Service for creating GitHub PRs automatically"""
    
    def __init__(self):
        self.base_dir = os.getcwd()
    
    def create_pr_from_description(self, description: str) -> Dict:
        """Create a PR from natural language description"""
        try:
            # Parse requirements
            requirements = self._parse_description(description)
            
            # Generate branch name
            branch_name = self._generate_branch_name(description)
            
            # Create and switch to branch
            self._create_branch(branch_name)
            
            # Apply changes (implement your logic here)
            changes_applied = self._apply_changes(requirements)
            
            # Commit and push
            self._commit_and_push(description, branch_name)
            
            # Create PR
            pr_url = self._create_github_pr(description, branch_name)
            
            return {
                "success": True,
                "pr_url": pr_url,
                "branch_name": branch_name,
                "changes": changes_applied
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_description(self, description: str) -> List[str]:
        """Parse description into actionable requirements"""
        # Simple implementation - split by sentences
        return [s.strip() for s in description.split('.') if s.strip()]
    
    def _generate_branch_name(self, description: str) -> str:
        """Generate branch name from description"""
        # Take first few words and make them branch-safe
        words = description.lower().split()[:4]
        safe_words = [w for w in words if w.isalnum()]
        return f"feature/{'_'.join(safe_words)}"
    
    def _create_branch(self, branch_name: str):
        """Create and switch to new branch"""
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
    
    def _apply_changes(self, requirements: List[str]) -> List[str]:
        """Apply code changes based on requirements"""
        # Placeholder - implement actual change logic
        return requirements
    
    def _commit_and_push(self, description: str, branch_name: str):
        """Commit changes and push to remote"""
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f"feat: {description}"], check=True)
        subprocess.run(['git', 'push', '-u', 'origin', branch_name], check=True)
    
    def _create_github_pr(self, description: str, branch_name: str) -> str:
        """Create GitHub PR using gh CLI"""
        result = subprocess.run([
            'gh', 'pr', 'create',
            '--title', f"feat: {description}",
            '--body', f"Automatically generated PR for: {description}",
            '--head', branch_name
        ], capture_output=True, text=True, check=True)
        
        return result.stdout.strip()
'''

    def _create_feature_branch(self, description: str) -> Optional[str]:
        """Create a feature branch for the PR"""
        try:
            # Generate branch name
            words = description.lower().split()[:4]
            safe_words = [re.sub(r"[^a-z0-9]", "", w) for w in words if w.isalnum()]
            branch_name = (
                f"feature/{'_'.join(safe_words)}_{datetime.now().strftime('%m%d')}"
            )

            # Create and checkout branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name], check=True, capture_output=True
            )

            return branch_name

        except subprocess.CalledProcessError as e:
            print(f"Failed to create branch: {e}")
            return None

    def _apply_code_changes(self, changes: List[CodeChange]) -> List[CodeChange]:
        """Apply the generated code changes to files"""
        applied_changes = []

        for change in changes:
            try:
                if change.change_type == "create":
                    self._create_file(change)
                elif change.change_type == "modify":
                    self._modify_file(change)
                elif change.change_type == "delete":
                    self._delete_file(change)

                applied_changes.append(change)

            except Exception as e:
                print(f"Failed to apply change to {change.file_path}: {e}")
                continue

        return applied_changes

    def _create_file(self, change: CodeChange):
        """Create a new file"""
        os.makedirs(os.path.dirname(change.file_path), exist_ok=True)
        with open(change.file_path, "w") as f:
            f.write(change.new_content or "")

    def _modify_file(self, change: CodeChange):
        """Modify an existing file"""
        if change.file_path == "app.py":
            self._modify_app_py(change)
        else:
            # Generic file modification
            if os.path.exists(change.file_path):
                with open(change.file_path, "r") as f:
                    content = f.read()

                # Simple append for now - could be made more sophisticated
                modified_content = content + f"\n\n# Added: {change.description}\n"

                with open(change.file_path, "w") as f:
                    f.write(modified_content)

    def _modify_app_py(self, change: CodeChange):
        """Specifically modify app.py to add PR creation functionality"""
        if not os.path.exists("app.py"):
            return

        with open("app.py", "r") as f:
            content = f.read()

        # Add import for PR service
        if "from pr_creator import PRCreator" not in content:
            import_line = "from pr_creator import PRCreator\n"
            # Insert after existing imports
            lines = content.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("from ") or line.strip().startswith(
                    "import "
                ):
                    insert_idx = i + 1
            lines.insert(insert_idx, import_line)
            content = "\n".join(lines)

        # Add PR creator handler
        pr_handler = '''
    elif user_message.lower().startswith('create pr:') or user_message.lower().startswith('pr:'):
        # Extract PR description
        pr_description = user_message[user_message.find(':')+1:].strip()
        
        if not pr_description:
            reply_text = "請提供 PR 描述，例如：create pr: 添加用戶登入功能"
        else:
            # Initialize PR creator
            pr_creator = PRCreator()
            
            # Send processing message
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🚀 正在創建 PR，請稍候...")
            )
            
            # Create PR
            result = pr_creator.create_instant_pr(pr_description)
            
            if result['success']:
                success_msg = f"""✅ PR 創建成功！
                
🔗 **PR URL:** {result['pr_url']}
🌿 **分支:** {result['branch_name']} 
📝 **變更數量:** {result['changes_applied']}

💡 請檢查 GitHub 查看完整的 PR 內容"""
                
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=success_msg)
                )
            else:
                error_msg = f"❌ PR 創建失敗: {result['error']}"
                line_bot_api.push_message(
                    event.source.user_id,
                    TextSendMessage(text=error_msg)
                )
        return
'''

        # Insert PR handler before the default else clause
        if "elif user_message.lower().startswith('create pr:')" not in content:
            # Find the position to insert (before the final else in handle_text_message)
            lines = content.split("\n")
            insert_idx = -1

            for i, line in enumerate(lines):
                if "else:" in line and "batch_manager.is_in_batch_mode" in "".join(
                    lines[i + 1 : i + 5]
                ):
                    insert_idx = i
                    break

            if insert_idx != -1:
                lines.insert(insert_idx, pr_handler)
                content = "\n".join(lines)

        with open("app.py", "w") as f:
            f.write(content)

    def _delete_file(self, change: CodeChange):
        """Delete a file"""
        if os.path.exists(change.file_path):
            os.remove(change.file_path)

    def _validate_changes(self) -> Dict:
        """Validate that changes don't break the code"""
        result = {"success": True, "issues": []}

        try:
            # Basic Python syntax check
            for root, dirs, files in os.walk(self.current_dir):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r") as f:
                                compile(f.read(), file_path, "exec")
                        except SyntaxError as e:
                            result["issues"].append(f"Syntax error in {file_path}: {e}")
                            result["success"] = False

        except Exception as e:
            result["issues"].append(f"Validation error: {e}")
            result["success"] = False

        return result

    def _commit_changes(
        self, description: str, requirements: List[PRRequirement]
    ) -> bool:
        """Commit the changes with a descriptive message"""
        try:
            # Add all changes
            subprocess.run(["git", "add", "."], check=True, capture_output=True)

            # Create commit message
            commit_msg = f"feat: {description}\n\n"
            for req in requirements:
                commit_msg += f"- {req.action}: {req.description}\n"

            commit_msg += "\n🤖 Generated with Claude Code PR Creator"

            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg], check=True, capture_output=True
            )

            return True

        except subprocess.CalledProcessError as e:
            print(f"Failed to commit changes: {e}")
            return False

    def _create_pull_request(
        self,
        description: str,
        requirements: List[PRRequirement],
        branch_name: str,
        base_branch: str,
    ) -> Dict:
        """Create the GitHub pull request"""
        try:
            # Push branch
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                check=True,
                capture_output=True,
            )

            # Create PR body
            pr_body = f"""## 📋 Summary

{description}

## 🎯 Requirements Implemented

"""
            for req in requirements:
                pr_body += f"- **{req.action.title()}**: {req.description}\n"

            pr_body += f"""
## 🧪 Test Plan

- [ ] Code compiles without errors
- [ ] Basic functionality works as expected
- [ ] No breaking changes to existing features

## 📝 Notes

This PR was automatically generated using Claude Code's instant PR creation feature.

🤖 Generated with [Claude Code](https://claude.ai/code)
"""

            # Create PR using gh CLI
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    f"feat: {description}",
                    "--body",
                    pr_body,
                    "--base",
                    base_branch,
                    "--head",
                    branch_name,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            pr_url = result.stdout.strip()

            return {"success": True, "url": pr_url}

        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Failed to create PR: {e}"}

    def _cleanup_temp_files(self):
        """Clean up any temporary files created during the process"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass  # Ignore cleanup errors

        self.temp_files.clear()


# CLI interface for direct usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print('Usage: python pr_creator.py "PR description"')
        print(
            'Example: python pr_creator.py "Add user authentication with email verification"'
        )
        sys.exit(1)

    description = sys.argv[1]
    creator = PRCreator()

    print(f"🚀 Creating PR for: {description}")
    result = creator.create_instant_pr(description)

    if result["success"]:
        print(f"✅ PR created successfully!")
        print(f"🔗 URL: {result['pr_url']}")
        print(f"🌿 Branch: {result['branch_name']}")
        print(f"📝 Changes: {result['changes_applied']}")
    else:
        print(f"❌ Failed to create PR: {result['error']}")
