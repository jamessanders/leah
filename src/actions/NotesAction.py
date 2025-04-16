from datetime import datetime
from typing import Any, Dict
import uuid
from actions.IActions import IAction

class NotesAction(IAction): 
    def __init__(self, config_manager, persona, query, conversation_history):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def getTools(self):
        return [
            (self.put_note, 
             "put_note", 
             "Add a note in your notes files, these can be used to answer the user's query. Note names should be in the format of 'note_name.txt'", 
             {"note_name": "<the name of the note to add>", "note_content": "<the content of the note to add>"}),
            (self.get_note,
              "get_note", 
              "Get a note from your notes, these can be used to answer the user's query. Note names should be in the format of 'note_name.txt'", 
              {"note_name": "<the name of the note to get>"}),
            (self.list_notes, "list_notes", "List all the notes you have, this will be used to answer the user's query", {}),
            (self.store_reminder, "store_reminder", "Store a reminder in your notes, this will be used to answer the user's query", {"reminder": "<the reminder to store>", "when": "<when the reminder is for>"}),
            (self.get_reminders, "get_reminders", "Get all the reminders you have, this will be used to answer the user's query", {}),
            (self.remove_reminder, "remove_reminder", "Remove a reminder", {"id": "<the id of the reminder to remove>"})
        ]

    def context_template(self, query: str, context: str, note_name: str) -> str:
        return f"""
Here is the content of the note {note_name}:

{context}

Source: {note_name} 

Here is the query:

{query}

Answer the query using the context provided above.
"""
    
    def store_reminder(self, arguments: Dict[str, Any]):
        id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("reminders")
        if notes is None:
            notes = ""
        notes_manager.put_note("reminders", notes + "\n" + "Reminder: " + arguments["reminder"] + ",When: " + arguments.get("when", "whenever") + ", Stored at: " + now + ", ID: " + id)
        yield ("end", "Reminder stored")

    def get_reminders(self, arguments: Dict[str, Any]):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("reminders")
        if notes is None:
            yield ("result", self.context_template(self.query, "No reminders found", "reminders"))
        yield ("result", self.context_template(self.query, notes, "reminders"))

    def remove_reminder(self, arguments: Dict[str, Any]):
        id = arguments["id"]
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        reminders = notes_manager.get_note("reminders")
        keepers = []
        removed = False
        for line in reminders.split("\n"):
            if id in line:
                removed = True
                continue
            keepers.append(line)
        notes_manager.put_note("reminders", "\n".join(keepers))
        if removed:
            yield ("end", "Reminder removed")
        else:
            yield ("end", "Reminder not found")

    def put_note(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", self.context_template(self.query, notes_manager.get_note(arguments["note_name"]), arguments["note_name"]))

    def get_note(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", self.context_template(self.query, notes_manager.get_note(arguments["note_name"]), arguments["note_name"]))

    def list_notes(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", "Here are all the notes you have: " + str(", ".join(notes_manager.get_all_notes())) + " answer the query based on this information, the query is: " + self.query)
