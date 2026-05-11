"""
AI Collab CLI 模块入口

允许通过 python3 -m ai_collab.cli 运行 CLI
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ai_collab.cli._cli_main import main

if __name__ == "__main__":
    main()
