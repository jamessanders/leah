import os
from LocalConfigManager import LocalConfigManager

class NotesManager:
    def __init__(self, config_manager: LocalConfigManager):
        """
        Initialize the NotesManager with a LocalConfigManager instance.
        
        Args:
            config_manager (LocalConfigManager): The LocalConfigManager instance to use for path management
        """
        self.config_manager = config_manager
        self.notes_directory = self.config_manager.get_path("notes")
        if not os.path.exists(self.notes_directory):
            os.makedirs(self.notes_directory, exist_ok=True)

    def get_note(self, note_name: str) -> str:
        """Retrieve the content of a specific note file."""
        note_path = os.path.join(self.notes_directory, note_name)
        if os.path.exists(note_path):
            with open(note_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            return None

    def put_note(self, note_name: str, content: str) -> None:
        """Store content into a specific note file."""
        note_path = os.path.join(self.notes_directory, note_name)
        with open(note_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def get_all_notes_content(self) -> str:
        """Retrieve the content of all note files and output them as a single string."""
        all_content = []
        for note_name in os.listdir(self.notes_directory):
            note_path = os.path.join(self.notes_directory, note_name)
            if (not note_path.endswith(".txt")):
                continue
            if os.path.isfile(note_path):
                with open(note_path, 'r', encoding='utf-8') as file:
                    print("Note: ", note_name)
                    all_content.append(note_name + ":\n" + file.read())
        return "\n".join(all_content) 