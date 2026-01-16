"""
Configuration loader for Tuya Power Monitor.
Loads settings from config.yaml (local) or environment variables (Lambda).
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class TuyaConfig:
    endpoint: str
    access_id: str
    access_key: str
    device_id: str


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass
class AppConfig:
    tuya: TuyaConfig
    telegram: TelegramConfig
    ddb_table: str
    debounce_count: int
    timezone: str


def load_yaml_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config.yaml in project root.

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML required for config file support. Install with: pip install pyyaml"
        )

    if config_path is None:
        # Look for config.yaml in project root (parent of src/)
        src_dir = Path(__file__).parent
        config_path = src_dir.parent / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Copy config.template.yaml to config.yaml and fill in your credentials."
        )

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_config(use_env: bool = True, config_path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from environment variables or config file.

    Priority:
    1. Environment variables (for Lambda deployment)
    2. config.yaml file (for local development)

    Args:
        use_env: If True, try environment variables first
        config_path: Optional path to config file

    Returns:
        AppConfig object with all settings
    """
    # Check if running in Lambda (environment variables set)
    if use_env and os.environ.get("TUYA_ACCESS_ID"):
        return AppConfig(
            tuya=TuyaConfig(
                endpoint=os.environ["TUYA_ENDPOINT"],
                access_id=os.environ["TUYA_ACCESS_ID"],
                access_key=os.environ["TUYA_ACCESS_KEY"],
                device_id=os.environ["TUYA_DEVICE_ID"],
            ),
            telegram=TelegramConfig(
                bot_token=os.environ["TG_BOT_TOKEN"],
                chat_id=os.environ["TG_CHAT_ID"],
            ),
            ddb_table=os.environ["DDB_TABLE"],
            debounce_count=int(os.environ.get("DEBOUNCE_COUNT", "2")),
            timezone=os.environ.get("TIMEZONE", "Europe/Kyiv"),
        )

    # Load from config file (local development)
    cfg = load_yaml_config(config_path)

    return AppConfig(
        tuya=TuyaConfig(
            endpoint=cfg["tuya"]["endpoint"],
            access_id=cfg["tuya"]["access_id"],
            access_key=cfg["tuya"]["access_key"],
            device_id=cfg["tuya"]["device_id"],
        ),
        telegram=TelegramConfig(
            bot_token=cfg["telegram"]["bot_token"],
            chat_id=str(cfg["telegram"]["chat_id"]),
        ),
        ddb_table=cfg.get("aws", {}).get("table_name", "power_watch_state"),
        debounce_count=cfg.get("settings", {}).get("debounce_count", 2),
        timezone=cfg.get("settings", {}).get("timezone", "Europe/Kyiv"),
    )


def get_aws_config(config_path: Optional[str] = None) -> Dict[str, str]:
    """
    Get AWS deployment configuration from config file.

    Returns:
        Dictionary with region, stack_name, table_name, and credentials
    """
    cfg = load_yaml_config(config_path)
    aws_cfg = cfg.get("aws", {})

    return {
        "region": aws_cfg.get("region", "eu-central-1"),
        "stack_name": aws_cfg.get("stack_name", "tuya-power-monitor"),
        "table_name": aws_cfg.get("table_name", "power_watch_state"),
        "access_key_id": aws_cfg.get("access_key_id", ""),
        "secret_access_key": aws_cfg.get("secret_access_key", ""),
    }


def configure_aws_cli(config_path: Optional[str] = None) -> None:
    """
    Configure AWS CLI using credentials from config file.

    Args:
        config_path: Optional path to config file
    """
    import subprocess

    aws_cfg = get_aws_config(config_path)

    if not aws_cfg["access_key_id"] or aws_cfg["access_key_id"].startswith("AKIA..."):
        raise ValueError("AWS access_key_id not configured in config.yaml")

    if not aws_cfg["secret_access_key"] or aws_cfg["secret_access_key"] == "your_secret":
        raise ValueError("AWS secret_access_key not configured in config.yaml")

    # Configure AWS CLI
    subprocess.run(
        ["aws", "configure", "set", "aws_access_key_id", aws_cfg["access_key_id"]], check=True
    )
    subprocess.run(
        ["aws", "configure", "set", "aws_secret_access_key", aws_cfg["secret_access_key"]],
        check=True,
    )
    subprocess.run(["aws", "configure", "set", "region", aws_cfg["region"]], check=True)
    subprocess.run(["aws", "configure", "set", "output", "json"], check=True)

    print(f"✅ AWS CLI configured")
    print(f"   Region: {aws_cfg['region']}")
    print(f"   Access Key ID: {aws_cfg['access_key_id'][:8]}...")
