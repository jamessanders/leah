import json
from typing import Callable, Generator
from call_llm_api import ask_agent
import re
from datetime import datetime
from content_extractor import download_and_extract_content, download_and_extract_links, download_and_extract_rss
from NotesManager import NotesManager
from LocalConfigManager import LocalConfigManager

def context_template(message: str, context: str, extracted_url: str) -> str:
    now = datetime.now()
    today = now.strftime("%B %d, %Y")
    return f"""
Here is some context for the query:
{context}

Source: {extracted_url} (Last updated {today})

Here is the query:
{message}

Answer the query using the context provided above.
"""

def notes_template(message: str, context: str) -> str:
    return f"""
Here are all of the users notes:
{context}

Here is the query:
{message}

Answer the query using the users notes provided above.
"""

def noop_agent(query: str, conversation_history: list[dict]) -> str:
    yield ("result", query)

def get_urls(message: str) -> list[str]:
    url_pattern = r'https?://\S+'
    url_matches = re.findall(url_pattern, message)
    has_url = len(url_matches) > 0
    extracted_url = url_matches if has_url else []
    return extracted_url

def rawlink_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    extract_urls = get_urls(" ".join(arguments))
    contents = [download_and_extract_content(url) for url in extract_urls]
    contents = "\n".join([c[0] for c in contents if c[2] == 200])
    yield ("result", context_template(query, contents, " ".join(extract_urls)))

def link_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    extract_urls = get_urls(" ".join(arguments))
    links = "\n".join([download_and_extract_links(url) for url in extract_urls])
    pages = [x[0] for x in [download_and_extract_content(url) for url in extract_urls] if x[2] == 200]
    chunked_pages = []
    for page in pages:
        words = page.split()
        for i in range(0, len(words), 1000):
            chunk = ' '.join(words[i:i+1000])
            chunked_pages.append(chunk)
    pages = chunked_pages
    summaries = []
    source = " ".join(extract_urls)
    yield("message", "Extracting information from " + str(len(pages)) + " pages")
    for r in pages:
        if sum([len(x.split()) for x in summaries]) > 1500:
            report = ask_agent("summer", 
                               "Here is context: \n\n" + summary + f"\n\nBuild a comprehensive report based on the given context and the query '{query}'.",
                               should_cache=True)
            summaries = [report]
            yield("message", "Compiled report: " + report)
        try:
            summary = ask_agent("summer", 
                                "Here is some context from {source}: \n\n" + r + f"\n\noutput the main content exactly as it is.  Only use the provided context to answer the query.",
                                should_cache=True)
            summaries.append(summary)
            yield("message", "Rover summary: " + summary)
        except Exception as e:
            print("Error: ", e)
            continue
    summary = "\n\n".join(summaries)
    yield("message", "Compiling report...")
    report = ask_agent("summer", 
                       "Here is context: \n\n" + summary + f"\n\nBuild a comprehensive report based on the given context and the query '{query}'.",
                       should_cache=False)
    reportWithLinks = ask_agent("summer", 
                                 "Here is context: \n\nReport: \n\n" + report + "\n\nLinks: \n\n" + links + f"\n\nInclude the links in the report without changing the report.",
                                 should_cache=True)
    yield("message", "Final Report: " + reportWithLinks)
    # Remove URLs from the query before yielding the result
    query = re.sub(r'https?://\S+', '', query).strip()
    yield ("result", context_template(query, reportWithLinks, "Research documents by @rover"))


def joke_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield from rawlink_agent(query, conversation_history, arguments=["https://www.skiptomylou.org/funny-jokes/"])

def news_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield ("message", "Getting the latest news...")
    yield from rawlink_agent(query, conversation_history, arguments=["https://lite.cnn.com/"])

def broker_agent(query: str, conversation_history: list[dict]) -> str:
    yield ("message", "Broker is thinking...")
    response = ask_agent("broker", query, should_cache=True)
    if not "@" in response:
        yield ("result", query)
    else:
        yield ("message", "Broker: " + response)
        yield ("result", response + " " + query)

def time_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    timeAndDate = "The time and date is " + datetime.now().strftime("%I:%M %p on %A, %B %d %Y") + "\n\n" 
    yield ("result", context_template(query, timeAndDate, "Time by @time"))

def weather_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield ("message", "Getting the latest weather...")
    yield from rawlink_agent(query, conversation_history, arguments=["https://forecast.weather.gov/MapClick.php?lat=35.2334&lon=-82.7343"])


def notes_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield ("message", "Checking notes...")
    config_manager = LocalConfigManager("default")
    notesManager = NotesManager(config_manager)
    decider = ask_agent("decider", "Query was" + query + "\n\nDid the query ask to store something in notes, take note of something, or remember something?")
    print("Decider when asked should store a note: ", decider)
    if "yes" in decider.lower():
        note_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
        notesManager.put_note(note_name, ask_agent("emily", "Query was" + query + "\n\nWhat is the note that the user wants to store?"))
        print("Note stored at " + note_name)
        yield ("message", "Note stored at " + note_name)
        yield ("result", "Say: Note stored at " + note_name)
    else:
        notes = notesManager.get_all_notes_content()
        print("Notes: ", notes)
        yield ("result", notes_template(query, notes))

def remember_this_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield ("message", "Remembering this...")
    print("Conversation history: ", conversation_history)
    result = [x for x in conversation_history if x["role"] == "assistant"][-1]['content']
    print("Result: ", result)
    config_manager = LocalConfigManager("default")
    notesManager = NotesManager(config_manager)
    notesManager.put_note(datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt", result)
    yield ("result", "Just say: " + result)

def remember_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield ("message", "Remembering this...")
    config_manager = LocalConfigManager("default")
    notesManager = NotesManager(config_manager)
    notesManager.put_note(datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt", query)
    yield ("result", "Just say you will remember this: " + query)

def reminder_agent(query: str, conversation_history: list[dict], arguments: list[str]) -> str:
    yield ("message", "Remembering this...")
    config_manager = LocalConfigManager("default")
    notesManager = NotesManager(config_manager)
    reminders = notesManager.get_note("reminders.txt")
    if reminders:
       reminders = json.loads(reminders)
    else:
        reminders = []
    reminders.append({
        "time":arguments[0],
        "message": arguments[1]
    })
    notesManager.put_note("reminders.txt", json.dumps(reminders))
    yield ("result", "Just say you will remember this: " + query)


def get_agent(agent_name: str) -> Callable:
    if agent_name.startswith("@"):
        agent_name = agent_name[1:]
    if agent_name in agents:
        return agents[agent_name]
    else:
        return None

agents = {
    "joke": joke_agent,
    "news": news_agent,
    "noop": noop_agent,
    "broker": broker_agent,
    "link": link_agent,
    "time": time_agent,
    "weather": weather_agent,
    "notes": notes_agent,
    "remember_this": remember_this_agent,
    "remember": remember_agent,
    "rawlink": rawlink_agent,
    "reminder": reminder_agent,
}
