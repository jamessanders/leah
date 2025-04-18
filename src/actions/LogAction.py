from datetime import datetime
from typing import List, Dict, Any
from .IActions import IAction

class LogAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def getTools(self) -> List[tuple]:
        return [
            (self.searchConversationLogs, "search_conversation_logs", "Searches past conversation logs for search terms related to the query and the response. Use this tool to find information from past conversations. Provide multiple terms to search for to expand the search. Only use this tool if you cannot answer the query based on conversation context.", {"terms": "<comma separated list of search terms>"}),
            (self.getPastConversations, "get_past_conversations", "Searches past conversation logs. Use this tool to find information from past conversations. It takes a single argument for the number of days to worth of conversation to gather. Only use this tool if you cannot answer the query using the searchConversationLogs tool.", {"days": "<number of days to gather>"})
        ]
    
    def context_template(self, message: str, context: str) -> str:
        return f"""
Here is some context for the query:

{context}

Source: logs of past conversations 

Here is the query:

{message}

Answer the query using the context provided above.
"""

    def logIndex(self, arguments: Dict[str, Any]):
        logManager = self.config_manager.get_log_manager()
        terms = arguments.get("terms", "").split(",")
        for term in terms:
            logManager.log_index_item(term, "[USER] " + self.query.replace("\n", "\\n"), self.persona)
            logManager.log_index_item(term, "[ASSISTANT] " + self.conversation_history[-1]["content"].replace("\n", "\\n"), self.persona)
        yield ("end", "")

    def searchIndex(self, terms):
        logManager = self.config_manager.get_log_manager()
        results = []
        for term in terms:
            for result in logManager.search_log_item(self.persona, term):
                results.append(result)
        return results

    def searchConversationLogs(self, arguments: Dict[str, Any]):
        yield ("system", "Searching logs for " + arguments["terms"])
        terms = arguments["terms"].split(",")
        results = self.searchIndex(terms)
        if not results:
            yield ("result", self.context_template(self.query, "No results found in logs, do not search logs for this query."))
        else:
            yield ("result", self.context_template(self.query, "\n".join(results)))

    def getPastConversations(self, arguments: Dict[str, Any]):
        yield ("system", "Getting logs for the past " + arguments["days"] + " days")
        logManager = self.config_manager.get_log_manager()
        days = int(arguments["days"])
        results = logManager.get_logs_for_days(self.persona, days)
        yield ("result", self.context_template(self.query, results))


    def additional_notes(self) -> str:
        logManager = self.config_manager.get_log_manager()
        indexes = logManager.get_largest_index_logs(self.persona, 50)
        indexes_str = ",".join(indexes)
        out = f"""Always search past conversation logs if you cannot answer the query. The indexes are: {indexes_str}"""
        if indexes:
            out += "These are some of the most common search terms that you can use but you are not required to use them: " + indexes_str
        return out

    

