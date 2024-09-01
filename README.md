# Gemini with Memory: A Powerful AI Chatbot with Enhanced Personalisation

**Gemini with Memory** is an advanced AI chatbot built upon Google's Gemini model, augmented with a sophisticated memory system. This system allows the chatbot to retain some specific usefuyl information about user locally from past interactions, providing a more personalized and contextually relevant conversational experience.

## Features

* **Dual Memory System:** Employs a dual memory system comprising:
    * **Permanent Memory:** Stores user preferences, important facts, and frequently used information for long-term personalization.
    * **Time-Based Memory:** Stores time-sensitive information like reminders and scheduled events, automatically expiring outdated entries.
* **Automatic Data Extraction:** Extracts relevant information from user input using a dedicated LLM and saves it to the appropriate memory type.
* **Memory Compression:** Periodically compresses memory by deduplicating and merging entries using an LLM, ensuring efficient storage and retrieval.
* **Conversation Management:** Supports starting new conversations, loading previous ones, and deleting conversations.
* **Rich User Interface:** Provides a user-friendly interface with clear menus, conversation history, and formatting options.

## Real-Life Use Cases

* **Personalized Assistants:** Create customized AI assistants that remember user preferences, habits, and important information, providing tailored support and recommendations.
* **Interactive Storytelling:** Develop immersive interactive stories where the AI remembers past events and character details, creating a dynamic and engaging narrative.
* **Educational Tools:** Build AI tutors that track student progress, adapt to individual learning styles, and provide personalized feedback.
* **Customer Service Bots:** Implement intelligent customer service bots that recall past interactions and customer details, offering efficient and personalized support.
* **Research Assistants:** Create AI-powered research assistants that can store and retrieve relevant information from various sources, aiding in literature reviews and data analysis.

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KingNish24/gemini-with-memory.git
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables:**
   Create a `.env` file and set the GEMINI_API_KEY in it.
4. **Run the chatbot:**
   ```bash
   python run.py
   ```

## Future Enhancements

* **Multimodal Memory:** Extend the memory system to store and process various data types, including images, audio, and video.
* **Improved Memory Search:** Implement more sophisticated search algorithms for efficient retrieval of information from memory.
* **User-Defined Memory Tags:** Allow users to tag memory entries with custom labels for better organization and retrieval.
* **Integration with External Services:** Integrate with external services like calendars, task managers, and knowledge bases to enhance the chatbot's capabilities.

## Contributing

Contributions are welcome!

## License

This project is licensed under the [MIT License](LICENSE).
