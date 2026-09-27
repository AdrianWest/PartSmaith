"""

@package src.partsmith.__main__
@brief Allow ``python -m partsmith``.
@details Provides the module implementation and public interfaces.
"""

from partsmith.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
