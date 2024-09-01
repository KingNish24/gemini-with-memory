import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key
from gemini import gemini_request, GeminiPlus
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.style import Style
from rich.traceback import install
from rich.text import Text

# Install rich traceback handler for better error messages
install()

# Load environment variables
load_dotenv()
console = Console()

API_KEY = None

# Global Styles
ERROR_STYLE = Style(color="red", bold=True)

def is_valid_json(json_string: str) -> bool:
    """Checks if a string is valid JSON."""
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False


def load_memory(filename: str) -> dict:
    """Loads memory from a JSON file, handling potential errors."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/] Invalid JSON in {filename}. Using empty memory.", style=ERROR_STYLE)
        return {}


def save_to_permanent_memory(data: dict) -> None:
    """Saves data to permanent memory (JSON file)."""
    try:
        with open("permanent_memory.json", "w") as f:
            json.dump(data, f, indent=4)  # Added indentation for readability
    except Exception as e:
        console.print(f"[bold red]Error:[/] Could not save to permanent memory: {e}", style=ERROR_STYLE)


def save_to_time_based_memory(data: dict) -> None:
    """Saves data to time-based memory (JSON file)."""
    try:
        with open("time_based_memory.json", "w") as f:
            json.dump(data, f, indent=4)  # Added indentation for readability
    except Exception as e:
        console.print(f"[bold red]Error:[/] Could not save to time-based memory: {e}", style=ERROR_STYLE)


def generate_response(user_input: str, gemini_plus_instance: GeminiPlus):
    """Generates a response from the Gemini model, updating memory and environment."""
    try:
        system_prompt = construct_system_prompt()
        gemini_plus_instance.system = system_prompt
        main_llm_response = gemini_plus_instance.send_message(user_input)
        for chunk in main_llm_response:
            yield chunk
        update_env('num_hist_memory', 1)
        update_env('num_conversations', 1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to generate response: {e}", style=ERROR_STYLE)
        yield "[bold red]Error:[/] Failed to generate response. Please try again later."


def construct_system_prompt() -> str:
    """Constructs the system prompt for the Gemini model, including memory information."""
    permanent_memory = load_memory("permanent_memory.json")
    time_based_memory = load_memory("time_based_memory.json")

    system_prompt = f"""You are Gemini, a powerful and knowledgeable assistant. Your task is to answer the user's query in the best possible way. 
    Analyze the user's query and answer it in a step-by-step manner if required, or in a structured manner. The current date and time is {datetime.now()}.
    You try your best to answer the user's query. Below is an explanation of more information about the user in the form of Memory given to you.
    There are two types of memory:

    **Permanent Memory:** This memory stores information that is always relevant and doesn't expire. It helps you understand the user better, their preferences, important facts, and frequently used information, allowing you to provide more personalized and relevant responses.
    Examples include:
        * User preferences
        * Important facts or knowledge about the user
        * Frequently used information

    **Time-Based Memory:** This memory stores information that is only relevant for a specific period.
    Examples include:
        * Reminders
        * Scheduled events
        * Time-sensitive information

    **Existing Memory:**"""

    if permanent_memory:
        system_prompt += "\n**Permanent Memory:**\n"
        for title, data in permanent_memory.items():
            system_prompt += f"- **{title}:** {data['compressed_info']}\n"
    if time_based_memory:
        system_prompt += "\n**Time-Based Memory:**\n"
        for title, data in time_based_memory.items():
            system_prompt += f"- **{title}:** {data['compressed_info']} (Expires: {data['expiry_time']})\n"

    return system_prompt


def extract_and_save_data(user_input: str) -> None:
    """Extracts data from user input using an LLM and saves it to memory."""
    try:
        system_prompt = construct_data_extraction_prompt()
        data_extraction_llm = gemini_request(input=user_input, system=system_prompt, response_type="text", API_KEY=API_KEY)

        try:
            start_index = data_extraction_llm.find('{')
            end_index = data_extraction_llm.rfind('}') + 1
            extracted_data = json.loads(data_extraction_llm[start_index:end_index])
            if "title" in extracted_data and "compressed_info" in extracted_data:
                if "expiry_time" in extracted_data:
                    try:
                        expiry_time = calculate_expiry_time(extracted_data["expiry_time"])
                        save_time_based_memory_entry(extracted_data, expiry_time)
                    except Exception as e:
                        console.print(f"[bold red]Error:[/] Invalid expiry time format: {e}", style=ERROR_STYLE)
                        save_permanent_memory_entry(extracted_data)  # Save as permanent if expiry time is invalid
                else:
                    save_permanent_memory_entry(extracted_data)
        except json.JSONDecodeError:
            console.print("[bold yellow]Warning:[/] Could not extract valid JSON from data extraction LLM response.", style=ERROR_STYLE)
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to extract and save data: {e}", style=ERROR_STYLE)


def construct_data_extraction_prompt() -> str:
    """Constructs the prompt for the data extraction LLM."""
    permanent_memory = load_memory("permanent_memory.json")
    time_based_memory = load_memory("time_based_memory.json")

    system_prompt = f"""You are a data extraction expert. Analyze the user's query and identify any relevant information 
    that should be saved to memory. There are two types of memory:

    **Permanent Memory:** This memory is for information that is always relevant and doesn't expire. This memory helps you understand the user better, their preferences, important facts, and frequently used information, allowing you to provide more personalized and relevant responses.
    Examples include:
        * User preferences
        * Important facts or knowledge about the user
        * Frequently used information

    **Time-Based Memory:** This memory is for information that is only relevant for a specific period.
    Examples include:
        * Reminders
        * Scheduled events
        * Time-sensitive information

    **Existing Memory:**
    """

    if permanent_memory:
        system_prompt += "\n**Permanent Memory:**\n"
        for title, data in permanent_memory.items():
            system_prompt += f"- **{title}:** {data['compressed_info']}\n"
    if time_based_memory:
        system_prompt += "\n**Time-Based Memory:**\n"
        for title, data in time_based_memory.items():
            system_prompt += f"- **{title}:** {data['compressed_info']} (Expires: {data['expiry_time']})\n"

    system_prompt += """

    **Instructions for saving data to memory:**

    * **Prioritize saving information that is directly relevant to the user or their requests.** This includes user preferences, important facts about them, and information that helps you understand their needs and context better.
    * **Avoid saving generic information or facts that are not directly related to the user.**
    * **Focus on information that will be useful for future interactions and providing personalized responses.**

    If no relevant information should be saved, reply with "Don't save to memory".

    If relevant information should be saved, determine the appropriate memory type and return your response in the following JSON format:

    ```json
    {
        "title": "Title of the data",
        "compressed_info": "Main data compressed into a short, Without grammer or anything, Just storing Important Data in Compressed Form",
        "importance": "Importance level (1-5), where 5 is most important",
        "relevance": "Relevance level (1-5), where 5 is most relevant",
        "expiry_time": "{ reply in json with minutes, hours, days, weeks, months which is good. Example: {"days": 2 } }" (use this format if time-based) 
    }
    ```
    You can use the existing memory to add more data to it or create new entries. Remember to prioritize providing a concise and informative `compressed_info` that captures the essence of the data.
    """

    return system_prompt


def calculate_expiry_time(expiry_time_data: dict) -> str:
    """Calculates the expiry time based on a dictionary of time units."""
    expiry_time = datetime.now()
    for key, value in expiry_time_data.items():
        if key == "minutes":
            expiry_time += timedelta(minutes=value)
        elif key == "hours":
            expiry_time += timedelta(hours=value)
        elif key == "days":
            expiry_time += timedelta(days=value)
        elif key == "weeks":
            expiry_time += timedelta(weeks=value)
        # Add more time units (months, years) as needed
    return expiry_time.isoformat()


def save_time_based_memory_entry(extracted_data: dict, expiry_time: str) -> None:
    """Saves an entry to time-based memory and cleans up expired entries."""
    time_based_memory = load_memory("time_based_memory.json")
    
    # Clean up expired entries
    current_time = datetime.now()
    keys_to_delete = []
    
    for title, data in time_based_memory.items():
        expiry_time_dt = datetime.fromisoformat(data["expiry_time"])
        if expiry_time_dt < current_time:
            keys_to_delete.append(title)
    
    for key in keys_to_delete:
        del time_based_memory[key]
    
    # Add the new entry
    time_based_memory[extracted_data["title"]] = {
        "compressed_info": extracted_data["compressed_info"],
        "importance": extracted_data["importance"],
        "relevance": extracted_data["relevance"],
        "expiry_time": expiry_time
    }
    
    # Save the updated memory
    save_to_time_based_memory(time_based_memory)


def save_permanent_memory_entry(extracted_data: dict) -> None:
    """Saves an entry to permanent memory."""
    permanent_memory = load_memory("permanent_memory.json")
    permanent_memory[extracted_data["title"]] = {
        "compressed_info": extracted_data["compressed_info"],
        "importance": extracted_data["importance"],
        "relevance": extracted_data["relevance"]
    }
    save_to_permanent_memory(permanent_memory)


def update_env(key: str, value: str) -> None:
    """Updates environment variables, triggering memory operations when thresholds are met."""
    try:
        if key in os.environ:
            key_value = os.environ[key]
            if key == 'num_hist_memory' and int(key_value) >= 1:
                key_value = 1
                extract_and_save_data(user_input)  # Extract and save data after each user input
            elif key == 'num_conversations' and int(key_value) >= 10:
                key_value = 0
                memory_compression()  # Compress memory after 10 conversations
            else:
                key_value = int(key_value) + int(value)
        else:
            key_value = value
        set_key(".env", key, str(key_value))
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to update environment variable: {e}", style=ERROR_STYLE)


def memory_compression() -> None:
    """Compresses memory by deduplicating and merging entries using an LLM."""
    try:
        permanent_memory = load_memory("permanent_memory.json")
        time_based_memory = load_memory("time_based_memory.json")

        memory_data_for_gemini = {
            "permanent_memory": permanent_memory,
            "time_based_memory": time_based_memory
        }

        system_prompt = """You are a data deduplication and merging expert. Your task is to analyze the provided memory data, eliminate duplicate entries, and merge similar information to create a more efficient dataset.

        **Data Deduplication:**
        Data deduplication involves identifying and removing redundant entries in a dataset. Retain only one unique copy of each entry, prioritizing the one with the highest `importance` level when duplicates are found.

        **Data Merging:**
        Data merging is the process of combining related information from multiple sources into a single, comprehensive entry. This enhances data representation and reduces redundancy.

        **Instructions:**

        1. **Deduplication:**
           - Analyze the `permanent_memory` and `time_based_memory` dictionaries.
           - Identify entries with identical `compressed_info` content. 
           - Retain the entry with the highest `importance` level and remove all other duplicates.

        2. **Merging:**
           - Identify entries with similar or related content across both memory types.
           - Merge parameters of similar entries into a new, comprehensive entry.
           - Create a new `compressed_info` that accurately reflects the merged data.
           - Assign appropriate `importance` and `relevance` levels to the merged entry.
           - If merging entries from different memory types, prioritize the `permanent_memory` entry in case of conflicting expiry times.

        3. **Output:**
           - Return the deduplicated and merged data in JSON format, maintaining the structure of `permanent_memory` and `time_based_memory`.

        **Goals:**
        - Enhance accuracy and speed of data processing.
        - Ensure a consolidated representation of information for better usability.
        """

        deduplication_llm = gemini_request(
            input=json.dumps(memory_data_for_gemini),
            system=system_prompt,
            response_type="json",
            API_KEY=API_KEY
        )

        try:
            deduplicated_data = json.loads(deduplication_llm)
            save_to_permanent_memory(deduplicated_data["permanent_memory"])
            save_to_time_based_memory(deduplicated_data["time_based_memory"])
        except json.JSONDecodeError:
            console.print("[bold yellow]Warning:[/] Could not extract valid JSON from memory compression LLM response.", style=ERROR_STYLE)
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to compress memory: {e}", style=ERROR_STYLE)


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
    while True:
        global user_input
        user_input = Prompt.ask("\n[bold #ADD8E6]You[/]")
        if user_input.lower() in ['exit', 'quit']:
            break
        response = ""
        with Live(screen=False, refresh_per_second=5) as live:
            for chunk in generate_response(user_input, gemini_instance):
                response += chunk
                live.update(Panel.fit(Markdown(response), title="[bold #90EE90]AI[/]", border_style="green"))


if __name__ == "__main__":
    run_chat()