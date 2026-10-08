"""@package tests.test_cad_licensing
@brief Exercises CAD vendor coverage and redistribution evidence boundaries.
@details Uses the committed byte identities without loading native code.
"""

import copy
import json
from pathlib import Path

import pytest

from partsmith.pcm.licensing import validate_cad_vendors

ROOT = Path(__file__).resolve().parents[1]


def documents() -> tuple[dict, dict]:
    """@brief Loads independent committed lock and vendor documents.
    @return Current production lock and CAD vendor ledger.
    @details Tests alter copies while original source identities stay frozen.
    """
    return (
        json.loads(
            (ROOT / "resources/runtime/production-lock.json").read_bytes()
        ),
        json.loads(
            (ROOT / "resources/licensing/cad-native/vendors.json").read_bytes()
        ),
    )


def test_recorded_cad_vendor_sources_and_notices() -> None:
    """@brief Verifies all additional CAD vendor redistribution inputs.
    @return None.
    @details Checks the recorded static JPEG XR association too.
    """
    lock, ledger = documents()
    validate_cad_vendors(lock, ledger)
    versions = {v["name"]: v["version"] for v in ledger["vendors"]}
    assert versions["freeimage"] == "3.18.0"
    assert versions["freetype"] == "2.12.1"
    assert versions["openexr"] == "3.4.12"
    assert versions["lcms2"] == "2.19.1"


@pytest.mark.parametrize(
    "fault",
    [
        "unknown-dll",
        "unknown-tk-dll",
        "missing-dll",
        "duplicate-binary",
        "altered-binary",
        "unproved-repair",
        "missing-source",
        "altered-source",
        "missing-notice",
        "altered-recipe",
        "changed-package",
        "missing-component",
        "static-jxr",
        "changed-wheel",
        "changed-version",
        "modified-msvc",
        "changed-sdk",
        "changed-core-source",
        "changed-tool-source",
    ],
)
def test_cad_vendor_audit_rejects_incomplete_evidence(fault: str) -> None:
    """@brief Rejects gaps which generic file ownership cannot establish.
    @param fault Specific incomplete or mismatched producer evidence.
    @return None.
    @details These cases repair no audit claims or binary source provenance.
    """
    lock, ledger = map(copy.deepcopy, documents())
    vendor = ledger["vendors"][0]
    binary = vendor["binaries"][0]
    if fault == "unknown-dll":
        lock["files"][binary["path"].replace("FreeImage-", "Unknown-")] = lock[
            "files"
        ][binary["path"]]
    elif fault == "unknown-tk-dll":
        lock["files"][binary["path"].replace("FreeImage-", "TKUnknown-")] = (
            lock["files"][binary["path"]]
        )
    elif fault == "missing-dll":
        vendor["binaries"] = []
    elif fault == "duplicate-binary":
        vendor["binaries"].append(copy.deepcopy(binary))
    elif fault == "altered-binary":
        lock["files"][binary["path"]]["sha256"] = "0" * 64
    elif fault == "unproved-repair":
        binary["exact_repair_match"] = False
    elif fault == "missing-source":
        vendor["sources"] = []
    elif fault == "altered-source":
        vendor["sources"][0]["sha256"] = "0" * 64
    elif fault == "missing-notice":
        vendor["notices"] = {}
    elif fault == "altered-recipe":
        next(iter(vendor["build_inputs"].values()))["sha256"] = "0" * 64
    elif fault == "changed-package":
        vendor["package_identity"]["sha256"] = "0" * 64
    elif fault == "missing-component":
        lock["components"] = [
            c
            for c in lock["components"]
            if c["name"] != "cad-vendor-freeimage"
        ]
    elif fault == "static-jxr":
        next(v for v in ledger["vendors"] if v["name"] == "jxrlib")[
            "linkage"
        ] = "UNVERIFIED"
    elif fault == "changed-wheel":
        ledger["wheel"]["sha256"] = "0" * 64
    elif fault == "changed-version":
        vendor["version"] = "unverified"
    elif fault == "modified-msvc":
        next(v for v in ledger["vendors"] if v["name"] == "vc14_runtime")[
            "binaries"
        ][0]["original_sha256"] = "0" * 64
    elif fault == "changed-sdk":
        next(iter(ledger["occt_binaries"].values()))["sha256"] = "0" * 64
    elif fault == "changed-core-source":
        ledger["core_source_material"][0]["sha256"] = "0" * 64
    elif fault == "changed-tool-source":
        ledger["producer_tools"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="CAD_"):
        validate_cad_vendors(lock, ledger)
