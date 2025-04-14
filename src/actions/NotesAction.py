from actions.IActions import IAction

class NotesAction(IAction): 
    def __init__(self, config_manager, persona, query, conversation_history):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def getTools(self):
        return [
            (self.add_note, "add_note", "Add a note to your notes, these can be used to answer the user's query. Example notes would be 'todo.txt', 'user_info.txt', 'meeting_notes.txt'", {"note_name": "<the name of the note to add>", "note_content": "<the content of the note to add>"}),
            (self.read_note, "read_note", "Read a note from your notes, these can be used to answer the user's query. Example notes would be 'todo.txt', 'user_info.txt', 'meeting_notes.txt'", {"note_name": "<the name of the note to get>"}),
            (self.edit_note, "edit_note", "Edit a note from your notes, always pull the latest version of the note before editing and include the latest version in the note content", {"note_name": "<the name of the note to edit>", "note_content": "<the content of the note to edit>"}),
            (self.list_notes, "list_notes", "List all the notes you have, this will be used to answer the user's query", {})
        ]

    def context_template(self, query: str, context: str, note_name: str) -> str:
        return f"""
Here is the content of the note:

{context}

Source: {note_name} 

Here is the query:

{query}

Answer the query using the context provided above.
"""
    
    def add_note(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes_manager.put_note(arguments["note_name"], arguments["note_content"])
        yield ("result", f"Just say 'ok note {arguments['note_name']} added'")

    def read_note(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", self.context_template(self.query, notes_manager.get_note(arguments["note_name"]), arguments["note_name"]))

    def list_notes(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", "Here are all the notes you have: " + str(", ".join(notes_manager.get_all_notes())) + " answer the query based on this information, the query is: " + self.query)

    def edit_note(self, arguments):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes_manager.put_note(arguments["note_name"], notes_manager.get_note(arguments["note_name"]) + "\n" + arguments["note_content"])
        yield ("result", f"Just say 'ok note {arguments['note_name']} updated'")
