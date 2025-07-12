from tools.mcp_tool import query_meeting_rooms
from tools.mcp_search import search_meeting_rooms  
import json

def test_query_rooms():
    # result = query_meeting_rooms("仁愛", "2025/07/04")
    # print(json.dumps(result, indent=2, ensure_ascii=False))
    search_meeting_rooms("2025/07/04", "4")

if __name__ == "__main__":
    # test_query_rooms()
        # 示例用法
    START_DATE = "2025/07/04"
    BUILDING_CODE = "4"  # 仁愛 = 4，松仁 = 6，瑞湖 = 12 ...
    search_meeting_rooms(START_DATE, BUILDING_CODE)
