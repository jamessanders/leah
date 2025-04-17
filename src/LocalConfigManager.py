import os
from pathlib import Path
from NotesManager import NotesManager
from LogManager import LogManager
from config import Config
from webdriver_singleton import WebDriverSingleton  
from selenium.webdriver.remote.webdriver import WebDriver

class LocalConfigManager:
    def __init__(self, user_id: str):
        """
        Initialize the LocalConfigManager with a user ID.
        
        Args:
            user_id (str): The user ID to create a config directory for
        """
        self.user_id = user_id
        self.base_dir = os.path.expanduser(f'~/.leah/{user_id}')
        
        # Create the directory structure if it doesn't exist
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
    
    def get_http_path(self, filename: str) -> str:
        """
        Get the full path for a file under the user's config directory.
        
        Args:
            filename (str): The name of the file to get the path for
        """
        return "/"+self.user_id + "/" + filename

    def get_path(self, filename: str) -> str:
        """
        Get the full path for a file under the user's config directory.
        
        Args:
            filename (str): The name of the file to get the path for
            
        Returns:
            str: The full path to the file
        """
        return os.path.join(self.base_dir, filename)
    
    def ensure_file_exists(self, filename: str) -> None:
        """
        Ensure that a file exists in the config directory, creating it if necessary.
        
        Args:
            filename (str): The name of the file to ensure exists
        """
        file_path = self.get_path(filename)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                pass  # Create empty file
                
    def get_notes_manager(self) -> NotesManager:
        """
        Get a NotesManager instance for managing notes.
        
        Returns:
            NotesManager: A NotesManager instance configured for this user
        """
        return NotesManager(self)
        
    def get_log_manager(self) -> LogManager:
        """
        Get a LogManager instance for managing logs.
        
        Returns:
            LogManager: A LogManager instance configured for this user
        """
        return LogManager(self) 
    
    def get_config(self) -> Config:
        """
        Get a Config instance for managing configuration.
        
        Returns:
            Config: A Config instance configured for this user
        """
        return Config()
    
    def get_web_driver(self) -> WebDriver:
        """
        Get a WebDriver instance for managing web drivers.
        
        Returns:
            WebDriver: A WebDriver instance configured for this user
        """
        return WebDriverSingleton().get_driver()