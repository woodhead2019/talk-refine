"""Launcher script for TalkRefine - can be run from any directory."""
import sys
import os

# Ensure project root is in path (before importing talkrefine)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# talkrefine/__init__.py fixes stdout/stderr for pythonw.exe
from talkrefine.app import main
main()
