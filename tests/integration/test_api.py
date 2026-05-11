"""
Local Backend API 测试
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "local-backend"))

from app.core.cache import get_cache_manager
from app.core.database import SessionLocal, create_tables
from app.main import app
from app.models.pack import ExecutionHistoryModel, PackModel, QualityMetricModel

client = TestClient(app)


def _reset_db():
    create_tables()
    get_cache_manager(force_reload=True).clear()
    db = SessionLocal()
    try:
        db.query(QualityMetricModel).delete()
        db.query(ExecutionHistoryModel).delete()
        db.query(PackModel).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_database():
    _reset_db()
    yield
    _reset_db()


class TestHealthAPI:
    """健康检查 API 测试"""

    def test_root(self):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Prompt Pack API"
        assert data["status"] == "running"

    def test_health_check(self):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_metrics_endpoint(self):
        """测试 Prometheus 指标端点"""
        # 先产生一点访问流量
        client.get("/")
        client.get("/health")

        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        content = response.text
        assert "prompt_pack_http_requests_total" in content
        assert "prompt_pack_http_request_duration_seconds" in content

    def test_cache_hit_stats_observable(self):
        """测试缓存命中统计可观测"""
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-cache-001",
                "pack_name": "缓存测试 Pack",
                "version": "1.0.0",
                "type": "custom",
                "description": "cache test",
                "designer": "Test",
            },
            "workflow": {"steps": []},
        }
        create_response = client.post("/api/packs", json=pack_data)
        assert create_response.status_code == 201

        list_response_1 = client.get("/api/packs")
        assert list_response_1.status_code == 200
        list_response_2 = client.get("/api/packs")
        assert list_response_2.status_code == 200

        health_response = client.get("/health")
        assert health_response.status_code == 200
        cache_stats = health_response.json().get("cache", {})
        assert cache_stats.get("total_requests", 0) >= 2
        assert cache_stats.get("hits", 0) >= 1


class TestPackAPI:
    """Pack API 测试"""

    def test_list_packs_empty(self):
        """测试空列表"""
        response = client.get("/api/packs")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "packs" in data

    def test_create_pack(self):
        """测试创建 Pack"""
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-api-001",
                "pack_name": "API 测试 Pack",
                "version": "1.0.0",
                "type": "custom",
                "description": "API 测试用",
                "designer": "Test",
                "category": "测试",
                "tags": ["测试"],
                "language": "zh",
            },
            "workflow": {"steps": [{"id": "step_1", "name": "测试步骤", "type": "local"}]},
        }

        response = client.post("/api/packs", json=pack_data)
        assert response.status_code == 201
        data = response.json()
        assert data["pack_id"] == "test-pack-api-001"

    def test_get_pack(self):
        """测试获取 Pack"""
        # 先创建
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-api-002",
                "pack_name": "API 测试 Pack 2",
                "version": "1.0.0",
                "type": "custom",
                "description": "API 测试用 2",
                "designer": "Test",
            },
            "workflow": {"steps": []},
        }

        create_response = client.post("/api/packs", json=pack_data)
        assert create_response.status_code == 201

        # 再获取
        response = client.get("/api/packs/test-pack-api-002")
        assert response.status_code == 200
        data = response.json()
        assert data["pack_name"] == "API 测试 Pack 2"

    def test_update_pack(self):
        """测试更新 Pack"""
        # 先创建
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-api-003",
                "pack_name": "API 测试 Pack 3",
                "version": "1.0.0",
                "type": "custom",
                "description": "原始描述",
                "designer": "Test",
            },
            "workflow": {"steps": []},
        }

        client.post("/api/packs", json=pack_data)

        # 更新
        update_data = {"description": "更新后的描述"}

        response = client.put("/api/packs/test-pack-api-003", json=update_data)
        assert response.status_code == 200

    def test_delete_pack(self):
        """测试删除 Pack"""
        # 先创建
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-api-004",
                "pack_name": "API 测试 Pack 4",
                "version": "1.0.0",
                "type": "custom",
                "description": "待删除",
                "designer": "Test",
            },
            "workflow": {"steps": []},
        }

        client.post("/api/packs", json=pack_data)

        # 删除
        response = client.delete("/api/packs/test-pack-api-004")
        assert response.status_code == 204

        # 确认已删除（软删除，is_active=False）
        get_response = client.get("/api/packs/test-pack-api-004")
        assert get_response.status_code == 404

    def test_bulk_create_packs_partial_failure(self):
        """测试批量创建 Pack 的部分失败处理"""
        payload = {
            "continue_on_error": True,
            "packs": [
                {
                    "metadata": {
                        "pack_id": "test-bulk-pack-001",
                        "pack_name": "Bulk Pack 1",
                        "version": "1.0.0",
                        "type": "custom",
                        "description": "bulk",
                        "designer": "Test",
                    },
                    "workflow": {"steps": []},
                },
                {
                    "metadata": {
                        "pack_id": "test-bulk-pack-001",
                        "pack_name": "Bulk Pack Dup",
                        "version": "1.0.0",
                        "type": "custom",
                        "description": "bulk dup",
                        "designer": "Test",
                    },
                    "workflow": {"steps": []},
                },
                {
                    "metadata": {
                        "pack_id": "test-bulk-pack-002",
                        "pack_name": "Bulk Pack 2",
                        "version": "1.0.0",
                        "type": "custom",
                        "description": "bulk2",
                        "designer": "Test",
                    },
                    "workflow": {"steps": []},
                },
            ],
        }

        response = client.post("/api/packs/bulk/create", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["succeeded"] == 2
        assert data["failed"] == 1
        assert len(data["errors"]) == 1

    def test_bulk_get_packs(self):
        """测试批量查询 Pack"""
        payload_create = {
            "packs": [
                {
                    "metadata": {
                        "pack_id": "test-bulk-get-001",
                        "pack_name": "Bulk Get 1",
                        "version": "1.0.0",
                        "type": "custom",
                        "description": "bulk-get",
                        "designer": "Test",
                    },
                    "workflow": {"steps": []},
                },
                {
                    "metadata": {
                        "pack_id": "test-bulk-get-002",
                        "pack_name": "Bulk Get 2",
                        "version": "1.0.0",
                        "type": "custom",
                        "description": "bulk-get",
                        "designer": "Test",
                    },
                    "workflow": {"steps": []},
                },
            ]
        }
        create_response = client.post("/api/packs/bulk/create", json=payload_create)
        assert create_response.status_code == 200

        payload_get = {
            "pack_ids": ["test-bulk-get-001", "test-bulk-get-002", "test-bulk-get-missing"]
        }
        response = client.post("/api/packs/bulk/get", json=payload_get)
        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 3
        assert data["found"] == 2
        assert data["missing"] == ["test-bulk-get-missing"]


class TestExecutionAPI:
    """执行历史 API 测试"""

    def test_create_execution(self):
        """测试创建执行记录"""
        # 先创建 Pack
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-exec-001",
                "pack_name": "执行测试 Pack",
                "version": "1.0.0",
                "type": "custom",
                "description": "执行测试用",
                "designer": "Test",
            },
            "workflow": {"steps": []},
        }

        client.post("/api/packs", json=pack_data)

        # 创建执行记录
        exec_data = {"pack_id": "test-pack-exec-001", "input_data": {"test": "input"}}

        response = client.post("/api/packs/test-pack-exec-001/executions", json=exec_data)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    def test_list_executions(self):
        """测试获取执行历史列表"""
        response = client.get("/api/packs/test-pack-exec-001/executions")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "executions" in data

    def test_bulk_create_executions_partial_failure(self):
        """测试批量创建执行记录（部分失败）"""
        pack_data = {
            "metadata": {
                "pack_id": "test-pack-bulk-exec-001",
                "pack_name": "执行批量测试 Pack",
                "version": "1.0.0",
                "type": "custom",
                "description": "执行批量测试",
                "designer": "Test",
            },
            "workflow": {"steps": []},
        }
        create_pack_response = client.post("/api/packs", json=pack_data)
        assert create_pack_response.status_code == 201

        payload = {
            "continue_on_error": True,
            "items": [{"input": "ok1"}, "invalid-item", {"input": "ok2"}],
        }
        response = client.post(
            "/api/packs/test-pack-bulk-exec-001/executions/bulk-create", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["succeeded"] == 2
        assert data["failed"] == 1
        assert len(data["executions"]) == 2
        assert len(data["errors"]) == 1


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
