"""
MiniMax AI Content Studio - Thin Wrapper
向后兼容：直接代理到 studio_orchestrator
"""
import sys as _sys
from pathlib import Path as _Path

# 确保 scripts/studio/ 目录在 sys.path 中
_SCRIPT_DIR = _Path(__file__).parent
if str(_SCRIPT_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SCRIPT_DIR))

from studio_orchestrator import main as _main

if __name__ == "__main__":
    _sys.exit(_main())
