"""@file pcm_acceptance_bootstrap.py
@brief Runs copied acceptance tests using isolated installed modules.
@details Original checkout paths are absent from imports and working directory.
"""
import json
import sys
from pathlib import Path


def main():
    """@brief Runs exact PCM tests once in the supervising interpreter.
    @return Pytest exit status after checking every loaded PartSmith origin.
    @details A main guard prevents multiprocessing children restarting pytest.
    """
    payload = Path(sys.argv[1]).resolve()
    workspace = Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(workspace))
    sys.path.insert(0, str(workspace / "tests"))
    sys.path.insert(0, str(payload))
    import partsmith
    assert sys.flags.isolated
    assert Path(partsmith.__file__).resolve().is_relative_to(payload)
    from partsmith.pcm.runtime import verify_inventory
    inventory = verify_inventory(payload)
    import pytest
    arguments = ["-c", str(workspace / "pytest.ini"), "-q", "--maxfail=1",
                 "-p", "no:cacheprovider", "--junitxml=" + sys.argv[3],
                 str(workspace / "tests")]
    if sys.argv[4] == "desktop":
        arguments.append(str(workspace / "scripts/verify_gui.py"))
    code = pytest.main(arguments)
    origins = {}
    for name, module in sorted(sys.modules.items()):
        if name == "partsmith" or name.startswith("partsmith."):
            origin = getattr(module, "__file__", None)
            if origin is not None:
                assert Path(origin).resolve().is_relative_to(payload), name
                origins[name] = str(Path(origin).resolve().relative_to(payload))
    (workspace.parent / "origins.json").write_text(json.dumps({
        "version": inventory["version"], "origins": origins,
        "repository_imports": False, "isolated": True,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
