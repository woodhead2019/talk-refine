"""Entry point for `python -m talkrefine`."""

import sys
import os

# Ensure stdout/stderr exist before any imports that might print.
# pythonw.exe sets them to None, which crashes native extensions.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from talkrefine.app import main

if __name__ == "__main__":
    main()
