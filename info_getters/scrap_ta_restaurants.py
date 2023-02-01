import json, os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from scrap_ta_restaurant import scrap

info = dict()

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 2)[0]

# webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
service = Service(parent_folder + f"/extra/chromedriver.exe")

# Get file with the restaurants links
data = dict()
with open(parent_folder + f"/data/trip_advisor/links_ta.json", 'r', encoding='utf-8') as f:
    data = json.load(f)
    f.close()

# For each restaurant, scrap data
for i in range(len(data["restaurants"])):
    try:
        scrap(data["restaurants"][i]["link"], data["restaurants"][i]["name"], i)
    except:
        print(f'Error: {data["restaurants"][i]["link"]}')