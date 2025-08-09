#!/usr/bin/env python3
"""改进版的 Agent 主程序示例"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

from src.async_agent import AsyncAgentRuntime
from src.config import AgentConfig
from src.entities import EventType, Role

# Rich console for beautiful output
console = Console()

# Custom style for prompt
custom_style = Style.from_dict({
    'prompt': '#00aa00 bold',
    'prompt.prefix': '#008800',
})

class OutputLevel:
    MINIMAL = "minimal"
    NORMAL = "normal"
    VERBOSE = "verbose"

class ImprovedAgent:
    """改进版的 Agent 交互界面"""
    
    def __init__(self, project_root: Path, config: AgentConfig, output_level: str = OutputLevel.NORMAL):
        self.runtime = AsyncAgentRuntime(project_root, config)
        self.output_level = output_level
        self.session = PromptSession(
            history=FileHistory('.agent_history'),
            auto_suggest=AutoSuggestFromHistory(),
            style=custom_style,
            message=[
                ('class:prompt.prefix', '👤 '),
                ('class:prompt', 'User: '),
            ]
        )
        self.task_history = []
        
    def print_welcome(self):
        """打印美化的欢迎信息"""
        welcome_text = """
[bold cyan]FileSystem-based Agent[/bold cyan] - 增强交互模式
        
• 输入任务描述，Agent 会执行并回复
• 输入 'exit' 或 'quit' 退出
• 输入 'clear' 清空对话历史
• 输入 'help' 查看可用命令
• 输入 'status' 查看当前状态
• 输入 'history' 查看任务历史
• 使用 ↑↓ 浏览历史命令
• 按 Tab 自动完成
"""
        console.print(Panel(welcome_text, title="🤖 欢迎", border_style="cyan"))
        
    def print_help(self):
        """打印帮助信息表格"""
        table = Table(title="可用命令", show_header=True, header_style="bold magenta")
        table.add_column("命令", style="cyan", width=20)
        table.add_column("描述", style="white")
        
        commands = [
            ("exit/quit", "退出程序"),
            ("clear", "清空对话历史并重置 context"),
            ("help", "显示此帮助信息"),
            ("status", "显示当前 context 和文件系统状态"),
            ("history", "查看最近的任务历史"),
            ("output <level>", "设置输出级别 (minimal/normal/verbose)"),
            ("save <filename>", "保存当前对话到文件"),
            ("load <filename>", "从文件加载任务"),
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
            
        console.print(table)
        
    def print_status(self):
        """打印状态信息"""
        # Context 状态
        context_path = self.runtime.agent.path_manager.agent_root / self.runtime.agent.context_file
        if context_path.exists():
            context = context_path.read_text(encoding="utf-8")
            console.print(Panel(context, title="📄 Context Window", border_style="blue"))
        
        # 统计信息
        stats_table = Table(title="📊 统计信息", show_header=False)
        stats_table.add_column("指标", style="cyan")
        stats_table.add_column("值", style="yellow")
        
        stats_table.add_row("对话历史", f"{len(self.runtime.agent.conversation_history)} 条")
        stats_table.add_row("消息历史", f"{len(self.runtime.messages)} 条")
        stats_table.add_row("输入 Token", f"{self.runtime.total_usage.input_tokens:,}")
        stats_table.add_row("输出 Token", f"{self.runtime.total_usage.output_tokens:,}")
        stats_table.add_row("任务历史", f"{len(self.task_history)} 条")
        
        console.print(stats_table)
        
    def print_history(self):
        """打印任务历史"""
        if not self.task_history:
            console.print("[yellow]没有任务历史[/yellow]")
            return
            
        table = Table(title="📜 任务历史", show_header=True)
        table.add_column("时间", style="cyan")
        table.add_column("任务", style="white")
        table.add_column("状态", style="green")
        
        for task in self.task_history[-10:]:  # 最近10条
            table.add_row(
                task['time'].strftime("%H:%M:%S"),
                task['content'][:50] + "..." if len(task['content']) > 50 else task['content'],
                task['status']
            )
            
        console.print(table)
        
    def print_tool_call(self, tool_name: str, params: dict):
        """根据输出级别打印工具调用"""
        if self.output_level == OutputLevel.MINIMAL:
            console.print(f"[dim cyan]⚙️ {tool_name}[/dim cyan]")
        elif self.output_level == OutputLevel.VERBOSE:
            console.print(f"[cyan]⚙️ 调用工具: {tool_name}[/cyan]")
            console.print(json.dumps(params, indent=2, ensure_ascii=False))
        else:
            params_str = json.dumps(params, ensure_ascii=False)
            if len(params_str) > 100:
                params_str = params_str[:100] + "..."
            console.print(f"[cyan]⚙️ {tool_name}({params_str})[/cyan]")
            
    async def process_task(self, user_input: str):
        """处理单个任务"""
        task_start = datetime.now()
        
        # 记录任务
        task_record = {
            'time': task_start,
            'content': user_input,
            'status': 'processing'
        }
        self.task_history.append(task_record)
        
        # 使用进度条
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("[cyan]Processing...", total=None)
            
            try:
                console.print("\n[bold green]🤖 Agent:[/bold green] ", end="")
                
                async for event in self.runtime.invoke_stream(Role.User, user_input):
                    if event.type == EventType.Message and event.role == Role.Assistant:
                        if hasattr(event.content, "text"):
                            console.print(event.content.text, end="")
                    elif event.type == EventType.ToolUse:
                        if isinstance(event.content, list):
                            for tc in event.content:
                                self.print_tool_call(tc.name, tc.input)
                    elif event.type == EventType.Thinking and self.output_level == OutputLevel.VERBOSE:
                        if hasattr(event.content, "thinking"):
                            console.print(f"\n[dim yellow]🧠 思考: {event.content.thinking}[/dim yellow]")
                    elif event.type == EventType.Error:
                        console.print(f"\n[red]❌ 错误: {event.content.text}[/red]")
                        
                console.print()  # 确保换行
                task_record['status'] = 'completed'
                
            except Exception as e:
                console.print(f"\n[red]❌ 错误: {e}[/red]\n")
                task_record['status'] = 'failed'
                
    async def run_interactive(self):
        """运行交互式会话"""
        self.print_welcome()
        
        try:
            while True:
                # 使用 prompt_toolkit 获取输入
                user_input = await self.session.prompt_async()
                
                if not user_input.strip():
                    continue
                    
                # 处理命令
                cmd = user_input.lower().strip()
                
                if cmd in ["exit", "quit"]:
                    console.print("\n[yellow]👋 再见！[/yellow]")
                    break
                elif cmd == "clear":
                    # 清空对话历史
                    self.runtime.messages.clear()
                    console.print("[green]✅ 对话历史已清空[/green]\n")
                elif cmd == "help":
                    self.print_help()
                elif cmd == "status":
                    self.print_status()
                elif cmd == "history":
                    self.print_history()
                elif cmd.startswith("output "):
                    level = cmd.split()[1]
                    if level in [OutputLevel.MINIMAL, OutputLevel.NORMAL, OutputLevel.VERBOSE]:
                        self.output_level = level
                        console.print(f"[green]✅ 输出级别设置为: {level}[/green]")
                    else:
                        console.print("[red]❌ 无效的输出级别[/red]")
                else:
                    # 处理任务
                    await self.process_task(user_input)
                    
        except KeyboardInterrupt:
            console.print("\n\n[yellow]👋 再见！[/yellow]")
        except Exception as e:
            console.print(f"\n[red]❌ 发生错误: {e}[/red]")
            import traceback
            if self.output_level == OutputLevel.VERBOSE:
                traceback.print_exc()

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FileSystem-based Agent - 增强版")
    parser.add_argument('--output-level', choices=['minimal', 'normal', 'verbose'], 
                       default='normal', help='输出详细程度')
    parser.add_argument('--task', help='直接执行单个任务')
    parser.add_argument('--batch', help='从文件批量执行任务')
    parser.add_argument('--no-history', action='store_true', help='禁用历史记录')
    
    args = parser.parse_args()
    
    # 加载环境变量
    load_dotenv()
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]❌ 错误: 未找到 ANTHROPIC_API_KEY[/red]")
        console.print("\n请先配置 .env 文件：")
        console.print("1. cp .env.example .env")
        console.print("2. 编辑 .env 文件，填入你的 API Key")
        sys.exit(1)
        
    project_root = Path.cwd()
    config = AgentConfig.from_env()
    
    # 创建改进版 Agent
    agent = ImprovedAgent(project_root, config, args.output_level)
    
    # 根据参数执行不同模式
    if args.task:
        # 单任务模式
        await agent.process_task(args.task)
    elif args.batch:
        # 批处理模式
        batch_file = Path(args.batch)
        if batch_file.exists():
            tasks = batch_file.read_text().strip().split('\n')
            console.print(f"[cyan]执行 {len(tasks)} 个任务...[/cyan]")
            for i, task in enumerate(tasks, 1):
                if task.strip():
                    console.print(f"\n[bold]任务 {i}/{len(tasks)}:[/bold] {task}")
                    await agent.process_task(task.strip())
        else:
            console.print(f"[red]❌ 批处理文件不存在: {args.batch}[/red]")
    else:
        # 交互模式
        await agent.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())