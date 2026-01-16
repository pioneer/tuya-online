"""
Invoke tasks for Tuya Power Monitor.
Run `invoke --list` to see all available tasks.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from invoke import task, Collection

# Project root directory
PROJECT_ROOT = Path(__file__).parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


def get_venv_python():
    """Get path to venv Python, with fallback."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def run_cmd(ctx, cmd, **kwargs):
    """Run a command with proper error handling."""
    return ctx.run(cmd, pty=True, **kwargs)


# =============================================================================
# Setup Tasks
# =============================================================================

@task
def install(ctx):
    """Install development dependencies."""
    print("📦 Installing development dependencies...")
    run_cmd(ctx, "uv pip install -r requirements-dev.txt")
    print("✅ Dependencies installed")


@task
def venv(ctx):
    """Create Python virtual environment."""
    if (PROJECT_ROOT / ".venv").exists():
        print("⚠️  Virtual environment already exists at .venv/")
        print("   To recreate, first run: invoke venv-clean")
    else:
        print("🐍 Creating virtual environment...")
        run_cmd(ctx, "uv venv --python 3.11 .venv")
        print("✅ Virtual environment created")
    print()
    print("To activate, run:")
    print("  source .venv/bin/activate")


@task
def venv_clean(ctx):
    """Remove virtual environment."""
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        print("🗑️  Removing virtual environment...")
        shutil.rmtree(venv_path)
        print("✅ Virtual environment removed")
    else:
        print("ℹ️  No virtual environment found")


@task
def aws_configure(ctx):
    """Configure AWS CLI from config.yaml."""
    python = get_venv_python()
    run_cmd(ctx, f'{python} -c "import sys; sys.path.insert(0, \'src\'); from config_loader import configure_aws_cli; configure_aws_cli()"')


# =============================================================================
# Code Quality Tasks
# =============================================================================

@task
def format(ctx, files=""):
    """
    Format code with ruff.
    
    Examples:
        invoke format                    # Format all code
        invoke format --files src/app.py # Format specific file
        invoke format --files "src/ tests/"  # Format specific directories
    """
    if files:
        targets = files
        print(f"✨ Formatting: {targets}")
    else:
        targets = "src/ tests/ scripts/ tasks.py"
        print("✨ Formatting all code...")
    
    run_cmd(ctx, f"ruff format {targets}")
    run_cmd(ctx, f"ruff check --fix --select I {targets}")  # Also fix import sorting


@task
def lint(ctx, files=""):
    """
    Run linter (ruff).
    
    Examples:
        invoke lint                    # Lint all code
        invoke lint --files src/app.py # Lint specific file
    """
    if files:
        targets = files
        print(f"🔍 Linting: {targets}")
    else:
        targets = "src/ tests/ scripts/ tasks.py"
        print("🔍 Running linter...")
    
    run_cmd(ctx, f"ruff check {targets}")


@task
def lint_fix(ctx, files=""):
    """
    Run linter and fix issues.
    
    Examples:
        invoke lint-fix                    # Fix all code
        invoke lint-fix --files src/app.py # Fix specific file
    """
    if files:
        targets = files
        print(f"🔧 Fixing: {targets}")
    else:
        targets = "src/ tests/ scripts/ tasks.py"
        print("🔧 Running linter with auto-fix...")
    
    run_cmd(ctx, f"ruff check --fix {targets}")


# =============================================================================
# Local Testing Tasks
# =============================================================================

@task
def test(ctx):
    """Run unit tests."""
    print("🧪 Running unit tests...")
    run_cmd(ctx, "pytest tests/ -v")


@task
def test_cov(ctx):
    """Run unit tests with coverage."""
    print("🧪 Running unit tests with coverage...")
    run_cmd(ctx, "pytest tests/ -v --cov=src --cov-report=term-missing")


@task
def test_tuya(ctx):
    """Test Tuya API connection."""
    python = get_venv_python()
    run_cmd(ctx, f"{python} scripts/test_local.py --test-tuya")


@task
def test_telegram(ctx):
    """Test Telegram notification."""
    python = get_venv_python()
    run_cmd(ctx, f"{python} scripts/test_local.py --test-telegram")


@task
def test_all(ctx):
    """Test all integrations (Tuya + Telegram)."""
    python = get_venv_python()
    run_cmd(ctx, f"{python} scripts/test_local.py --test-all")


@task
def poll(ctx):
    """Run a single poll locally (no DynamoDB)."""
    python = get_venv_python()
    run_cmd(ctx, f"{python} scripts/test_local.py --poll")


# =============================================================================
# Build & Deploy Tasks
# =============================================================================

@task
def init(ctx):
    """Generate SAM configuration from config.yaml."""
    python = get_venv_python()
    run_cmd(ctx, f"{python} scripts/deploy.py --init")


@task
def show_config(ctx):
    """Show deployment configuration."""
    python = get_venv_python()
    run_cmd(ctx, f"{python} scripts/deploy.py --show")


@task
def validate(ctx):
    """Validate SAM template."""
    print("🔍 Validating SAM template...")
    run_cmd(ctx, "sam validate")


@task
def build(ctx):
    """Build SAM application."""
    print("🔨 Building SAM application...")
    run_cmd(ctx, "sam build")


@task(pre=[init, build])
def deploy(ctx):
    """Regenerate config, build, and deploy to AWS (auto-confirm)."""
    print("🚀 Deploying to AWS...")
    run_cmd(ctx, "sam deploy --no-confirm-changeset")


@task(pre=[init, build])
def deploy_guided(ctx):
    """Regenerate config, build, and deploy with guided prompts."""
    print("🚀 Deploying to AWS (guided)...")
    run_cmd(ctx, "sam deploy --guided")


# =============================================================================
# AWS Operations Tasks
# =============================================================================

@task
def logs(ctx, tail=False, start_time="", end_time="", filter=""):
    """
    View Lambda function logs.
    
    Examples:
        invoke logs --tail              # Live tail logs
        invoke logs --start-time "2 hours ago"
        invoke logs --start-time "2026-01-16T08:00:00" --end-time "2026-01-16T10:00:00"
        invoke logs --start-time "1 hour ago" --filter "notification_sent"
    """
    from src.config_loader import get_aws_config
    aws_cfg = get_aws_config()
    stack_name = aws_cfg["stack_name"]
    
    cmd = f"sam logs -n PowerMonitorFunction --stack-name {stack_name}"
    
    if tail:
        cmd += " --tail"
        print(f"📋 Tailing logs for {stack_name} (Ctrl+C to exit)...")
    else:
        if start_time:
            cmd += f" --start-time '{start_time}'"
        if end_time:
            cmd += f" --end-time '{end_time}'"
        print(f"📋 Fetching logs for {stack_name}...")
    
    if filter:
        cmd += f" 2>&1 | grep -A 10 '{filter}'"
    
    run_cmd(ctx, cmd)


@task
def check_state(ctx):
    """Check current state in DynamoDB."""
    from src.config_loader import get_aws_config
    aws_cfg = get_aws_config()
    table_name = aws_cfg["table_name"]
    
    print(f"📊 Checking state in DynamoDB table: {table_name}")
    result = ctx.run(
        f'aws dynamodb get-item --table-name {table_name} --key \'{{"pk":{{"S":"state"}}}}\' --output json',
        hide=True,
        warn=True
    )
    if result.ok and result.stdout.strip():
        import json
        data = json.loads(result.stdout)
        print(json.dumps(data, indent=2))
    else:
        print("ℹ️  No state found (table may be empty or not exist yet)")


@task
def invoke_remote(ctx):
    """Invoke Lambda function remotely."""
    from src.config_loader import get_aws_config
    aws_cfg = get_aws_config()
    stack_name = aws_cfg["stack_name"]
    function_name = f"{stack_name}-power-monitor"
    
    print(f"⚡ Invoking Lambda function: {function_name}")
    run_cmd(ctx, f"aws lambda invoke --function-name {function_name} --payload '{{}}' response.json")
    print()
    print("📄 Response:")
    run_cmd(ctx, "cat response.json && echo")


@task
def test_remote(ctx):
    """Send a test notification from the deployed Lambda."""
    from src.config_loader import get_aws_config
    aws_cfg = get_aws_config()
    stack_name = aws_cfg["stack_name"]
    function_name = f"{stack_name}-power-monitor"
    
    print(f"🧪 Sending test notification from Lambda: {function_name}")
    # Use base64 encoding for the payload to avoid shell escaping issues
    import base64
    payload = base64.b64encode(b'{"test": true}').decode()
    run_cmd(ctx, f"aws lambda invoke --function-name {function_name} --payload '{payload}' --cli-binary-format base64 response.json")
    print()
    print("📄 Response:")
    run_cmd(ctx, "cat response.json && echo")


@task
def invoke_local(ctx):
    """Invoke Lambda function locally (requires Docker)."""
    print("⚡ Invoking Lambda function locally...")
    build(ctx)
    run_cmd(ctx, "sam local invoke PowerMonitorFunction --event events/test-event.json")


# =============================================================================
# Cleanup Tasks
# =============================================================================

@task
def clean(ctx):
    """Remove build artifacts."""
    print("🧹 Cleaning build artifacts...")
    
    # Remove .aws-sam directory
    aws_sam = PROJECT_ROOT / ".aws-sam"
    if aws_sam.exists():
        shutil.rmtree(aws_sam)
        print("   Removed .aws-sam/")
    
    # Remove __pycache__ directories
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)
        print(f"   Removed {pycache.relative_to(PROJECT_ROOT)}/")
    
    # Remove .pyc files
    for pyc in PROJECT_ROOT.rglob("*.pyc"):
        pyc.unlink()
    
    # Remove response.json
    response_json = PROJECT_ROOT / "response.json"
    if response_json.exists():
        response_json.unlink()
        print("   Removed response.json")
    
    print("✅ Clean complete")


@task
def clean_all(ctx):
    """Remove all generated files (build artifacts + config)."""
    clean(ctx)
    
    files_to_remove = ["samconfig.toml", "env.json"]
    for filename in files_to_remove:
        filepath = PROJECT_ROOT / filename
        if filepath.exists():
            filepath.unlink()
            print(f"   Removed {filename}")
    
    print("✅ Full clean complete")


@task
def delete(ctx):
    """Delete all AWS resources (sam delete)."""
    print("🗑️  Deleting AWS resources...")
    run_cmd(ctx, "sam delete")


# =============================================================================
# Code Quality Tasks
# =============================================================================

@task
def lint(ctx):
    """Run linter (ruff)."""
    print("🔍 Running linter...")
    run_cmd(ctx, "ruff check src/ tests/ scripts/")


@task
def lint_fix(ctx):
    """Run linter and fix issues."""
    print("🔧 Running linter with auto-fix...")
    run_cmd(ctx, "ruff check --fix src/ tests/ scripts/")


@task
def format(ctx):
    """Format code (ruff format)."""
    print("✨ Formatting code...")
    run_cmd(ctx, "ruff format src/ tests/ scripts/")


@task
def typecheck(ctx):
    """Run type checker (mypy)."""
    print("🔍 Running type checker...")
    run_cmd(ctx, "mypy src/")


@task
def check(ctx):
    """Run all checks (lint + typecheck + test)."""
    print("🔍 Running all checks...")
    lint(ctx)
    typecheck(ctx)
    test(ctx)
    print("✅ All checks passed")
