"""
风格模板数据库管理
支持自定义灵魂注入风格的 CRUD 操作
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 预设风格模板
PRESET_STYLES = {
    "luoyonghao": {
        "name": "luoyonghao",
        "display_name": "罗永浩风格",
        "prefix": "我跟你讲，",
        "suffix": "\n\n别整那些虚的，直接说重点。",
        "tone": "直率、幽默、有态度",
        "keywords": ["我跟你讲", "这才是", "别整虚的", "直接说"],
        "is_preset": True,
    },
    "daojie": {
        "name": "daojie",
        "display_name": "刀姐风格",
        "prefix": "具体怎么做呢？",
        "suffix": "\n\n核心逻辑就是这样。",
        "tone": "实用、系统、可执行",
        "keywords": ["具体怎么做", "核心逻辑", "方法论", "三步"],
        "is_preset": True,
    },
    "dongyuhui": {
        "name": "dongyuhui",
        "display_name": "董宇辉风格",
        "prefix": "就像",
        "suffix": "\n\n你会发现，这背后有更深的含义。",
        "tone": "诗意、温暖、有深度",
        "keywords": ["就像", "你会发现", "更深的含义", "背后"],
        "is_preset": True,
    },
}


class StyleDB:
    """风格模板数据库管理器"""

    def __init__(self, db_path: str = "data/packs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 风格模板表
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS custom_styles (
            name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            prefix TEXT,
            suffix TEXT,
            tone TEXT,
            keywords TEXT,
            is_preset INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """
        )

        # 插入预设风格
        for name, style in PRESET_STYLES.items():
            cursor.execute(
                """
            INSERT OR IGNORE INTO custom_styles
            (name, display_name, prefix, suffix, tone, keywords, is_preset, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    style["display_name"],
                    style["prefix"],
                    style["suffix"],
                    style["tone"],
                    json.dumps(style["keywords"]),
                    1,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

        conn.commit()
        conn.close()

    def get_all_styles(self) -> List[Dict[str, Any]]:
        """获取所有风格（预设 + 自定义）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
        SELECT name, display_name, prefix, suffix, tone, keywords, is_preset, created_at, updated_at
        FROM custom_styles
        ORDER BY is_preset DESC, created_at DESC
        """
        )

        rows = cursor.fetchall()
        conn.close()

        styles = []
        for row in rows:
            styles.append(
                {
                    "name": row[0],
                    "display_name": row[1],
                    "prefix": row[2] or "",
                    "suffix": row[3] or "",
                    "tone": row[4] or "",
                    "keywords": json.loads(row[5]) if row[5] else [],
                    "is_preset": bool(row[6]),
                    "created_at": row[7],
                    "updated_at": row[8],
                }
            )

        return styles

    def get_style(self, name: str) -> Optional[Dict[str, Any]]:
        """获取单个风格"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
        SELECT name, display_name, prefix, suffix, tone, keywords, is_preset, created_at, updated_at
        FROM custom_styles WHERE name = ?
        """,
            (name,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "name": row[0],
            "display_name": row[1],
            "prefix": row[2] or "",
            "suffix": row[3] or "",
            "tone": row[4] or "",
            "keywords": json.loads(row[5]) if row[5] else [],
            "is_preset": bool(row[6]),
            "created_at": row[7],
            "updated_at": row[8],
        }

    def create_style(self, style_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建自定义风格"""
        name = style_data.get("name")
        if not name:
            raise ValueError("Style name is required")

        # 检查是否与预设风格冲突
        if name in PRESET_STYLES:
            raise ValueError(f"Cannot overwrite preset style: {name}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute(
            """
        INSERT INTO custom_styles
        (name, display_name, prefix, suffix, tone, keywords, is_preset, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
            (
                name,
                style_data.get("display_name", name),
                style_data.get("prefix", ""),
                style_data.get("suffix", ""),
                style_data.get("tone", ""),
                json.dumps(style_data.get("keywords", [])),
                now,
                now,
            ),
        )

        conn.commit()
        conn.close()

        return self.get_style(name)

    def update_style(self, name: str, style_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新自定义风格"""
        # 检查风格是否存在
        existing = self.get_style(name)
        if not existing:
            return None

        # 不允许修改预设风格
        if existing["is_preset"]:
            raise ValueError(f"Cannot modify preset style: {name}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute(
            """
        UPDATE custom_styles SET
            display_name = ?,
            prefix = ?,
            suffix = ?,
            tone = ?,
            keywords = ?,
            updated_at = ?
        WHERE name = ? AND is_preset = 0
        """,
            (
                style_data.get("display_name", existing["display_name"]),
                style_data.get("prefix", existing["prefix"]),
                style_data.get("suffix", existing["suffix"]),
                style_data.get("tone", existing["tone"]),
                json.dumps(style_data.get("keywords", existing["keywords"])),
                now,
                name,
            ),
        )

        conn.commit()
        conn.close()

        return self.get_style(name)

    def delete_style(self, name: str) -> bool:
        """删除自定义风格（不能删除预设）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 只能删除自定义风格
        cursor.execute(
            """
        DELETE FROM custom_styles WHERE name = ? AND is_preset = 0
        """,
            (name,),
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def apply_style(self, name: str, text: str) -> str:
        """应用风格到文本"""
        style = self.get_style(name)
        if not style:
            # 默认使用罗永浩风格
            style = PRESET_STYLES.get("luoyonghao")

        prefix = style.get("prefix", "")
        suffix = style.get("suffix", "")

        return f"{prefix}{text}{suffix}"


# 全局实例
style_db = StyleDB()
