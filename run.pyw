"""Launcher script for TalkRefine - can be run from any directory."""
import sys
import os

# Handle pythonw.exe: stdout/stderr may be None OR a closed file handle.
def _ensure_stream(name):
    stream = getattr(sys, name, None)
    if stream is None or getattr(stream, "closed", False):
        setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))

_ensure_stream("stdout")
_ensure_stream("stderr")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from talkrefine.app import main
main()
