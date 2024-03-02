import os
import time
import math
import boto3
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from utils.helper import store_in_s3_bucket, set_chrome_options, CHROMEDRIVER_PATH, ta_bucket

logging.getLogger().setLevel(logging.INFO)
month_code = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago", 9: "sept", 10: "oct",
              11: "nov", 12: "dic"}


def handler(event, context) -> None:
    """
    Obtains all the restaurants links that are in trip-advisor
    event: day of the month
    context: month of the year
    Returns: None
    """
    dynamodb = boto3.client('dynamodb')

    ta_place_id = event.get("trip_advisor_place_id", None)
    if ta_place_id is None:
        logging.error("missing trip_advisor_place_id variable in the event")
        return
    
    only_first_page = event.get("only_first_page", False)

    places_db_table = f"trip-advisor-place-links-db-{os.environ['stage']}"
    response = dynamodb.get_item(
        Key={
            'ta_place_id': {
                'S': ta_place_id
            }
        },
        TableName=places_db_table
    )
    ta_place_link = response.get("Item", {}).get('link', None)
    if ta_place_link is None:
        logging.error(f"{ta_place_id} link could not be found in the {places_db_table} table")
        return
    logging.info(f"Obtained trip_advisor URL for place id: {ta_place_id}")

    options = set_chrome_options()
    driver = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()
    tomorrow = today + timedelta(days=1)

    # load page
    driver.get(ta_place_link.get('S', None))
    time.sleep(10)

    # accept cookies
    try:
        driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
        time.sleep(10)
    except NoSuchElementException:
        logging.info("There is not cookies message")

    # GET BASIC INFO OF THE RESTAURANTS
    restaurants_per_page = 30
    # number of found restaurants
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    results = driver.find_element(By.CSS_SELECTOR, '.biGQs._P.pZUbB.hzzSG.KxBGd')
    num_restaurants = results.find_element(By.CSS_SELECTOR, '.b').get_attribute("innerHTML")
    logging.info(f"{num_restaurants} restaurants have been found")
    links = []

    if only_first_page:
        logging.info(f"Obtaining links from {0} to {restaurants_per_page}")
        # Scrap info of each restaurant
        all_restaurants = driver.find_elements(By.CSS_SELECTOR, '.vIjFZ.Gi.o.VOEhq')
        for restaurant in all_restaurants:
            restaurant_data = restaurant.find_element(By.CSS_SELECTOR, '.BMQDV._F.Gv.wSSLS.SwZTJ.FGwzt.ukgoS')
            restaurant_name = restaurant_data.get_attribute('innerHTML')
            restaurant_name = restaurant_name[restaurant_name.find('.')+2:]
            links.append({"name": restaurant_name, 'link': restaurant_data.get_attribute('href')})
    else:
        # Scrap all pages
        for i in range(math.ceil(int(num_restaurants)/restaurants_per_page)):
            logging.info(f"Obtaining links from {i*restaurants_per_page} to {(i+1)*restaurants_per_page}")
            # Scrap info of each restaurant
            all_restaurants = driver.find_elements(By.CSS_SELECTOR, '.vIjFZ.Gi.o.VOEhq')
            for restaurant in all_restaurants:
                restaurant_data = restaurant.find_element(By.CSS_SELECTOR, '.BMQDV._F.Gv.wSSLS.SwZTJ.FGwzt.ukgoS')
                restaurant_name = restaurant_data.get_attribute('innerHTML')
                restaurant_name = restaurant_name[restaurant_name.find('.')+2:]
                links.append({"name": restaurant_name, 'link': restaurant_data.get_attribute('href')})
            # Navigate to the next page
            pages_links = driver.find_element(By.CSS_SELECTOR, '.gBgtO')
            if i < int(num_restaurants)//restaurants_per_page - 1:
                pages_links.find_element(By.XPATH, "//a/span/span[normalize-space()="+str(i+2)+"]").find_element(By.XPATH, "./../..").click()
                time.sleep(15)

    driver.close()
    driver.quit()
    logging.info("Obtained all links. Storing file to S3")

    # Write in a file all the data
    today_iso = today.isocalendar()
    data = {
        "restaurants": links,
        "datetime": today.strftime("%Y/%m/%d, %H:%M:%S")
    }
    filename = f"ta_restaurants_links_{ta_place_id}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
    s3_path = f"raw_data/links/{ta_place_id}/{today_iso.year}/{today_iso.week}"
    store_in_s3_bucket(ta_bucket, s3_path, data, filename)
    logging.info("Process finished")
