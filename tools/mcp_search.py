from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time as t
import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# ----------- 參數設定區 -------------
mcp = FastMCP("search_meeting_rooms", log_level="ERROR")
BOOKING_URL = "https://booking.cathayholdings.com/frontend/mrm101w/index?"

USERNAME = "username"   # TODO: 替換成你的員編
PASSWORD = "password"  # TODO: 替換成你的密碼
# -----------------------------------

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver

def login_and_set_date(driver, username, password, start_date, end_date):
    driver.get(BOOKING_URL)
    driver.find_element(By.NAME, 'username').send_keys(username)
    driver.find_element(By.ID, 'KEY').send_keys(password)
    driver.find_element(By.ID, 'btnLogin').click()
    driver.implicitly_wait(100)

    # 設定日期
    start_input = driver.find_element(By.ID, 'startDate')
    end_input = driver.find_element(By.ID, 'endDate')

    for elem, value in zip([start_input, end_input], [start_date, end_date]):
        driver.execute_script("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, elem, value)

def set_building_and_period(driver, building_code, period):
    # 選擇建築物
    dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
    select = Select(dropdown)
    select.select_by_value(building_code)

    # 點選早上或下午
    driver.find_element(By.XPATH, f'//button[@name="selectedTimePeriod" and @value="{period}"]').click()

    # # 等待資料載入
    # WebDriverWait(driver, 10).until(
    #     EC.presence_of_element_located((By.CSS_SELECTOR, '.Pink_bg_block, .Green_bg_block, .Pink_whitebg_block'))
    # )

def parse_html_content(html_content, query_date_str, period):
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
    building_name = building_option.text.strip()

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

def save_to_csv(meeting_data, query_date_str, output_dir, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{query_date_str}_query_{timestamp}.csv"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    df = pd.DataFrame(meeting_data)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ 已將資料儲存至 CSV 檔案: {output_path}")
    return output_path

def process_and_save_data(meeting_data, query_date_str):
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if meeting_data:
        save_to_csv(meeting_data, query_date_str, output_dir=os.path.join(script_dir, "..", "rag-file"), timestamp=datetime.now().strftime('%H%M%S'))
    else:
        print(f"⚠️ 沒有找到任何會議資料，無法儲存 CSV 檔案")


@mcp.tool()
def search_meeting_rooms(start_date, building_code):
    end_date = start_date
    driver = create_driver()
    try:
        login_and_set_date(driver, USERNAME, PASSWORD, start_date, end_date)
        meeting_data = []
        for period in ["MORNING", "AFTERNOON"]:
            print(f"正在查詢 {period} 的會議室資料...")
            set_building_and_period(driver, building_code, period)
            t.sleep(2)
            html = driver.page_source
            query_date_str = start_date.replace("/", "")
            partial_data = parse_html_content(html, query_date_str, period)
            meeting_data.extend(partial_data)
        process_and_save_data(meeting_data, query_date_str)
    finally:
        driver.quit()


if __name__ == "__main__":
    mcp.run(transport="stdio")
