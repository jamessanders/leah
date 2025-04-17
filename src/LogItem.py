from datetime import datetime

class LogItem:
    def __init__(self, date_str, user_type, message):
        self.date = datetime.strptime(date_str, '[%Y-%m-%d_%H-%M-%S]')
        self.user_type = user_type
        self.message = message

    def __repr__(self):
        return f"LogItem(date={self.date}, user_type={self.user_type}, message={self.message})"

    @staticmethod
    def fromLogLine(log_line: str):
        # Extract the date, user, and message from the log line
        parsed_line = log_line.split(' ', 2)
        if len(parsed_line) > 2:
            date_str = parsed_line[0]
            user_type = parsed_line[1]
            message = parsed_line[2]
        else:
            return None
        # Create and return a new LogItem instance
        return LogItem(date_str, user_type, message.replace("\\n", "\n"))

    def get_fuzzy_date(self):
        now = datetime.now()
        delta = now - self.date
        if delta.days == 0:
            return 'Today'
        elif delta.days == 1:
            return 'Yesterday'
        elif delta.days < 7:
            return f'{delta.days} days ago'
        elif delta.days < 14:
            return 'Last week'
        elif delta.days < 30:
            return f'{delta.days // 7} weeks ago'
        elif delta.days < 365:
            return f'{delta.days // 30} months ago'
        else:
            return f'{delta.days // 365} years ago'

class LogCollection:
    def __init__(self):
        self.logs = []
        self.log_set = set()  # To track unique logs

    def add_log(self, log_item: LogItem):
        log_identifier = (log_item.date, log_item.message)
        if log_identifier not in self.log_set:
            self.logs.append(log_item)
            self.logs.sort(key=lambda log: log.date)
            self.log_set.add(log_identifier)

    def __repr__(self):
        return f"LogCollection({self.logs})"

    @staticmethod
    def fromLogLines(log_lines: list[str]):
        collection = LogCollection()
        for line in log_lines:
            log_item = LogItem.fromLogLine(line)
            if log_item:
                collection.add_log(log_item)
        return collection

    def generate_report(self, max_logs: int = 50):
        print("Generating report for " + str(len(self.logs)) + " logs")
        report = []
        grouped_logs = {}
        c = 0
        for log in self.logs:
            if c > max_logs:
                break
            c += 1
            fuzzy_date = log.get_fuzzy_date()
            if fuzzy_date not in grouped_logs:
                grouped_logs[fuzzy_date] = []
            grouped_logs[fuzzy_date].append(log)

        for fuzzy_date in sorted(grouped_logs.keys()):
            report.append(f"Logs from {fuzzy_date}:")
            for log in grouped_logs[fuzzy_date]:
                time_str = log.date.strftime('%H:%M:%S')
                user_str = log.user_type == "[ASSISTANT]" and "You" or "User"
                if log.get_fuzzy_date() not in ['Today', 'Yesterday']:
                    full_date_str = log.date.strftime('%B %d, %Y')
                    report.append(f"at {time_str} on {full_date_str}, {user_str} said: {log.message} ")
                else:
                    report.append(f"at {time_str} {fuzzy_date}, {user_str} said: {log.message}")
            report.append("")  # Add a newline for separation

        return "\n".join(report) 