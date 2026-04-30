"""Configuration loading utilities."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration loading fails."""


def load_env_file(env_file: Optional[Path] = None) -> None:
    """Load environment variables from a .env file.

    Args:
        env_file: Path to the .env file. If None, looks for .env in current directory.
    """
    if env_file is None:
        env_file = Path.cwd() / ".env"

    if env_file.exists():
        load_dotenv(env_file)


def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Dictionary containing the configuration.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}")


def get_env_var(
    key: str,
    default: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    """Get an environment variable value.

    Args:
        key: Environment variable name.
        default: Default value if the variable is not set.
        required: If True, raises ConfigError when the variable is not set.

    Returns:
        The environment variable value, or default if not set.

    Raises:
        ConfigError: If required=True and the variable is not set.
    """
    value = os.getenv(key)

    if value is None:
        if required:
            raise ConfigError(f"Required environment variable not set: {key}")
        return default

    return value


def get_config(
    config_path: Optional[Path] = None,
    env_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load configuration from YAML and environment variables.

    Args:
        config_path: Path to the YAML configuration file.
        env_file: Path to the .env file.

    Returns:
        Dictionary containing the merged configuration.
    """
    config: Dict[str, Any] = {}

    # Load environment variables
    load_env_file(env_file)

    # Load YAML configuration if provided
    if config_path is not None:
        yaml_config = load_yaml_config(config_path)
        config.update(yaml_config)

    return config
