"""
Script clean_tkb.py:
Dọn dẹp và chuẩn hóa file Thời Khóa Biểu (TKB):
1. Giữ lại duy nhất các cột thông tin quan trọng:
   - Thứ (ngày trong tuần: 2..8)
   - Thời gian (dạng 0920-1145)
   - Giờ bắt đầu (09:20)
   - Giờ kết thúc (11:45)
   - Kíp (Sáng / Chiều / Tối)
   - Tuần (ví dụ 2-9,11-18)
   - Tòa (ví dụ D9)
   - Tên phòng (ví dụ 102)
   - Phòng (ví dụ D9-102)
2. Xóa bỏ tất cả các cột thừa không cần thiết (Kỳ, Khoa, Mã lớp, Mã HP, Tên HP, Khối lượng, Ghi chú, v.v.).
3. Xóa bỏ các dòng không có lịch / đồ án tự học (Phòng NULL, Thời gian NULL).
4. Loại bỏ các lớp đã bị HỦY (để không báo bận sai).
5. Sửa lỗi chính tả & định dạng:
   - Sửa lỗi font chữ Kíp: Sng -> Sáng, Chi?u -> Chiều, T?i -> Tối.
   - Sửa lỗi thời gian typo: 0645-0645 -> 0645-1145.
   - Sửa lỗi tuần có dấu chấm hoặc khoảng trắng: '11.13' -> '11,13', '8, 12, 16' -> '8,12,16'.
   - Chuẩn hóa tên các khu thể chất / phòng đặc thù: 'B? b?i' -> 'Bể bơi', 'Sn Pickleball 1' -> 'Sân Pickleball 1', 'SV? 1' -> 'SVĐ 1', 'Nha A-Tangham' -> 'Nhà A-Tầng hầm',...
6. Loại bỏ các dòng trùng lặp (nhiều mã lớp gộp chung 1 phòng cùng giờ).
7. Xuất file UTF-8 BOM chuẩn hiển thị 100% tiếng Việt trên Excel.
"""

import os
import sys
import csv
import re
from typing import List, Dict, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def format_hhmm(s: str) -> str:
    """Chuyển chuỗi 4 chữ số 0920 thành 09:20"""
    return f"{s[:2]}:{s[2:]}"

def clean_room(raw_room: str) -> Tuple[str, str, str]:
    """Tách phòng thành (Tòa, Tên phòng, Mã phòng đầy đủ) và sửa lỗi hiển thị."""
    r = raw_room.strip()
    r_lower = r.lower()

    if "b? b?i" in r_lower or "be boi" in r_lower:
        return "Bể bơi", "Bể bơi", "Bể bơi"
    if "pickleball 1" in r_lower:
        return "Sân Pickleball", "Sân 1", "Sân Pickleball 1"
    if "pickleball 3" in r_lower:
        return "Sân Pickleball", "Sân 3", "Sân Pickleball 3"
    if "san ktx" in r_lower:
        return "Sân KTX", "Sân KTX", "Sân KTX"
    if "sanb13" in r_lower:
        return "Sân B13", "Sân B13", "Sân B13"
    if "sanb7" in r_lower:
        return "Sân B7", "Sân B7", "Sân B7"
    if "sv? 1" in r_lower or "svd 1" in r_lower:
        return "SVĐ", "Sân 1", "SVĐ 1"
    if "sv? 2" in r_lower or "svd 2" in r_lower:
        return "SVĐ", "Sân 2", "SVĐ 2"
    if "sv? 3" in r_lower or "svd 3" in r_lower:
        return "SVĐ", "Sân 3", "SVĐ 3"
    if r in ("SVD", "SV?"):
        return "SVĐ", "SVĐ", "SVĐ"
    if r == "NTD":
        return "NTD", "Nhà thi đấu", "NTD"
    if "nha a-tangham" in r_lower:
        return "Nhà A", "Tầng hầm", "Nhà A-Tầng hầm"
    if "nha a-" in r_lower:
        p = r.split("-", 1)[1]
        return "Nhà A", p, f"Nhà A-{p}"
    if "nha b-" in r_lower:
        p = r.split("-", 1)[1]
        return "Nhà B", p, f"Nhà B-{p}"
    if "tvtqb-tang" in r_lower:
        return "TVTQB", "Tầng 10", "TVTQB-Tầng 10"
    if "-" in r:
        toa, ten_phong = r.rsplit("-", 1)
        return toa.strip(), ten_phong.strip(), r
    return r, r, r

def natural_sort_key(s: str) -> List:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]

def process_file(input_path: str) -> List[Dict[str, str]]:
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        # Bỏ qua 2 dòng header rỗng ban đầu nếu có
        first_line = f.readline()
        second_line = f.readline()
        reader = csv.reader(f)
        header = next(reader)
        
        # Tìm vị trí các cột
        thu_col = 10
        time_col = 11
        kip_col = 14
        week_col = 15
        room_col = 16
        status_col = 20

        for idx, col in enumerate(header):
            c = col.strip().lower()
            if "thứ" in c or c == "th?": thu_col = idx
            elif "thời_gian" in c or "th?i_gian" in c or "time" in c: time_col = idx
            elif "kíp" in c or "kp" in c or "kip" in c: kip_col = idx
            elif "tuần" in c or "tu?n" in c or "week" in c: week_col = idx
            elif "phòng" in c or "phng" in c or "room" in c: room_col = idx
            elif "trạng_thái" in c or "tr?ng_thi" in c or "status" in c: status_col = idx

        cleaned_records = []
        seen = set()

        stats = {
            "total_read": 0,
            "cancelled_dropped": 0,
            "null_room_dropped": 0,
            "invalid_time_dropped": 0,
            "time_typo_fixed": 0,
            "week_format_fixed": 0,
            "deduplicated": 0
        }

        for r in reader:
            stats["total_read"] += 1
            if len(r) <= max(thu_col, time_col, room_col, week_col):
                continue

            # 1. Bỏ lớp hủy
            if status_col < len(r) and "hu" in r[status_col].lower():
                stats["cancelled_dropped"] += 1
                continue

            # 2. Bỏ phòng NULL hoặc rỗng
            raw_room = r[room_col].strip()
            if not raw_room or raw_room.upper() in ("NULL", "NONE"):
                stats["null_room_dropped"] += 1
                continue

            # 3. Thứ
            thu = r[thu_col].strip()
            if thu not in ("2", "3", "4", "5", "6", "7", "8"):
                continue

            # 4. Thời gian
            raw_time = r[time_col].strip()
            if raw_time == "0645-0645":
                raw_time = "0645-1145"
                stats["time_typo_fixed"] += 1

            if len(raw_time) != 9 or "-" not in raw_time:
                stats["invalid_time_dropped"] += 1
                continue

            s_raw, e_raw = raw_time.split("-")
            if not (s_raw.isdigit() and e_raw.isdigit() and int(s_raw) < int(e_raw)):
                stats["invalid_time_dropped"] += 1
                continue

            start_hhmm = format_hhmm(s_raw)
            end_hhmm = format_hhmm(e_raw)

            # 5. Kíp
            raw_kip = r[kip_col].strip().lower() if kip_col < len(r) else ""
            if "s" in raw_kip:
                kip = "Sáng"
            elif "chi" in raw_kip:
                kip = "Chiều"
            elif "t" in raw_kip:
                kip = "Tối"
            else:
                sh = int(s_raw[:2])
                kip = "Sáng" if sh < 12 else ("Chiều" if sh < 17 else "Tối")

            # 6. Tuần
            raw_week = r[week_col].strip().replace(" ", "")
            if "." in raw_week and re.match(r"^\d+\.\d+$", raw_week):
                raw_week = raw_week.replace(".", ",")
                stats["week_format_fixed"] += 1

            if not raw_week or raw_week.upper() in ("NULL", "NONE"):
                continue

            # 7. Phòng
            toa, ten_phong, ma_phong = clean_room(raw_room)

            record_key = (thu, raw_time, kip, raw_week, ma_phong)
            if record_key in seen:
                stats["deduplicated"] += 1
                continue
            seen.add(record_key)

            cleaned_records.append({
                "Thứ": thu,
                "Thời_gian": raw_time,
                "Bắt_đầu": start_hhmm,
                "Kết_thúc": end_hhmm,
                "Kíp": kip,
                "Tuần": raw_week,
                "Tòa": toa,
                "Tên_phòng": ten_phong,
                "Phòng": ma_phong
            })

    # Sắp xếp danh sách theo Tòa -> Tên phòng -> Thứ -> Giờ bắt đầu
    cleaned_records.sort(key=lambda x: (
        natural_sort_key(x["Tòa"]),
        natural_sort_key(x["Tên_phòng"]),
        int(x["Thứ"]),
        x["Bắt_đầu"],
        x["Tuần"]
    ))

    print("\n" + "=" * 60)
    print(" BÁO CÁO DỌN DẸP & CHUẨN HÓA THỜI KHÓA BIỂU")
    print("=" * 60)
    print(f"- Tổng số dòng đọc từ file gốc   : {stats['total_read']:,}")
    print(f"- Đã loại bỏ lớp bị Hủy          : {stats['cancelled_dropped']:,}")
    print(f"- Đã loại bỏ dòng thiếu phòng/giờ: {stats['null_room_dropped']:,}")
    print(f"- Đã sửa lỗi typo giờ (0645-0645): {stats['time_typo_fixed']}")
    print(f"- Đã sửa lỗi tuần dùng dấu chấm  : {stats['week_format_fixed']}")
    print(f"- Đã gộp các lớp học chung phòng : {stats['deduplicated']:,}")
    print(f"- Tổng số buổi học hợp lệ còn lại: {len(cleaned_records):,}")
    print("=" * 60)

    return cleaned_records

def save_csv(records: List[Dict[str, str]], output_path: str):
    fieldnames = ["Thứ", "Thời_gian", "Bắt_đầu", "Kết_thúc", "Kíp", "Tuần", "Tòa", "Tên_phòng", "Phòng"]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"[✓] Đã lưu file chuẩn hóa tại: {output_path}")

if __name__ == "__main__":
    src_file = "Find_empty_room/TKB20261-FULL(Sheet1).csv"
    if not os.path.exists(src_file):
        src_file = "TKB20261-FULL(Sheet1).csv"

    print(f"[*] Đang xử lý dọn dẹp file: {src_file}...")
    cleaned = process_file(src_file)

    # Xuất ra các file cần thiết
    destinations = [
        "Find_empty_room/TKB20261-FULL(Sheet1).csv",
        "Find_empty_room/api/TKB20261-FULL(Sheet1).csv",
        "Find_empty_room/TKB_CLEAN.csv",
        "TKB20261-FULL(Sheet1).csv",
        "TKB_CLEAN.csv"
    ]

    for dst in destinations:
        save_csv(cleaned, dst)

    print("\nHoàn tất dọn dẹp file!")
