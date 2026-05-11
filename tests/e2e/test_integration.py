"""
端到端集成测试
测试 Chrome Extension + Local Backend 的完整流程
"""

import json
import os
import sys

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestPackWorkflow:
    """Pack 工作流端到端测试"""

    def test_load_pack_from_file(self):
        """测试从文件加载 Pack"""
        pack_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "packs",
            "examples",
            "xiaohongshu_beauty_review.json",
        )

        if not os.path.exists(pack_path):
            pytest.skip("示例 Pack 文件不存在")

        with open(pack_path, "r", encoding="utf-8") as f:
            pack_data = json.load(f)

        assert "metadata" in pack_data
        assert "workflow" in pack_data
        assert pack_data["metadata"]["pack_id"] == "xiaohongshu-beauty-review"

    def test_pack_schema_validation(self):
        """测试 Pack Schema 验证"""
        from ai_collab.pack.schema_v2 import PromptPackV2

        pack_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "packs",
            "examples",
            "xiaohongshu_beauty_review.json",
        )

        if not os.path.exists(pack_path):
            pytest.skip("示例 Pack 文件不存在")

        with open(pack_path, "r", encoding="utf-8") as f:
            pack_data = json.load(f)

        # 反序列化为对象
        pack = PromptPackV2.from_dict(pack_data)

        assert pack.metadata.pack_name == "小红书美妆测评文案生成包"
        assert len(pack.workflow.steps) == 6  # 6 个工作流步骤

    def test_workflow_steps_integrity(self):
        """测试工作流步骤完整性"""
        from ai_collab.pack.schema_v2 import PromptPackV2

        pack_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "packs",
            "examples",
            "xiaohongshu_beauty_review.json",
        )

        if not os.path.exists(pack_path):
            pytest.skip("示例 Pack 文件不存在")

        with open(pack_path, "r", encoding="utf-8") as f:
            pack_data = json.load(f)

        pack = PromptPackV2.from_dict(pack_data)

        # 验证步骤 ID 唯一性
        step_ids = [step.id for step in pack.workflow.steps]
        assert len(step_ids) == len(set(step_ids))

        # 验证步骤类型
        for step in pack.workflow.steps:
            assert step.type.value in [
                "local",
                "analysis",
                "generation",
                "validation",
                "fusion",
                "tracking",
            ]


class TestChromeExtensionFiles:
    """Chrome Extension 文件完整性测试"""

    def test_manifest_exists(self):
        """测试 manifest.json 存在"""
        manifest_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "manifest.json",
        )

        assert os.path.exists(manifest_path), "manifest.json 不存在"

    def test_manifest_valid(self):
        """测试 manifest.json 格式有效"""
        manifest_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "manifest.json",
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["manifest_version"] == 3
        assert "name" in manifest
        assert "version" in manifest
        assert "permissions" in manifest

    def test_content_script_exists(self):
        """测试 Content Script 存在"""
        content_script_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "index.js",
        )

        assert os.path.exists(content_script_path), "Content Script 不存在"

    def test_error_recovery_manager_exists(self):
        """测试错误恢复管理器存在"""
        error_recovery_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "error-recovery.js",
        )

        assert os.path.exists(error_recovery_path), "error-recovery.js 不存在"

    def test_error_recovery_strategies(self):
        """测试错误恢复策略存在"""
        error_recovery_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "error-recovery.js",
        )

        with open(error_recovery_path, "r", encoding="utf-8") as F:
            content = F.read()

        # 检查关键恢复策略
        assert "dom_observer_missing" in content, "缺少 DOM 观察器恢复策略"
        assert "executor_stuck" in content, "缺少执行器恢复策略"
        assert "message_channel_error" in content, "缺少消息通道恢复策略"
        assert "storage_error" in content, "缺少存储恢复策略"

    def test_enhanced_message_handler_exists(self):
        """测试增强消息处理器存在"""
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "enhanced-message-handler.js",
        )

        assert os.path.exists(handler_path), "enhanced-message-handler.js 不存在"

    def test_message_retry_mechanism(self):
        """测试消息重试机制存在"""
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "enhanced-message-handler.js",
        )

        with open(handler_path, "r", encoding="utf-8") as F:
            content = F.read()

        assert "retryQueue" in content, "缺少重试队列"
        assert "isRetryableError" in content, "缺少可重试性判断"
        assert "addToRetryQueue" in content, "缺少重试队列添加方法"
        assert "processRetryQueue" in content, "缺少重试队列处理方法"

    def test_storage_manager_exists(self):
        """测试存储管理器存在"""
        storage_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "storage-manager.js",
        )

        assert os.path.exists(storage_path), "storage-manager.js 不存在"

    def test_storage_encryption(self):
        """测试存储加密功能存在"""
        storage_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "storage-manager.js",
        )

        with open(storage_path, "r", encoding="utf-8") as F:
            content = F.read()

        assert "AES-GCM" in content, "缺少 AES-GCM 加密算法"
        assert "encrypt(" in content, "缺少加密方法"
        assert "decrypt(" in content, "缺少解密方法"
        assert "encryption_key" in content, "缺少加密密钥管理"

    def test_storage_capacity_management(self):
        """测试存储容量管理功能存在"""
        storage_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "storage-manager.js",
        )

        with open(storage_path, "r", encoding="utf-8") as F:
            content = F.read()

        assert "getStorageInfo" in content, "缺少存储信息获取方法"
        assert "checkStorageCapacity" in content, "缺少容量检查方法"
        assert "runCleanup" in content, "缺少清理方法"
        assert "maxStorageSize" in content, "缺少最大容量配置"

    def test_content_script_initialization_order(self):
        """测试 Content Script 初始化顺序正确"""
        manifest_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "manifest.json",
        )

        with open(manifest_path, "r", encoding="utf-8") as F:
            manifest = json.load(F)

        # 获取 content scripts
        content_scripts = manifest.get("content_scripts", [])
        assert len(content_scripts) > 0, "缺少 content_scripts 配置"

        js_files = content_scripts[0].get("js", [])

        # 验证加载顺序（完整路径）
        expected_files = [
            "src/content/storage-manager.js",
            "src/content/error-recovery.js",
            "src/content/enhanced-message-handler.js",
            "src/content/dom-observer.js",
            "src/content/pack-executor.js",
            "src/content/message-handler.js",
            "src/content/index.js",
        ]

        for expected_file in expected_files:
            assert expected_file in js_files, f"缺少必要的加载文件: {expected_file}"

        # 验证实际顺序符合预期
        storage_idx = js_files.index("src/content/storage-manager.js")
        index_idx = js_files.index("src/content/index.js")
        assert storage_idx < index_idx, "storage-manager.js 应该在 index.js 之前加载"

    def test_platform_detection_fallback(self):
        """测试平台探测回退机制"""
        index_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "index.js",
        )

        with open(index_path, "r", encoding="utf-8") as F:
            content = F.read()

        assert "detectPlatform" in content, "缺少平台检测函数"
        assert "'generic'" in content or "'unknown'" in content, "缺少未知平台回退"

    def test_error_handling_in_init(self):
        """测试初始化过程中的错误处理"""
        index_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "content",
            "index.js",
        )

        with open(index_path, "r", encoding="utf-8") as F:
            content = F.read()

        assert "try {" in content, "缺少 try 块"
        assert "catch (error)" in content, "缺少错误捕获"
        assert "errorRecovery.handleError" in content, "缺少错误恢复调用"

    def test_background_script_exists(self):
        """测试 Background Script 存在"""
        background_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "background",
            "index.js",
        )

        assert os.path.exists(background_path), "Background Script 不存在"

    def test_background_storage_schema_markers(self):
        """测试 Background 已包含存储 schema 迁移标记"""
        background_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "background",
            "index.js",
        )

        with open(background_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "const STORAGE_SCHEMA_VERSION = 2;" in content
        assert "async function ensureStorageSchema" in content
        assert "async function getStorageInfo" in content
        assert "schemaVersion" in content

    def test_options_use_background_settings_api(self):
        """测试 Options 通过 Background 设置 API 读写配置"""
        options_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "products",
            "prompt-pack-extension",
            "chrome",
            "src",
            "options",
            "options.js",
        )

        with open(options_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "action: 'getSettings'" in content
        assert "action: 'updateSettings'" in content
        assert "sendBackgroundMessage" in content


class TestLocalBackendFiles:
    """Local Backend 文件完整性测试"""

    def test_main_app_exists(self):
        """测试主应用文件存在"""
        main_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "local-backend", "app", "main.py"
        )

        assert os.path.exists(main_path), "main.py 不存在"

    def test_docker_config_exists(self):
        """测试 Docker 配置存在"""
        dockerfile_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "local-backend", "Dockerfile"
        )

        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "local-backend", "docker-compose.yml"
        )

        assert os.path.exists(dockerfile_path), "Dockerfile 不存在"
        assert os.path.exists(compose_path), "docker-compose.yml 不存在"


class TestProjectStructure:
    """项目结构测试"""

    def test_required_directories(self):
        """测试必要目录存在"""
        base_path = os.path.join(os.path.dirname(__file__), "..", "..")

        required_dirs = [
            "src/ai_collab/pack",
            "products/prompt-pack-extension/chrome/src/content",
            "products/prompt-pack-extension/chrome/src/background",
            "products/prompt-pack-extension/chrome/src/popup",
            "local-backend/app",
            "local-backend/app/api",
            "packs/examples",
        ]

        for dir_path in required_dirs:
            full_path = os.path.join(base_path, dir_path)
            assert os.path.exists(full_path), f"目录不存在: {dir_path}"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
