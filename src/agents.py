from typing import Callable
from call_llm_api import ask_agent
import re
from datetime import datetime
from content_extractor import download_and_extract_content

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

def rover_agent(query: str, conversation_history: list[dict]) -> str:
    rover_result = ask_agent("rover", query)
    print("Rover result: ", rover_result)
    extract_urls = get_urls(rover_result)
    print("Rover result: ", extract_urls)
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
    for r in pages:
        if sum([len(x.split()) for x in summaries]) > 1500:
            break
        try:
            summary = ask_agent("summer", "Here is some context from {source}: \n\n" + r + f"\n\nIf this content has infomation to answer the query '{query}', summarize the content in detail, list the key points and the most important details providing urls for the articles. Ignore the urls that are not articles.  Only use the provided context to answer the query. Only return the summary and no other text.")
            summaries.append(summary)
        except Exception as e:
            print("Error: ", e)
            continue
    summary = "\n\n".join(summaries)
    report = ask_agent("summer", "Here is the summary of the research documents: \n\n" + summary + f"\n\nBuild a comprehensive report based on the research documents and the query '{query}'.")
    print("Final Report: ", report)
    return context_template(query, report, "Research documents by @rover")

def dive_agent(query: str, conversation_history: list[dict]) -> str:
    last_message = conversation_history[-1]['content']
    urls = " ".join(get_urls(last_message))
    print("Urls: ", urls)
    return rover_agent(query + "\n\n" + "\n".join(urls), conversation_history)

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
