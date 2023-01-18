import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_place_id(restaurant_name: str):
    restaurant_name = "La Posadica Horno de Leña"
    fields = ["place_id", "name"]
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
    url += f"input={'%20'.join(restaurant_name.split())}"
    url += f"&inputtype=textquery"
    url += f"&fields={'%2C'.join(fields)}"
    url += f"&key={google_maps_api_key}"
    
    payload={}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)

def get_place_details(restaurant_id: str):
    fields = ["name", "rating", "formatted_address", "opening_hours", "takeout", "delivery"]
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

    url = "https://maps.googleapis.com/maps/api/place/details/json?"
    url += f"place_id={restaurant_id}"
    url += f"&fields={'%2C'.join(fields)}"
    url += f"&key={google_maps_api_key}"

    payload={}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)

restaurant_id = "ChIJi0WdGrdfZg0RAc0Gh7wuCzo"
get_place_details(restaurant_id)