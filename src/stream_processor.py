class StreamProcessor:
    def __init__(self, match_start, match_end):
        self.buffer = ""
        self.match_start = match_start
        self.match_end = match_end
        self.matches = []

    def process_chunk(self, chunk):
        return "".join([self.process_character(c) for c in chunk])

    def process_character(self, character):
        if not character:
            return ""
        """Process a character and filter out <think></think> tags."""
        # Check if the character is the start of a potential <think> tag
        # start buffering
        if not self.buffer and character == self.match_start[0]:
            self.buffer = self.buffer + character
            return ""
        elif not self.buffer:
            return character
        
        # continue buffering
        self.buffer = self.buffer + character
        current_string = self.buffer
        if len(current_string) == len(self.match_start) and not current_string.startswith(self.match_start):
            # false match bail out
            self.buffer = ""
            return current_string
        if len(current_string) >= len(self.match_start) + len(self.match_end) and current_string.endswith(self.match_end):
            # stop buffering
            self.buffer = ""
            self.matches.append(current_string[len(self.match_start):-len(self.match_end)])
            return ""
        return ""