from typing import Callable, Generator
from call_llm_api import ask_agent
import re
from datetime import datetime
from content_extractor import download_and_extract_content, download_and_extract_links

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

def noop_agent(query: str) -> str:
    return query

def get_urls(message: str) -> list[str]:
    url_pattern = r'https?://\S+'
    url_matches = re.findall(url_pattern, message)
    has_url = len(url_matches) > 0
    extracted_url = url_matches if has_url else []
    return extracted_url

def rover_agent(query: str, conversation_history: list[dict]) -> Generator[tuple[str, str], None, None]:
    yield ("message", "Rover is thinking...")
    rover_result = ask_agent("rover", query)
    yield("message", "Rover result: " + rover_result)
    extract_urls = get_urls(rover_result)
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
            report = ask_agent("summer", "Here is context: \n\n" + summary + f"\n\nBuild a comprehensive report based on the given context and the query '{query}'.")
            summaries = [report]
            yield("message", "Compiled report: " + report)
        try:
            summary = ask_agent("summer", "Here is some context from {source}: \n\n" + r + f"\n\noutput the main content exactly as it is.  Only use the provided context to answer the query.")
            summaries.append(summary)
            yield("message", "Rover summary: " + summary)
        except Exception as e:
            print("Error: ", e)
            continue
    summary = "\n\n".join(summaries)
    yield("message", "Compiling report...")
    report = ask_agent("summer", "Here is context: \n\n" + summary + f"\n\nBuild a comprehensive report based on the given context and the query '{query}'.")
    reportWithLinks = ask_agent("summer", "Here is context: \n\nReport: \n\n" + report + "\n\nLinks: \n\n" + links + f"\n\nInclude the links in the report without changing the report.")
    yield("message", "Final Report: " + reportWithLinks)
    yield ("result", context_template(query, reportWithLinks, "Research documents by @rover"))

def dive_agent(query: str, conversation_history: list[dict]) -> str:
    last_message = conversation_history[-1]['content']
    urls = " ".join(get_urls(last_message))
    print("Urls: ", urls)
    yield ("message", "Diving into the research documents...")
    yield from rover_agent(query + "\n\n" + "\n".join(urls), conversation_history)

def get_agent(agent_name: str) -> Callable:
    if agent_name in agents:
        return agents[agent_name]
    else:
        return noop_agent

agents = {
    "rover": rover_agent,
    "dive": dive_agent,
    "noop": noop_agent
}
