import re
import os
import time
import json
import boto3
import botocore
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from utils.helper import store_in_s3_bucket, set_chrome_options, CHROMEDRIVER_PATH, ta_bucket

logging.getLogger().setLevel(logging.INFO)
naming = {"Comida": "score_food", "Servicio": "score_service", "Calidad/precio": "score_price_quality",
          "Atmósfera": "score_atmosphere"}
months_nums = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
               "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def handler(event, context) -> None:
    """
    Scrap the restaurant data from trip-advisor
    """
    for request in event.get("Records", []):
        body = json.loads(request.get("body", "{}"))
        info = dict()
        logging.info(f"Event body: {body}")

        ta_link = body.get("link", None)
        if ta_link is None:
            logging.error("Could not find a link to obtain data from trip advisor")
            return

        if body.get("trip_advisor_complete_id", None) is not None:
            restaurant_id_ta = body["trip_advisor_complete_id"]
        else:
            restaurant_id_ta = re.search('(?<=Restaurant_Review-)(.*)(?=-Reviews)', ta_link).group(0)

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
            logging.info(f"[{restaurant_id_ta}]There is not cookies message")

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
            schedule.find_element(By.CSS_SELECTOR, '.UikNM._G.B-._S._W._T.c.G_.wSSLS.TXrCr').click()
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
        divs = cards[2].find_element(By.CSS_SELECTOR, '.f.e').find_elements(By.TAG_NAME, 'div')
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

        # Num Comments
        num_reviews = driver.find_element(By.CSS_SELECTOR, '.reviews_header_count').get_attribute('innerHTML')
        info['num_reviews'] = num_reviews[1:-1]

        # Comments
        reviews_list = driver.find_element(By.ID, 'taplc_location_reviews_list_resp_rr_resp_0')
        reviews = reviews_list.find_elements(By.XPATH, './div/div')
        reviews_info = []
        if body.get("custom_date", None) is not None:
            dt_upper = datetime.strptime(body["custom_date"], "%Y_%m_%d_%H_%M_%S")
        else:
            dt_upper = datetime.now()
        dt_upper = dt_upper.replace(hour=0, minute=0, second=0, microsecond=0)
        dt_lower = dt_upper - timedelta(weeks=1)
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
            date_review = datetime(int(date[4]), months_nums[date[2]], int(date[0]))
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

        driver.close()
        driver.quit()

        logging.info(f"[{restaurant_id_ta}] Obtained all restaurant info. Storing file to S3")

        if body.get("custom_date", None) is not None:
            today = datetime.strptime(body["custom_date"], "%Y_%m_%d_%H_%M_%S")
        else:
            today = datetime.today()
        today_iso = today.isocalendar()
        ids = restaurant_id_ta.split('-')
        ta_place_id = body.get('ta_place_id', ids[0])
        # Write in a file all the data
        data_to_store = {
            'ta_restaurant': {
                "link": ta_link,
                "name": body.get("restaurant_name", restaurant_id_ta),
                "data": info,
                "datetime": today.strftime("%Y/%m/%d, %H:%M:%S"),
                "week_obtained_link": body.get("week_obtained_link", f"{today_iso.year}-{today_iso.week}")
            }
        }
        filename = f"{restaurant_id_ta}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
        s3_path = f"raw_data/restaurants/{ids[0]}/{ids[1]}/{today_iso.year}/{today_iso.week}"
        store_in_s3_bucket(ta_bucket, s3_path, data_to_store, filename)
        logging.info(f"[{restaurant_id_ta}] Stored in S3")

        dynamodb = boto3.client('dynamodb')
        restaurants_db = f'restaurants-db-{os.environ["stage"]}'
        try:
            dynamodb.put_item(
                TableName=restaurants_db,
                Item={
                    'ta_place_id': {'S': ids[0]},
                    'ta_restaurant_id': {'S': ids[1]},
                    'ta_general_place_id': {'S': ta_place_id},
                    'valid': {'S': 'no'},
                    'trip_advisor_last_time': {'S': today.strftime("%Y/%m/%d, %H:%M:%S")},
                    'google_maps_id': {'S': 'not_searched'}
                },
                ConditionExpression='attribute_not_exists(ta_place_id) AND attribute_not_exists(ta_restaurant_id)'
            )
        except botocore.exceptions.ClientError as e:
            # Ignore the ConditionalCheckFailedException, bubble up
            # other exceptions.
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logging.info(f"[{restaurant_id_ta}] already exists in DB. Proceeding to update values")
                dynamodb.update_item(
                    TableName=restaurants_db,
                    Key={
                        'ta_place_id': {'S': ids[0]},
                        'ta_restaurant_id': {'S': ids[1]}
                    },
                    UpdateExpression='SET trip_advisor_last_time = :new_date',
                    ExpressionAttributeValues={
                        ':new_date': {'S': today.strftime("%Y/%m/%d, %H:%M:%S")}
                    }
                )

        logging.info(f"[{restaurant_id_ta}] has been updated in the restaurants-db table")
