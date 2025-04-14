import os
from datetime import datetime

class LogManager:
    def __init__(self, config_manager):
        """
        Initialize the LogManager with a LocalConfigManager instance.
        
        Args:
            config_manager (LocalConfigManager): The LocalConfigManager instance to use for path management
        """
        self.config_manager = config_manager
        self.logs_directory = self.config_manager.get_path("logs")
        if not os.path.exists(self.logs_directory):
            os.makedirs(self.logs_directory, exist_ok=True)

    def log(self, message_type: str, message: str, persona: str = "default") -> None:
        """
        Log a tool message with a timestamp.
        
        Args:
            message_type (str): The type of message ('user' or 'assistant')
            message (str): The message content to log   
            persona (str): The persona name to organize logs under (default: "default")
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_entry = f"[{timestamp}] {message_type.upper()}  {persona}: {message}\n"
        

        # Create a log file for the current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.logs_directory, f"system.log")
        
        # Append the log entry to the file
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(log_entry) 

    def log_chat(self, message_type: str, message: str, persona: str = "default") -> None:
        """
        Log a chat message with a timestamp.
        
        Args:
            message_type (str): The type of message ('user' or 'assistant')
            message (str): The message content to log
            persona (str): The persona name to organize logs under (default: "default")
        """
        if message_type not in ['user', 'assistant']:
            raise ValueError("message_type must be either 'user' or 'assistant'")
            
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # Escape newlines in the message
        escaped_message = message.replace('\n', '\\n')
        log_entry = f"[{timestamp}] {message_type.upper()}: {escaped_message}\n"
        
        # Create persona-specific directory under logs/chat/
        chat_dir = os.path.join(self.logs_directory, "chat", persona)
        if not os.path.exists(chat_dir):
            os.makedirs(chat_dir, exist_ok=True)
        
        # Create a log file for the current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(chat_dir, f"chat_{current_date}.log")
        
        # Append the log entry to the file
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(log_entry) 