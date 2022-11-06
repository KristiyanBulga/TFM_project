import time, json
from selenium import webdriver
from selenium.webdriver.support.ui import Select


### find all links to restaurants in tripadvisor
### webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome("C:/Users/krist/Downloads/chromedriver.exe", options=options)

### load page
driver.get("https://www.tripadvisor.es/Restaurants-g187486-Albacete_Province_of_Albacete_Castile_La_Mancha.html")
time.sleep(2)

### accept cookies
driver.find_element_by_id('onetrust-accept-btn-handler').click()
time.sleep(1)

### select date
driver.find_element_by_css_selector('.unified-picker.ui_picker').click()
months = driver.find_elements_by_css_selector(".dsdc-month")
month_name = months[1].find_element_by_css_selector(".dsdc-month-title")
print("Seleccionando fecha del mes:", month_name.get_attribute("innerHTML"))
dates = months[1].find_elements_by_css_selector(".dsdc-cell.dsdc-day")
dates[10].click()
time.sleep(1)

### select hour
print("Ponemos la hora a las 19:30")
selector_div = driver.find_element_by_css_selector('.ui_picker.resv_img.drop_down_input.drop_down_select.notOldIE.inner.time_dropdown.twenty_four_format')
select = Select(selector_div.find_element_by_css_selector('.drop_down_select_elmt'))
select.select_by_visible_text('19:30')
time.sleep(1)

### select people
print("Fijamos cantidad de personas a 1")
selector_div = driver.find_element_by_css_selector('.ui_picker.resv_img.drop_down_input.drop_down_select.notOldIE.inner.ppl_dropdown ')
select = Select(selector_div.find_element_by_css_selector('.drop_down_select_elmt'))
select.select_by_value('1')
time.sleep(1)

### push search button
driver.find_element_by_id('RESTAURANT_SEARCH_BTN').click()
time.sleep(2)

### GET BASIC INFO OF THE RESTAURANTS
restaurants_per_page = 30
### number of found restaurants
num_restaurants = driver.find_element_by_id('component_36').find_element_by_css_selector('.b').get_attribute("innerHTML")
print('Se han encontrado', num_restaurants, 'restaurantes')
links = dict()

### Scrap all pages
print("Sacando los links de los restaurantes ...")
for i in range(int(num_restaurants)//restaurants_per_page+1):
    ### Scrap info of each restaurant
    restaurant_list = driver.find_element_by_id('component_2')
    all_restaurants = restaurant_list.find_elements_by_css_selector('.Lwqic.Cj.b')
    for restaurant in all_restaurants:
        restaurant_name = restaurant.get_attribute('innerHTML')
        restaurant_name = restaurant_name[restaurant_name.find('.')+2:]
        links[restaurant_name] = {"name":restaurant_name, 'link':restaurant.get_attribute('href')}
    ### Navigate to the next page
    pages_links = driver.find_element_by_css_selector('.unified.pagination.js_pageLinks')
    if i < int(num_restaurants)//restaurants_per_page:
        pages_links.find_element_by_xpath("//a[normalize-space()="+str(i+2)+"]").click()
    time.sleep(2)
print("Se han sacado los links correctamente")
### Write in a file all the data
with open('data/links_ta.json', 'w', encoding='utf-8') as f:
    json.dump({'restaurants':links}, f, ensure_ascii=False)