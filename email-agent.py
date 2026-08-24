"""Compatibility launcher for the MetAKNews Gmail draft agent.

The canonical implementation lives in ``metaknews@gmail.com.py``. Keeping this
small launcher prevents the historical ``email-agent.py`` entry point from
drifting into a second implementation or bypassing the Gmail Drafts guardrail.
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).with_name("metaknews@gmail.com.py")
    runpy.run_path(str(target), run_name="__main__")
