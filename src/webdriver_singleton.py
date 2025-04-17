from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class WebDriverSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebDriverSingleton, cls).__new__(cls)
            cls._instance.driver = cls._create_driver()
        return cls._instance

    @staticmethod
    def _create_driver():
        options = webdriver.ChromeOptions()
        options.add_argument("--user-data-dir=~/Library/Application Support/Google/Chrome/")
        options.add_argument("--profile-directory=Default")
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def get_driver(self):
        return self.driver

# Usage example:
# driver = WebDriverSingleton().get_driver() 