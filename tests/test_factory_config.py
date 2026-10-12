"""Tests for factory config loading."""

import tempfile
from pathlib import Path

import pytest

from src.llm.factory import load_config, get_backend
from src.llm.mock_backend import MockBackend
from src.llm.ollama_backend import OllamaBackend


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_existing_yaml(self):
        """Test load_config reads existing YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
backend: "ollama"
model: "test-model"
host: "http://test:11434"
temperature: 0.3
""")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["backend"] == "ollama"
            assert config["model"] == "test-model"
            assert config["host"] == "http://test:11434"
            assert config["temperature"] == 0.3
        finally:
            temp_path.unlink()

    def test_load_missing_file_fallback(self):
        """Test load_config falls back to defaults when file missing."""
        missing_path = Path("/nonexistent/path/llm.yaml")
        config = load_config(missing_path)

        assert config["backend"] == "mock"
        assert config["model"] == "qwen2.5:14b"
        assert config["host"] == "http://localhost:11434"
        assert config["temperature"] == 0.5

    def test_load_invalid_yaml_fallback(self):
        """Test load_config falls back to defaults on invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["backend"] == "mock"
        finally:
            temp_path.unlink()

    def test_load_partial_config_merges_defaults(self):
        """Test load_config merges partial config with defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("backend: ollama")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["backend"] == "ollama"
            # Should have defaults for other fields
            assert config["model"] == "qwen2.5:14b"
            assert config["host"] == "http://localhost:11434"
            assert config["temperature"] == 0.5
        finally:
            temp_path.unlink()


class TestFactoryConfigIntegration:
    """Tests for factory with config file."""

    def test_get_backend_from_default_config(self):
        """Test get_backend uses default config (mock)."""
        # The default config file exists and has backend: mock
        backend = get_backend()
        assert isinstance(backend, MockBackend)

    def test_factory_config_file_exists(self):
        """Test that configs/llm.yaml exists and is readable."""
        config_path = Path(__file__).parent.parent / "configs" / "llm.yaml"
        assert config_path.exists()

        config = load_config(config_path)
        assert "backend" in config
        assert config["backend"] in ("mock", "ollama")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])