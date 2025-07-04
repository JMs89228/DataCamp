from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

# 讀取上傳的 HTML 檔案
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(script_dir, "..", "tmp", "query_result.html")
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# 抓取查詢日期
search_date_input = soup.find("input", {"id": "searchBean.searchDate"})
query_date = search_date_input["value"] if search_date_input else "unknown"

# 抓取建築名稱
building_select = soup.find("select", {"id": "searchBeanBuildingPK"})
building_option = building_select.find("option", selected=True)
building_name = building_option.text.strip() if building_option else "未知大樓"

# 抓取所有會議室 Booking 區塊
meeting_data = []
for booking_area in soup.select(".Booking_area"):
    # 樓層與會議室名稱
    title = booking_area.find("div", class_="Title")
    if not title:
        continue
    floor = title.find("div", class_="Floor").text.strip()
    room = title.find("div", class_="Room").text.strip()

    # 抓取各個 button 上的預約資訊
    for button in booking_area.select("button.meetingRecordBtn"):
        start_time = button.get("data-starttime")
        end_time = button.get("data-endtime")
        fields = button.find_all("div", recursive=False)
        if len(fields) < 4:
            continue

        topic = fields[0].text.strip()
        host_org = fields[1].text.strip()
        department = fields[2].text.strip()
        person_name = re.sub(r"\s*\d{7,}", "", fields[3].text.strip())  # 移除電話號碼
        host = f"{host_org} {department} {person_name}"

        meeting_data.append({
            "building": building_name,
            "room": room,
            "date": query_date,
            "start_time": start_time,
            "end_time": end_time,
            "topic": topic,
            "host": host
        })

# 依查詢時間戳記決定輸出檔名
now = datetime.now()
timestamp = now.strftime("%m%d%H%M")
filename = f"{query_date.replace('/', '')}_query_{timestamp}.csv"
output_dir = os.path.join(script_dir, "..", "rag-file")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, filename)

# 寫入 CSV
import pandas as pd
df = pd.DataFrame(meeting_data)
df.to_csv(output_path, index=False, encoding="utf-8-sig")
