from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time as t
import os

# ----------- 參數設定區 -------------
BOOKING_URL = "https://booking.cathayholdings.com/frontend/mrm101w/index?"

USERNAME = "00897772"   # TODO: 替換成你的員編
PASSWORD = "Cz@832789237"  # TODO: 替換成你的密碼
START_DATE = "2025/07/04"
END_DATE = "2025/07/04"
BUILDING_CODE = "4"  # 仁愛 = 4，松仁 = 6，瑞湖 = 12 ...
PERIOD = "MORNING"  # 或 "AFTERNOON"
from datetime import datetime
# 不再需要儲存 HTML 檔案，直接處理並儲存為 CSV
# OUTPUT_PATH = f"tmp/query_result_{START_DATE.replace('/', '')}{PERIOD}_{datetime.now().strftime('%H%M%S')}.html"
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
    driver.implicitly_wait(30)

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

def process_and_save_data(driver, start_date, period):
    from tools.web_data_parser import WebDataParser
    html = driver.page_source
    parser = WebDataParser(output_dir="rag-file")
    query_date_str = start_date.replace('/', '')
    meeting_data = parser.parse_html(html, query_date_str, period)
    if meeting_data:
        parser.save_to_csv(meeting_data, query_date_str, period, timestamp=datetime.now().strftime('%H%M%S'))
    else:
        print("⚠️ 沒有找到會議資料，無法儲存 CSV 檔案")

def main():
    driver = create_driver()
    try:
        login_and_set_date(driver, USERNAME, PASSWORD, START_DATE, END_DATE)
        set_building_and_period(driver, BUILDING_CODE, PERIOD)
        process_and_save_data(driver, START_DATE, PERIOD)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
