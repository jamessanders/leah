from datetime import datetime
import json
from typing import List, Dict, Any, Callable
from .IActions import IAction
import urllib.request

class WeatherAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def process_query(self) -> Dict[str, Any]:
        # Implement the logic to process the query
        return {
            "response": f"WeatherAction processed query: {self.query} with persona: {self.persona}",
            "success": True
        }

    def getTools(self) -> List[tuple]:
        # Return a list of callable tools and their descriptions
        return [
            (self.fetch_weather, 
             "fetch_weather", 
             "Fetches weather information based for a specific city using latitude and longitude, first fetch the latitude and longitude of the city", 
             {"latitude": "<the latitude of the area to fetch weather for>", "longitude": "<the longitude of the area to fetch weather for>"})
        ]

    def context_template(self, message: str, context: str, extracted_url: str) -> str:
        now = datetime.now()
        today = now.strftime("%B %d, %Y")
        return f"""
Here is some context for the query (in json format):
{context}

You just fetched the weather for the location. from the source below.
Source: {extracted_url} (Last updated {today})

Here is the query:
{message}

Answer the query using the context provided above.
"""

    def get_lat_long(self, arguments: Dict[str, Any]):
        # Example tool method
        yield ("result", "The latitude and longitude of " + arguments['city'] + " are 37.774929 and -122.419418")

    def fetch_weather(self, arguments: Dict[str, Any]):
        yield ("system", "Fetching weather data for " + arguments['latitude'] + "," + arguments['longitude'])
        # Example tool method
        if not arguments['latitude'] or not arguments['longitude']:
            yield ("result", self.context_template(self.query, "Error fetching weather data, try giving a more specific location", url))
            return
        
        url = f"https://api.weather.gov/points/{arguments['latitude']},{arguments['longitude']}"
        with urllib.request.urlopen(url) as response:
            html = response.read()
            status_code = response.getcode()
        if status_code != 200:
            yield ("result", self.context_template(self.query, "Error fetching weather data, try giving a more specific location", url))
        else:
            response = json.loads(html)
            try:
                forecast_url = response['properties']['forecast']
            except:
                yield ("result", self.context_template(self.query, "Error fetching weather data, try giving a more specific location", url))
                return
            with urllib.request.urlopen(forecast_url) as response:
                html = response.read()
                status_code = response.getcode()
            if status_code != 200:
                yield ("result", self.context_template(self.query, "Error fetching weather data, try giving a more specific location", url))
            else:
                yield ("result", self.context_template(self.query, html, url))

    def fetch_weather_for_city(self, arguments: Dict[str, Any]):
        # Example tool method
        yield ("result", "The weather in " + arguments['city'] + " is sunny")
