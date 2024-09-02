import json
from datetime import datetime, timedelta
from rich.console import Console

from gemini import gemini_request  # Import from gemini.py
from utils import ERROR_STYLE  # Import from utils.py

console = Console()


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
        return {}


def save_to_permanent_memory(data: dict) -> None:
    """Saves data to permanent memory (JSON file)."""
    try:
        with open("permanent_memory.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        console.print(
            f"[bold red]Error:[/] Could not save to permanent memory: {e}",
            style=ERROR_STYLE,
        )


def save_to_time_based_memory(data: dict) -> None:
    """Saves data to time-based memory (JSON file)."""
    try:
        with open("time_based_memory.json", "w") as f:
            json.dump(data, f) 
    except Exception as e:
        console.print(
            f"[bold red]Error:[/] Could not save to time-based memory: {e}",
            style=ERROR_STYLE,
        )


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
            system_prompt += (
                f"- **{title}:** {data['compressed_info']} (Expires: {data['expiry_time']})\n"
            )

    return system_prompt


def extract_and_save_data(user_input: str, API_KEY = None) -> None:
    """Extracts data from user input using an LLM and saves it to memory."""
    try:
        system_prompt = construct_data_extraction_prompt()
        for chunk in gemini_request(input=user_input, system=system_prompt, response_type="text", API_KEY=API_KEY, stream=False ):
            data_extraction_llm = chunk

        try:
            start_index = data_extraction_llm.find("{")
            end_index = data_extraction_llm.rfind("}") + 1
            extracted_data = json.loads(data_extraction_llm[start_index:end_index])
            if "title" in extracted_data and "compressed_info" in extracted_data:
                if "expiry_time" in extracted_data:
                    try:
                        expiry_time = calculate_expiry_time(extracted_data["expiry_time"])
                        save_time_based_memory_entry(extracted_data, expiry_time)
                    except Exception as e:
                        save_permanent_memory_entry(
                            extracted_data
                        )  # Save as permanent if expiry time is invalid
                else:
                    save_permanent_memory_entry(extracted_data)
        except:
            pass
    except Exception as e:
        pass


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
            system_prompt += (
                f"- **{title}:** {data['compressed_info']} (Expires: {data['expiry_time']})\n"
            )

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
        "expiry_time": expiry_time,
    }

    # Save the updated memory
    save_to_time_based_memory(time_based_memory)


def save_permanent_memory_entry(extracted_data: dict) -> None:
    """Saves an entry to permanent memory."""
    permanent_memory = load_memory("permanent_memory.json")
    permanent_memory[extracted_data["title"]] = {
        "compressed_info": extracted_data["compressed_info"],
        "importance": extracted_data["importance"],
        "relevance": extracted_data["relevance"],
    }
    save_to_permanent_memory(permanent_memory)


def memory_compression(API_KEY = None) -> None:
    """Compresses memory by deduplicating and merging entries using an LLM."""
    try:
        permanent_memory = load_memory("permanent_memory.json")
        time_based_memory = load_memory("time_based_memory.json")

        memory_data_for_gemini = {
            "permanent_memory": permanent_memory,
            "time_based_memory": time_based_memory,
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
            API_KEY=API_KEY,
        )
        
        for chunk in deduplication_llm:
            deduplication_llm = chunk

        try:
            deduplicated_data = json.loads(deduplication_llm)
            save_to_permanent_memory(deduplicated_data["permanent_memory"])
            save_to_time_based_memory(deduplicated_data["time_based_memory"])
        except json.JSONDecodeError:
            pass
    except Exception as e:
        console.print(
            f"[bold red]Error:[/] Failed to compress memory: {e}", style=ERROR_STYLE
        )