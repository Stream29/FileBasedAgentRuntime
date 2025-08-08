#!/usr/bin/env python3
"""Basic test for the FileSystem-based Agent."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.file_system_agent import FileSystemAgent
from src.logger import OperationLogger
from src.path_manager import PathManager
from src.tools import ObservableTools


def test_components():
    """Test basic components functionality."""
    print("🔧 Testing basic components...\n")
    
    project_root = Path(__file__).parent
    
    # Test PathManager
    print("1. Testing PathManager...")
    pm = PathManager(project_root)
    assert pm.agent_root.exists()
    assert pm.workspace.exists()
    assert pm.storage.exists()
    
    # Test path resolution
    agent_path = pm.resolve_agent_path("/workspace/test.txt")
    assert str(agent_path).endswith("agent_root/workspace/test.txt")
    print("✓ PathManager working correctly\n")
    
    # Test Logger
    print("2. Testing Logger...")
    logger = OperationLogger(project_root / "logs")
    logger.log_operation("test_op", {"param": "value"}, "test result")
    print("✓ Logger working correctly\n")
    
    # Test ObservableTools
    print("3. Testing ObservableTools...")
    tools = ObservableTools(logger, pm)
    
    # Test write_file
    result = tools.write_file("/workspace/test.txt", "Hello, Agent!")
    assert result['path'] == "/workspace/test.txt"
    print("✓ write_file working")
    
    # Test read_file
    content = tools.read_file("/workspace/test.txt")
    assert content == "Hello, Agent!"
    print("✓ read_file working")
    
    # Test list_directory
    items = tools.list_directory("/workspace")
    assert any(item['name'] == 'test.txt' for item in items)
    print("✓ list_directory working")
    
    # Test execute_command
    result = tools.execute_command("echo 'Test command'")
    assert result['success']
    assert "Test command" in result['stdout']
    print("✓ execute_command working\n")
    
    # Test FileSystemAgent
    print("4. Testing FileSystemAgent...")
    agent = FileSystemAgent("test", "context_window_main.md", project_root)
    
    # Test tool execution
    result = agent.execute_tool("write_file", {
        "file_path": "/workspace/agent_test.txt",
        "content": "Agent test file"
    })
    assert result['path'] == "/workspace/agent_test.txt"
    print("✓ Agent tool execution working")
    
    # Test sync_context
    result = agent.execute_tool("sync_context", {})
    assert result['status'] == 'success'
    print("✓ sync_context working\n")
    
    print("🎉 All basic tests passed!")
    

def test_simple_task():
    """Test a simple task without LLM."""
    print("\n📝 Testing simple task workflow...\n")
    
    project_root = Path(__file__).parent
    agent = FileSystemAgent("test", "context_window_main.md", project_root)
    
    # Simulate a simple task
    print("1. Creating a Python script...")
    agent.execute_tool("write_file", {
        "file_path": "/workspace/hello.py",
        "content": """#!/usr/bin/env python3
print("Hello from the Agent!")
"""
    })
    
    print("2. Executing the script...")
    result = agent.execute_tool("execute_command", {
        "command": "python hello.py",
        "working_dir": "/workspace"
    })
    
    if result['success']:
        print(f"   Output: {result['stdout'].strip()}")
    else:
        print(f"   Error: {result['stderr']}")
        
    print("3. Syncing context...")
    sync_result = agent.execute_tool("sync_context", {})
    print(f"   Archived to: {sync_result.get('archive_path', 'None')}")
    
    print("\n✅ Simple task completed!")


if __name__ == "__main__":
    print("=== FileSystem-based Agent Basic Test ===\n")
    
    try:
        test_components()
        test_simple_task()
        
        print("\n✨ All tests completed successfully!")
        print("\nTo run the agent with Anthropic API:")
        print("1. Set ANTHROPIC_API_KEY environment variable")
        print('2. Run: uv run python -m src.main "your task here"')
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)