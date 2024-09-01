from bs4 import BeautifulSoup as bs
from os import walk
from datetime import datetime
import pandas as pd

restaurant = "g187486-d11938465"
main_route = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\data"
route = f"{main_route}\\raw\\{restaurant}"
months_nums = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
title_list, content_list, score_list, group_list, date_list, ts_list = [], [], [], [], [], []
def process_files():
    filenames = next(walk(route), (None, None, []))[2]  # [] if no file
    for file in filenames:
        print(file)
        with open(f"{route}\\{file}", encoding="utf8") as fp:
            soup = bs(fp, 'html.parser')
            reviews_parent = soup.find("div", class_="JmLZe")
            reviews = reviews_parent.find_all("div", class_="_c")
            for review in reviews:
                titles = review.find_all("a", class_="BMQDV _F Gv wSSLS SwZTJ FGwzt ukgoS")
                title_list.append(titles[1].contents[0])
                contents = review.find_all("span", class_="JguWG")
                content_list.append(contents[0].contents[0].replace("\n", ""))
                score = review.find("title").contents[0]
                score = score.split(" ")[0].split(",")
                score = int(score[0]) + int(score[1])/10
                score_list.append(score)
                group = review.find("span", class_="xUaOf").contents[0]
                group_list.append(group)
                date = review.find("div", class_="biGQs _P pZUbB ncFvv osNWb").contents[2]
                date = date.split(" ")
                date_str = f"{date[4]}/{months_nums[date[2]]}/{date[0]}"
                date_list.append(date_str)
                ts = int(datetime(int(date[4]), int(months_nums[date[2]]), int(date[0])).timestamp())
                ts_list.append(ts)
        
process_files()
df = pd.DataFrame({"date": date_list, "ts": ts_list, "group":group_list, "score":score_list, "title": title_list, "content": content_list})
df.to_csv(f'{main_route}\\{restaurant}.csv', index=False)