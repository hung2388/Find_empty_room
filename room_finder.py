import os, sys, re, csv, io, datetime
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Base semester start for Fall 2026 (Semester 20261)
# 2026-09-14 is Monday of Week 1; today 2026-10-30 is Friday of Week 7.
DEFAULT_SEMESTER_START = datetime.date(2026, 9, 14)

def parse_time_range(t_str: Any) -> Optional[Tuple[int, int]]:
    """Parses time string like 0920-1145, 1230-1410 into (start_min, end_min)."""
    if not t_str or str(t_str).strip().upper() in ("NULL", "NONE", ""):
        return None
    s = str(t_str).strip()
    m = re.match(r"^(\d{2})(\d{2})\s*[-–—]\s*(\d{2})(\d{2})$", s)
    if m:
        h1, m1 = int(m.group(1)), int(m.group(2))
        h2, m2 = int(m.group(3)), int(m.group(4))
        return (h1 * 60 + m1, h2 * 60 + m2)
    # Check with colons / h
    m2 = re.match(r"^(\d{1,2})[:h](\d{2})\s*[-–—]\s*(\d{1,2})[:h](\d{2})$", s.lower())
    if m2:
        h1, m1 = int(m2.group(1)), int(m2.group(2))
        h2, m2 = int(m2.group(3)), int(m2.group(4))
        return (h1 * 60 + m1, h2 * 60 + m2)
    return None

def parse_weeks(w_str: Any) -> Set[int]:
    """Parses week string like '2-9,11-18' into set of ints {2,3,4,...,9,11,...,18}."""
    if not w_str:
        return set()
    s = str(w_str).strip().replace('"', "").replace("'", "")
    if not s or s.upper() in ("NULL", "NONE"):
        return set()
    weeks = set()
    for token in re.split(r"[,;]+", s):
        token = token.strip()
        if not token:
            continue
        m = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", token)
        if m:
            start_w, end_w = int(m.group(1)), int(m.group(2))
            if 0 < start_w <= end_w <= 60:
                weeks.update(range(start_w, end_w + 1))
        elif token.isdigit():
            w = int(token)
            if 0 < w <= 60:
                weeks.add(w)
    return weeks

def parse_thu(thu_raw: Any) -> Optional[int]:
    """Parses day of week into 2..8 (2=Thứ 2, 7=Thứ 7, 8=Chủ nhật)."""
    if not thu_raw:
        return None
    s = str(thu_raw).strip().lower()
    if not s or s in ("null", "none"):
        return None
    if s.isdigit() and 2 <= int(s) <= 8:
        return int(s)
    if "cn" in s or "chủ" in s or "chu" in s:
        return 8
    for d in range(2, 8):
        if str(d) in s:
            return d
    return None

def split_room(room_str: Any) -> Tuple[Optional[str], Optional[str], str]:
    """Splits room into (building, room_num, raw_room) e.g. D9-102 -> (D9, 102, D9-102)."""
    raw = str(room_str).strip() if room_str is not None else ""
    if not raw or raw.upper() in ("NULL", "NONE"):
        return None, None, raw
    if "-" in raw:
        b, r = raw.rsplit("-", 1)
        return b.strip(), r.strip(), raw
    return raw, raw, raw

def natural_sort_key(s: str) -> List[Any]:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]

def date_to_thu_and_week(target_date: datetime.date, semester_start: datetime.date = DEFAULT_SEMESTER_START) -> Tuple[int, int]:
    thu = target_date.isoweekday() + 1 # Monday=1 -> 2
    week_num = ((target_date - semester_start).days // 7) + 1
    return thu, week_num

class TimetableEngine:
    def __init__(self):
        self.all_rooms: Set[str] = set()
        self.all_buildings: Set[str] = set()
        self.building_to_rooms: Dict[str, Set[str]] = defaultdict(set)
        # room -> thu -> list of (start_min, end_min, weeks, is_cancelled, line_no)
        self.room_classes: Dict[str, Dict[int, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self.invalid_rows: List[Dict[str, Any]] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.detected_encoding: str = "cp1252"
        self.total_rows: int = 0

    def load_file(self, file_path_or_bytes: Any, encoding_override: Optional[str] = None) -> Dict[str, Any]:
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as f:
                raw_bytes = f.read()
        else:
            raw_bytes = file_path_or_bytes

        # Encoding detection
        text = ""
        enc = encoding_override
        if not enc:
            try:
                text = raw_bytes.decode("utf-8")
                enc = "utf-8"
            except UnicodeDecodeError:
                for cand in ["cp1252", "cp1258", "latin1"]:
                    try:
                        text = raw_bytes.decode(cand)
                        enc = cand
                        break
                    except Exception:
                        pass
        else:
            text = raw_bytes.decode(enc, errors="replace")

        self.detected_encoding = enc or "cp1252"
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        self.total_rows = len(rows)

        # Find header row
        header_idx = -1
        thu_col = 10
        time_col = 11
        week_col = 15
        room_col = 16
        status_col = 20

        for idx, r in enumerate(rows[:20]):
            r_str = " ".join(r).lower()
            if "ph" in r_str and ("th" in r_str or "tu" in r_str):
                header_idx = idx
                # Map columns dynamically
                for c_idx, c_val in enumerate(r):
                    cv = c_val.strip().lower()
                    if cv in ("th?", "thứ", "thu"): thu_col = c_idx
                    elif "gian" in cv or "time" in cv: time_col = c_idx
                    elif "tu" in cv or "week" in cv: week_col = c_idx
                    elif "ph" in cv or "room" in cv: room_col = c_idx
                    elif "tr?ng" in cv or "trạng" in cv or "status" in cv: status_col = c_idx
                break

        if header_idx == -1:
            header_idx = 2 # standard default for HUST export

        for line_no, r in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            if not r or all(not str(c).strip() for c in r):
                continue
            
            raw_room = r[room_col].strip() if room_col < len(r) else ""
            raw_thu = r[thu_col].strip() if thu_col < len(r) else ""
            raw_time = r[time_col].strip() if time_col < len(r) else ""
            raw_week = r[week_col].strip() if week_col < len(r) else ""
            status = r[status_col].strip() if status_col < len(r) else ""

            bldg, rm_num, _ = split_room(raw_room)
            thu = parse_thu(raw_thu)
            t_range = parse_time_range(raw_time)
            weeks = parse_weeks(raw_week)

            if not bldg or not thu or not t_range or not weeks:
                self.invalid_rows.append({
                    "line": line_no,
                    "room": raw_room,
                    "thu": raw_thu,
                    "time": raw_time,
                    "week": raw_week,
                    "reason": "Thiếu thông tin hoặc sai định dạng"
                })
                continue

            is_canc = "hu" in status.lower() or "hủy" in status.lower()

            self.all_rooms.add(raw_room)
            self.all_buildings.add(bldg)
            self.building_to_rooms[bldg].add(raw_room)

            self.room_classes[raw_room][thu].append({
                "start": t_range[0],
                "end": t_range[1],
                "weeks": weeks,
                "cancelled": is_canc,
                "line": line_no,
                "raw_time": raw_time,
                "raw_weeks": raw_week
            })

        # Conflict check
        for rm, day_map in self.room_classes.items():
            for d, sessions in day_map.items():
                n = len(sessions)
                for i in range(n):
                    s1 = sessions[i]
                    if s1["cancelled"]: continue
                    for j in range(i + 1, n):
                        s2 = sessions[j]
                        if s2["cancelled"]: continue
                        if max(s1["start"], s2["start"]) < min(s1["end"], s2["end"]):
                            overlap_w = sorted(list(s1["weeks"].intersection(s2["weeks"])))
                            if overlap_w:
                                self.conflicts.append({
                                    "room": rm,
                                    "thu": d,
                                    "s1_line": s1["line"],
                                    "s2_line": s2["line"],
                                    "weeks": overlap_w
                                })

        return {
            "total_rows": self.total_rows,
            "valid_rooms": len(self.all_rooms),
            "buildings": len(self.all_buildings),
            "invalid_rows": len(self.invalid_rows),
            "conflicts": len(self.conflicts),
            "encoding": self.detected_encoding
        }

    def is_room_busy(self, room: str, thu: int, week: int, start_min: int, end_min: int) -> bool:
        """Returns True if the room is busy at (thu, week, [start_min, end_min])."""
        sessions = self.room_classes.get(room, {}).get(thu, [])
        for s in sessions:
            if s["cancelled"]:
                continue
            if week in s["weeks"]:
                if max(s["start"], start_min) < min(s["end"], end_min):
                    return True
        return False

    def find_free_rooms(self, buildings: List[str], thu: int, week: int, start_min: int, end_min: int) -> List[str]:
        target_rooms = set()
        for b in buildings:
            if b.upper() in ("ALL", "TAT_CA"):
                target_rooms.update(self.all_rooms)
            else:
                target_rooms.update(self.building_to_rooms.get(b, set()))

        free = [rm for rm in target_rooms if not self.is_room_busy(rm, thu, week, start_min, end_min)]
        return sorted(free, key=natural_sort_key)

    def get_table_result(self, buildings: List[str], thu: int, week: int, session: str) -> List[Dict[str, Any]]:
        # Define slots based on session
        s = session.lower()
        if "sang" in s or "sáng" in s:
            slots = [
                ("06h45-09h10", 6 * 60 + 45, 9 * 60 + 10),
                ("09h20-11h45", 9 * 60 + 20, 11 * 60 + 45),
            ]
        elif "toi" in s or "tối" in s:
            slots = [
                ("17h45-19h15", 17 * 60 + 45, 19 * 60 + 15),
                ("18h00-20h30", 18 * 60, 20 * 60 + 30),
            ]
        else: # afternoon (chiều)
            slots = [
                ("12h30-14h10", 12 * 60 + 30, 14 * 60 + 10),
                ("14h10-16h40", 14 * 60 + 10, 16 * 60 + 40),
                ("15h05-17h30", 15 * 60 + 5, 17 * 60 + 30),
            ]

        res = []
        for label, start_m, end_m in slots:
            free = self.find_free_rooms(buildings, thu, week, start_m, end_m)
            res.append({
                "time": label,
                "free_rooms": free,
                "count": len(free)
            })
        return res

def render_grid_table(table_data: List[Dict[str, Any]]) -> str:
    """
    Renders table exactly in format:
    time        | Phòng 1 | Phòng 2 | Phòng 3 ...
    12h30-14h10 | D3-101  | D3-106  | D3-303  ...
    14h10-16h40 | D3-303  | D3-304  | D3-305  ...
    """
    if not table_data:
        return "Không có dữ liệu."
    max_rooms = max((len(r["free_rooms"]) for r in table_data), default=0)
    if max_rooms == 0:
        return "Không có phòng nào trống trong các khung giờ đã chọn."

    headers = ["time"] + [f"Phòng {i+1}" for i in range(max_rooms)]
    rows = []
    for r in table_data:
        row = [r["time"]] + r["free_rooms"] + [""] * (max_rooms - len(r["free_rooms"]))
        rows.append(row)

    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    data_lines = [" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) for row in rows]

    return f"{header_line}\n{sep_line}\n" + "\n".join(data_lines)

# Run CLI if executed
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tra cứu phòng trống")
    parser.add_argument("--file", default="TKB20261-FULL(Sheet1).csv")
    parser.add_argument("--date", default="2026-10-30", help="YYYY-MM-DD")
    parser.add_argument("--week", type=int, default=None)
    parser.add_argument("--session", default="chieu", choices=["sang", "chieu", "toi"])
    parser.add_argument("--buildings", default="D3", help="Danh sách tòa, ví dụ: D3 hoặc D3,D5")
    args = parser.parse_args()

    engine = TimetableEngine()
    engine.load_file(args.file)

    target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    thu, week_calc = date_to_thu_and_week(target_date)
    week_final = args.week if args.week is not None else week_calc

    bldgs = [b.strip() for b in args.buildings.split(",") if b.strip()]

    print(f"\n=== KẾT QUẢ TÌM PHÒNG TRỐNG: Tòa {', '.join(bldgs)} | Thứ {thu} | Tuần {week_final} ({args.date}) | Buổi {args.session.upper()} ===\n")
    data = engine.get_table_result(bldgs, thu, week_final, args.session)
    print(render_grid_table(data))
    print()
