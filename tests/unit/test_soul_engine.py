"""Tests for the Soul Engine."""

from pathlib import Path
from unittest.mock import patch

import pytest

from seal_agent.core.soul_engine import SoulEngine


@pytest.fixture
def soul_engine(tmp_path: Path) -> SoulEngine:
    """Create a SoulEngine with a temporary soul directory."""
    engine = SoulEngine()
    engine.soul_dir = tmp_path

    # Create test soul files
    (tmp_path / "soul.md").write_text("# Test Soul\nI am a test agent.")
    (tmp_path / "style.md").write_text("# Test Style\nBe direct.")
    (tmp_path / "playbook.md").write_text("# Test Playbook\nUse MEDDIC.")

    return engine


@pytest.mark.asyncio
async def test_soul_engine_loads_files(soul_engine: SoulEngine) -> None:
    """Test that the soul engine loads markdown files."""
    await soul_engine.load()

    assert "Test Soul" in soul_engine.identity
    assert "Test Style" in soul_engine.style_guide
    assert "Test Playbook" in soul_engine.playbook


@pytest.mark.asyncio
async def test_soul_engine_generates_system_prompt(soul_engine: SoulEngine) -> None:
    """Test that the system prompt includes soul content."""
    await soul_engine.load()
    prompt = soul_engine.get_system_prompt()

    assert "Seal-Agent" in prompt
    assert "Test Soul" in prompt
    assert "Test Style" in prompt


@pytest.mark.asyncio
async def test_soul_engine_handles_missing_files(tmp_path: Path) -> None:
    """Test that missing soul files don't crash the engine."""
    engine = SoulEngine()
    engine.soul_dir = tmp_path

    # Should not raise even with no files
    await engine.load()

    assert engine.identity == ""
    assert engine.style_guide == ""
