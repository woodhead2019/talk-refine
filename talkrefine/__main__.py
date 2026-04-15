"""Entry point for `python -m talkrefine`."""

# talkrefine/__init__.py fixes stdout/stderr for pythonw.exe
from talkrefine.app import main

if __name__ == "__main__":
    main()
