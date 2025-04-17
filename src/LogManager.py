import os
from datetime import datetime
from datetime import timedelta

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

    def log_index_item(self, term: str, message: str, persona: str = "default") -> None:
        """
        Log an index item with a timestamp.
        
        Args:
            term (str): The term to log
            message (str): The message to log
            persona (str): The persona name to organize logs under (default: "default")
        """
        term = term.lower().replace(" ", "_")
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        message = message.replace("\n", "\\n")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Create a log file for the current term in the logs/index/persona directory
        index_dir = os.path.join(self.logs_directory, "index", persona)
        if not os.path.exists(index_dir):
            os.makedirs(index_dir, exist_ok=True)
        log_file = os.path.join(index_dir, f"{term}.log")
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(log_entry)
        
    def search_log_item(self, persona: str, term: str) -> list[str]:
        """
        Search the log for an index item with a timestamp.
        """
        term = term.lower().replace(" ", "_")
        log_file = os.path.join(self.logs_directory, "index", persona, f"{term}.log")
        if not os.path.exists(log_file):
            return []
        with open(log_file, 'r', encoding='utf-8') as file:
            return file.readlines()


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



    def get_all_indexes(self, persona: str) -> list[str]:
        """
        Get a list of all log file names in the logs/index directory without extensions.
        
        Returns:
            list[str]: A list of log file names without extensions.
        """
        index_dir = os.path.join(self.logs_directory, "index", persona)
        if not os.path.exists(index_dir):
            return []
        log_files = []
        for root, _, files in os.walk(index_dir):
            for file in files:
                file_name, _ = os.path.splitext(file)
                log_files.append(file_name)
        return log_files 

    def get_logs_for_days(self, persona: str, days: int) -> list[str]:
        """
        Get log files from the current date back to the specified number of days.

        Args:
            persona (str): The persona name to filter logs.
            days (int): The number of days to look back.

        Returns:
            list[str]: A list of log file paths.
        """
        log_entries = []
        chat_dir = os.path.join(self.logs_directory, "chat", persona)
        if not os.path.exists(chat_dir):
            return log_entries

        current_date = datetime.now().date()
        for i in range(days + 1):
            date_to_check = current_date - timedelta(days=i)
            log_file = os.path.join(chat_dir, f"chat_{date_to_check.strftime('%Y-%m-%d')}.log")
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as file:
                    for line in file:
                        log_entries.append(" ".join(line.split(" ")[:200]).replace("\\n","\n"))

        return log_entries 