#!/usr/bin/env python3
"""
AI Collab CLI 入口脚本

用法: python3 -m ai_collab.cli [命令] [选项]
"""

import sys

from ai_collab.cli import main

if __name__ == "__main__":
    sys.exit(main())
