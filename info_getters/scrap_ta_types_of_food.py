import time, json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service


### find all links to restaurants in tripadvisor
### webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
service = Service("C:/Users/krist/Downloads/chromedriver.exe")
driver = webdriver.Chrome(service=service, options=options)

### load page
driver.get("https://www.tripadvisor.es/Restaurants-g187486-Albacete_Province_of_Albacete_Castile_La_Mancha.html")
time.sleep(2)

### accept cookies
driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
time.sleep(1)

### 
filters = driver.find_elements(By.CSS_SELECTOR, '.yhkZG.Z.Pe.PN.Pr.PA')
i, aux = 0, filters[0].find_element(By.CSS_SELECTOR, '.SoNfr.F1._T.b').get_attribute('innerHTML')
while aux != 'Tipo de cocina':
    i += 1
    aux = filters[i].find_element(By.CSS_SELECTOR, '.SoNfr.F1._T.b').get_attribute('innerHTML')

# print(filters[i].find_element(By.CSS_SELECTOR, '._').get_attribute('innerHTML'))
data = filters[i].find_element(By.CSS_SELECTOR, '._').find_elements(By.CSS_SELECTOR, '.mTKbF')
for x in data:
    print(x.find_element(By.XPATH, 'span').get_attribute('innerHTML'))


### Write in a file all the data
# with open('data/links_ta.json', 'w', encoding='utf-8') as f:
#     json.dump({'restaurants':links}, f, ensure_ascii=False)