#!/usr/bin/env python3
"""
AI Collab CLI 入口脚本

用法: python3 -m ai_collab.cli [命令] [选项]
"""

import os
import sys

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 直接运行 cli.py 的 main 函数
from ai_collab.cli import main

if __name__ == "__main__":
    sys.exit(main())
