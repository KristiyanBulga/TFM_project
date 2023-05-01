import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service

# find all links to restaurants in tripadvisor
# web_driver options
options = webdriver.ChromeOptions()
service = Service("C:/Users/krist/Downloads/chromedriver.exe")
month_code = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago", 9: "sept", 10: "oct",
              11: "nov", 12: "dic"}

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 3)[0]


def scrap_links(day_num: int, month_num: int, year_num: int) -> None:
    """
    Obtains all the restaurants links that are in trip-advisor
    Args:
        day_num: day of the month
        month_num: month of the year
        year_num:
    Returns: None
    """
    options.add_argument("--headless")  # Hide the GUI
    driver = webdriver.Chrome(service=service, options=options)

    # load page
    driver.get("https://www.tripadvisor.es/Restaurants-g187486-Albacete_Province_of_Albacete_Castile_La_Mancha.html")
    time.sleep(2)

    # accept cookies
    driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
    time.sleep(1)

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
    time.sleep(10)

    # select hour
    # selector_div = driver.find_element(By.CSS_SELECTOR, '.ui_picker.resv_img.drop_down_input.drop_down_select.notOldIE.inner.time_dropdown.twenty_four_format')
    # select = Select(selector_div.find_element(By.CSS_SELECTOR, '.drop_down_select_elmt'))
    # select.select_by_visible_text('19:30')
    # time.sleep(1)

    # select people
    selector_div = driver.find_element(By.CSS_SELECTOR, '.ui_picker.resv_img.drop_down_input.drop_down_select.notOldIE.inner.ppl_dropdown ')
    select = Select(selector_div.find_element(By.CSS_SELECTOR, '.drop_down_select_elmt'))
    select.select_by_value('1')
    time.sleep(1)

    # push search button
    driver.find_element(By.ID, 'RESTAURANT_SEARCH_BTN').click()
    time.sleep(4)

    # GET BASIC INFO OF THE RESTAURANTS
    restaurants_per_page = 30
    # number of found restaurants
    driver.save_screenshot(parent_folder + '/data/capture.png')
    num_restaurants = driver.find_element(By.ID, 'component_36').find_element(By.CSS_SELECTOR,
                                                                              '.b').get_attribute("innerHTML")
    print(f"{num_restaurants} restaurants have been found")
    links = []

    # Scrap all pages
    for i in range(int(num_restaurants)//restaurants_per_page+1):
        print(i)
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
        time.sleep(5)

    # Write in a file all the data
    with open(parent_folder + '/data/trip_advisor/links_ta.json', 'w', encoding='utf-8') as f:
        json.dump({'restaurants': links}, f, ensure_ascii=False)
        f.close()


scrap_links(23, 4, 2023)
