#!/usr/bin/env python3
"""Demo script to showcase FileSystem-based Agent capabilities."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import FileSystemAgent


def demo_without_llm():
    """Demonstrate agent capabilities without LLM."""
    print("=== FileSystem-based Agent Demo ===\n")

    project_root = Path(__file__).parent
    agent = FileSystemAgent("demo", "context_window_main.md", project_root)

    # Demo 1: File operations
    print("📁 Demo 1: File Operations")
    print("-" * 40)

    # Create a project structure
    agent.execute_tool("write_file", {
        "file_path": "/workspace/project/main.py",
        "content": '''#!/usr/bin/env python3
"""A simple calculator module."""

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

if __name__ == "__main__":
    print(f"2 + 3 = {add(2, 3)}")
    print(f"4 * 5 = {multiply(4, 5)}")
'''
    })
    print("✓ Created main.py")

    agent.execute_tool("write_file", {
        "file_path": "/workspace/project/test_main.py",
        "content": '''import main

def test_add():
    assert main.add(2, 3) == 5
    assert main.add(-1, 1) == 0

def test_multiply():
    assert main.multiply(3, 4) == 12
    assert main.multiply(0, 5) == 0

if __name__ == "__main__":
    test_add()
    test_multiply()
    print("All tests passed!")
'''
    })
    print("✓ Created test_main.py")

    # List the project directory
    items = agent.execute_tool("list_directory", {"dir_path": "/workspace/project"})
    print(f"✓ Project contains {len(items)} files")

    # Demo 2: Command execution
    print("\n💻 Demo 2: Command Execution")
    print("-" * 40)

    # Run the main script
    result = agent.execute_tool("execute_command", {
        "command": "python main.py",
        "working_dir": "/workspace/project"
    })
    print("✓ Executed main.py")
    print(f"  Output: {result['stdout'].strip()}")

    # Run tests
    result = agent.execute_tool("execute_command", {
        "command": "python test_main.py",
        "working_dir": "/workspace/project"
    })
    print("✓ Executed tests")
    print(f"  Output: {result['stdout'].strip()}")

    # Demo 3: Context synchronization
    print("\n🔄 Demo 3: Context Synchronization")
    print("-" * 40)

    # Check conversation history size
    print(f"📊 Conversation history items: {len(agent.conversation_history)}")

    # Sync context
    sync_result = agent.execute_tool("sync_context", {})
    print("✓ Context synchronized")
    print(f"  Hot data items: {sync_result['hot_data_items']}")
    print(f"  Cold data archived: {sync_result['cold_data_archived']}")
    if sync_result['archive_path']:
        print(f"  Archive file: {sync_result['archive_path']}")

    # Check conversation history after sync
    print(f"📊 Conversation history after sync: {len(agent.conversation_history)}")

    # Demo 4: Context window content
    print("\n📄 Demo 4: Context Window")
    print("-" * 40)

    context_content = agent.execute_tool("read_file", {
        "file_path": "/context_window_main.md"
    })
    print("Current context window:")
    print("```")
    print(context_content)
    print("```")

    print("\n✨ Demo completed!")
    print("\n💡 To run with LLM:")
    print('   export ANTHROPIC_API_KEY=your_key')
    print('   uv run python -m src.main "Create a web scraper for weather data"')


if __name__ == "__main__":
    try:
        demo_without_llm()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
