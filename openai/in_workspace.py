#!/usr/bin/env python3
"""Execute an argv in this proof's workspace, including when a recorder resets cwd."""
import os
from pathlib import Path
import sys

base = Path(__file__).resolve().parent
tool_bin = base / "elan/toolchains/leanprover--lean4---v4.34.1/bin"
os.environ["PATH"] = str(tool_bin) + os.pathsep + os.environ.get("PATH", "")
os.environ["ELAN_HOME"] = str(base / "elan")
os.environ["XDG_CACHE_HOME"] = str(base / "cache")
os.environ["MATHLIB_CACHE_DIR"] = str(base / "cache/mathlib")
os.environ["LEAN_NUM_THREADS"] = "2"
os.chdir(base / "workspace")
if len(sys.argv) < 2:
    raise SystemExit("supply an executable and its arguments")
os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
