from typing import List, Dict, Any, Callable
from .IActions import IAction

class LinkAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def process_query(self) -> Dict[str, Any]:
        # Implement the logic to process the query
        return {
            "response": f"LinkAction processed query: {self.query} with persona: {self.persona}",
            "success": True
        }

    def getTools(self) -> List[tuple]:
        # Return a list of callable tools and their descriptions
        return [
            (self.fetch_link, 
             "fetch_link",
             "Fetches the contents of a url", 
             {"url": "<the url of the link to fetch>"})
        ]

    def fetch_link(self):
        # Example tool method
        pass 