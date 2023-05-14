import os
import re
import json
from jellyfish import jaro_similarity
from get_data import get_place_details

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 3)[0]


def _get_places_id() -> dict:
    path_to_data = parent_folder + '/data/google_maps/place_id_queries.json'
    if not os.path.isfile(path_to_data):
        return dict()
    data = dict()
    with open(path_to_data, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
        f.close()
    return data


def _get_ta_address(restaurant_name: str) -> str:
    path_to_links = parent_folder + '/data/trip_advisor/links_ta.json'
    if not os.path.isfile(path_to_links):
        return ""
    data = dict()
    with open(path_to_links, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
        f.close()
    restaurant = list(filter(lambda x: x["name"] == restaurant_name, data["restaurants"]))
    if not restaurant:
        return ""
    rest_name = re.search('(?<=Reviews-)(.*)(?=.html)', restaurant[0]["link"]).group(0)
    path_to_file = parent_folder + f'/data/trip_advisor/restaurants_ta/{rest_name}.json'
    if not os.path.isfile(path_to_file):
        return ""
    data = dict()
    with open(path_to_file, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
        f.close()
    addr = data["restaurant"]["data"].get("address", dict()).get("name", "")
    return addr


def get_places_details():
    places_id = _get_places_id()
    for key, value in places_id.items():
        if len(value["candidates"]) == 1:
            pass
        elif len(value["candidates"]) > 1:
            ta_address = _get_ta_address(key)
            candidates = [(jaro_similarity(ta_address, c["formatted_address"]), c) for c in value["candidates"]]
            candidates = sorted(candidates, key=lambda x: x[0], reverse=True)
            pass
        else:
            pass
            # TODO _add_restaurant_to_blacklist()


get_places_details()
