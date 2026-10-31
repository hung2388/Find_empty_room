import unittest
import datetime
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from room_finder import (
    TimetableEngine,
    parse_time_range,
    parse_weeks,
    parse_thu,
    split_room,
    date_to_thu_and_week,
    render_grid_table,
    DEFAULT_SEMESTER_START
)

class TestRoomFinder(unittest.TestCase):

    def setUp(self):
        self.engine = TimetableEngine()
        self.stats = self.engine.load_file("TKB20261-FULL(Sheet1).csv")

    def test_1_file_normalization_and_encoding(self):
        """1. Đọc và chuẩn hóa file, phát hiện encoding, tách tòa/phòng."""
        print("\n--- Test 1: Chuẩn hóa file & Encoding ---")
        self.assertGreater(self.stats["total_rows"], 10000)
        self.assertIn(self.stats["encoding"], ["utf-8", "utf-8-sig", "cp1252", "latin1"])
        self.assertGreater(self.stats["valid_rooms"], 400)
        self.assertGreater(self.stats["buildings"], 40)
        
        # Test room splitting
        b, r, raw = split_room("D9-102")
        self.assertEqual(b, "D9")
        self.assertEqual(r, "102")
        self.assertEqual(raw, "D9-102")

        b2, r2, raw2 = split_room("D3-5-201")
        self.assertEqual(b2, "D3-5")
        self.assertEqual(r2, "201")

    def test_2_session_comparison_and_conflicts(self):
        """2. So sánh lịch học và rà soát trùng lịch phòng."""
        print("\n--- Test 2: So sánh lịch học & Trùng lịch ---")
        # Time parsing
        t = parse_time_range("0920-1145")
        self.assertEqual(t, (9 * 60 + 20, 11 * 60 + 45))

        # Weeks parsing
        w = parse_weeks("2-9,11-18")
        self.assertIn(2, w)
        self.assertIn(9, w)
        self.assertIn(11, w)
        self.assertIn(18, w)
        self.assertNotIn(10, w)
        self.assertNotIn(1, w)

        print(f"Số cặp phòng trùng lịch trong file: {self.stats['conflicts']}")

    def test_3_room_availability_lookup(self):
        """3. Chức năng tìm phòng trống với thời gian thực (Tuần 7, Thứ 6)."""
        print("\n--- Test 3: Tìm phòng trống tòa D3 chiều thứ 6 tuần 7 ---")
        target_date = datetime.date(2026, 10, 30)
        thu, week = date_to_thu_and_week(target_date)
        
        self.assertEqual(thu, 6, "Ngày 30/10/2026 phải là Thứ 6")
        self.assertEqual(week, 7, "Ngày 30/10/2026 phải là Tuần 7")

        table_data = self.engine.get_table_result(["D3"], thu, week, "chieu")
        self.assertEqual(len(table_data), 3)

        # Slot 1: 12h30-14h10
        slot1 = table_data[0]
        self.assertEqual(slot1["time"], "12h30-14h10")
        self.assertIn("D3-101", slot1["free_rooms"])
        self.assertIn("D3-106", slot1["free_rooms"])
        self.assertIn("D3-303", slot1["free_rooms"])

        # Render format
        table_text = render_grid_table(table_data)
        self.assertIn("time", table_text)
        self.assertIn("12h30-14h10", table_text)
        self.assertIn("14h10-16h40", table_text)
        print("\n" + table_text)

if __name__ == "__main__":
    unittest.main()
