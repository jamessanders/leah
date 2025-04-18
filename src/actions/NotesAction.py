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
            (self.put_note, 
             "update_note", 
             "Update a note in your notes files, these can be used to answer the user's query. Note names should be in the format of 'note_name.txt'", 
             {"note_name": "<the name of the note to add>", "note_content": "<the content of the note to add>"}),
            (self.get_note,
              "get_note", 
              "Get a note from your notes, these can be used to answer the user's query. Note names should be in the format of 'note_name.txt'", 
              {"note_name": "<the name of the note to get>"}),
            (self.store_reminder, "store_reminder", "Store a reminder in your notes, this will be used to keep track of the users reminders", {"reminder": "<the reminder to store>", "when": "<when the reminder is for>"}),
            (self.get_reminders, "get_reminders", "Get all the reminders you have, this will be used to answer the user's queries about their reminders", {}),
            (self.remove_reminder, "remove_reminder", "Remove a reminder", {"id": "<the id of the reminder to remove>"}),
            (self.schedule_task, 
             "schedule_task", 
             "Schedule a task for yourself for later, this can be used to notify the user of something at a later date, the date must be in the format %Y-%m-%d_%H-%M-%S.  Consider using this along with reminders so you can notfy the user at specific times. Always create task to remind the user of something later.", 
             {"when": "when the task should be scheduled for, must be in the format %Y-%m-%d_%H-%M-%S.", "task":"what the task is, for example notify user of a meeting."})
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
    def schedule_task(self, arguments: Dict[str, Any]):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("task_schedule")
        when = arguments.get("when","")
        task = arguments.get("task","")
        id = str(uuid.uuid4())
        if not when or not task:
            yield ("end", "Couldn't store task")
        if notes is None:
            notes = ""
        yield("system", f"Setting task for {when}, the task is {task}")
        task = f"{when} - Id: {id} - Task: {task}"
        notes_manager.put_note("task_schedule", task + "\n" + notes)
        yield ("end", "Task has been scheduled.")
        
    def store_reminder(self, arguments: Dict[str, Any]):
        yield ("system", "Storing reminder: " + arguments["reminder"] + " for " + arguments.get("when", "whenever"))
        id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("reminders")
        if notes is None:
            notes = ""
        notes_manager.put_note("reminders", "Reminder: " + arguments["reminder"] + ",When: " + arguments.get("when", "whenever") + ", Stored at: " + now + ", ID: " + id + "\n" + notes)
        yield ("end", "Stored a reminder: " + arguments["reminder"] + " for " + arguments.get("when", "whenever") + ".")

    def get_reminders(self, arguments: Dict[str, Any]):
        yield ("system", "Getting reminders")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("reminders")
        if notes is None:
            yield ("result", self.context_template(self.query, "No reminders found", "reminders"))
        yield ("result", self.context_template(self.query, notes, "reminders"))

    def remove_reminder(self, arguments: Dict[str, Any]):
        yield ("system", "Removing reminder")
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
        name = arguments.get("note_name","")
        content = arguments.get("note_content","")
        if not name or not content:
            return
        
        def update_note(update_content):
            notes_manager.put_note(name, update_content)
            return f"Note named '{name}' updated with the contents: {update_content}"
        
        yield ("system", "Putting note: " + name)
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        
        prev_contents = notes_manager.get_note(name)
        if not prev_contents:
            prev_contents = ""
            notes_manager.put_note(name,content)
            yield ("end", f"Note '{name}' added with contents: {content}")
        else:
            yield ("feedback", (f"Here are the contents of a document: \n{prev_contents}\n\nRewrite the contents to include the following information, responde with only the updated document and no other text: {content}", update_note))

    def get_note(self, arguments):
        yield ("system", "Getting note: " + arguments.get("note_name",""))
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", self.context_template(self.query, notes_manager.get_note(arguments["note_name"]), arguments["note_name"]))

    def list_notes(self, arguments):
        yield ("system", "Listing notes")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", "Here are all the notes you have: " + str(", ".join(notes_manager.get_all_notes())) + " answer the query based on this information, the query is: " + self.query)

    def additional_notes(self):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        all_notes = notes_manager.get_notes_by_size(100)
        if all_notes:
            return "Here are some current notes you have but you can also create new ones: " + str(", ".join(all_notes))
        return ""