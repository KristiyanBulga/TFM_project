import datetime
import time
import json
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

info = dict()

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 3)[0]

# webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
service = Service(parent_folder + f"/extra/chromedriver.exe")

naming = {"Comida": "score_food", "Servicio": "score_service", "Calidad/precio": "score_price_quality",
          "Atmósfera": "score_atmosphere"}
months_nums = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
               "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def scrap(url: str, res_name: str) -> None:
    """
    Scrap the restaurant data from trip-advisor
    Parameters:
        url: The url of the restaurant in tripadvisor
        res_name: The name of the restaurant in tripadvisor
    """
    driver = webdriver.Chrome(service=service, options=options)
    ta_link = url
    # load page
    driver.get(ta_link)
    time.sleep(3)

    # accept cookies
    driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
    time.sleep(1)

    # get euros symbol
    try:
        before_images = driver.find_element(By.CSS_SELECTOR, '.lBkqB._T')
        euros = before_images.find_element(By.CSS_SELECTOR, '.dlMOJ')
        symbols = euros.get_attribute("innerHTML")
        info["symbol"] = symbols if '€' in symbols else None
    except:
        info["symbol"] = None

    # Before images
    # The site is claimed (Someone of the restaurant manages the profile)
    try:
        driver.find_element(By.CSS_SELECTOR, '.ui_icon.verified-checkmark.BVOnm.d')
        info["claimed"] = True
    except NoSuchElementException:
        info["claimed"] = False

    # Menu ???

    # Schedule
    try:
        driver.find_element(By.CSS_SELECTOR, '.DsyBj.YTODE').click()
        schedule = driver.find_element(By.CSS_SELECTOR, '.KWdaU.Za.f.e')
        all_days = schedule.find_elements(By.CSS_SELECTOR, ".RiEuX.f")
        info["schedule"] = dict()
        for day in all_days:
            day_of_the_week = day.find_element(By.CSS_SELECTOR, '.BhOTk').get_attribute("innerHTML")
            info["schedule"][day_of_the_week] = []
            hours = day.find_element(By.CSS_SELECTOR, '.lieuc')
            hours_data = hours.find_elements(By.XPATH, './div/span')
            for hour_data in hours_data:
                try:
                    aux = hour_data.find_elements(By.XPATH, './span')
                    hour = aux[0].get_attribute('innerHTML')
                    evening = "tarde" in aux[1].get_attribute('innerHTML')
                    if evening and int(hour.split(":")[0]) < 12:
                        hour = hour.split(":")
                        hour = str(int(hour[0]) + 12) + ":" + hour[1]
                    elif not evening and int(hour.split(":")[0]) == 12:
                        hour = hour.split(":")
                        hour = "00" + ":" + hour[1]
                    info["schedule"][day_of_the_week].append(hour)
                except:
                    pass
        schedule.find_element(By.CSS_SELECTOR, '.Tatqp._Q.t._U.c._S').click()
    except:
        info["schedule"] = None

    # Cards after images
    cards = driver.find_elements(By.CSS_SELECTOR, '.xLvvm.ui_column.is-12-mobile.is-4-desktop')

    # "Score and opinions" card
    # Overall score
    try:
        score = cards[0].find_element(By.CSS_SELECTOR, '.ZDEqb')
        score = score.get_attribute('innerHTML')
        score = re.search('.+?(?=<!--)', score).group(0)
        score = str.replace(score, ",", ".")
        info["score_overall"] = float(score)
    except:
        info["score_overall"] = None

    # ranking
    try:
        ranking = cards[0].find_element(By.CSS_SELECTOR, '.cNFlb')
        ranking = ranking.find_element(By.TAG_NAME, "span")
        ranking = ranking.get_attribute('innerHTML')
        ranking = re.search('(?<=N.º ).*$', ranking).group(0)
        info["ranking"] = int(ranking)
    except:
        info["ranking"] = None
    # Traveller's choice
    try:
        driver.find_element(By.CSS_SELECTOR, '.ui_icon.travelers-choice-badge.YbepA')
        info["travellers_choice"] = True
    except NoSuchElementException:
        info["travellers_choice"] = False

    # More scores
    for score_type in naming:
        info[naming[score_type]] = None
    scores = cards[0].find_elements(By.CSS_SELECTOR, '.DzMcu')
    for score in scores:
        name = score.find_element(By.CSS_SELECTOR, '.BPsyj').get_attribute('innerHTML')
        rating = score.find_element(By.CSS_SELECTOR, '.ui_bubble_rating')
        rating = rating.get_attribute('class').split()[1]
        rating = float(re.search('(?<=bubble_).*$', rating).group(0))
        info[naming[name]] = rating / 10

    # Second card: we inspect directly the all details option
    try:
        cards[1].find_element(By.CSS_SELECTOR, '.OTyAN._S.b').click()
        all_details = driver.find_element(By.CSS_SELECTOR, '.VZmgo.D.X0.X1.Za')
        columns = all_details.find_elements(By.CSS_SELECTOR, '.ui_column')
        # Some general information
        # info["general_info"] = columns[0].find_element(By.CSS_SELECTOR, '.jmnaM').get_attribute('innerHTML')
        details_divs = columns[-1].find_elements(By.XPATH, './div/div')

        for dd in details_divs:
            title = dd.find_element(By.CSS_SELECTOR, '.tbUiL.b').get_attribute('innerHTML').lower()
            value = dd.find_element(By.CSS_SELECTOR, '.SrqKb').get_attribute('innerHTML')

            if title == "rango de precios":
                info["price"] = dict()
                prices = value.split('-')
                info["price"]["lower"] = float(re.search('.+?(?=&nbsp)', prices[0].strip()).group(0))
                info["price"]["upper"] = float(re.search('.+?(?=&nbsp)', prices[1].strip()).group(0))
            elif title == "tipos de cocina":
                info["type"] = [x.strip() for x in value.split(",")]
            elif title == "dietas especiales":
                info["special_diets"] = [x.strip() for x in value.split(",")]
            elif title == "comidas":
                info["meals"] = [x.strip() for x in value.split(",")]
            elif title == "ventajas":
                info["advantages"] = [x.strip() for x in value.split(",")]
        all_details.find_element(By.CSS_SELECTOR, '.zPIck._Q.Z1.t._U.c._S.zXWgK').click()
    except:
        info["price"] = None
        info["type"] = None
        info["special_diets"] = None
        info["meals"] = None
        info["advantages"] = None

    info["address"] = None
    info["webpage"] = None
    info["email"] = None
    info["phone"] = None
    # Third card
    divs = cards[2].find_elements(By.CSS_SELECTOR, '.IdiaP.Me')
    for div in divs:
        try:
            div.find_element(By.CSS_SELECTOR, '.ui_icon.map-pin-fill.XMrSj')
            link = div.find_element(By.CSS_SELECTOR, '.YnKZo.Ci.Wc._S.C.FPPgD')
            address = link.find_element(By.CSS_SELECTOR, '.yEWoV')
            info["address"] = {
                "name": address.get_attribute('innerHTML'),
                "link": link.get_attribute('href')
            }
        except:
            pass
        try:
            div.find_element(By.CSS_SELECTOR, '.ui_icon.laptop.XMrSj')
            link = div.find_element(By.CSS_SELECTOR, '.YnKZo.Ci.Wc._S.C.FPPgD')
            info["webpage"] = link.get_attribute('href')
        except:
            pass
        try:
            div.find_element(By.CSS_SELECTOR, '.ui_icon.email.XMrSj')
            link = div.find_element(By.TAG_NAME, 'a')
            info['email'] = re.search('(?<=mailto:)(.*)(?=\?subject)', link.get_attribute('href')).group(0)
        except:
            pass
        try:
            div.find_element(By.CSS_SELECTOR, '.ui_icon.phone.XMrSj')
            link = div.find_element(By.TAG_NAME, 'a')
            info['phone'] = re.search('(?<=tel:)(.*)', link.get_attribute('href')).group(0)
        except:
            pass

    # Comments
    reviews_list = driver.find_element(By.ID, 'taplc_location_reviews_list_resp_rr_resp_0')
    reviews = reviews_list.find_elements(By.XPATH, './div/div')
    reviews_info = []
    dt_upper = datetime.datetime(2023, 5, 20)
    # dt_upper = datetime.datetime.now()
    dt_upper = dt_upper.replace(hour=0, minute=0, second=0, microsecond=0)
    dt_lower = dt_upper - datetime.timedelta(weeks=1)
    for row in reviews:
        rating = 0
        try:
            rating = row.find_element(By.CSS_SELECTOR, '.ui_bubble_rating')
            rating = rating.get_attribute('class').split()[1]
            rating = float(re.search('(?<=bubble_).*$', rating).group(0))
            rating = rating / 10
        except:
            continue
        date = row.find_element(By.CSS_SELECTOR, '.ratingDate').get_attribute('title').split()
        date_review = datetime.datetime(int(date[4]), months_nums[date[2]], int(date[0]))
        title = row.find_element(By.CSS_SELECTOR, '.noQuotes').get_attribute('innerHTML')
        text_html = row.find_element(By.CSS_SELECTOR, '.partial_entry')
        text = text_html.get_attribute('innerHTML')
        # Parse date and select it
        if dt_lower <= date_review <= dt_upper:
            reviews_info.append({
                "date_review": date_review.strftime('%Y_%m_%d'),
                "title": title,
                "text": text,
                "rating": rating
            })

    info["reviews"] = reviews_info

    id_ta = re.search('(?<=Restaurant_Review-)(.*)(?=-Reviews)', url).group(0)

    with open(parent_folder + f"/data/trip_advisor/restaurants_ta/{id_ta}.json", 'w', encoding='utf-8') as f:
        json.dump({'restaurant': {"ta_link": ta_link, "name": res_name, "data": info}}, f, ensure_ascii=False)
        f.close()

    driver.quit()
