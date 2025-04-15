from datetime import datetime
from typing import Any, Dict, List
from .IActions import IAction

class TimeAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def getTools(self) -> List[tuple]:
        return [
            (self.get_time, "get_time", "Get the current time", {})
        ]

    def context_template(self, message: str, context: str) -> str:
        now = datetime.now()
        today = now.strftime("%B %d, %Y")
        return f"""
Here is some context for the query:
{context}

Here is the query:
{message}

Answer the query using the context provided above.
"""
    def get_time(self, arguments: Dict[str, Any]):
        timeAndDate = "The time and date is " + datetime.now().strftime("%I:%M %p on %A, %B %d %Y") + "\n\n" 
        yield ("result", self.context_template(self.query, timeAndDate))
