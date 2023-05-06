import re
import time
import boto3
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from utils.helper import store_in_s3_bucket, set_chrome_options, CHROMEDRIVER_PATH, ta_bucket

logging.getLogger().setLevel(logging.INFO)
naming = {"Comida": "score_food", "Servicio": "score_service", "Calidad/precio": "score_price_quality",
          "Atmósfera": "score_atmosphere"}


def handler(event, context) -> None:
    """
    Scrap the restaurant data from trip-advisor
    """
    for request in event.get("Records", []):
        body = request.get("body", {})
        info = dict()

        ta_link = body.get("link", None)
        if ta_link is None:
            logging.error("Could not find a link to obtain data from trip advisor")
            return

        options = set_chrome_options()
        driver = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)

        # load page
        driver.get(ta_link)
        time.sleep(10)

        # accept cookies
        try:
            driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
            time.sleep(5)
        except NoSuchElementException:
            logging.info("There is not cookies message")

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

        driver.close()
        driver.quit()

        if body.get("trip_advisor_complete_id", None) is not None:
            restaurant_id_ta = body["trip_advisor_complete_id"]
        else:
            restaurant_id_ta = re.search('(?<=Restaurant_Review-)(.*)(?=-Reviews)', ta_link).group(0)
        logging.info(f"Obtained all info for {restaurant_id_ta} restaurant. Storing file to S3")

        today = datetime.today()
        # Write in a file all the data
        data_to_store = {'ta_restaurant': {"link": ta_link,
                                           "name": body.get("restaurant_name", restaurant_id_ta),
                                           "data": info}}
        filename = f"{restaurant_id_ta}_{today.strftime('%H%M%S')}"
        s3_path = f"raw_data/restaurants/{today.strftime('%Y/%m/%d')}"
        store_in_s3_bucket(ta_bucket, s3_path, data_to_store, filename)
        logging.info(f"Process finished for {restaurant_id_ta}")

        # Update dynamodb information
        # response = dynamodb.get_item(
        #     Key={
        #         'ta_place_id': {
        #             'S': ta_place_id
        #         }
        #     },
        #     TableName=places_db_table
        # )
        # ta_place_link = response.get("Item", {}).get('link', None)
        # if ta_place_link is None:
        #     logging.error(f"{ta_place_id} link could not be found in the {places_db_table} table")
        #     return
        # table = boto3.resource('dynamodb').Table('my_table')
        #
        # table.update_item(
        #     Key={'ta_place_id': '', 'ta_restaurant_id': ''},
        #     AttributeUpdates={
        #         'status': 'complete',
        #     },
        # )
