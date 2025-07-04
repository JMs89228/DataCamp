from tools.mcp_tool import query_meeting_rooms
import json

def test_query_rooms():
    result = query_meeting_rooms("仁愛", "2025/07/04")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_query_rooms()
