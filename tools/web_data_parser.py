from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
import pandas as pd

class WebDataParser:
    def __init__(self, output_dir="rag-file"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def parse_html(self, html_content, query_date_str, period):
        """
        Parse HTML content to extract meeting data.
        :param html_content: String containing the HTML content.
        :param query_date_str: String representing the query date in YYYYMMDD format.
        :param period: String representing the period (MORNING or AFTERNOON).
        :return: List of dictionaries containing meeting data.
        """
        soup = BeautifulSoup(html_content, "html.parser")

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
                    "date": query_date_str,
                    "start_time": start_time,
                    "end_time": end_time,
                    "topic": topic,
                    "host": host
                })

        return meeting_data

    def save_to_csv(self, meeting_data, query_date_str, period, timestamp=None):
        """
        Save meeting data to a CSV file.
        :param meeting_data: List of dictionaries containing meeting data.
        :param query_date_str: String representing the query date in YYYYMMDD format.
        :param period: String representing the period (MORNING or AFTERNOON).
        :param timestamp: Optional string representing the timestamp for uniqueness.
        :return: Path to the saved CSV file.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{query_date_str}{period}_query_{timestamp}.csv"
        output_path = os.path.join(self.output_dir, filename)
        df = pd.DataFrame(meeting_data)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 已將資料儲存至 CSV 檔案: {output_path}")
        return output_path
