import os
import time
from datetime import datetime, timedelta
from tools.rag_csv_tool import build_vectorstore_from_csv, load_qa_chain
from tools.mcp_search import search_meeting_rooms

RAG_DIR = "rag-file"

# 建築對應表
building_map = {
    "仁愛": "4",
    "松仁": "6",
    "瑞湖": "12",
    "信義安和": "15",
    "台中忠明": "19"
}

# 找出最新的某天 CSV
def find_latest_csv(date_str: str) -> str:
    pattern = f"{date_str}_query_"
    candidates = [f for f in os.listdir(RAG_DIR) if f.startswith(pattern) and f.endswith(".csv")]
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return os.path.join(RAG_DIR, candidates[0])

# 建立所有可能時段（30 分鐘間隔）
def generate_all_slots(start="07:00", end="18:00", step=30):
    fmt = "%H:%M"
    start_time = datetime.strptime(start, fmt)
    end_time = datetime.strptime(end, fmt)
    result = []
    while start_time < end_time:
        next_time = start_time + timedelta(minutes=step)
        result.append((start_time.strftime(fmt), next_time.strftime(fmt)))
        start_time = next_time
    return result

# 取得可用時段
def get_available_slots(reserved_slots, all_slots):
    return [slot for slot in all_slots if slot not in reserved_slots]

# 將 reserved start~end 轉為 slot list
def convert_to_slots(start, end, all_slots):
    return [slot for slot in all_slots if slot[0] >= start and slot[1] <= end]

# 根據 CSV 判斷空閒時段（room → available slot list）
def calculate_room_availability(csv_path: str):
    import pandas as pd
    df = pd.read_csv(csv_path)
    all_slots = generate_all_slots()

    room_reserved = {}
    for _, row in df.iterrows():
        key = f"{row['building']} {row['room']}"
        reserved = convert_to_slots(row['start_time'], row['end_time'], all_slots)
        room_reserved.setdefault(key, []).extend(reserved)

    availability = {
        room: get_available_slots(reserved, all_slots)
        for room, reserved in room_reserved.items()
    }
    return availability

# 使用者狀態
user_state = {
    "building": None,
    "date": None,
    "confirmed": False,
    "qa_chain": None,
    "availability": None
}

last_loaded_csv = None  # 快取避免重複 Embedding

print("您好，我是您的 AI 會議助理，有什麼我可以幫忙的嗎？")

while True:
    query = input("\n> ")
    if query.lower() in ["exit", "quit"]:
        break

    # 還沒收集到足夠參數 → 進入收集模式
    if not user_state["confirmed"]:
        for bname in building_map:
            if bname in query:
                user_state["building"] = bname
                break

        for fmt in ["%Y/%m/%d", "%Y-%m-%d", "%Y%m%d"]:
            try:
                dt = datetime.strptime(query[:10], fmt)
                user_state["date"] = dt.strftime("%Y%m%d")
                break
            except:
                continue

        if user_state["building"] and user_state["date"]:
            print(f"確認查詢資訊如下：\n- 大樓：{user_state['building']}\n- 日期：{user_state['date']}")
            confirm = input("是否確認以上查詢？(y/n): ")
            if confirm.lower() == "y":
                user_state["confirmed"] = True
        else:
            print("請提供查詢的建築名稱與日期（如 2025/07/14 或 20250714）。")
            continue

    # 已確認查詢條件，進行資料載入與嵌入處理
    if user_state["confirmed"] and user_state["qa_chain"] is None:
        found_csv = find_latest_csv(user_state["date"])

        if not found_csv:
            print(f"⚠️ 找不到 {user_state['date']} 的會議室資料，啟動 MCP 爬蟲工具查詢...")
            try:
                formatted_date = f"{user_state['date'][:4]}/{user_state['date'][4:6]}/{user_state['date'][6:]}"
                search_meeting_rooms(start_date=formatted_date, building_code=building_map[user_state["building"]])
                time.sleep(3)
                found_csv = find_latest_csv(user_state["date"])
            except Exception as e:
                print("❌ MCP 工具執行失敗：", e)

        if not found_csv:
            print(f"❌ 無法獲取 {user_state['date']} 的資料，請稍後再試。")
            continue

        if found_csv == last_loaded_csv:
            print("✅ 查詢資料庫已載入，可直接問問題")
        else:
            print("正在建立查詢資料庫...")
            build_vectorstore_from_csv(found_csv)
            user_state["qa_chain"] = load_qa_chain()
            user_state["availability"] = calculate_room_availability(found_csv)
            last_loaded_csv = found_csv
            print("✅ 載入完成，您現在可以詢問與會議室預約或空閒時段相關的問題。")
        continue

    # 若已載入 QA Chain → 執行查詢
    if user_state["qa_chain"]:
        if "空" in query and "會議室" in query:
            print("\n🔍 空閒會議室時段如下：")
            for room, slots in user_state["availability"].items():
                if slots:
                    formatted = ", ".join([f"{s}-{e}" for s, e in slots])
                    print(f"- {room}：{formatted}")
        else:
            result = user_state["qa_chain"](query)
            print("\nAI 回答：", result["result"])
            print("\n🔍 參考片段：")
            for doc in result["source_documents"]:
                print("-", doc.page_content)
