"""@package partsmith.gui.__main__
@brief Starts the desktop app after checking manual OCR prerequisites.
@details Missing external installations are explained before session recovery.
"""

import sys


def main():
    """@brief Opens the desktop app or a manual-prerequisite error dialog.
    @return Zero on normal exit, two for missing prerequisites, or one for
    missing Python imports.
    @details Python package failures remain separate from manual installations.
    """
    try:
        import wx

        from partsmith.external_dependencies import check_external_dependencies

        from .prerequisites import show_missing_dependencies

        app = wx.App(False)
        missing = check_external_dependencies()
        if missing:
            show_missing_dependencies(missing)
            return 2
        from .app import SetupFrame
    except ImportError:
        print(
            'GUI dependencies missing. Install with: pip install ".[gui]"',
            file=sys.stderr,
        )
        return 1
    frame = SetupFrame()
    frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
