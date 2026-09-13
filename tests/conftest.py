"""Root conftest.py - ensure project root is on sys.path for all tests."""
import sys
from pathlib import Path

# 把项目根目录加入 sys.path（在 src/ 前面）
# 这样可以加载完整的 ai_collab/ 包，而不是精简版的 src/ai_collab/
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
