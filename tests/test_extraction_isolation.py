"""Native extraction failures must not kill the application process."""

import subprocess
import sys
from threading import Event

import pymupdf
import pytest

from partsmith.extraction.isolated import extract_isolated
from partsmith.extraction.ocr import ExtractionCancelled


@pytest.fixture
def pdf(tmp_path):
    source = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        for _ in range(3):
            document.new_page().insert_text((20, 30), "Package test")
        document.save(source)
    return source


def test_isolated_result_and_progress(pdf):
    progress = []
    result = extract_isolated(pdf, pages=[2], dpi=100, log=progress.append)
    assert result["selected_pages"] == [2]
    assert any("page 2" in entry for entry in progress)
    assert any(
        "Package test" in entry["extracted"]["text"]
        for entry in result["evidence"]
    )


def test_isolated_native_failure_is_reported(pdf, monkeypatch):
    real_popen = subprocess.Popen
    processes = []

    def failing_worker(command, **kwargs):
        process = real_popen(
            [sys.executable, "-c", "import os; os._exit(17)"], **kwargs
        )
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", failing_worker)
    with pytest.raises(ValueError, match="parser process failed"):
        extract_isolated(pdf)
    assert processes[0].poll() == 17
    assert pdf.exists()


def test_isolated_cancellation_reaps_worker(pdf, monkeypatch):
    real_popen = subprocess.Popen
    processes = []

    def capture(command, **kwargs):
        process = real_popen(command, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", capture)
    cancel = Event()
    with pytest.raises(ExtractionCancelled):
        extract_isolated(pdf, cancel=cancel, log=lambda _: cancel.set())
    assert processes[0].poll() is not None


def test_isolated_input_error_is_preserved(pdf):
    with pytest.raises(ValueError, match="DPI"):
        extract_isolated(pdf, dpi=0)
