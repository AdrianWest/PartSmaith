"""@package tests.test_extraction_isolation
@brief Verify extraction isolation, cancellation and parser independence.
@details Native failures must not kill the application process.
"""

import subprocess
import sys
from pathlib import Path
from threading import Event

import pymupdf
import pytest

import partsmith.extraction
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


def test_production_reader_does_not_load_mupdf(pdf):
    """@brief Exercise the production reader with MuPDF imports blocked.
    @param pdf Native test document path.
    @return None.
    @details Verify both page reading and rendering in a fresh Python process.
    """
    package_root = Path(partsmith.extraction.__file__).resolve().parents[2]
    code = """
import builtins, sys
sys.path.insert(0, sys.argv[1])
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'fitz' or name == 'pymupdf' or name.startswith('pymupdf.'):
        raise AssertionError('Production must not import MuPDF')
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
from partsmith.extraction import extract_document
result = extract_document(sys.argv[2], pages=[1], dpi=100)
assert any(e['type'] == 'TEXT' for e in result['evidence'])
assert result['pages'][0]['render_transform']['renderer'] == 'PDFium'
assert not any(n == 'pymupdf' or n.startswith('pymupdf.') for n in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", code, str(package_root), str(pdf)],
        check=True,
        capture_output=True,
        text=True,
    )
