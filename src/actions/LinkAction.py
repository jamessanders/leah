from datetime import datetime
from typing import List, Dict, Any, Callable
from .IActions import IAction
from .utils import fetch_url_with_selenium
from selenium.webdriver.common.by import By


class LinkAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def process_query(self) -> Dict[str, Any]:
        # Implement the logic to process the query
        return {
            "response": f"LinkAction processed query: {self.query} with persona: {self.persona}",
            "success": True
        }

    def additional_notes(self) -> str:
        return " - You can fetch any URL from the internet.  Always use the fetch_link tool to fetch the contents of a URL.  Always use fetch_weather_info to get the latest weather and fetch_stock_info to get the latest info on a stock symbol."

    def getTools(self) -> List[tuple]:
        # Return a list of callable tools and their descriptions
        return [
            (self.fetch_link_with_selenium, 
             "fetch_url",
             "Downloads the contents of a url.  Used to fetch content of urls", 
             {"url": "<the url of the page to fetch>"}),
            (self.fetch_stock_info, 
             "fetch_stock_info",
             "Downloads the contents of a stock info url.  Used to fetch stock info of stock symbol", 
             {"symbol": "<the symbol of the stock to fetch>"}),
            (self.fetch_weather_info, 
             "fetch_weather_info",
             "Fetches weather information based for a specific city using latitude and longitude, first fetch the latitude and longitude of the city", 
             {"latitude": "<the latitude of the weather to fetch>", "longitude": "<the longitude of the weather to fetch>"})
        ]
    def context_template(self, message: str, context: str, extracted_url: str) -> str:
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
    def fetch_stock_info(self, arguments: Dict[str, Any]):
        try:
            symbol = arguments['symbol']
            yield ("system", "Fetching stock info for " + symbol)
            yield from self.fetch_link_with_selenium({"url": f"https://finance.yahoo.com/quote/{symbol}"})
        except Exception as e:
            yield ("result", self.context_template(self.query, "Error fetching the stock info", symbol))
            
    def fetch_weather_info(self, arguments: Dict[str, Any]):
        def find_weather_element(driver):
            try:
                current_conditions_body = driver.find_element(By.ID, 'current-conditions')
                seven_day_forecast = driver.find_element(By.ID, 'seven-day-forecast')
                return [current_conditions_body, seven_day_forecast]
            except:
                return None

        if not arguments['latitude'] or not arguments['longitude']:
            yield ("result", self.context_template(self.query, "Error fetching weather data, try giving a more specific location", url))
            return
        url = f"https://forecast.weather.gov/MapClick.php?lat={arguments['latitude']}&lon={arguments['longitude']}"
        yield ("system", "Fetching weather data for " + arguments['latitude'] + "," + arguments['longitude'])
        try:
            yield ("result", self.context_template(self.query, fetch_url_with_selenium(url, find_element=find_weather_element), url))
        except Exception as e:
            yield ("result", self.context_template(self.query, "Error fetching the weather info", url))
        
        
    def fetch_link_with_selenium(self, arguments: Dict[str, Any]):
        try:
            url = arguments['url']
            yield ("system", "Fetching url with Selenium: " + url)
            main_content = fetch_url_with_selenium(url)
            yield ("result", self.context_template(self.query, main_content, url))
        except Exception as e:
            yield ("result", self.context_template(self.query, "Error fetching the url with Selenium", url))
