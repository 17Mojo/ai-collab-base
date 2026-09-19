"""
ai_collab/pack/pack_executor_mvp.py 测试
目标: 把 54% → 80%+
"""

import json

import pytest

from ai_collab.pack.pack_executor_mvp import (
    PackExecutorMVP,
    execute_pack,
    load_pack_from_file,
)


def _make_minimal_pack(steps=None, metadata=None):
    return {
        "metadata": metadata or {"pack_name": "TestPack", "version": "1.0.0", "type": "test"},
        "workflow": {"steps": steps or []},
    }


# init + execute 主流程
def test_init_extracts_metadata_and_workflow():
    pack = _make_minimal_pack(
        steps=[{"name": "s1", "type": "LOCAL"}],
        metadata={"pack_name": "P1", "version": "2.0", "type": "x"},
    )
    exe = PackExecutorMVP(pack)
    assert exe.pack == pack
    assert exe.metadata["pack_name"] == "P1"
    assert exe.workflow == {"steps": [{"name": "s1", "type": "LOCAL"}]}
    assert exe.context == {}
    assert exe.results == []


def test_execute_runs_all_steps_in_order(capsys):
    pack = _make_minimal_pack(steps=[
        {"name": "loc", "type": "LOCAL", "inputs": [{"key": "k1", "source": "user_input"}]},
        {"name": "gen", "type": "GENERATION", "template": "hi {k1}"},
        {"name": "val", "type": "VALIDATION"},
    ])
    exe = PackExecutorMVP(pack)
    result = exe.execute({"k1": "world"})

    assert result["pack_name"] == "TestPack"
    assert result["version"] == "1.0.0"
    assert result["status"] == "completed"
    assert len(result["results"]) == 3
    assert all(r["status"] == "success" for r in result["results"])
    assert "hi world" in result["final_content"]


def test_execute_breaks_on_error(capsys):
    pack = _make_minimal_pack(steps=[
        {"name": "s1", "type": "LOCAL"},
        {"name": "s2", "type": "UNKNOWN_TYPE"},
        {"name": "s3", "type": "LOCAL"},
    ])
    exe = PackExecutorMVP(pack)
    orig = exe._execute_step
    def fake_step(step):
        if step["name"] == "s2":
            return {"status": "error", "error": "boom"}
        return orig(step)
    exe._execute_step = fake_step

    result = exe.execute({"k1": "v"})
    assert len(result["results"]) == 2
    assert result["results"][1]["status"] == "error"


# _execute_step dispatch
def test_step_dispatch_local():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "LOCAL", "inputs": []})
    assert out["step_type"] == "LOCAL"


def test_step_dispatch_analysis():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "ANALYSIS"})
    assert out["step_type"] == "ANALYSIS"


def test_step_dispatch_generation():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "GENERATION"})
    assert out["step_type"] == "GENERATION"


def test_step_dispatch_validation():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "VALIDATION"})
    assert out["step_type"] == "VALIDATION"


def test_step_dispatch_fusion():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "FUSION", "strategy": "concat"})
    assert out["step_type"] == "FUSION"


def test_step_dispatch_tracking(tmp_path):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "TRACKING", "output_file": str(tmp_path / "t.json")})
    assert out["step_type"] == "TRACKING"


def test_step_unknown_type_returns_skipped():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"type": "FOO_BAR"})
    assert out["status"] == "skipped"
    assert "FOO_BAR" in out["message"]


def test_step_missing_type_defaults_to_unknown():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_step({"name": "no-type"})
    assert out["status"] == "skipped"


# LOCAL
def test_local_step_pulls_from_user_input(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["user_input"] = {"a": 1, "b": "two"}
    out = exe._execute_local({"inputs": [
        {"key": "a", "source": "user_input"},
        {"key": "b", "source": "user_input"},
    ]})
    assert out["status"] == "success"
    assert exe.context["a"] == 1
    assert exe.context["b"] == "two"


# ANALYSIS
def test_analysis_with_content(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["content"] = "alpha beta gamma delta epsilon zeta"
    out = exe._execute_analysis({})
    assert out["status"] == "success"
    assert exe.context["analysis_result"]["keywords"] == ["alpha", "beta", "gamma", "delta", "epsilon"]
    assert exe.context["analysis_result"]["word_count"] == 6


def test_analysis_with_empty_content():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe._execute_analysis({})
    assert exe.context["analysis_result"]["keywords"] == []
    assert "word_count" not in exe.context["analysis_result"]


# GENERATION
def test_generation_with_template(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["topic"] = "T"
    exe.context["content"] = "C"
    out = exe._execute_generation({"template": "ZhuTi: {topic} ; NeiRong: {content}"})
    assert out["status"] == "success"
    assert "ZhuTi: T" in exe.context["generated_content"]
    assert out["outputs"]["length"] == len(exe.context["generated_content"])


def test_generation_default_template(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["topic"] = "TopicX"
    exe.context["content"] = "ContentY"
    exe.context["analysis_result"] = {"keywords": ["kw1", "kw2"]}
    exe._execute_generation({"template": "默认模板"})
    body = exe.context["generated_content"]
    assert "TopicX" in body
    assert "ContentY" in body
    assert "kw1" in body or "kw2" in body


def test_generation_with_params_does_not_crash():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["x"] = "v"
    out = exe._execute_generation({"template": "{x}", "params": {"temperature": 0.7}})
    assert out["status"] == "success"


# VALIDATION
def test_validation_pass_with_long_content_and_keywords(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "alpha beta " * 30
    exe.context["analysis_result"] = {"keywords": ["alpha"]}
    out = exe._execute_validation({})
    assert out["status"] == "success"
    vr = out["outputs"]
    assert vr["is_valid"] is True
    assert vr["issues"] == []
    assert vr["score"] == 0.8


def test_validation_fail_short_content(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "short"
    out = exe._execute_validation({})
    vr = out["outputs"]
    assert vr["is_valid"] is False
    assert "内容过短" in vr["issues"]
    assert vr["score"] == pytest.approx(0.6)


def test_validation_fail_keyword_coverage(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "a " * 40
    exe.context["analysis_result"] = {"keywords": ["x", "y", "z"]}
    out = exe._execute_validation({})
    vr = out["outputs"]
    assert vr["is_valid"] is False
    assert any("关键词" in i for i in vr["issues"])


def test_validation_empty_content_default_score():
    """空 generated_content 是 '' (len=0), <50 触发'内容过短', 但 keywords 也空 → 只扣 0.2 → 0.6"""
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_validation({})
    # len("") < 50 → score 减 0.2
    assert out["outputs"]["score"] == pytest.approx(0.6)
    assert out["outputs"]["is_valid"] is False
    assert "内容过短" in out["outputs"]["issues"]


# FUSION
def test_fusion_concat_strategy(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "A"
    out = exe._execute_fusion({"strategy": "concat"})
    assert out["status"] == "success"
    assert out["outputs"]["strategy"] == "concat"
    assert exe.context["fused_content"] == "A"


def test_fusion_best_strategy(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "the-longest-content-here"
    exe._execute_fusion({"strategy": "best"})
    assert exe.context["fused_content"] == "the-longest-content-here"


def test_fusion_default_strategy_falls_back(capsys):
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "X"
    exe._execute_fusion({"strategy": "unknown-strategy"})
    assert exe.context["fused_content"] == "X"


# TRACKING
def test_tracking_creates_new_file(tmp_path, capsys):
    out_file = tmp_path / "track.json"
    pack = _make_minimal_pack(metadata={"pack_name": "P", "version": "1.0"})
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "hello world"
    exe.context["validation_result"] = {"score": 0.9}
    out = exe._execute_tracking({"output_file": str(out_file)})
    assert out["status"] == "success"
    data = json.loads(out_file.read_text())
    assert len(data["tracking_records"]) == 1
    rec = data["tracking_records"][0]
    assert rec["pack_name"] == "P"
    assert rec["validation_score"] == 0.9
    assert rec["content_length"] == 11
    assert rec["execution_id"].startswith("EXEC-")


def test_tracking_appends_to_existing_file(tmp_path, capsys):
    out_file = tmp_path / "track.json"
    out_file.write_text(json.dumps({"tracking_records": [{"old": True}]}), encoding="utf-8")
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    exe._execute_tracking({"output_file": str(out_file)})
    data = json.loads(out_file.read_text())
    assert len(data["tracking_records"]) == 2
    assert data["tracking_records"][0] == {"old": True}


def test_tracking_handles_corrupted_json(tmp_path, capsys):
    out_file = tmp_path / "track.json"
    out_file.write_text("not json{", encoding="utf-8")
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._execute_tracking({"output_file": str(out_file)})
    assert out["status"] == "success"
    data = json.loads(out_file.read_text())
    assert data["tracking_records"][0]["pack_name"] == "TestPack"


# _generate_final_result
def test_generate_final_result_aggregates_context():
    pack = _make_minimal_pack(metadata={"pack_name": "FP", "version": "9.9"})
    exe = PackExecutorMVP(pack)
    exe.context["generated_content"] = "FINAL"
    exe.context["validation_result"] = {"score": 1.0}
    exe.results = [{"status": "success"}]
    result = exe._generate_final_result()
    assert result["pack_name"] == "FP"
    assert result["version"] == "9.9"
    assert result["status"] == "completed"
    assert result["final_content"] == "FINAL"
    assert result["validation"] == {"score": 1.0}
    assert result["results"] == [{"status": "success"}]


def test_generate_final_result_defaults_when_empty():
    # metadata 空 → .get("pack_name", "Unknown") 落回 "Unknown"
    pack = {"metadata": {}, "workflow": {"steps": []}}
    exe = PackExecutorMVP(pack)
    result = exe._generate_final_result()
    assert result["pack_name"] == "Unknown"
    assert result["version"] == "N/A"
    assert result["final_content"] == ""


# 顶层函数
def test_load_pack_from_file(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"metadata": {"k": "v"}, "workflow": {}}), encoding="utf-8")
    data = load_pack_from_file(str(p))
    assert data == {"metadata": {"k": "v"}, "workflow": {}}


def test_execute_pack_function(capsys):
    pack = _make_minimal_pack(steps=[
        {"name": "g", "type": "GENERATION", "template": "OK"},
    ])
    result = execute_pack(pack, {"x": 1})
    assert result["status"] == "completed"
    assert result["final_content"] == "OK"


# _apply_fusion_strategy (consensus 路径)
def test_apply_fusion_strategy_no_sources_returns_consensus():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    out = exe._apply_fusion_strategy({"consensus": "hello", "sources": []}, "concat")
    assert out == "hello"


def test_apply_fusion_strategy_concat():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    consensus = {"sources": [
        {"response": "A", "confidence": 0.9},
        {"response": "B", "confidence": 0.7},
    ]}
    out = exe._apply_fusion_strategy(consensus, "concat")
    assert "A" in out and "B" in out


def test_apply_fusion_strategy_best_picks_highest_confidence():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    consensus = {"sources": [
        {"response": "low", "confidence": 0.2},
        {"response": "high", "confidence": 0.95},
    ]}
    out = exe._apply_fusion_strategy(consensus, "best")
    assert out == "high"


def test_apply_fusion_strategy_weighted_sorts_by_confidence():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    consensus = {"sources": [
        {"response": "low", "confidence": 0.3},
        {"response": "high", "confidence": 0.9},
    ]}
    out = exe._apply_fusion_strategy(consensus, "weighted")
    assert out.index("high") < out.index("low")
    assert "[置信度: 0.90]" in out


def test_apply_fusion_strategy_unknown_returns_consensus():
    pack = _make_minimal_pack()
    exe = PackExecutorMVP(pack)
    consensus = {"consensus": "fallback-text", "sources": []}
    out = exe._apply_fusion_strategy(consensus, "weird-strategy")
    assert out == "fallback-text"
