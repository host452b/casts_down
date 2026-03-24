"""Tests for setup-transcribe environment detection and installation."""
from unittest.mock import patch
import pytest
from casts_down.transcribe.installer import detect_platform, get_install_packages

class TestDetectPlatform:
    @patch("casts_down.transcribe.installer.platform")
    def test_mac_arm64(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        assert detect_platform() == "mac_arm64"

    @patch("casts_down.transcribe.installer.platform")
    def test_mac_intel(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "x86_64"
        assert detect_platform() == "mac_intel"

    @patch("casts_down.transcribe.installer.platform")
    def test_linux(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        assert detect_platform() == "linux"

class TestGetInstallPackages:
    def test_mac_arm64_packages(self):
        pkgs = get_install_packages("mac_arm64")
        assert "mlx-whisper>=0.4.0,<1.0.0" in pkgs
        assert "faster-whisper>=1.0.0,<2.0.0" in pkgs

    def test_mac_intel_packages(self):
        pkgs = get_install_packages("mac_intel")
        assert "faster-whisper>=1.0.0,<2.0.0" in pkgs
        assert not any("mlx" in p for p in pkgs)

    def test_linux_packages(self):
        pkgs = get_install_packages("linux")
        assert "faster-whisper>=1.0.0,<2.0.0" in pkgs
        assert not any("mlx" in p for p in pkgs)
