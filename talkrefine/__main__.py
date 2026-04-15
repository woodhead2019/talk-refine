"""Entry point for `python -m talkrefine`."""

import sys
import os
import io

# Ensure stdout/stderr are usable before any imports that might print.
# pythonw.exe may set them to None OR to a closed file handle — both crash
# third-party libs (funasr, tqdm, etc.) that call print() or sys.stdout.flush().
def _ensure_stream(name):
    stream = getattr(sys, name, None)
    if stream is None or getattr(stream, "closed", False):
        setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))

_ensure_stream("stdout")
_ensure_stream("stderr")

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
