from typing import List, Dict, Any
from actions import LinkAction, WeatherAction
import json

class Actions:
    """
    A class to handle actions based on user queries and conversation history.
    
    This class processes user queries and manages actions based on the conversation
    context, persona settings, and local configuration.
    """
    
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        """
        Initialize the Actions class with the required parameters.
        
        Args:
            config_manager: An instance of LocalConfigManager for managing user configuration
            persona (str): The persona to use for processing the query
            query (str): The user's query to process
            conversation_history (List[Dict[str, Any]]): The history of the conversation
        """
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history
        
        # Initialize managers from config_manager
        self.notes_manager = config_manager.get_notes_manager()
        self.log_manager = config_manager.get_log_manager()
        
        self.actions = [
            LinkAction.LinkAction(config_manager, persona, query, conversation_history),
            WeatherAction.WeatherAction(config_manager, persona, query, conversation_history)
        ]

    def run_tool(self, tool_name: str, arguments: List[str]) -> str:
        tool_sp = tool_name.split(".")
        tool_name = tool_sp[0]
        tool_method = tool_sp[1]
        for action in self.actions:
            if action.__class__.__name__ == tool_name:
                tools = action.getTools()
                for tool in tools:
                    if tool[1] == tool_method:
                        yield from tool[0](arguments)
                        return
        yield "Tool not found"

    def get_actions_prompt(self) -> str:
        prompt = """
Prompt: You are a helpful assistant that can use the following tools to answer the user's question. 
If you need to use a tool, respond with the tool name and arguments in the json format, start with START_TOOL_JSON and end with END_TOOL_JSON.
The json should be in the format of {"tool_name": "tool_name", "arguments": {"argument_name": "argument_value"}}
Tool names should be in the format of ActionName.ToolName
Do not ask the user to provide the tool name, just respond with the json.
Do not ask the user if you can use a tool, just respond with the json.
If no tool is needed, respond with @other.
The tools are listed below in the format of Tool Name, Tool Description, and Tool Arguments.
Tools: 

"""
        for action in self.actions:
            actionName = action.__class__.__name__
            tools = action.getTools()
            for tool in tools:
                actionDescription = tool[2]
                actionArgs = json.dumps(tool[3])
                prompt += f"""
Tool Name: {actionName}.{tool[1]}
Tool Description: {actionDescription}
Tool Arguments: {actionArgs}

"""
        return prompt