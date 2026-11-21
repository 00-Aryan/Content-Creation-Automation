"""CLI entrypoint for module execution (python -m content_creation.cli)."""

import sys

from content_creation.cli import main

if __name__ == "__main__":
    sys.exit(main())
