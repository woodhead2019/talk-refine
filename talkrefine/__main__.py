"""Entry point for `python -m talkrefine`."""

import sys
import os
import io

# Ensure stdout/stderr exist before any imports that might print.
# pythonw.exe sets them to None, which crashes native extensions.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Wrap stdout/stderr with UTF-8 encoding to avoid UnicodeEncodeError
# when printing emoji in non-UTF-8 consoles (e.g. cp1252 in detached mode).
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name)
    if hasattr(_stream, "buffer"):
        setattr(sys, _stream_name,
                io.TextIOWrapper(_stream.buffer, encoding="utf-8",
                                 errors="replace", line_buffering=True))

from talkrefine.app import main

if __name__ == "__main__":
    main()
