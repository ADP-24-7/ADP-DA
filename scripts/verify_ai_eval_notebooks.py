"""Execute all consumer notebooks using the current Python and local Jupyter state."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-outputs", action="store_true")
    args = parser.parse_args()
    (ROOT / ".tmp/ipython").mkdir(parents=True, exist_ok=True)
    (ROOT / ".tmp/jupyter-runtime").mkdir(parents=True, exist_ok=True)
    os.environ["IPYTHONDIR"] = str(ROOT / ".tmp/ipython")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".tmp/jupyter-runtime")
    # Verification must use the bundled synthetic fixture, never an ambient API token/source.
    for key in (
        "ADP_AI_BUNDLE_SOURCE",
        "ADP_AI_EVALUATION_RUN_ID",
        "ADP_BE_TOKEN",
        "ADP_AI_INDEPENDENT_CASES",
        "ADP_AI_SYMMETRIC_DIFFERENCES",
    ):
        os.environ.pop(key, None)
    for path in sorted((ROOT / "02_ai/notebooks").glob("AI_EVAL_*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [
            sys.executable,
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]
        client = NotebookClient(
            notebook, km=manager, timeout=120, resources={"metadata": {"path": str(ROOT)}}
        )
        try:
            client.execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
            manager.cleanup_resources()
        if args.write_outputs:
            nbformat.write(notebook, path)
        print(path.name + " PASS")


if __name__ == "__main__":
    main()
