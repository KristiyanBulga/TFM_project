import time
import boto3
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from utils.helper import store_in_s3_bucket, set_chrome_options, CHROMEDRIVER_PATH, ta_bucket

logging.getLogger().setLevel(logging.INFO)
places_db_table = "trip-advisor-place-links-db"
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
    logging.info(f"Obtained trip_advisor URL for place id: {ta_place_id}")

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

    options = set_chrome_options()
    driver = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)

    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    day_num, month_num, year_num = tomorrow.day, tomorrow.month, tomorrow.year

    # load page
    driver.get(ta_place_link.get('S', None))
    time.sleep(5)

    # accept cookies
    try:
        driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
        time.sleep(5)
    except NoSuchElementException:
        logging.info("There is not cookies message")

    # select date
    driver.find_element(By.CSS_SELECTOR, '.unified-picker.ui_picker').click()
    months = driver.find_elements(By.CSS_SELECTOR, ".dsdc-month")
    for month in months:
        month_name = month.find_element(By.CSS_SELECTOR, ".dsdc-month-title")
        if month_name.get_attribute("innerHTML") == f"{month_code[month_num]} {year_num}":
            clicked_date = False
            dates = month.find_elements(By.CSS_SELECTOR, ".dsdc-cell.dsdc-day")
            for date in dates:
                if date.get_attribute("innerHTML") == str(day_num):
                    date.click()
                    clicked_date = True
                    break
            if not clicked_date:
                raise Exception("ERROR: The specified day does not exist")
            break
    time.sleep(3)

    # select hour
    selector_div = driver.find_element(By.CSS_SELECTOR, '.ui_picker.resv_img.drop_down_input.drop_down_select.notOldIE.inner.time_dropdown.twenty_four_format')
    select = Select(selector_div.find_element(By.CSS_SELECTOR, '.drop_down_select_elmt'))
    select.select_by_visible_text('19:30')
    time.sleep(3)

    # select people
    selector_div = driver.find_element(By.CSS_SELECTOR, '.ui_picker.resv_img.drop_down_input.drop_down_select.notOldIE.inner.ppl_dropdown ')
    select = Select(selector_div.find_element(By.CSS_SELECTOR, '.drop_down_select_elmt'))
    select.select_by_value('1')
    time.sleep(3)

    # push search button
    driver.find_element(By.ID, 'RESTAURANT_SEARCH_BTN').click()
    time.sleep(10)

    # GET BASIC INFO OF THE RESTAURANTS
    restaurants_per_page = 30
    # number of found restaurants
    component_36 = driver.find_element(By.ID, 'component_36')
    num_restaurants = component_36.find_element(By.CSS_SELECTOR, '.b').get_attribute("innerHTML")
    logging.info(f"{num_restaurants} restaurants have been found")
    links = []

    # Scrap all pages
    for i in range(int(num_restaurants)//restaurants_per_page+1):
        logging.info(f"Obtaining links from {i*num_restaurants} to {(i+1)*num_restaurants}")
        # Scrap info of each restaurant
        restaurant_list = driver.find_element(By.ID, 'component_2')
        all_restaurants = restaurant_list.find_elements(By.CSS_SELECTOR, '.Lwqic.Cj.b')
        for restaurant in all_restaurants:
            restaurant_name = restaurant.get_attribute('innerHTML')
            restaurant_name = restaurant_name[restaurant_name.find('.')+2:]
            links.append({"name": restaurant_name, 'link': restaurant.get_attribute('href')})
        # Navigate to the next page
        pages_links = driver.find_element(By.CSS_SELECTOR, '.unified.pagination.js_pageLinks')
        if i < int(num_restaurants)//restaurants_per_page:
            pages_links.find_element(By.XPATH, "//a[normalize-space()="+str(i+2)+"]").click()
            time.sleep(10)

    driver.close()
    driver.quit()
    logging.info("Obtained all links. Storing file to S3")

    # Write in a file all the data
    filename = f"ta_restaurants_links_{ta_place_id}_{today.strftime('%Y%m%d%H%M%S')}"
    s3_path = f"raw_data/links/{today.strftime('%Y/%m/%d')}"
    store_in_s3_bucket(ta_bucket, s3_path, links, filename)
    logging.info("Process finished")
