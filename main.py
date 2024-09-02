import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from rich.spinner import Spinner

from gemini import GeminiPlus  # Import from gemini.py
from memory import (  # Import from memory.py
    load_memory,
    save_to_permanent_memory,
    save_to_time_based_memory,
    construct_system_prompt,
    extract_and_save_data,
    memory_compression,
)
from utils import update_env, ERROR_STYLE

# Load environment variables
load_dotenv()
console = Console()

API_KEY = None

def run_chat(model="gemini-1.5-flash", GEMINI_API_KEY=None):
    """Main function to run the chat interface."""
    global API_KEY
    API_KEY = GEMINI_API_KEY
    
    gemini_instance = GeminiPlus(model_name=model, API_KEY=API_KEY)

    while True:
        # Create a table for the menu
        table = Table(title=Text("Chat Options", style="bold magenta"), border_style="green")

        # Add columns to the table
        table.add_column("Option", justify="center", style="cyan", no_wrap=True)
        table.add_column("Description", justify="left", style="white")

        # Add rows to the table
        table.add_row("1", "New Conversation")
        table.add_row("2", "Load Previous Conversation")
        table.add_row("3", "Temporary Conversation")
        table.add_row("4", "Delete Conversation")
        table.add_row("5", "Exit")

        # Print the table
        console.print(table)

        choice = Prompt.ask("\n[bold green]Enter your choice[/]", choices=["1", "2", "3", "4", "5"])

        if choice == '1':
            convo_name = Prompt.ask("[bold #FFA500]Enter conversation name[/]")
            gemini_instance.start_conversation(convo_name)
            chat_loop(gemini_instance)
        elif choice == '2':
            sorted_convos = gemini_instance.display_conversation_list()
            if sorted_convos:
                with Live(Spinner("dots", "Loading conversations..."), screen=True, refresh_per_second=10) as live:
                    live.update(Panel.fit(
                        "\n".join([f"{i+1}. {convo}" for i, convo in enumerate(sorted_convos)]),
                        title="Previous Conversations",
                        border_style="blue"
                    ))
                try:
                    choice = int(Prompt.ask("Choose a conversation by number", choices=[str(i) for i in range(1, len(sorted_convos) + 1)])) - 1
                    if 0 <= choice < len(sorted_convos):
                        gemini_instance.start_conversation(sorted_convos[choice])
                        chat_loop(gemini_instance)
                    else:
                        console.print("[bold red]Invalid choice. Please try again.[/]", style=ERROR_STYLE)
                except ValueError:
                    console.print("[bold red]Invalid input. Please enter a number.[/]", style=ERROR_STYLE)
            else:
                console.print("[bold red]No previous conversations found.[/]", style=ERROR_STYLE)
        elif choice == '3':
            gemini_instance.start_temp_conversation()
            chat_loop(gemini_instance)
        elif choice == '4':
            sorted_convos = gemini_instance.display_conversation_list()
            if sorted_convos:
                with Live(Spinner("dots", "Loading conversations..."), screen=True, refresh_per_second=10) as live:
                    live.update(Panel.fit(
                        "\n".join([f"{i+1}. {convo}" for i, convo in enumerate(sorted_convos)]),
                        title="Previous Conversations",
                        border_style="blue"
                    ))
                try:
                    choice = int(Prompt.ask("Choose a conversation to delete by number", choices=[str(i) for i in range(1, len(sorted_convos) + 1)])) - 1
                    if 0 <= choice < len(sorted_convos):
                        if Confirm.ask(f"Are you sure you want to delete '{sorted_convos[choice]}'?"):
                            gemini_instance.delete_conversation(sorted_convos[choice])
                            console.print("[bold green]Conversation deleted successfully![/]")
                    else:
                        console.print("[bold red]Invalid choice. Please try again.[/]", style=ERROR_STYLE)
                except ValueError:
                    console.print("[bold red]Invalid input. Please enter a number.[/]", style=ERROR_STYLE)
            else:
                console.print("[bold red]No previous conversations found.[/]", style=ERROR_STYLE)
        elif choice == '5':
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/]", style=ERROR_STYLE)


def chat_loop(gemini_instance: GeminiPlus):
    """Handles the main chat loop within a conversation."""
    console.print("\n[bold #a276ff]Enter 'exit' or 'quit' to go back to main menu[/]")
    while True:
        global user_input
        user_input = Prompt.ask("\n[bold #ADD8E6]You[/]")
        if user_input.lower() in ['exit', 'quit']:
            break
        response = ""
        with Live(screen=False, refresh_per_second=5) as live:
            system_prompt = construct_system_prompt()
            gemini_instance.system = system_prompt
            main_llm_response = gemini_instance.send_message(user_input)
            for chunk in main_llm_response:
                response += chunk
                live.update(Panel.fit(Markdown(response), title="[bold #90EE90]AI[/]", border_style="green"))
        update_env('num_hist_memory', 1, user_input, API_KEY)
        update_env('num_conversations', 1 , API_KEY=API_KEY)


if __name__ == "__main__":
    run_chat()