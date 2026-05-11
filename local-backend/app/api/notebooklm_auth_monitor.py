"""
NotebookLM 认证状态监控
检测 Cookie 过期并提供自动提醒
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# NotebookLM Skill 数据目录
SKILL_DATA_DIR = Path.home() / ".claude" / "skills" / "notebooklm" / "data"
AUTH_STATE_FILE = SKILL_DATA_DIR / "auth_info.json"
BROWSER_STATE_FILE = SKILL_DATA_DIR / "browser_state" / "state.json"

# Cookie 过期阈值（小时）
COOKIE_EXPIRY_THRESHOLD_HOURS = 24  # 24小时后建议重新认证
COOKIE_CRITICAL_THRESHOLD_HOURS = 48  # 48小时后强制提醒


class AuthStatus(BaseModel):
    """认证状态响应"""

    authenticated: bool
    state_age_hours: float
    last_auth: str
    expires_in_hours: float
    status: str  # "healthy", "warning", "critical", "expired"
    recommendation: str
    needs_reauth: bool


def get_auth_status() -> AuthStatus:
    """
    获取当前认证状态

    Returns:
        AuthStatus: 认证状态信息
    """
    try:
        # 首先检查 state.json 文件（NotebookLM skill 使用此文件）
        if BROWSER_STATE_FILE.exists():
            # 使用 state.json 文件的修改时间作为认证时间
            mtime = os.path.getmtime(BROWSER_STATE_FILE)
            mtime_dt = datetime.fromtimestamp(mtime)
            state_age = datetime.now() - mtime_dt
            state_age_hours = state_age.total_seconds() / 3600
            expires_in_hours = max(0, COOKIE_EXPIRY_THRESHOLD_HOURS - state_age_hours)

            # 确定状态
            if state_age_hours >= COOKIE_CRITICAL_THRESHOLD_HOURS:
                status = "critical"
                recommendation = "认证即将过期，请立即重新认证以确保 NotebookLM 正常工作"
                needs_reauth = True
            elif state_age_hours >= COOKIE_EXPIRY_THRESHOLD_HOURS:
                status = "warning"
                recommendation = "认证状态即将过期，建议重新认证"
                needs_reauth = False
            elif state_age_hours < 1:
                status = "healthy"
                recommendation = "认证状态良好"
                needs_reauth = False
            else:
                status = "healthy"
                recommendation = f"认证状态正常，预计 {expires_in_hours:.1f} 小时后建议重新认证"
                needs_reauth = False

            return AuthStatus(
                authenticated=True,
                state_age_hours=state_age_hours,
                last_auth=mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
                expires_in_hours=expires_in_hours,
                status=status,
                recommendation=recommendation,
                needs_reauth=needs_reauth,
            )

        # 然后检查 auth_info.json 文件
        if AUTH_STATE_FILE.exists():
            with open(AUTH_STATE_FILE, "r") as f:
                auth_info = json.load(f)

            authenticated = auth_info.get("authenticated", False)
            last_auth_str = auth_info.get("last_auth", "")

            if not authenticated or not last_auth_str:
                return AuthStatus(
                    authenticated=False,
                    state_age_hours=0,
                    last_auth="Never",
                    expires_in_hours=0,
                    status="expired",
                    recommendation="需要立即认证 NotebookLM",
                    needs_reauth=True,
                )

            # 解析最后认证时间
            try:
                last_auth = datetime.strptime(last_auth_str, "%Y-%m-%d %H:%M:%S")
            except:
                last_auth = datetime.now() - timedelta(hours=24)

            # 计算状态年龄
            state_age = datetime.now() - last_auth
            state_age_hours = state_age.total_seconds() / 3600

            # 计算剩余有效时间
            expires_in_hours = max(0, COOKIE_EXPIRY_THRESHOLD_HOURS - state_age_hours)

            # 确定状态
            if state_age_hours >= COOKIE_CRITICAL_THRESHOLD_HOURS:
                status = "critical"
                recommendation = "认证即将过期，请立即重新认证以确保 NotebookLM 正常工作"
                needs_reauth = True
            elif state_age_hours >= COOKIE_EXPIRY_THRESHOLD_HOURS:
                status = "warning"
                recommendation = "认证状态即将过期，建议重新认证"
                needs_reauth = False
            elif state_age_hours < 1:
                status = "healthy"
                recommendation = "认证状态良好"
                needs_reauth = False
            else:
                status = "healthy"
                recommendation = f"认证状态正常，预计 {expires_in_hours:.1f} 小时后建议重新认证"
                needs_reauth = False

            return AuthStatus(
                authenticated=True,
                state_age_hours=state_age_hours,
                last_auth=last_auth_str,
                expires_in_hours=expires_in_hours,
                status=status,
                recommendation=recommendation,
                needs_reauth=needs_reauth,
            )

        else:
            return AuthStatus(
                authenticated=False,
                state_age_hours=0,
                last_auth="Never",
                expires_in_hours=0,
                status="expired",
                recommendation="未找到认证状态文件，需要认证 NotebookLM",
                needs_reauth=True,
            )

    except Exception as e:
        return AuthStatus(
            authenticated=False,
            state_age_hours=0,
            last_auth="Error",
            expires_in_hours=0,
            status="error",
            recommendation=f"读取认证状态失败: {str(e)}",
            needs_reauth=True,
        )


def check_browser_state_freshness() -> dict:
    """
    检查浏览器状态文件的新鲜度

    Returns:
        dict: 浏览器状态信息
    """
    try:
        if BROWSER_STATE_FILE.exists():
            # 获取文件修改时间
            mtime = os.path.getmtime(BROWSER_STATE_FILE)
            mtime_dt = datetime.fromtimestamp(mtime)
            age = datetime.now() - mtime_dt
            age_hours = age.total_seconds() / 3600

            # 检查文件大小
            file_size = os.path.getsize(BROWSER_STATE_FILE)

            return {
                "exists": True,
                "last_modified": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "age_hours": age_hours,
                "size_bytes": file_size,
                "fresh": age_hours < COOKIE_EXPIRY_THRESHOLD_HOURS,
            }
        else:
            return {
                "exists": False,
                "last_modified": "Never",
                "age_hours": 0,
                "size_bytes": 0,
                "fresh": False,
            }
    except Exception as e:
        return {"exists": False, "error": str(e), "fresh": False}


@router.get("/status", response_model=AuthStatus)
async def get_authentication_status():
    """
    获取 NotebookLM 认证状态

    Returns:
        AuthStatus: 认证状态详情
    """
    return get_auth_status()


@router.get("/browser/state")
async def get_browser_state_info():
    """
    获取浏览器状态文件信息

    Returns:
        dict: 浏览器状态详情
    """
    return check_browser_state_freshness()


@router.post("/check")
async def check_and_notify():
    """
    检查认证状态并返回是否需要提醒

    Returns:
        dict: 检查结果和建议
    """
    auth_status = get_auth_status()
    browser_state = check_browser_state_freshness()

    return {
        "auth": auth_status,
        "browser": browser_state,
        "action_required": auth_status.needs_reauth or not browser_state.get("fresh", False),
        "notification": {
            "type": auth_status.status,
            "message": auth_status.recommendation,
            "priority": "high" if auth_status.status in ["critical", "expired"] else "normal",
        },
    }


@router.post("/auth/refresh-reminder")
async def set_refresh_reminder(hours: int = 24):
    """
    设置认证刷新提醒

    Args:
        hours: 提醒间隔（小时）

    Returns:
        dict: 提醒设置结果
    """
    # 创建提醒配置文件
    reminder_file = SKILL_DATA_DIR / "refresh_reminder.json"

    reminder_config = {
        "enabled": True,
        "interval_hours": hours,
        "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "next_reminder": (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with open(reminder_file, "w") as f:
            json.dump(reminder_config, f, indent=2)

        return {
            "success": True,
            "interval_hours": hours,
            "next_reminder": reminder_config["next_reminder"],
            "message": f"已设置 {hours} 小时后提醒重新认证",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "message": "设置提醒失败"}
