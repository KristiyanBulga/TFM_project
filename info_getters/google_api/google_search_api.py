from dotenv import load_dotenv
import requests
import json
import os

load_dotenv()

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 2)[0]

api_key = os.getenv('CUSTOM_SEARCH_API_KEY')
search_engine_id = os.getenv('PROGRAMMABLE_SEARCH_ID')
query = 'Restaurante L%27arruzz Albacete'

query = query.replace(' ', '%20')

url = 'https://www.googleapis.com/customsearch/v1?'
url += 'key=' + api_key
url += '&cx=' + search_engine_id
url += '&q=' + query

print('Searching:', url)

query = requests.get(url)

# Write in a file all the data
with open(parent_folder + '/data/google_api/google_search.json', 'w', encoding='utf-8') as f:
    json.dump(query.json(), f)
