"""Main entry point for the FileSystem-based Agent."""

# Use async implementation
from .async_main import main as async_main


def main() -> None:
    """Main entry point - redirects to async implementation"""
    async_main()


if __name__ == "__main__":
    main()
