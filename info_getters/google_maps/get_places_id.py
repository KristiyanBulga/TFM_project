import os
import json
from get_data import get_place_id

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 3)[0]


def _get_list_restaurants() -> list:
    path_to_data = parent_folder + '/data/trip_advisor/links_ta.json'
    if not os.path.isfile(path_to_data):
        return []
    data = dict()
    with open(path_to_data, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
        f.close()
    return data["restaurants"]


def get_places_id():
    restaurants = _get_list_restaurants()
    for restaurant in restaurants:
        get_place_id(restaurant["name"])


get_places_id()
