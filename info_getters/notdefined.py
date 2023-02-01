import os, json, time
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt

def generate_ta_restaurants_parquet(parent_folder):
    dfs = []
    for file in os.listdir(restaurants_folder):
        with open(restaurants_folder + f"/{file}", "r", encoding="utf8") as f:
            restaurant_json = json.loads(f.read())
            f.close()
        restaurant_json = restaurant_json["restaurant"]
        restaurant = restaurant_json["data"].copy()
        restaurant.pop("address", None)
        restaurant["address_name"] = restaurant_json["data"].get("address", {}).get("name", "no address")
        restaurant["address_link"] = restaurant_json["data"].get("address", {}).get("link", "no address")
        restaurant["name"] = restaurant_json.get("name", "no_name")
        restaurant["link"] = restaurant_json.get("ta_link", "no_link")
        
        dfs.append(pd.json_normalize(restaurant))
    df = pd.concat(dfs, ignore_index=True)
    df.to_parquet(parent_folder + "/data/trip_advisor/ta_restaurants.parquet")

# Get current directory
current_file_dir = os.path.realpath(__file__)
current_file_dir = current_file_dir.replace("\\", "/")
parent_folder = current_file_dir.rsplit("/", 2)[0]

restaurants_folder = parent_folder + "/data/trip_advisor/restaurants_ta"
dfs = []
data = dict()
# generate_ta_restaurants_parquet(parent_folder)
# TODO





for file in os.listdir(restaurants_folder):
    with open(restaurants_folder + f"/{file}", "r", encoding="utf8") as f:
        file_data = json.loads(f.read())
        f.close()
    aux = dict()
    file_data = file_data["restaurant"]
    aux["name"] = file_data["name"]
    restaurant_data = file_data["data"]
    score = restaurant_data.get("score_overall", None)
    for tag in restaurant_data.get("type", []):
        if data.get(tag, None):
            data[tag]["values"].append(score)
        else:
            data[tag] = {"values": [score]}
        aux[tag] = score
    for tag in restaurant_data.get("special_diets", []):
        if data.get(tag, None):
            data[tag]["values"].append(score)
        else:
            data[tag] = {"values": [score]}
        aux[tag] = score
    for tag in restaurant_data.get("meals", []):
        if data.get(tag, None):
            data[tag]["values"].append(score)
        else:
            data[tag] = {"values": [score]}
        aux[tag] = score
    for tag in restaurant_data.get("advantages", []):
        if data.get(tag, None):
            data[tag]["values"].append(score)
        else:
            data[tag] = {"values": [score]}
        aux[tag] = score
    
    dfs.append(pd.json_normalize(aux))

df = pd.concat(dfs, ignore_index=True)
df.to_parquet(parent_folder + "/data/trip_advisor/ta_tags_score.parquet")

auxiliary = dict()
with open('C:/Users/krist/Documents/MiGithub/TFM_project/data/trip_advisor/food_type_ta.json', "r", encoding="utf8") as f:
    auxiliary = json.loads(f.read())
    f.close()
print(auxiliary)
data2 = []
for key in data:
    data[key]["tag"] = key
    data[key]["count"] = len(data[key]["values"])
    data[key]["mean"] = sum(data[key]["values"]) / data[key]["count"]
    data[key]["group"] = auxiliary.get(key, dict()).get("type", "no_group")
    data[key].pop("values", None)
    data2.append(data[key])

df = pd.json_normalize(data2)
df.to_parquet(parent_folder + "/data/trip_advisor/ta_tag_aggregation.parquet")

fig = px.scatter(df, x="count", y="mean",size="mean", color="group",hover_name="tag", log_x=False, size_max=60)
fig.write_html(parent_folder + '/data/trip_advisor/bubble_chart.html')
fig.show()
exit(0)

# from wordcloud import WordCloud

# repeated = dict()
# values = dict()
# for i, row in df.iterrows():
#     repeated[row["tag"]] = row["count"]
#     values[row["tag"]] = row["mean"]

# # Generate a word cloud - negative sentiment
# wordcloud_trigrams_neg = WordCloud(background_color="white", colormap="twilight_shifted").generate_from_frequencies(repeated)
# plt.figure()
# plt.imshow(wordcloud_trigrams_neg, interpolation="bilinear")
# plt.axis("off")
# plt.savefig(parent_folder + '/data/trip_advisor/images/repeated_tags.png')

# # Generate a word cloud - positive sentiment
# wordcloud_trigrams_pos = WordCloud(background_color="white", colormap="twilight_shifted").generate_from_frequencies(values)
# plt.figure()
# plt.imshow(wordcloud_trigrams_pos, interpolation="bilinear")
# plt.axis("off")
# plt.savefig(parent_folder + '/data/trip_advisor/images/overall_score_tags.png')
