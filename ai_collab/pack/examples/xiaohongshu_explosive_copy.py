"""小红书爆文 Pack 示例加载器。"""

import json
from pathlib import Path

from ..schema_v2 import PromptPackV2


def create_xiaohongshu_explosive_copy_pack() -> PromptPackV2:
    repo_root = Path(__file__).resolve().parents[4]
    pack_file = repo_root / "packs" / "examples" / "xiaohongshu_beauty_review.json"
    with pack_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return PromptPackV2.from_dict(data)


if __name__ == "__main__":
    pack = create_xiaohongshu_explosive_copy_pack()
    print(pack.metadata.pack_name)
