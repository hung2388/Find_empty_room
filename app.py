"""
app.py: Web Application for finding available university classrooms.
Runs using Python's built-in http.server (no external dependencies required).
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime

# Import the core engine
from room_finder import TimetableEngine, date_to_thu_and_week, DEFAULT_SEMESTER_START

DATA_FILE = "TKB20261-FULL(Sheet1).csv"
PORT = 5000

# Initialize and load data on startup
engine = TimetableEngine()
if os.path.exists(DATA_FILE):
    print(f"[*] Đang tải dữ liệu từ {DATA_FILE}...")
    load_stats = engine.load_file(DATA_FILE)
    print(f"[✓] Đã tải xong: {load_stats['valid_rooms']} phòng, {load_stats['buildings']} tòa nhà.")
else:
    print(f"[!] Không tìm thấy file {DATA_FILE}.")


HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HUST Room Finder - Tra Cứu Phòng Trống</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    .room-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.25rem 0.6rem;
      border-radius: 0.375rem;
      font-weight: 600;
      font-size: 0.85rem;
      background-color: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
      transition: all 0.15s ease-in-out;
    }
    .room-pill:hover {
      background-color: #059669;
      color: #ffffff;
      transform: translateY(-1px);
    }
    .custom-scrollbar::-webkit-scrollbar {
      height: 8px;
      width: 8px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col">

  <!-- Header -->
  <header class="bg-gradient-to-r from-red-700 via-red-800 to-rose-900 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
          <i class="fa-solid fa-door-open text-xl text-amber-300"></i>
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">Tra Cứu Phòng Trống</h1>
          <p class="text-xs text-red-200">Tìm nhanh phòng học khả dụng theo ngày, buổi và tòa nhà</p>
        </div>
      </div>
      <div class="flex items-center gap-4 text-xs bg-black/20 px-3 py-1.5 rounded-lg border border-white/10">
        <div><span class="text-red-300">File:</span> <span class="font-semibold text-white">TKB20261-FULL</span></div>
        <div class="w-px h-4 bg-white/20"></div>
        <div><span class="text-red-300">Tuần hiện tại:</span> <span class="font-bold text-amber-300">Tuần 7</span></div>
        <div class="w-px h-4 bg-white/20"></div>
        <div><span class="text-red-300">Tổng phòng:</span> <span class="font-semibold text-white" id="stat-total-rooms">--</span></div>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
    
    <!-- Filter Card -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-6">
      <h2 class="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
        <i class="fa-solid fa-sliders text-red-600"></i>
        Tiêu chí tìm phòng trống
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        <!-- 1. Date selection -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold uppercase text-slate-500 tracking-wider">
            1. Chọn Ngày
          </label>
          <div class="relative">
            <input type="date" id="input-date" value="2026-10-30" 
              class="w-full bg-slate-50 border border-slate-300 text-slate-800 rounded-xl px-3.5 py-2.5 text-sm font-medium focus:ring-2 focus:ring-red-500 focus:outline-none transition">
          </div>
          <div class="flex items-center justify-between text-xs text-slate-500 px-1 pt-1">
            <span id="date-thu-label" class="font-semibold text-red-600">Thứ Sáu (6)</span>
            <span id="date-week-label" class="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">Tuần 7</span>
          </div>
        </div>

        <!-- 2. Session selection -->
        <div class="space-y-1.5">
          <label class="block text-xs font-semibold uppercase text-slate-500 tracking-wider">
            2. Chọn Buổi
          </label>
          <div class="grid grid-cols-3 gap-2">
            <button type="button" onclick="selectSession('sang')" id="btn-session-sang" 
              class="session-btn py-2.5 px-3 rounded-xl border text-sm font-medium text-slate-700 bg-slate-50 border-slate-200 hover:bg-slate-100 transition flex flex-col items-center">
              <i class="fa-solid fa-sun text-amber-500 mb-1"></i>
              <span>Sáng</span>
            </button>
            <button type="button" onclick="selectSession('chieu')" id="btn-session-chieu" 
              class="session-btn py-2.5 px-3 rounded-xl border text-sm font-medium text-white bg-red-600 border-red-600 shadow-sm transition flex flex-col items-center">
              <i class="fa-solid fa-cloud-sun text-amber-200 mb-1"></i>
              <span>Chiều</span>
            </button>
            <button type="button" onclick="selectSession('toi')" id="btn-session-toi" 
              class="session-btn py-2.5 px-3 rounded-xl border text-sm font-medium text-slate-700 bg-slate-50 border-slate-200 hover:bg-slate-100 transition flex flex-col items-center">
              <i class="fa-solid fa-moon text-indigo-400 mb-1"></i>
              <span>Tối</span>
            </button>
          </div>
          <div class="text-[11px] text-slate-400 text-center pt-0.5" id="session-desc">
            Chiều: 12h30-14h10, 14h10-16h40, 15h05-17h30
          </div>
        </div>

        <!-- 3. Buildings Quick Filter & Selection -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="block text-xs font-semibold uppercase text-slate-500 tracking-wider">
              3. Chọn Tòa Nhà
            </label>
            <div class="text-[11px] space-x-2">
              <button onclick="selectBuildingPreset('D')" class="text-red-600 hover:underline font-medium">Dãy D</button>
              <button onclick="selectBuildingPreset('C')" class="text-red-600 hover:underline font-medium">Dãy C</button>
              <button onclick="selectBuildingPreset('ALL')" class="text-blue-600 hover:underline font-medium">Tất cả</button>
              <button onclick="clearBuildings()" class="text-slate-400 hover:underline">Bỏ chọn</button>
            </div>
          </div>
          
          <!-- Selected buildings tags container -->
          <div id="building-badges-box" class="min-h-[42px] p-2 bg-slate-50 border border-slate-300 rounded-xl flex flex-wrap gap-1.5 max-h-24 overflow-y-auto custom-scrollbar">
            <!-- Badges injected dynamically -->
          </div>
          <p class="text-[11px] text-slate-400">Bấm các nút chọn nhanh hoặc chọn các tòa bên dưới.</p>
        </div>
      </div>

      <!-- Building Pills List (Collapsible/Selectable) -->
      <div class="mt-4 pt-4 border-t border-slate-100">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-slate-500">Danh sách tòa nhà khả dụng (chạm để bật/tắt):</span>
          <button onclick="toggleBuildingGrid()" id="btn-toggle-grid" class="text-xs text-red-600 font-semibold hover:text-red-700">
            Thu gọn danh sách <i class="fa-solid fa-chevron-up ml-0.5"></i>
          </button>
        </div>
        <div id="all-buildings-container" class="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto custom-scrollbar p-2 bg-slate-50/50 rounded-xl border border-slate-200">
          <!-- Building chips injected here -->
        </div>
      </div>

      <!-- Action Button -->
      <div class="mt-5 flex items-center justify-end gap-3">
        <button onclick="searchRooms()" 
          class="bg-red-600 hover:bg-red-700 text-white font-semibold text-sm px-6 py-2.5 rounded-xl shadow-md shadow-red-500/20 transition flex items-center gap-2">
          <i class="fa-solid fa-magnifying-glass"></i>
          <span>Tra cứu phòng trống ngay</span>
        </button>
      </div>
    </div>

    <!-- Results Section -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <!-- Section Header -->
      <div class="px-5 py-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 class="text-base font-bold text-slate-800 flex items-center gap-2">
            <i class="fa-solid fa-table-cells text-emerald-600"></i>
            Kết quả phòng trống theo khung giờ
          </h3>
          <p class="text-xs text-slate-500 mt-0.5" id="results-summary">
            Hiển thị các phòng hoàn toàn trống, không có lịch học trong khung giờ
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="copyTableText()" 
            class="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm transition flex items-center gap-1.5">
            <i class="fa-regular fa-copy"></i>
            <span>Sao chép bảng</span>
          </button>
          <button onclick="exportCSV()" 
            class="px-3 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 shadow-sm transition flex items-center gap-1.5">
            <i class="fa-solid fa-file-csv"></i>
            <span>Tải CSV</span>
          </button>
        </div>
      </div>

      <!-- Results Table View (As requested: Row is Time, Columns are Free Rooms) -->
      <div class="overflow-x-auto custom-scrollbar p-4">
        <table class="w-full text-left border-collapse" id="results-table">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-100/70 text-slate-600 text-xs uppercase font-semibold">
              <th class="py-3 px-4 min-w-[140px] sticky left-0 bg-slate-100 shadow-[1px_0_0_0_#e2e8f0]">Time</th>
              <!-- Dynamic Room Columns Header will go here -->
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-sm" id="results-tbody">
            <tr>
              <td colspan="10" class="py-12 text-center text-slate-400">
                <i class="fa-solid fa-spinner fa-spin text-2xl text-red-500 mb-2"></i>
                <p>Đang tải dữ liệu...</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Additional Info Tabs: Conflicts & Missing Rows -->
    <div class="mt-6">
      <div class="flex items-center gap-4 border-b border-slate-200 text-xs font-medium text-slate-500 mb-3">
        <button onclick="toggleAuditTab('conflicts')" id="tab-btn-conflicts" class="pb-2 border-b-2 border-transparent hover:text-slate-700">
          <i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i> Rà soát trùng lịch trong file (<span id="count-conflicts">0</span>)
        </button>
        <button onclick="toggleAuditTab('invalids')" id="tab-btn-invalids" class="pb-2 border-b-2 border-transparent hover:text-slate-700">
          <i class="fa-solid fa-circle-info text-blue-500 mr-1"></i> Dòng thiếu thông tin trong file (<span id="count-invalids">0</span>)
        </button>
      </div>

      <div id="audit-content-conflicts" class="hidden bg-white p-4 rounded-xl border border-slate-200 text-xs max-h-72 overflow-y-auto custom-scrollbar">
        <p class="font-semibold text-slate-700 mb-2">Các phòng bị xếp trùng lịch trong file TKB (được đánh dấu để rà soát lại):</p>
        <ul id="conflicts-list" class="space-y-1.5 text-slate-600"></ul>
      </div>

      <div id="audit-content-invalids" class="hidden bg-white p-4 rounded-xl border border-slate-200 text-xs max-h-72 overflow-y-auto custom-scrollbar">
        <p class="font-semibold text-slate-700 mb-2">Các dòng trong file bị thiếu thông tin hoặc sai định dạng:</p>
        <ul id="invalids-list" class="space-y-1 text-slate-600"></ul>
      </div>
    </div>

  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-slate-200 py-4 mt-8 text-center text-xs text-slate-400">
    Hệ thống Tra cứu phòng trống & Chuẩn hóa TKB ĐHBK Hà Nội • 2026
  </footer>

  <!-- Scripts -->
  <script>
    let selectedSession = "chieu";
    let selectedBuildings = new Set(["D3"]);
    let allAvailableBuildings = [];
    let currentTableData = [];

    const SEMESTER_START = new Date("2026-09-14");

    function getThuAndWeek(dateStr) {
      const d = new Date(dateStr + "T00:00:00");
      let day = d.getDay(); // 0 is Sunday, 1 is Monday...
      let thu = day === 0 ? 8 : day + 1; // 2..8
      
      const diffTime = d.getTime() - SEMESTER_START.getTime();
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
      const week = Math.floor(diffDays / 7) + 1;
      return { thu, week };
    }

    const thuNames = {
      2: "Thứ Hai (2)",
      3: "Thứ Ba (3)",
      4: "Thứ Tư (4)",
      5: "Thứ Năm (5)",
      6: "Thứ Sáu (6)",
      7: "Thứ Bảy (7)",
      8: "Chủ Nhật (CN)"
    };

    function updateDateLabels() {
      const val = document.getElementById("input-date").value;
      if (!val) return;
      const { thu, week } = getThuAndWeek(val);
      document.getElementById("date-thu-label").innerText = thuNames[thu] || "Thứ " + thu;
      document.getElementById("date-week-label").innerText = "Tuần " + week;
    }

    document.getElementById("input-date").addEventListener("change", () => {
      updateDateLabels();
      searchRooms();
    });

    function selectSession(sess) {
      selectedSession = sess;
      ["sang", "chieu", "toi"].forEach(s => {
        const btn = document.getElementById("btn-session-" + s);
        if (s === sess) {
          btn.className = "session-btn py-2.5 px-3 rounded-xl border text-sm font-medium text-white bg-red-600 border-red-600 shadow-sm transition flex flex-col items-center";
        } else {
          btn.className = "session-btn py-2.5 px-3 rounded-xl border text-sm font-medium text-slate-700 bg-slate-50 border-slate-200 hover:bg-slate-100 transition flex flex-col items-center";
        }
      });
      const desc = {
        sang: "Sáng: 06h45-09h10, 09h20-11h45",
        chieu: "Chiều: 12h30-14h10, 14h10-16h40, 15h05-17h30",
        toi: "Tối: 17h45-19h15, 18h00-20h30"
      };
      document.getElementById("session-desc").innerText = desc[sess] || "";
      searchRooms();
    }

    function renderBuildingChips() {
      const container = document.getElementById("all-buildings-container");
      container.innerHTML = "";
      allAvailableBuildings.forEach(b => {
        const isSelected = selectedBuildings.has(b);
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = `text-xs px-2.5 py-1 rounded-lg border font-medium transition ${
          isSelected 
            ? "bg-red-600 text-white border-red-600 shadow-xs" 
            : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
        }`;
        chip.innerText = b;
        chip.onclick = () => toggleBuilding(b);
        container.appendChild(chip);
      });

      renderSelectedBadges();
    }

    function renderSelectedBadges() {
      const box = document.getElementById("building-badges-box");
      box.innerHTML = "";
      if (selectedBuildings.size === 0) {
        box.innerHTML = `<span class="text-xs text-slate-400 italic">Chưa chọn tòa nhà nào</span>`;
        return;
      }
      Array.from(selectedBuildings).sort().forEach(b => {
        const badge = document.createElement("span");
        badge.className = "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-red-50 text-red-700 border border-red-200";
        badge.innerHTML = `${b} <button onclick="toggleBuilding('${b}')" class="hover:text-red-900 ml-0.5">&times;</button>`;
        box.appendChild(badge);
      });
    }

    function toggleBuilding(b) {
      if (selectedBuildings.has(b)) {
        selectedBuildings.delete(b);
      } else {
        selectedBuildings.add(b);
      }
      renderBuildingChips();
      searchRooms();
    }

    function selectBuildingPreset(type) {
      if (type === "D") {
        selectedBuildings = new Set(["D3", "D4", "D5", "D6", "D7", "D8", "D9"]);
      } else if (type === "C") {
        selectedBuildings = new Set(["C1", "C3", "C4", "C5", "C7", "C9", "C10"]);
      } else if (type === "ALL") {
        selectedBuildings = new Set(allAvailableBuildings);
      }
      renderBuildingChips();
      searchRooms();
    }

    function clearBuildings() {
      selectedBuildings.clear();
      renderBuildingChips();
      searchRooms();
    }

    let gridExpanded = true;
    function toggleBuildingGrid() {
      gridExpanded = !gridExpanded;
      const el = document.getElementById("all-buildings-container");
      const btn = document.getElementById("btn-toggle-grid");
      if (gridExpanded) {
        el.classList.remove("hidden");
        btn.innerHTML = `Thu gọn danh sách <i class="fa-solid fa-chevron-up ml-0.5"></i>`;
      } else {
        el.classList.add("hidden");
        btn.innerHTML = `Mở rộng danh sách <i class="fa-solid fa-chevron-down ml-0.5"></i>`;
      }
    }

    async function searchRooms() {
      const dateVal = document.getElementById("input-date").value || "2026-10-30";
      const { thu, week } = getThuAndWeek(dateVal);
      const buildingsList = Array.from(selectedBuildings).join(",");

      if (!buildingsList) {
        document.getElementById("results-tbody").innerHTML = `
          <tr>
            <td colspan="10" class="py-8 text-center text-slate-400">
              Vui lòng chọn ít nhất một tòa nhà để xem phòng trống.
            </td>
          </tr>
        `;
        return;
      }

      document.getElementById("results-tbody").innerHTML = `
        <tr>
          <td colspan="10" class="py-8 text-center text-slate-400">
            <i class="fa-solid fa-spinner fa-spin text-xl text-red-500 mr-2"></i> Đang tìm phòng trống...
          </td>
        </tr>
      `;

      try {
        const res = await fetch(`/api/search?date=${dateVal}&week=${week}&thu=${thu}&session=${selectedSession}&buildings=${encodeURIComponent(buildingsList)}`);
        const json = await res.json();
        currentTableData = json.data || [];
        renderResultsTable(currentTableData);
      } catch (e) {
        console.error(e);
        document.getElementById("results-tbody").innerHTML = `
          <tr>
            <td colspan="10" class="py-8 text-center text-red-500">
              Lỗi kết nối khi tìm phòng. Vui lòng thử lại.
            </td>
          </tr>
        `;
      }
    }

    function renderResultsTable(tableData) {
      const thead = document.querySelector("#results-table thead tr");
      const tbody = document.getElementById("results-tbody");

      if (!tableData || tableData.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="10" class="py-8 text-center text-slate-400">
              Không tìm thấy phòng trống nào.
            </td>
          </tr>
        `;
        return;
      }

      // Max free rooms across all slots
      let maxRooms = 0;
      tableData.forEach(r => {
        if (r.free_rooms.length > maxRooms) maxRooms = r.free_rooms.length;
      });

      // Build Header: Time | Phòng 1 | Phòng 2 | ...
      let thHtml = `<th class="py-3 px-4 min-w-[130px] sticky left-0 bg-slate-100 shadow-[1px_0_0_0_#e2e8f0] font-bold text-slate-700">Time</th>`;
      for (let i = 1; i <= maxRooms; i++) {
        thHtml += `<th class="py-3 px-3 min-w-[90px] text-center font-medium text-slate-600">Phòng ${i}</th>`;
      }
      thead.innerHTML = thHtml;

      // Build Rows
      let trHtml = "";
      tableData.forEach(row => {
        trHtml += `<tr class="hover:bg-slate-50 transition border-b border-slate-100">`;
        trHtml += `<td class="py-3 px-4 font-bold text-slate-800 sticky left-0 bg-white hover:bg-slate-50 shadow-[1px_0_0_0_#e2e8f0] whitespace-nowrap">
          <span class="text-red-700">${row.time}</span>
          <span class="ml-1 text-[11px] font-normal text-slate-400">(${row.free_rooms.length} phòng)</span>
        </td>`;

        for (let i = 0; i < maxRooms; i++) {
          const rm = row.free_rooms[i];
          if (rm) {
            trHtml += `<td class="py-2.5 px-2 text-center">
              <span class="room-pill">${rm}</span>
            </td>`;
          } else {
            trHtml += `<td class="py-2.5 px-2 text-center text-slate-200">-</td>`;
          }
        }
        trHtml += `</tr>`;
      });

      tbody.innerHTML = trHtml;
    }

    function copyTableText() {
      if (!currentTableData || currentTableData.length === 0) return;
      let maxRooms = 0;
      currentTableData.forEach(r => { if (r.free_rooms.length > maxRooms) maxRooms = r.free_rooms.length; });

      let text = "time";
      for (let i = 1; i <= maxRooms; i++) text += ` | Phòng ${i}`;
      text += "\\n";

      currentTableData.forEach(r => {
        text += r.time;
        for (let i = 0; i < maxRooms; i++) {
          text += " | " + (r.free_rooms[i] || "");
        }
        text += "\\n";
      });

      navigator.clipboard.writeText(text).then(() => {
        alert("Đã sao chép bảng phòng trống vào clipboard!");
      });
    }

    function exportCSV() {
      if (!currentTableData || currentTableData.length === 0) return;
      let maxRooms = 0;
      currentTableData.forEach(r => { if (r.free_rooms.length > maxRooms) maxRooms = r.free_rooms.length; });

      let csv = "time";
      for (let i = 1; i <= maxRooms; i++) csv += `,Phong ${i}`;
      csv += "\\r\\n";

      currentTableData.forEach(r => {
        csv += `"${r.time}"`;
        for (let i = 0; i < maxRooms; i++) {
          csv += `,"${r.free_rooms[i] || ""}"`;
        }
        csv += "\\r\\n";
      });

      const blob = new Blob(["\\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `phong_trong_${selectedSession}.csv`;
      a.click();
    }

    function toggleAuditTab(tab) {
      const confBox = document.getElementById("audit-content-conflicts");
      const invBox = document.getElementById("audit-content-invalids");
      if (tab === "conflicts") {
        confBox.classList.toggle("hidden");
        invBox.classList.add("hidden");
      } else {
        invBox.classList.toggle("hidden");
        confBox.classList.add("hidden");
      }
    }

    // Init load
    async function init() {
      updateDateLabels();
      try {
        const res = await fetch("/api/init");
        const json = await res.json();
        allAvailableBuildings = json.buildings || [];
        document.getElementById("stat-total-rooms").innerText = json.total_rooms || "--";
        document.getElementById("count-conflicts").innerText = (json.conflicts_count || 0) + " cặp";
        document.getElementById("count-invalids").innerText = (json.invalid_rows_count || 0) + " dòng";

        // Render conflicts list sample
        const confUl = document.getElementById("conflicts-list");
        (json.sample_conflicts || []).forEach(c => {
          const li = document.createElement("li");
          li.innerHTML = `<strong>Phòng ${c.room}</strong> (Thứ ${c.thu}): Trùng dòng ${c.s1_line} & ${c.s2_line} ở các tuần [${c.weeks.join(", ")}]`;
          confUl.appendChild(li);
        });

        const invUl = document.getElementById("invalids-list");
        (json.sample_invalids || []).forEach(inv => {
          const li = document.createElement("li");
          li.innerHTML = `Dòng ${inv.line}: Phòng '${inv.room}', Thứ '${inv.thu}', Giờ '${inv.time}', Tuần '${inv.week}' &rarr; ${inv.reason}`;
          invUl.appendChild(li);
        });

        renderBuildingChips();
        searchRooms();
      } catch (e) {
        console.error(e);
      }
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default request logging to keep console clean
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/api/init":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            data = {
                "total_rooms": len(engine.all_rooms),
                "total_buildings": len(engine.all_buildings),
                "buildings": sorted(list(engine.all_buildings)),
                "conflicts_count": len(engine.conflicts),
                "invalid_rows_count": len(engine.invalid_rows),
                "sample_conflicts": engine.conflicts[:20],
                "sample_invalids": engine.invalid_rows[:20]
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/search":
            date_str = params.get("date", ["2026-10-30"])[0]
            session = params.get("session", ["chieu"])[0]
            buildings_param = params.get("buildings", ["D3"])[0]

            buildings = [b.strip() for b in buildings_param.split(",") if b.strip()]
            
            try:
                target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                calc_thu, calc_week = date_to_thu_and_week(target_date)
            except Exception:
                calc_thu, calc_week = 6, 7

            week = int(params.get("week", [calc_week])[0])
            thu = int(params.get("thu", [calc_thu])[0])

            table_data = engine.get_table_result(buildings, thu, week, session)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"data": table_data}, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print("\n" + "=" * 65)
    print(f" [✓] SERVER TRA CỨU PHÒNG TRỐNG ĐANG CHẠY TẠI:")
    print(f"     👉 http://localhost:{PORT}")
    print("=" * 65)
    print(" (Bấm Ctrl+C trong terminal để dừng server khi cần)\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Đang tắt server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()

