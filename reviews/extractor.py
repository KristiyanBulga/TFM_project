import re
import os
import time
import json
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options

logging.getLogger().setLevel(logging.INFO)
CHROMEDRIVER_PATH = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\opt\\chromedriver.exe"
CHROMIUM_PATH = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\opt\\headless-chromium"

months_nums = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

def handler() -> None:
    """
    Scrap the restaurant data from trip-advisor
    """
    list_reviews = [{
        "place": {
            "S": "g187486-d11938465"
        },
        "hash": {
            "S": "288c39f2c4e931dd4686aaf261d8f2fc0f2447d8f0f195d4a43e02da5ba0d9c9"
        },
        "platform": {
            "S": "google_maps"
        },
        "rate": {
            "N": "5"
        },
        "review": {
            "S": "Estuvimos por Albacete y cenamos tapas aquí. Las tapas estaban muy buenas y nos gustó también el tataki de atún y sobre todo el solomillo de cerdo con salsa chimichurri y boniato. Nos atendieron muy bien. Recomendable!"
        },
        "ts": {
            "N": "1723790571000"
        }
    }]
    for review in list_reviews:
        text = review["review"]["S"] # TODO : check if empty
        # options = Options()
        # options.binary_location = CHROMIUM_PATH
        options = webdriver.ChromeOptions() 
        # Adding argument to disable the AutomationControlled flag 
        options.add_argument("--disable-blink-features=AutomationControlled") 
        # Exclude the collection of enable-automation switches 
        options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
        # Turn-off userAutomationExtension 
        options.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(CHROMEDRIVER_PATH, options=options)

        # load page
        driver.get("https://chatgpt.com/")
        # time.sleep(10)
        input()
        driver.find_element(By.CSS_SELECTOR, "btn.relative.btn-blue.btn-large").click()
        input()
        # Comments
        # reviews_list = driver.find_element(By.ID, 'taplc_location_reviews_list_resp_rr_resp_0')
        # reviews = reviews_list.find_elements(By.XPATH, './div/div')
        # reviews_info = []
        # if body.get("custom_date", None) is not None:
        #     dt_upper = datetime.strptime(body["custom_date"], "%Y_%m_%d_%H_%M_%S")
        # else:
        #     dt_upper = datetime.now()
        # dt_upper = dt_upper.replace(hour=0, minute=0, second=0, microsecond=0)
        # dt_lower = dt_upper - timedelta(weeks=1)
        # for row in reviews:
        #     rating = 0
        #     try:
        #         rating = row.find_element(By.CSS_SELECTOR, '.ui_bubble_rating')
        #         rating = rating.get_attribute('class').split()[1]
        #         rating = float(re.search('(?<=bubble_).*$', rating).group(0))
        #         rating = rating / 10
        #     except:
        #         continue
        #     date = row.find_element(By.CSS_SELECTOR, '.ratingDate').get_attribute('title').split()
        #     date_review = datetime(int(date[4]), months_nums[date[2]], int(date[0]))
        #     title = row.find_element(By.CSS_SELECTOR, '.noQuotes').get_attribute('innerHTML')
        #     text_html = row.find_element(By.CSS_SELECTOR, '.partial_entry')
        #     text = text_html.get_attribute('innerHTML')
        #     # Parse date and select it
        #     if dt_lower <= date_review <= dt_upper:
        #         reviews_info.append({
        #             "date_review": date_review.strftime('%Y_%m_%d'),
        #             "title": title,
        #             "text": text,
        #             "rating": rating
        #         })

        # info["reviews"] = reviews_info

        driver.close()
        driver.quit()



handler()