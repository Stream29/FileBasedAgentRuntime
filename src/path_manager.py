"""Path management for the agent's file system."""

from pathlib import Path


class PathManager:
    """管理 Agent 的文件系统路径"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.agent_root = self.project_root / "agent_root"
        self.agent_root.mkdir(parents=True, exist_ok=True)

        # 创建基础目录结构
        self.workspace = self.agent_root / "workspace"
        self.storage = self.agent_root / "storage"

        # 创建子目录
        directories = [
            self.workspace,
            self.storage / "documents",
            self.storage / "few_shots",
            self.storage / "history",
        ]

        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)

    def resolve_agent_path(self, agent_path: str | Path) -> Path:
        """
        将 Agent 视角的路径转换为实际路径
        Args:
            agent_path: Agent 视角的路径，可以是绝对路径或相对路径

        Returns:
            实际的文件系统路径

        Raises:
            ValueError: 如果路径包含非法字符或尝试访问系统目录
        """
        agent_path = str(agent_path)

        # 安全检查：防止路径遍历攻击
        if ".." in agent_path:
            raise ValueError("Path traversal not allowed")

        # 安全检查：防止访问系统目录
        system_dirs = ["/etc", "/usr", "/home", "/var", "/tmp", "/root", "/bin", "/sbin"]
        for sys_dir in system_dirs:
            if agent_path.startswith(sys_dir):
                raise ValueError(f"Access to system directory {sys_dir} not allowed")

        # Agent 认为 /workspace 是根目录下的
        if agent_path.startswith("/"):
            # 绝对路径：相对于 agent_root
            relative_path = agent_path.lstrip("/")
            resolved_path = self.agent_root / relative_path
        else:
            # 相对路径：默认相对于 workspace
            resolved_path = self.workspace / agent_path

        # 确保解析后的路径在 agent_root 内
        try:
            resolved_path = resolved_path.resolve()
            if not str(resolved_path).startswith(str(self.agent_root)):
                raise ValueError("Path escapes agent root directory")
        except Exception:
            # 如果路径还不存在，至少确保其父路径在范围内
            parent = resolved_path.parent.resolve()
            if not str(parent).startswith(str(self.agent_root)):
                raise ValueError("Path escapes agent root directory") from None

        return resolved_path

    def get_relative_path(self, absolute_path: Path) -> str:
        """
        将实际路径转换为 Agent 视角的路径
        Args:
            absolute_path: 实际的文件系统路径

        Returns:
            Agent 视角的路径字符串
        """
        absolute_path = Path(absolute_path).resolve()

        # 如果路径在 agent_root 内，返回相对路径
        if str(absolute_path).startswith(str(self.agent_root)):
            relative = absolute_path.relative_to(self.agent_root)
            return "/" + str(relative)
        else:
            # 不在 agent_root 内的路径，返回原路径
            return str(absolute_path)
