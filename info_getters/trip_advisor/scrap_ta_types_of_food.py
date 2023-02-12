import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 2)[0]

# webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
service = Service(parent_folder + f"/extra/chromedriver.exe")
driver = webdriver.Chrome(service=service, options=options)

# load page
driver.get("https://www.tripadvisor.es/Restaurants-g187486-Albacete_Province_of_Albacete_Castile_La_Mancha.html")
time.sleep(2)

# accept cookies
driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
time.sleep(1)

# Find the section we are looking for
filters = driver.find_elements(By.CSS_SELECTOR, '.yhkZG.Z.Pe.PN.Pr.PA')
i, aux = 0, filters[0].find_element(By.CSS_SELECTOR, '.SoNfr.F1._T.b').get_attribute('innerHTML')
while aux != 'Tipo de cocina':
    i += 1
    aux = filters[i].find_element(By.CSS_SELECTOR, '.SoNfr.F1._T.b').get_attribute('innerHTML')

# Get the different types of food
data = filters[i].find_element(By.CSS_SELECTOR, '._').find_elements(By.CSS_SELECTOR, '.mTKbF')
tags = [x.find_element(By.XPATH, 'span').get_attribute('innerHTML') for x in data]

print(tags)
