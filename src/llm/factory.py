"""LLM backend factory and config loader."""

import logging
from pathlib import Path
from typing import Optional

import yaml

from .interfaces import LLMBackend
from .ollama_backend import OllamaBackend
from .mock_backend import MockBackend

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "llm.yaml"


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load LLM config from YAML file.

    Args:
        config_path: Optional path to config file. Defaults to configs/llm.yaml.

    Returns:
        Config dict with backend, model, host, temperature.
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        logger.warning("Config file not found at %s, using defaults", path)
        return _default_config()

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        logger.info("Loaded LLM config from %s", path)
        return _merge_with_defaults(config)
    except yaml.YAMLError as e:
        logger.warning("Failed to parse YAML config: %s, using defaults", e)
        return _default_config()
    except Exception as e:
        logger.warning("Failed to load config: %s, using defaults", e)
        return _default_config()


def _default_config() -> dict:
    """Return default config."""
    return {
        "backend": "mock",
        "model": "qwen2.5:14b",
        "host": "http://localhost:11434",
        "temperature": 0.5,
    }


def _merge_with_defaults(config: dict) -> dict:
    """Merge user config with defaults."""
    defaults = _default_config()
    defaults.update(config)
    return defaults


def get_backend(config: Optional[dict] = None) -> LLMBackend:
    """Create LLM backend instance from config.

    Args:
        config: Optional config dict. If None, loads from configs/llm.yaml.

    Returns:
        LLMBackend instance (MockBackend or OllamaBackend).
    """
    if config is None:
        config = load_config()

    backend_type = config.get("backend", "mock").lower()

    if backend_type == "mock":
        return MockBackend()
    elif backend_type == "ollama":
        return OllamaBackend(
            model=config.get("model", "qwen2.5:14b"),
            host=config.get("host", "http://localhost:11434"),
            temperature=config.get("temperature", 0.5),
        )
    else:
        logger.warning(
            "Unknown backend '%s', falling back to mock. "
            "Valid options: 'mock', 'ollama'",
            backend_type,
        )
        return MockBackend()