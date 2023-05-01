import time
import logging
from tempfile import mkdtemp
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from utils.helper import store_in_s3_bucket, CHROMIUM_PATH, CHROMEDRIVER_PATH

import boto3

ta_bucket = "trip-advisor-dev"

month_code = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago", 9: "sept", 10: "oct",
              11: "nov", 12: "dic"}


def handler(event, context) -> None:
    """
    Obtains all the restaurants links that are in trip-advisor
    event: day of the month
    context: month of the year
    Returns: None
    """
    options = Options()
    options.binary_location = CHROMIUM_PATH
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu-sandbox')
    options.add_argument('--window-size=1920x1080')
    options.add_argument(
        '"user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"')

    # options.add_argument("--headless")  # Hide the GUI
    # options.add_argument("--no-sandbox")  # No protection needed
    # options.add_argument("--window-size=1920x1080")  # Setup a fixed screens size
    # options.add_argument("--single-process")  # Lambda only give us only one CPU
    # options.add_argument("--no-zygote")  # Don't create zygote processes because Lambda give us only one CPU
    # options.add_argument("--disable-dev-shm-usage")  # Create temporary folder for shared memory files
    # options.add_argument("--disable-dev-tools")  # Disable Chrome dev tools
    # options.add_argument(f"--user-data-dir={mkdtemp()}")  # Create temporary folder to user data
    # options.add_argument(f"--data-path={mkdtemp()}")  # Create temporary folder to browser data
    # options.add_argument(f"--disk-cache-dir={mkdtemp()}")  # Create temporary folder to cache
    # options.add_argument("--remote-debugging-port=9222")
    # options.add_argument("--enable-javascript")
    # options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)

    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    day_num, month_num, year_num = tomorrow.day, tomorrow.month, tomorrow.year
    image_name = f'{year_num}-{month_num}-{day_num}-{today.hour}-{today.minute}'
    s3_client = boto3.client('s3', region_name='us-east-1')

    # load page
    driver.get("https://www.tripadvisor.es/Restaurants-g187486-Albacete_Province_of_Albacete_Castile_La_Mancha.html")
    time.sleep(5)
    path_file = f'/tmp/{image_name}_01_first_load.png'
    driver.save_screenshot(path_file)
    s3_client.upload_file(path_file, ta_bucket, f"testing/{image_name}_01_first_load.png")

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

    path_file = f'/tmp/{image_name}_02_before_button.png'
    driver.save_screenshot(path_file)
    s3_client.upload_file(path_file, ta_bucket, f"testing/{image_name}_02_before_button.png")

    # push search button
    driver.find_element(By.ID, 'RESTAURANT_SEARCH_BTN').click()
    time.sleep(45)

    path_file = f'/tmp/{image_name}_03_after_button.png'
    driver.save_screenshot(path_file)
    s3_client.upload_file(path_file, ta_bucket, f"testing/{image_name}_03_after_button.png")

    # GET BASIC INFO OF THE RESTAURANTS
    restaurants_per_page = 30
    # number of found restaurants
    component_36 = driver.find_element(By.ID, 'component_36')
    # num_restaurants = component_36.find_element(By.CSS_SELECTOR, '.b').get_attribute("innerHTML")
    num_restaurants = 354
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
            time.sleep(12)
            path_file = f'/tmp/{image_name}_04_page_{i+2}.png'
            driver.save_screenshot(path_file)
            s3_client.upload_file(path_file, ta_bucket, f"testing/{image_name}_04_page_{i+2}.png")

    driver.close()
    driver.quit()
    logging.info("Obtained all links. Storing file to S3")

    # Write in a file all the data
    s3_path = f"raw_data/links/{today.strftime('%Y/%m/%d')}"
    filename = f"ta_restaurants_links_{today.strftime('%Y%m%d%H%M%S')}"
    store_in_s3_bucket(ta_bucket, s3_path, links, filename)
    logging.info("Process finished")
