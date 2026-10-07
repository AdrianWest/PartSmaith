"""Standalone entry point: python -m partsmith.gui."""

import sys


def main():
    try:
        import wx

        from .app import SetupFrame
    except ImportError:
        print(
            'GUI dependencies missing. Install with: pip install ".[gui]"',
            file=sys.stderr,
        )
        return 1
    app = wx.App(False)
    frame = SetupFrame()
    frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
