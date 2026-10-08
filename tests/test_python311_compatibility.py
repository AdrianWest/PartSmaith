"""@file test_python311_compatibility.py
@brief Checks runtime resource selection and Windows junction protection.
@details Uses isolated paths; no current-user installation is changed.
"""

import json
import os
import subprocess
import sys

import pytest

from partsmith.path_support import is_junction
from partsmith.pcm.installation import require_owned_path
from partsmith.pcm.package import _tree
from partsmith.release.runtime_resources import runtime_resources


@pytest.mark.parametrize("minor", [(3, 11), (3, 12)])
def test_runtime_resources_match_python_baseline(monkeypatch, minor):
    """@brief Checks that each runtime selects its own reviewed lock and pins.
    @param monkeypatch Interpreter selection substitution helper.
    @param minor Supported Python major and minor version tuple.
    @return None.
    @details The historical 3.12 baseline remains distinct from customer 3.11.
    """
    monkeypatch.setattr(sys, "version_info", minor)
    lock, constraints = runtime_resources()
    assert json.loads(lock)["python_baseline"] == ".".join(map(str, minor))
    expected = b"numpy==2.4.6" if minor == (3, 11) else b"numpy==2.5.3"
    assert expected in constraints
    if minor == (3, 11):
        assert "cp311-cp311-win_amd64" in lock.decode()
        assert b"backports.tarfile==1.2.0" in constraints


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse points")
def test_junctions_cannot_redirect_package_paths(tmp_path):
    """@brief Rejects real directory junctions on Python 3.11 and 3.12.
    @param tmp_path Disposable source and installation directories.
    @return None.
    @details Neither source collection nor owned target validation may follow
    a junction into an unrelated directory.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "untouched.txt").write_bytes(b"preserve")
    root = tmp_path / "source"
    root.mkdir()
    junction = root / "redirect"
    subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
        stdin=subprocess.DEVNULL,
        check=True,
        capture_output=True,
    )
    assert is_junction(junction)
    assert not is_junction(outside)
    assert not is_junction(root / "absent")
    with pytest.raises(ValueError, match="symlinks"):
        _tree(root)
    with pytest.raises(ValueError, match="escapes|redirection"):
        require_owned_path(junction, root)
    assert (outside / "untouched.txt").read_bytes() == b"preserve"
