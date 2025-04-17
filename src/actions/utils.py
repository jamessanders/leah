from datetime import datetime
from typing import List, Dict, Any, Callable
from .IActions import IAction
import lxml.html
from lxml.html.clean import Cleaner
import html2text
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests 
from selenium.webdriver.remote.webdriver import WebDriver

def extract_main_content(html: bytes, base_url: str) -> str:
    """Extract the main content as markdown from HTML content, using lxml.html.clean."""
    # Parse the HTML content
    document = lxml.html.fromstring(html)
    
    # Use lxml's Cleaner to clean the document
    cleaner = Cleaner()
    cleaner.javascript = True  # Remove JavaScript
    cleaner.style = True       # Remove styles
    cleaner.links = False       # Remove links
    cleaned_content = cleaner.clean_html(document)
    
    # Convert cleaned content to string
    main_content = lxml.html.tostring(cleaned_content, encoding='unicode')
            
    # Limit the number of tokens to 1024
    tokens = main_content.split()
    print("Tokens: ", len(tokens))
    limited_content = ' '.join(tokens[:15000])
    
    # Convert limited content to markdown
    markdown_content = html2text.html2text(limited_content)
    
    return markdown_content

def fetch_url_with_selenium(url: str, find_element: Callable = None, user_driver: WebDriver = None):
    if not user_driver:
        # Set up Selenium WebDriver with Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run headless Chrome
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        # Initialize the WebDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    else:
        driver = user_driver
    
    # Fetch the URL
    driver.get(url)
    
    # Attempt to find the main content section
    
    if find_element:
        main_content_elements = find_element(driver)
        if main_content_elements:
            return "\n".join([extract_main_content(element.get_attribute('innerHTML').encode('utf-8'), url) for element in main_content_elements])
    
    try:
        main_content_element = driver.find_element(By.TAG_NAME, 'main')
    except:
        try:
            main_content_element = driver.find_element(By.TAG_NAME, 'article')
        except:
            try:
                main_content_element = driver.find_element(By.CLASS_NAME, 'content')
            except:
                main_content_element = driver.find_element(By.TAG_NAME, 'body')
    
    # Extract the page source from the main content
    html = main_content_element.get_attribute('innerHTML')
    
    # Close the WebDriver
    if not user_driver:
        driver.quit()
    
    # Extract main content
    main_content = extract_main_content(html.encode('utf-8'), url)
    return main_content
