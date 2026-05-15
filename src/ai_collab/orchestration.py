"""
Agent Orchestration Module - Cold Start Detection & Configuration Management

This module handles:
- Cold start detection and wizard
- Agent provider detection
- Dynamic role binding management
- Orchestration configuration operations
"""

import json
import os
import shutil
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class BindingStatus(Enum):
    """Orchestration binding status levels"""
    UNINITIALIZED = "uninitialized"
    MINIMAL = "minimal"
    PARTIAL = "partial"
    ACTIVE = "active"


class StartupMode(Enum):
    """Startup mode options"""
    SINGLE_AGENT = "single_agent"
    SUB_AGENT = "sub_agent"
    MULTI_AGENT = "multi_agent"


class RoleStatus(Enum):
    """Role activation status"""
    ACTIVE = "active"
    DORMANT = "dormant"
    DISABLED = "disabled"


class ProviderConnectionStatus(Enum):
    """Provider connection status"""
    CONNECTED = "connected"
    DETECTED = "detected"
    UNAVAILABLE = "unavailable"


class AgentProvider:
    """Agent provider information"""

    PROVIDER_DETECTORS = {
        "claude_code": {
            "name": "Claude Code",
            "check_command": None,  # CLI integrated, always available when running
            "supports_sub_agent": True,
            "model_variants": ["opus", "sonnet", "haiku"],
            "capabilities": ["implementation", "refactoring", "testing", "architecture", "documentation"]
        },
        "codex_cli": {
            "name": "Codex CLI",
            "check_command": "which codex",
            "supports_sub_agent": False,
            "model_variants": [],
            "capabilities": ["architecture", "research", "implementation"]
        },
        "gemini_cli": {
            "name": "Gemini CLI",
            "check_command": "which gemini",
            "supports_sub_agent": False,
            "model_variants": [],
            "capabilities": ["research", "testing"]
        },
        "codearts_agent": {
            "name": "CodeArts Agent",
            "check_command": None,  # VSCode extension, check via environment
            "supports_sub_agent": False,
            "model_variants": [],
            "capabilities": ["testing", "documentation", "validation"]
        }
    }

    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.name = config.get("name", provider_id)
        self.connection_status = ProviderConnectionStatus.UNAVAILABLE
        self.supports_sub_agent = config.get("supports_sub_agent", False)
        self.model_variants = config.get("model_variants", [])
        self.capabilities = config.get("capabilities", [])
        self.last_check: Optional[datetime] = None

    def check_availability(self) -> bool:
        """Check if provider is available"""
        config = self.PROVIDER_DETECTORS.get(self.provider_id, {})
        check_command = config.get("check_command")

        # Claude Code is always available when this code is running
        if self.provider_id == "claude_code":
            self.connection_status = ProviderConnectionStatus.CONNECTED
            self.last_check = datetime.now()
            return True

        # CodeArts Agent - check environment
        if self.provider_id == "codearts_agent":
            # Check for VSCode extension environment
            if os.environ.get("VSCODE_PID") or os.environ.get("CODEARTS_SESSION"):
                self.connection_status = ProviderConnectionStatus.CONNECTED
                self.last_check = datetime.now()
                return True
            self.connection_status = ProviderConnectionStatus.UNAVAILABLE
            self.last_check = datetime.now()
            return False

        # CLI-based providers - check command
        if check_command:
            try:
                result = subprocess.run(
                    check_command,
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.connection_status = ProviderConnectionStatus.DETECTED
                    self.last_check = datetime.now()
                    return True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

        self.connection_status = ProviderConnectionStatus.UNAVAILABLE
        self.last_check = datetime.now()
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "provider_name": self.name,
            "connection_status": self.connection_status.value,
            "supports_sub_agent": self.supports_sub_agent,
            "model_variants": self.model_variants,
            "capabilities": self.capabilities,
            "last_check": self.last_check.isoformat() if self.last_check else None
        }


class OrchestrationRole:
    """Role definition with binding"""

    def __init__(
        self,
        role_id: str,
        display_name: str,
        duties: List[str],
        required_capabilities: List[str],
        raci_role: str = "C",
        binding: Optional[Dict[str, Any]] = None
    ):
        self.role_id = role_id
        self.display_name = display_name
        self.duties = duties
        self.required_capabilities = required_capabilities
        self.raci_role = raci_role
        self.binding = binding or {
            "provider": None,
            "model_variant": None,
            "status": RoleStatus.DORMANT.value
        }
        self.created_at: Optional[datetime] = None
        self.activated_at: Optional[datetime] = None

    def is_active(self) -> bool:
        """Check if role is active"""
        return self.binding.get("status") == RoleStatus.ACTIVE.value

    def activate(self, provider: str, model_variant: Optional[str] = None):
        """Activate role with provider binding"""
        self.binding["provider"] = provider
        self.binding["model_variant"] = model_variant
        self.binding["status"] = RoleStatus.ACTIVE.value
        self.activated_at = datetime.now()

    def deactivate(self):
        """Deactivate role"""
        self.binding["status"] = RoleStatus.DORMANT.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "role_id": self.role_id,
            "display_name": self.display_name,
            "duties": self.duties,
            "required_capabilities": self.required_capabilities,
            "binding": self.binding,
            "raci_role": self.raci_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None
        }


class OrchestrationConfig:
    """Agent orchestration configuration manager"""

    DEFAULT_ROLES = {
        "AGENT_EXEC": {
            "display_name": "主执行者",
            "duties": ["代码实现", "重构", "Bug修复"],
            "required_capabilities": ["implementation", "refactoring"],
            "raci_role": "R"
        },
        "AGENT_ARCH": {
            "display_name": "架构师",
            "duties": ["架构设计", "技术选型", "代码审查"],
            "required_capabilities": ["architecture", "design"],
            "raci_role": "A"
        },
        "AGENT_TEST": {
            "display_name": "测试验证",
            "duties": ["单元测试", "集成测试", "质量保证"],
            "required_capabilities": ["testing", "validation"],
            "raci_role": "C"
        }
    }

    DEFAULT_COMMAND_PREFIXES = {
        "A.RUN": "AGENT_ARCH",
        "X.RUN": "AGENT_EXEC",
        "C.RUN": "AGENT_TEST"
    }

    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = workspace_path or os.getcwd()
        self.config_dir = os.path.join(self.workspace_path, "config")
        self.config_file = os.path.join(self.config_dir, "agent-orchestration.json")
        self.template_file = os.path.join(self.config_dir, "agent-orchestration.template.json")

        self.config: Dict[str, Any] = {}
        self.providers: Dict[str, AgentProvider] = {}
        self.roles: Dict[str, OrchestrationRole] = {}

        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)

    def load(self) -> bool:
        """Load orchestration configuration"""
        if not os.path.exists(self.config_file):
            # Try to copy from template
            if os.path.exists(self.template_file):
                shutil.copy(self.template_file, self.config_file)
            else:
                # Create default config
                self._create_default_config()

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            # Parse roles
            for role_id, role_data in self.config.get("roles", {}).items():
                role = OrchestrationRole(
                    role_id=role_id,
                    display_name=role_data.get("display_name", role_id),
                    duties=role_data.get("duties", []),
                    required_capabilities=role_data.get("required_capabilities", []),
                    raci_role=role_data.get("raci_role", "C"),
                    binding=role_data.get("binding")
                )
                if role_data.get("created_at"):
                    role.created_at = datetime.fromisoformat(role_data["created_at"])
                if role_data.get("activated_at"):
                    role.activated_at = datetime.fromisoformat(role_data["activated_at"])
                self.roles[role_id] = role

            # Parse providers
            for provider_id, provider_data in self.config.get("provider_registry", {}).items():
                provider = AgentProvider(provider_id, provider_data)
                if provider_data.get("last_check"):
                    provider.last_check = datetime.fromisoformat(provider_data["last_check"])
                provider.connection_status = ProviderConnectionStatus(
                    provider_data.get("connection_status", "unavailable")
                )
                self.providers[provider_id] = provider

            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return False

    def save(self) -> bool:
        """Save orchestration configuration"""
        try:
            # Update config dict from objects
            self.config["roles"] = {
                role_id: role.to_dict()
                for role_id, role in self.roles.items()
            }
            self.config["provider_registry"] = {
                provider_id: provider.to_dict()
                for provider_id, provider in self.providers.items()
            }

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def _create_default_config(self):
        """Create default configuration"""
        now = datetime.now().isoformat()

        roles = {}
        for role_id, role_def in self.DEFAULT_ROLES.items():
            role = OrchestrationRole(
                role_id=role_id,
                display_name=role_def["display_name"],
                duties=role_def["duties"],
                required_capabilities=role_def["required_capabilities"],
                raci_role=role_def["raci_role"]
            )
            role.created_at = datetime.now()
            roles[role_id] = role

        self.roles = roles

        self.config = {
            "version": "2.0.0",
            "binding_status": BindingStatus.UNINITIALIZED.value,
            "startup_mode": None,
            "roles": {role_id: role.to_dict() for role_id, role in roles.items()},
            "command_prefixes": {
                **self.DEFAULT_COMMAND_PREFIXES,
                "custom_prefixes": {},
                "custom_allowed": True,
                "history_compatible": True
            },
            "provider_registry": {},
            "runtime_policy": {
                "allow_hot_reload": True,
                "require_confirmation": True,
                "snapshot_before_change": True,
                "max_roles": 10,
                "auto_activate_dormant": False
            },
            "snapshots": [],
            "history": [],
            "cold_start_config": {
                "initialized_at": None,
                "initial_provider": None,
                "initial_mode": None,
                "wizard_completed": False
            }
        }

        self.save()

    def get_binding_status(self) -> BindingStatus:
        """Get current binding status"""
        return BindingStatus(self.config.get("binding_status", "uninitialized"))

    def update_binding_status(self):
        """Update binding status based on role activations"""
        active_count = sum(1 for role in self.roles.values() if role.is_active())
        total_count = len(self.roles)

        if active_count == 0:
            status = BindingStatus.UNINITIALIZED
        elif active_count == 1:
            status = BindingStatus.MINIMAL
        elif active_count < total_count:
            status = BindingStatus.PARTIAL
        else:
            status = BindingStatus.ACTIVE

        self.config["binding_status"] = status.value

    def is_cold_start_needed(self) -> bool:
        """Check if cold start is needed"""
        status = self.get_binding_status()
        return status == BindingStatus.UNINITIALIZED or \
               not self.config.get("cold_start_config", {}).get("wizard_completed", False)

    def detect_providers(self) -> Dict[str, AgentProvider]:
        """Detect available agent providers"""
        self.providers = {}

        for provider_id, config in AgentProvider.PROVIDER_DETECTORS.items():
            provider = AgentProvider(provider_id, config)
            provider.check_availability()
            self.providers[provider_id] = provider

        return self.providers

    def get_available_providers(self) -> List[AgentProvider]:
        """Get list of available providers"""
        return [
            provider for provider in self.providers.values()
            if provider.connection_status in [
                ProviderConnectionStatus.CONNECTED,
                ProviderConnectionStatus.DETECTED
            ]
        ]

    def add_history_event(self, event: str, details: Dict[str, Any]):
        """Add event to history"""
        self.config["history"].append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details
        })

    def create_snapshot(self, trigger: str = "manual", note: str = "") -> str:
        """Create configuration snapshot"""
        snapshot_id = f"snap_{len(self.config.get('snapshots', [])) + 1:03d}"

        snapshot = {
            "snapshot_id": snapshot_id,
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger,
            "note": note,
            "config_copy": json.loads(json.dumps(self.config))  # Deep copy
        }

        self.config.setdefault("snapshots", []).append(snapshot)
        self.add_history_event("snapshot_created", {"snapshot_id": snapshot_id, "trigger": trigger})

        return snapshot_id

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """Rollback to a specific snapshot"""
        snapshots = self.config.get("snapshots", [])
        target_snapshot = None

        for snapshot in snapshots:
            if snapshot["snapshot_id"] == snapshot_id:
                target_snapshot = snapshot
                break

        if not target_snapshot:
            return False

        # Create pre-rollback snapshot
        self.create_snapshot(trigger="auto_before_change", note="Pre-rollback backup")

        # Restore config
        self.config = target_snapshot["config_copy"]
        self.save()

        self.add_history_event("rollback_executed", {"target_snapshot": snapshot_id})

        return True

    def get_role_for_command(self, command_prefix: str) -> Optional[OrchestrationRole]:
        """Get role for a command prefix"""
        command_prefixes = self.config.get("command_prefixes", {})

        # Check standard prefixes
        role_id = command_prefixes.get(command_prefix)

        # Check custom prefixes
        if not role_id:
            custom_prefixes = command_prefixes.get("custom_prefixes", {})
            role_id = custom_prefixes.get(command_prefix)

        if role_id:
            return self.roles.get(role_id)

        return None

    def add_role(
        self,
        role_id: str,
        display_name: str,
        duties: List[str],
        required_capabilities: List[str],
        raci_role: str = "C"
    ) -> OrchestrationRole:
        """Add a new role"""
        role = OrchestrationRole(
            role_id=role_id,
            display_name=display_name,
            duties=duties,
            required_capabilities=required_capabilities,
            raci_role=raci_role
        )
        role.created_at = datetime.now()

        self.roles[role_id] = role
        self.add_history_event("role_added", {"role_id": role_id})

        return role

    def activate_role(self, role_id: str, provider: str, model_variant: Optional[str] = None):
        """Activate a role with provider binding"""
        role = self.roles.get(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")

        # Create snapshot before change if enabled
        if self.config.get("runtime_policy", {}).get("snapshot_before_change", True):
            self.create_snapshot(trigger="auto_before_change", note=f"Before activating {role_id}")

        role.activate(provider, model_variant)
        self.update_binding_status()

        self.add_history_event("role_activated", {
            "role_id": role_id,
            "provider": provider,
            "model_variant": model_variant
        })

    def set_startup_mode(self, mode: StartupMode):
        """Set startup mode"""
        self.config["startup_mode"] = mode.value
        self.add_history_event("mode_switched", {"new_mode": mode.value})

    def complete_cold_start(self, initial_provider: str, mode: StartupMode):
        """Complete cold start wizard"""
        self.config["cold_start_config"] = {
            "initialized_at": datetime.now().isoformat(),
            "initial_provider": initial_provider,
            "initial_mode": mode.value,
            "wizard_completed": True
        }

        self.add_history_event("cold_start", {
            "initial_provider": initial_provider,
            "mode": mode.value
        })

        self.save()


class ColdStartWizard:
    """Cold start wizard for initial configuration"""

    def __init__(self, config: OrchestrationConfig):
        self.config = config

    def run(self) -> bool:
        """Run cold start wizard"""
        print("=" * 60)
        print("🚀 AI Collab Base - 冷启动配置")
        print("=" * 60)

        # Step 1: Detect providers
        print("\n[步骤 1] 检测可用 Agent 服务商...")
        providers = self.config.detect_providers()

        available = self.config.get_available_providers()

        if not available:
            print("\n⚠️  未检测到可用的 Agent 服务商")
            print("请确保至少有一个 Agent 服务商可用")
            print("支持的检测方式:")
            print("  - Claude Code: 自动检测（当前已运行）")
            print("  - Codex CLI: 检查 'codex' 命令")
            print("  - Gemini CLI: 检查 'gemini' 命令")
            print("  - CodeArts Agent: 检查 VSCode 环境")
            return False

        print(f"\n检测到 {len(available)} 个可用服务商:")
        for provider in available:
            status_icon = "✓" if provider.connection_status == ProviderConnectionStatus.CONNECTED else "○"
            sub_agent_info = " (支持 SubAgent)" if provider.supports_sub_agent else ""
            print(f"  {status_icon} {provider.name}{sub_agent_info}")

        # Step 2: Select startup mode
        print("\n[步骤 2] 选择启动模式:")
        print("  [1] 单 Agent 模式 - 使用单个 Agent 承担所有活跃角色")
        print("  [2] SubAgent 模式 - 单 Agent 内部模型变体分工")
        print("  [3] 多 Agent 模式 - 稍后通过 /menu 逐个添加服务商")

        mode_choice = input("\n请选择模式 (1-3): ").strip()

        mode_map = {
            "1": StartupMode.SINGLE_AGENT,
            "2": StartupMode.SUB_AGENT,
            "3": StartupMode.MULTI_AGENT
        }

        selected_mode = mode_map.get(mode_choice)
        if not selected_mode:
            print("无效选择，默认使用单 Agent 模式")
            selected_mode = StartupMode.SINGLE_AGENT

        # Step 3: Configure bindings
        print(f"\n[步骤 3] 配置角色绑定 ({selected_mode.value})")

        initial_provider = available[0].provider_id

        if selected_mode == StartupMode.SINGLE_AGENT:
            # Single agent takes EXEC role
            print(f"\n单 Agent 模式: {available[0].name} 将承担主执行角色")
            print("其他角色保持休眠状态，可通过 /menu 随时激活")

            self.config.activate_role("AGENT_EXEC", initial_provider)

        elif selected_mode == StartupMode.SUB_AGENT:
            # SubAgent mode - ask for variant mapping
            provider = available[0]
            if not provider.supports_sub_agent:
                print(f"\n⚠️  {provider.name} 不支持 SubAgent 模式")
                print("切换到单 Agent 模式")
                self.config.activate_role("AGENT_EXEC", initial_provider)
                selected_mode = StartupMode.SINGLE_AGENT
            else:
                print(f"\nSubAgent 模式配置 ({provider.name}):")
                print("可用模型变体:")
                for variant in provider.model_variants:
                    print(f"  - {variant}")

                # Map roles to variants
                default_mapping = {
                    "AGENT_ARCH": "opus",
                    "AGENT_EXEC": "sonnet",
                    "AGENT_TEST": "haiku"
                }

                for role_id in ["AGENT_EXEC", "AGENT_ARCH", "AGENT_TEST"]:
                    variant = default_mapping.get(role_id, provider.model_variants[0])
                    print(f"\n{role_id} → {variant}")
                    self.config.activate_role(role_id, initial_provider, variant)

        elif selected_mode == StartupMode.MULTI_AGENT:
            # Multi agent - activate EXEC only, others via /menu
            print(f"\n多 Agent 模式: {available[0].name} 作为主执行者")
            print("其他角色可通过 /menu 绑定到其他服务商")

            self.config.activate_role("AGENT_EXEC", initial_provider)

        # Step 4: Configure command prefixes
        print("\n[步骤 4] 命令前缀配置:")
        prefixes = self.config.config.get("command_prefixes", {})
        print(f"  A.RUN → {prefixes.get('A.RUN', 'AGENT_ARCH')}")
        print(f"  X.RUN → {prefixes.get('X.RUN', 'AGENT_EXEC')}")
        print(f"  C.RUN → {prefixes.get('C.RUN', 'AGENT_TEST')}")

        customize = input("\n是否自定义命令前缀? (y/n): ").strip().lower()
        if customize == "y":
            self._customize_prefixes()

        # Complete cold start
        self.config.set_startup_mode(selected_mode)
        self.config.complete_cold_start(initial_provider, selected_mode)

        print("\n" + "=" * 60)
        print("✓ 冷启动配置完成!")
        print("=" * 60)
        print(f"\n当前状态:")
        print(f"  模式: {selected_mode.value}")
        print(f"  绑定状态: {self.config.get_binding_status().value}")

        active_roles = [r for r in self.config.roles.values() if r.is_active()]
        print(f"  活跃角色: {len(active_roles)}")
        for role in active_roles:
            provider_info = role.binding.get("provider", "")
            variant_info = role.binding.get("model_variant", "")
            variant_display = f" ({variant_info})" if variant_info else ""
            print(f"    - {role.display_name} → {provider_info}{variant_display}")

        print("\n下一步:")
        print("  - 开始任务执行: 使用 X.RUN 命令")
        print("  - 调整配置: 输入 /menu 打开控制面板")
        print("  - 添加更多服务商: /menu → [2] Agent 绑定 → [接入新 Agent]")

        return True

    def _customize_prefixes(self):
        """Customize command prefixes"""
        print("\n自定义命令前缀:")
        print("输入新的映射，或按 Enter 保持当前值")

        prefixes = self.config.config.get("command_prefixes", {})
        roles = list(self.config.roles.keys())

        for prefix in ["A.RUN", "X.RUN", "C.RUN"]:
            current = prefixes.get(prefix, "")
            new_mapping = input(f"  {prefix} (当前: {current}): ").strip()

            if new_mapping and new_mapping in roles:
                prefixes[prefix] = new_mapping
                self.config.add_history_event("command_redefined", {
                    "prefix": prefix,
                    "old_mapping": current,
                    "new_mapping": new_mapping
                })

        # Ask for custom prefixes
        add_custom = input("\n是否添加自定义命令前缀? (y/n): ").strip().lower()
        if add_custom == "y":
            while True:
                custom_prefix = input("  命令前缀 (如 PERF.RUN): ").strip()
                if not custom_prefix:
                    break

                print(f"  可选角色: {', '.join(roles)}")
                role_mapping = input(f"  {custom_prefix} → ").strip()

                if role_mapping in roles:
                    prefixes.setdefault("custom_prefixes", {})[custom_prefix] = role_mapping
                    self.config.add_history_event("command_redefined", {
                        "prefix": custom_prefix,
                        "mapping": role_mapping
                    })


def check_cold_start(workspace_path: Optional[str] = None) -> Optional[ColdStartWizard]:
    """Check if cold start is needed and return wizard if so"""
    config = OrchestrationConfig(workspace_path)
    config.load()

    if config.is_cold_start_needed():
        return ColdStartWizard(config)

    return None


def get_orchestration_config(workspace_path: Optional[str] = None) -> OrchestrationConfig:
    """Get orchestration configuration (load or create)"""
    config = OrchestrationConfig(workspace_path)
    config.load()
    return config