from mcp.server.fastmcp import FastMCP
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, time as dtime
from datetime import timedelta
import time as t
from bs4 import BeautifulSoup
import os
import json
import logging
import pytz
import dateparser


mcp = FastMCP("query-meeting-rooms", log_level="ERROR")

BOOKING_URL = "https://booking.cathayholdings.com/frontend/mrm101w/index?"

log = logging.getLogger(__name__)

TPE = pytz.timezone("Asia/Taipei")

username: str = "00897772", # TODO: 替換自己的員編
password: str = "Cz@832789237" #TODO: 替換自己的員工入口網密碼

@mcp.tool()
def query_meeting_rooms(
    building_str: str = "仁愛",
    start_date: str = "",
    end_date: str = "",
) -> list:
    """
    查詢會議室預約資料（含早上與下午）
    - building_str: 建築物代碼()
    - start_date: 起始查詢日 (yyyy/MM/dd)
    - end_date: 結束查詢日（預設與 start_date 相同）
    """
    
    building_map = {
        "仁愛": "4",
        "松仁": "6",
        "瑞湖": "12",
        "信義安和": "15",
        "台中忠明": "19"
    }
    
    # 處理Building
    matched_code = None
    for keyword, code in building_map.items():
        if keyword in building_str:
            matched_code = code
            break

    if not matched_code:
        raise ValueError(f"無效的建築名稱：{building_str}，請包含以下之一: {', '.join(building_map.keys())}")

    building = matched_code
    
    # 處理日期格式
    start_date = parse_and_validate_date(start_date, "起始日期")

    if not end_date or end_date.strip() == "":
        end_date = start_date
    else:
        end_date = parse_and_validate_date(end_date, "結束日期")
    

    all_results = []
    current = start_date

    current_date_str = current.strftime('%Y/%m/%d')
    driver = create_driver()
    login_and_set_date(driver, username, password, current, current)

    try:
        dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
        select = Select(dropdown)
        select.select_by_value(building)

        # 取得當前日期字串
        log.info(f"查詢日期: {current.strftime('%Y/%m/%d')}")
        current_date_str = current.strftime('%Y/%m/%d')

        # 先建立一個 dict 以會議室名稱為 key
        room_dict = {}

        # 早上
        try:
            driver.find_element(By.XPATH, '//button[@name="selectedTimePeriod" and @value="MORNING"]').click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.Pink_bg_block, .Green_bg_block, .Pink_whitebg_block'))
            )
            morning_data = extract_meeting_info(driver.page_source)
            for item in morning_data:
                key = f"{item['floor']}{item['room']}"
                if key not in room_dict:
                    room_dict[key] = {
                        "building": building_str,
                        "date": current_date_str,
                        "room": item['room'],
                        "floor": item['floor'],
                        "records": []
                    }
                room_dict[key]["records"].append({
                    "startTime": item["startTime"],
                    "endTime": item["endTime"],
                    "topic": item["topic"],
                    "period": "morning"
                })
        except Exception as e:
            print(f"⚠️ {building_str} {current_date_str} 早上無資料: {e}")

        # 下午
        try:
            driver.find_element(By.XPATH, '//button[@name="selectedTimePeriod" and @value="AFTERNOON"]').click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.Pink_bg_block, .Green_bg_block, .Pink_whitebg_block'))
            )
            afternoon_data = extract_meeting_info(driver.page_source)
            for item in afternoon_data:
                key = f"{item['floor']}{item['room']}"
                if key not in room_dict:
                    room_dict[key] = {
                        "building": building_str,
                        "date": current_date_str,
                        "room": item['room'],
                        "floor": item['floor'],
                        "records": []
                    }
                room_dict[key]["records"].append({
                    "startTime": item["startTime"],
                    "endTime": item["endTime"],
                    "topic": item["topic"],
                    "period": "afternoon"
                })
        except Exception as e:
            print(f"⚠️ {building_str} {current_date_str} 下午無資料: {e}")

        # 將所有會議室資料合併進 all_results
        all_results.extend(room_dict.values())

    except Exception as e:
        log.error(f"查詢失敗: {e}")
    finally:
        driver.quit()


    return all_results
    
def parse_time_input(natural_time: str) -> dict:
    parsed = dateparser.parse(
        natural_time,
        settings={
            'PREFER_DATES_FROM': 'future',
            'TIMEZONE': 'Asia/Taipei',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'LANGUAGE': 'zh',
        }
    )

    if not parsed:
        return {"error": "無法解析時間，請重新輸入更明確的時間描述。"}

    parsed = parsed.astimezone(TPE)

    # 檢查是否超過3個月（約 90 天）
    now = datetime.now(TPE)
    max_date = now + timedelta(days=90)
    min_date = now - timedelta(days=90)
    if parsed < min_date or parsed > max_date:
        return {"error": "時間不可與現在時間相差超過三個月，請重新輸入。"}

    is_weekend = parsed.weekday() >= 5
    t = parsed.time()
    is_outside_work_hours = t < dtime(7, 0) or t > dtime(18, 0)

    alert = None
    if is_weekend:
        alert = "⚠️ 你輸入的時間為假日，請確認是否為可開會時段。"
    elif is_outside_work_hours:
        alert = "⚠️ 你輸入的時間為非上班時間（07:00 - 18:00），請確認。"

    return {
        "parsed_time": parsed.strftime("%Y-%m-%d"),
        "weekday": ["一", "二", "三", "四", "五", "六", "日"][parsed.weekday()],
        "alert": alert
    }

def extract_meeting_info(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    booking_areas = soup.select('.Booking_area')
    for area in booking_areas:
        title = area.select_one('.ToggleTitle')
        floor = title.select_one('.Floor').get_text(strip=True) if title else ''
        room = title.select_one('.Room').get_text(strip=True) if title else ''
        for btn in area.select('button.meetingRecordBtn'):
            topic = btn.select_one('.Company.textDis')
            result = {
                "startTime": btn.get('data-starttime', ''),
                "endTime": btn.get('data-endtime', ''),
                "topic": topic.get_text(strip=True) if topic else '',
                "room": room,
                "floor": floor
            }
            results.append(result)
    return results

def login_and_set_date(driver, username, password,start_date, end_date):
    driver.get(BOOKING_URL)
    driver.find_element(By.NAME, 'username').send_keys(username)
    driver.find_element(By.ID, 'KEY').send_keys(password)
    driver.find_element(By.ID, 'btnLogin').click()
    # 登入後等待手動 OTP 驗證完成
    driver.implicitly_wait(100)
    t.sleep(60)  # 等待 60 秒以完成 OTP 驗證

    start_date_input = driver.find_element(By.ID, 'startDate')
    end_date_input = driver.find_element(By.ID, 'endDate')

    for input_elem, date_value in zip([start_date_input, end_date_input], [start_date, end_date]):
        driver.execute_script("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, input_elem, date_value.strftime('%Y/%m/%d'))
        
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    return driver

def parse_and_validate_date(date_str, field_name):
    """
    將各種格式的日期（含中文、自然語言）轉為 %Y/%m/%d 格式的datetime object。
    如果無法解析，則拋出 ValueError。
    """
    if not date_str or date_str.strip() == "":
        raise ValueError(f"必須提供{field_name}。")
    try:
        dt = dateparser.parse(date_str, languages=['zh'])
        if not dt:
            raise ValueError("日期解析失敗")
        return dt
    except Exception as e:
        raise ValueError(f"{field_name} 發生錯誤：無法解析「{date_str}」，原因：{e}")


if __name__ == "__main__":
    mcp.run(transport='stdio')