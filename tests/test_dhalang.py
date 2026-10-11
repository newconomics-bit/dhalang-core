"""Tests for Dhalang orchestrator and Manunggal aggregator."""

import pytest

from src.dhalang import Dhalang, Manunggal
from src.sabda.models import WayangResult, WayangStatus


class TestDhalangIntegration:
    """Integration tests for Dhalang orchestrator."""

    def test_proses_scan_subdomain(self):
        """Test Dhalang processes security scan request."""
        dhalang = Dhalang()
        result = dhalang.proses("Cek subdomain target.com")

        assert isinstance(result, str)
        assert "api.target.com" in result
        assert "dev.target.com" in result
        assert "sec_wayang" in result
        assert "COMPLETED" in result

    def test_proses_analyze_code(self):
        """Test Dhalang processes code analysis request."""
        dhalang = Dhalang()
        result = dhalang.proses("Analisis bug di code login")

        assert isinstance(result, str)
        assert "auth.py" in result
        assert "password not hashed" in result
        assert "coder_wayang" in result
        assert "COMPLETED" in result

    def test_analisis_input_security_keywords(self):
        """Test analisis_input detects security keywords."""
        dhalang = Dhalang()

        target, task_type, payload = dhalang.analisis_input("Scan subdomain example.com")
        assert target == "sec_wayang"
        assert task_type == "scan_subdomain"
        assert payload["target"] == "example.com"

        target, task_type, payload = dhalang.analisis_input("Security audit for test.com")
        assert target == "sec_wayang"
        assert task_type == "scan_subdomain"
        assert payload["target"] == "test.com"

    def test_analisis_input_code_keywords(self):
        """Test analisis_input detects code keywords."""
        dhalang = Dhalang()

        target, task_type, payload = dhalang.analisis_input("Analyze code in auth.py")
        assert target == "coder_wayang"
        assert task_type == "analyze_code"
        assert payload["file"] == "auth.py"

        target, task_type, payload = dhalang.analisis_input("Find bug in login function")
        assert target == "coder_wayang"
        assert task_type == "analyze_code"

    def test_analisis_input_default(self):
        """Test analisis_input defaults to security scan."""
        dhalang = Dhalang()

        target, task_type, payload = dhalang.analisis_input("Random unknown request")
        assert target == "sec_wayang"
        assert task_type == "scan_subdomain"
        assert payload["target"] == "target.com"

    def test_register_wayang(self):
        """Test registering a custom Wayang."""
        dhalang = Dhalang()
        initial_count = len(dhalang.registered_wayangs)

        # Register a new mock wayang
        from src.wayang.base_wayang import Wayang
        from src.sabda.bus import SabdaBus

        class MockWayang(Wayang):
            def __init__(self, bus):
                super().__init__("mock_wayang", bus)

        mock_wayang = MockWayang(dhalang.bus)
        dhalang.register_wayang(mock_wayang)

        assert len(dhalang.registered_wayangs) == initial_count + 1
        assert "mock_wayang" in dhalang.registered_wayangs


class TestManunggalAggregator:
    """Tests for Manunggal aggregator."""

    def test_satukan_with_results(self):
        """Test satukan combines multiple results."""
        manunggal = Manunggal()

        results = [
            WayangResult(
                agent="sec_wayang",
                status=WayangStatus.COMPLETED,
                result={"subdomains": ["api.target.com"], "vulnerabilities": 1},
                notes="mock security scan"
            ),
            WayangResult(
                agent="coder_wayang",
                status=WayangStatus.COMPLETED,
                result={"file": "auth.py", "line": 45},
                notes="mock code analysis"
            ),
        ]

        output = manunggal.satukan(results, "Test input")

        assert "sec_wayang" in output
        assert "coder_wayang" in output
        assert "api.target.com" in output
        assert "auth.py" in output
        assert "COMPLETED" in output
        assert "mock security scan" in output
        assert "mock code analysis" in output
        assert "Test input" in output

    def test_satukan_empty_list(self):
        """Test satukan with empty list returns valid string."""
        manunggal = Manunggal()

        output = manunggal.satukan([], "Empty test")

        assert isinstance(output, str)
        assert len(output) > 0
        assert "Empty test" in output
        assert "Tidak ada hasil" in output

    def test_satukan_failed_result(self):
        """Test satukan handles failed results."""
        manunggal = Manunggal()

        results = [
            WayangResult(
                agent="sec_wayang",
                status=WayangStatus.FAILED,
                result={},
                notes="Connection timeout"
            ),
        ]

        output = manunggal.satukan(results, "Test failed")

        assert "FAILED" in output
        assert "Connection timeout" in output
        assert "sec_wayang" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])