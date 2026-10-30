import sys
import os

# Delegate to api/index.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "api"))
sys.path.insert(0, BASE_DIR)

from api.index import app

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print(" [✓] SERVER ĐANG CHẠY TẠI: http://localhost:5000")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
