import os
from dotenv import set_key, load_dotenv
from rich.console import Console
from rich.style import Style
from rich.traceback import install
import json

# Install rich traceback handler for better error messages
install()
load_dotenv()

# Global Styles
ERROR_STYLE = Style(color="red", bold=True)
WARNING_STYLE = Style(color="yellow", bold=True)
SUCCESS_STYLE = Style(color="green", bold=True) 

console = Console()

def update_env(key: str, value: str, user_input = None, API_KEY = None) -> None:
    """Updates environment variables, triggering memory operations when thresholds are met."""
    try:
        if key in os.environ:
            key_value = os.environ[key]
            if key == 'num_hist_memory' and int(key_value) >= 1:
                key_value = 1
                from memory import extract_and_save_data  # Import here to avoid circular dependency
                extract_and_save_data(user_input, API_KEY)  # Extract and save data after each user input
            elif key == 'num_conversations' and int(key_value) >= 10:
                key_value = 0
                from memory import memory_compression  # Import here to avoid circular dependency
                memory_compression(API_KEY)  # Compress memory after 10 conversations
            else:
                key_value = int(key_value) + int(value)
        else:
            key_value = value
        set_key(".env", key, str(key_value))
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to update environment variable: {e}", style=ERROR_STYLE)


def is_valid_json(json_string: str) -> bool:
    """Checks if a string is valid JSON."""
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False