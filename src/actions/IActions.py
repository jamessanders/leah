from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IAction(ABC):
    """
    Interface for the Actions class to ensure consistent implementation of methods.
    """

    @abstractmethod
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        """
        Initialize the Actions class with the required parameters.

        Args:
            config_manager: An instance of LocalConfigManager for managing user configuration
            persona (str): The persona to use for processing the query
            query (str): The user's query to process
            conversation_history (List[Dict[str, Any]]): The history of the conversation
        """
        pass

    @abstractmethod
    def getTools(self) -> List[tuple]:
        """
        Returns a list of tuples, where each tuple contains a callable and a description along with a dict of arguments and descriptions.

        Returns:
            List[tuple]: A list of tuples (Callable<arguments>, str, dict)
        """
        pass 

    def additional_notes(self) -> str:
        """
        Returns a string of additional notes for the action.
        """
        return ""