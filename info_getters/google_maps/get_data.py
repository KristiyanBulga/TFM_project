import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 3)[0]

basic_fields = ["address_components", "adr_address", "business_status", "formatted_address", "name", "place_id",
                "plus_code", "type", "url", "utc_offset", "vicinity", "wheelchair_accessible_entrance"]
contact_fields = ["current_opening_hours", "formatted_phone_number", "international_phone_number", "opening_hours",
                  "secondary_opening_hours", "website"]
atmosphere_fields = ["curbside_pickup", "delivery", "dine_in", "editorial_summary", "price_level", "rating",
                     "reservable", "reviews", "serves_beer", "serves_breakfast", "serves_brunch", "serves_dinner",
                     "serves_lunch", "serves_vegetarian_food", "serves_wine", "takeout", "user_ratings_total"]


def get_place_id(restaurant_name: str):
    place_id_queries = dict()
    path_to_data = parent_folder + f"/data/google_maps/place_id_queries.json"
    if os.path.isfile(path_to_data):
        with open(path_to_data, 'r', encoding='utf-8') as f:
            place_id_queries = json.loads(f.read())
            f.close()

    if place_id_queries.get(restaurant_name, None):
        return

    fields = ["place_id", "name", "formatted_address"]
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
    url += f"input={'%20'.join(restaurant_name.split())}"
    url += f"&inputtype=textquery"
    url += f"&fields={'%2C'.join(fields)}"
    url += f"&key={google_maps_api_key}"
    
    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    place_id_queries[restaurant_name] = json.loads(response.content)
    with open(path_to_data, 'w', encoding='utf-8') as f:
        json.dump(place_id_queries, f, ensure_ascii=False)
        f.close()


def get_place_details(restaurant_id: str):
    path_to_data = parent_folder + f"/data/google_maps/restaurants/{restaurant_id}.json"
    if os.path.isfile(path_to_data):
        return

    fields = basic_fields + contact_fields + atmosphere_fields
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

    url = "https://maps.googleapis.com/maps/api/place/details/json?"
    url += f"place_id={restaurant_id}"
    url += f"&fields={'%2C'.join(fields)}"
    url += f"&key={google_maps_api_key}"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    with open(path_to_data, 'w', encoding='utf-8') as f:
        json.dump(json.loads(response.content), f, ensure_ascii=False)
        f.close()


# rest_name = "La Posadica Horno de Leña"
# get_place_id(rest_name)

rest_id = "ChIJi0WdGrdfZg0RAc0Gh7wuCzo"
get_place_details(rest_id)



