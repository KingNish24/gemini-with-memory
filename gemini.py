import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


def gemini_request(input="", system="Answer in detail", model_name="gemini-1.5-flash",
                   max_tokens=8192, response_type="text", history=[], stream=False):
    response_type = "application/json" if response_type == "json" else "text/plain"
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": max_tokens,
        "response_mime_type": response_type,
    }
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=system, 
    )
    chat_session = model.start_chat(history=history)
    if stream:
        response = chat_session.send_message(input ,stream=True)
        for chunk in response:
            yield chunk.text
    else:
        response = chat_session.send_message(input)
        return response.text


class GeminiPlus:
    def __init__(self, model_name="gemini-1.5-flash", system="Answer in detail",
                 max_tokens=8192, response_type="text"):
        self.model_name = model_name
        self.system = system
        self.chat_histories = self.load_chat_histories('chat_histories.json')
        self.current_convo_name = None
        self.max_tokens = max_tokens
        self.response_type = "application/json" if response_type == "json" else "text/plain"
        self.convo_timestamps = {}

    @staticmethod
    def load_chat_histories(filename):
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_chat_histories(filename, histories):
        with open(filename, 'w') as file:
            json.dump(histories, file)

    def start_conversation(self, convo_name):
        self.current_convo_name = convo_name
        self.chat_history = self.chat_histories.get(convo_name, [])
        self.update_conversation_timestamp(convo_name)

    def start_temp_conversation(self):
        self.current_convo_name = "temporary"
        self.chat_history = []

    def update_conversation_timestamp(self, convo_name):
        self.convo_timestamps[convo_name] = datetime.now().isoformat()

    def display_conversation_list(self):
        if not self.chat_histories:
            print("No previous conversations found.")
            return []

        sorted_convos = sorted(self.chat_histories.keys(),
                               key=lambda x: self.convo_timestamps.get(x, "1970-01-01T00:00:00"),
                               reverse=True)
        print("Available conversations:")
        for index, convo in enumerate(sorted_convos):
            print(f"{index + 1}: {convo}")
        return sorted_convos

    def send_message(self, user_input):
        if self.current_convo_name is None:
            return "Please start a conversation first."

        try:
            response_text = gemini_request(user_input, system=self.system,
                                          model_name=self.model_name, max_tokens=self.max_tokens,
                                          response_type=self.response_type, history=self.chat_history, stream=True)
            response_history = ""
            for chunk in response_text:
                response_history += chunk
                yield chunk

            if self.current_convo_name != "temporary":
                self.chat_history.append({"role": "user", "parts": [user_input]})
                self.chat_history.append({"role": "model", "parts": [response_history]})
                self.chat_histories[self.current_convo_name] = self.chat_history
                self.save_chat_histories('chat_histories.json', self.chat_histories)
                self.update_conversation_timestamp(self.current_convo_name)
        except Exception as e:
            print(f"Error sending message: {e}")
            return "Sorry, there was an error processing your request."
        
    def delete_conversation(self, convo_name):
        if convo_name in self.chat_histories:
            del self.chat_histories[convo_name]
            if convo_name in self.convo_timestamps:
                del self.convo_timestamps[convo_name]
            self.save_chat_histories('chat_histories.json', self.chat_histories)
            print(f"Conversation '{convo_name}' deleted successfully.")
        else:
            print(f"Conversation '{convo_name}' not found.")


def run_chat():
    gemini_instance = GeminiPlus(model_name="gemini-1.5-flash")
    while True:
        convo_name = input("Enter conversation name (or type 'old' to choose from history, 'temp' for temporary chat): ")
        if convo_name.lower() in ['exit', 'quit']:
            break
        elif convo_name.lower() == 'old':
            sorted_convos = gemini_instance.display_conversation_list()
            if sorted_convos:
                try:
                    choice = int(input("Choose a conversation by number: ")) - 1
                    if 0 <= choice < len(sorted_convos):
                        gemini_instance.start_conversation(sorted_convos[choice])
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        elif convo_name.lower() == 'temp':
            gemini_instance.start_temp_conversation()
        else:
            if convo_name:
                gemini_instance.start_conversation(convo_name)
            else:
                gemini_instance.start_temp_conversation()

        while True:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            response_text = gemini_instance.send_message(user_input)
            print(f"Bot: ", end="")
            for chunk in response_text:
                print(chunk, end="")


if __name__ == "__main__":
    run_chat()
    # gems = gemini_request(input="Explain friction in detail", stream=True)
    # for chunk in gems:
    #     print(chunk)
    