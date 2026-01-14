#!/usr/bin/env python3
"""
Deployment helper script for Tuya Power Monitor.
Reads config.yaml and generates SAM deployment commands.

Usage:
    python scripts/deploy.py --init      # Create samconfig.toml from config.yaml
    python scripts/deploy.py --deploy    # Build and deploy
    python scripts/deploy.py --show      # Show deployment command
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_loader import load_yaml_config, get_aws_config


def generate_samconfig(config_path: str = None):
    """Generate samconfig.toml from config.yaml."""
    cfg = load_yaml_config(config_path)
    aws_cfg = cfg.get("aws", {})
    
    region = aws_cfg.get("region", "eu-central-1")
    stack_name = aws_cfg.get("stack_name", "tuya-power-monitor")
    table_name = aws_cfg.get("table_name", "power_watch_state")
    
    # Build parameter overrides - use single quotes inside, double quotes for TOML string
    params = [
        f"TuyaEndpoint='{cfg['tuya']['endpoint']}'",
        f"TuyaAccessId='{cfg['tuya']['access_id']}'",
        f"TuyaAccessKey='{cfg['tuya']['access_key']}'",
        f"TuyaDeviceId='{cfg['tuya']['device_id']}'",
        f"TelegramBotToken='{cfg['telegram']['bot_token']}'",
        f"TelegramChatId='{cfg['telegram']['chat_id']}'",
        f"DebounceCount='{cfg.get('settings', {}).get('debounce_count', 2)}'",
        f"Timezone='{cfg.get('settings', {}).get('timezone', 'Europe/Kyiv')}'",
        f"TableName='{table_name}'",
    ]
    
    param_overrides = " ".join(params)
    
    samconfig = f'''# Auto-generated from config.yaml
# Run: python scripts/deploy.py --init

version = 0.1

[default.deploy.parameters]
stack_name = "{stack_name}"
region = "{region}"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
disable_rollback = false
resolve_s3 = true
parameter_overrides = "{param_overrides}"
image_repositories = []

[default.build.parameters]
parallel = true
cached = true

[default.local_invoke.parameters]
env_vars = "env.json"
'''
    
    return samconfig


def create_env_json(config_path: str = None):
    """Create env.json for SAM local invoke."""
    cfg = load_yaml_config(config_path)
    
    env_vars = {
        "PowerMonitorFunction": {
            "TUYA_ENDPOINT": cfg["tuya"]["endpoint"],
            "TUYA_ACCESS_ID": cfg["tuya"]["access_id"],
            "TUYA_ACCESS_KEY": cfg["tuya"]["access_key"],
            "TUYA_DEVICE_ID": cfg["tuya"]["device_id"],
            "TG_BOT_TOKEN": cfg["telegram"]["bot_token"],
            "TG_CHAT_ID": str(cfg["telegram"]["chat_id"]),
            "DDB_TABLE": cfg.get("aws", {}).get("table_name", "power_watch_state"),
            "DEBOUNCE_COUNT": str(cfg.get("settings", {}).get("debounce_count", 2)),
            "TIMEZONE": cfg.get("settings", {}).get("timezone", "Europe/Kyiv"),
        }
    }
    
    import json
    return json.dumps(env_vars, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Deploy Tuya Power Monitor")
    parser.add_argument("--init", action="store_true", help="Generate samconfig.toml from config.yaml")
    parser.add_argument("--deploy", action="store_true", help="Build and deploy")
    parser.add_argument("--show", action="store_true", help="Show deployment parameters")
    parser.add_argument("--config", type=str, help="Path to config.yaml", default=None)
    
    args = parser.parse_args()
    
    if not any([args.init, args.deploy, args.show]):
        parser.print_help()
        sys.exit(1)
    
    project_root = Path(__file__).parent.parent
    
    try:
        if args.show:
            cfg = load_yaml_config(args.config)
            aws_cfg = get_aws_config(args.config)
            
            print("📋 Deployment Configuration:")
            print(f"   Region: {aws_cfg['region']}")
            print(f"   Stack: {aws_cfg['stack_name']}")
            print(f"   Table: {aws_cfg['table_name']}")
            print(f"   Tuya Endpoint: {cfg['tuya']['endpoint']}")
            print(f"   Device ID: {cfg['tuya']['device_id']}")
            print(f"   Timezone: {cfg.get('settings', {}).get('timezone', 'Europe/Kyiv')}")
            return
        
        if args.init:
            # Generate samconfig.toml
            samconfig_content = generate_samconfig(args.config)
            samconfig_path = project_root / "samconfig.toml"
            
            with open(samconfig_path, "w") as f:
                f.write(samconfig_content)
            print(f"✅ Created {samconfig_path}")
            
            # Generate env.json for local testing
            env_json_content = create_env_json(args.config)
            env_json_path = project_root / "env.json"
            
            with open(env_json_path, "w") as f:
                f.write(env_json_content)
            print(f"✅ Created {env_json_path}")
            
            print()
            print("Next steps:")
            print("  1. Review samconfig.toml")
            print("  2. Run: sam build && sam deploy")
            return
        
        if args.deploy:
            print("🔨 Building...")
            result = subprocess.run(["sam", "build"], cwd=project_root)
            if result.returncode != 0:
                sys.exit(1)
            
            print()
            print("🚀 Deploying...")
            result = subprocess.run(["sam", "deploy"], cwd=project_root)
            sys.exit(result.returncode)
            
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except KeyError as e:
        print(f"❌ Missing config key: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
