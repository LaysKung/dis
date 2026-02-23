#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║         Discord Server Copier — สำหรับทดลองเท่านั้น         ║
║  ⚠️  การใช้ User Token ผ่าน Script ผิด Discord TOS          ║
║      อาจโดน ban ถาวร ใช้กับบัญชี dev ของตัวเองเท่านั้น      ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests
import time
import json
import os
import sys
from datetime import datetime

# ─── สี Terminal ───────────────────────────────────────────────
R  = "\033[91m"   # แดง
G  = "\033[92m"   # เขียว
Y  = "\033[93m"   # เหลือง
B  = "\033[94m"   # น้ำเงิน
M  = "\033[95m"   # ม่วง
C  = "\033[96m"   # ฟ้า
W  = "\033[97m"   # ขาว
DIM = "\033[2m"   # หรี่
RESET = "\033[0m"
BOLD  = "\033[1m"

BASE = "https://discord.com/api/v9"

def banner():
    print(f"""
{M}{BOLD}╔══════════════════════════════════════════════════════════════╗
║       Discord Server Copier  v2.0  (Python Edition)         ║
╚══════════════════════════════════════════════════════════════╝{RESET}
{R}  ⚠️  WARNING: ใช้ User Token ผิด Discord TOS → อาจโดน ban     {RESET}
{DIM}  สำหรับทดลอง/ศึกษาเท่านั้น ใช้กับบัญชี dev ของตัวเองเท่านั้น{RESET}
""")

def log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"info": f"{B}[*]{RESET}", "ok": f"{G}[✓]{RESET}", "warn": f"{Y}[!]{RESET}",
             "err": f"{R}[✗]{RESET}", "send": f"{C}[→]{RESET}", "dim": f"{DIM}[-]{RESET}"}
    icon = icons.get(level, icons["info"])
    print(f"  {DIM}{ts}{RESET} {icon} {msg}")

def header(title):
    print(f"\n{M}{BOLD}  ── {title} {'─'*(50-len(title))}{RESET}")

# ─── Discord API ────────────────────────────────────────────────

def api_get(endpoint, token, params=None):
    """GET request พร้อม rate-limit retry"""
    url = f"{BASE}{endpoint}"
    headers = {"Authorization": token}
    while True:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
        except requests.exceptions.ConnectionError:
            raise ConnectionError("ไม่สามารถเชื่อมต่อ Discord API ได้")

        if r.status_code == 401:
            raise PermissionError("Token ไม่ถูกต้องหรือหมดอายุ (401)")
        if r.status_code == 403:
            return None  # ไม่มีสิทธิ์อ่าน channel นี้
        if r.status_code == 404:
            raise FileNotFoundError(f"ไม่พบ resource (404): {endpoint}")
        if r.status_code == 429:
            data = r.json()
            wait = data.get("retry_after", 5)
            log(f"Rate limited! รอ {wait:.1f}s...", "warn")
            time.sleep(wait + 0.5)
            continue
        if r.status_code == 200:
            return r.json()
        return None

def api_post(endpoint, token, payload):
    """POST request พร้อม rate-limit retry"""
    url = f"{BASE}{endpoint}"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    while True:
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
        except requests.exceptions.ConnectionError:
            raise ConnectionError("ไม่สามารถเชื่อมต่อ Discord API ได้")

        if r.status_code == 429:
            data = r.json()
            wait = data.get("retry_after", 5)
            log(f"Rate limited! รอ {wait:.1f}s...", "warn")
            time.sleep(wait + 0.5)
            continue
        if r.status_code in (200, 201):
            return r.json()
        return None

# ─── ดึงข้อความทุกข้อความใน Channel ────────────────────────────

def fetch_all_messages(token, channel_id, channel_name="?"):
    """ดึงข้อความทั้งหมด (ไม่จำกัด) จาก channel"""
    messages = []
    before = None
    page = 0

    while True:
        page += 1
        params = {"limit": 100}
        if before:
            params["before"] = before

        batch = api_get(f"/channels/{channel_id}/messages", token, params)

        if batch is None:
            log(f"  ไม่มีสิทธิ์อ่าน #{channel_name} — ข้าม", "warn")
            break

        if not batch:
            break

        messages.extend(batch)
        before = batch[-1]["id"]

        print(f"\r    {DIM}ดึงหน้า {page} | รวม {len(messages)} ข้อความ...{RESET}", end="", flush=True)

        if len(batch) < 100:
            break  # หน้าสุดท้าย

        time.sleep(0.4)  # หลีกเลี่ยง rate limit

    print()  # newline
    messages.reverse()  # เรียงจากเก่าไปใหม่
    return messages

# ─── ส่งข้อความ ─────────────────────────────────────────────────

def send_message(token, channel_id, content):
    result = api_post(f"/channels/{channel_id}/messages", token, {"content": content[:2000]})
    return result is not None

# ─── สร้าง Channel ──────────────────────────────────────────────

def create_channel(token, guild_id, name, ch_type=0, parent_id=None):
    payload = {"name": name, "type": ch_type}
    if parent_id:
        payload["parent_id"] = parent_id
    return api_post(f"/guilds/{guild_id}/channels", token, payload)

# ─── โหลดข้อมูล Server ──────────────────────────────────────────

def load_guild_info(token, guild_id):
    log(f"โหลดข้อมูล Server: {guild_id}", "info")
    return api_get(f"/guilds/{guild_id}", token)

def load_channels(token, guild_id):
    log("โหลดรายการ Channels...", "info")
    return api_get(f"/guilds/{guild_id}/channels", token)

# ─── บันทึกไฟล์ ─────────────────────────────────────────────────

def save_results(all_data, guild_name):
    safe_name = "".join(c for c in guild_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"discord_{safe_name}_{ts}"
    os.makedirs(folder, exist_ok=True)

    # JSON รวม
    json_path = os.path.join(folder, "all_messages.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    log(f"บันทึก JSON: {json_path}", "ok")

    # TXT แยก channel
    txt_path = os.path.join(folder, "all_messages.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for ch_name, msgs in all_data.items():
            f.write(f"\n{'='*60}\n# {ch_name}  ({len(msgs)} ข้อความ)\n{'='*60}\n")
            for m in msgs:
                ts_str = m.get("timestamp", "")[:19].replace("T", " ")
                author = m.get("author", {}).get("username", "?")
                content = m.get("content", "[embed/attachment]")
                f.write(f"[{ts_str}] {author}: {content}\n")
    log(f"บันทึก TXT: {txt_path}", "ok")

    # สรุป
    summary_path = os.path.join(folder, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        total = sum(len(v) for v in all_data.values())
        f.write(f"Server: {guild_name}\n")
        f.write(f"Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Channels: {len(all_data)}\n")
        f.write(f"Total Messages: {total}\n\n")
        for ch, msgs in all_data.items():
            f.write(f"  #{ch}: {len(msgs)} ข้อความ\n")
    log(f"บันทึก Summary: {summary_path}", "ok")

    return folder, json_path, txt_path

# ─── MAIN ────────────────────────────────────────────────────────

def main():
    banner()

    # ── รับ Input ──
    header("กรอกข้อมูล")
    print(f"  {DIM}กด Enter เพื่อข้าม (ถ้าไม่ต้องการ Copy){RESET}\n")

    token = input(f"  {C}Token{RESET}          : ").strip()
    src_guild  = input(f"  {C}Source Server ID{RESET}: ").strip()
    dst_guild  = input(f"  {C}Target Server ID{RESET}: ").strip()

    if not token or not src_guild:
        print(f"\n{R}  ✗ กรุณากรอก Token และ Source Server ID{RESET}\n")
        sys.exit(1)

    copy_mode = bool(dst_guild)
    send_delay = 1.5
    if copy_mode:
        delay_input = input(f"  {C}Delay ระหว่างส่ง (วินาที) [{send_delay}]{RESET}: ").strip()
        if delay_input:
            try:
                send_delay = float(delay_input)
            except ValueError:
                pass

    print()

    # ── โหลด Source Server ──
    header("โหลด Source Server")
    try:
        guild_info = load_guild_info(token, src_guild)
        if not guild_info:
            log("ไม่พบ Server หรือไม่มีสิทธิ์", "err")
            sys.exit(1)
        guild_name = guild_info.get("name", src_guild)
        log(f"Server: {W}{BOLD}{guild_name}{RESET}  (ID: {src_guild})", "ok")
    except (PermissionError, FileNotFoundError, ConnectionError) as e:
        log(str(e), "err")
        sys.exit(1)

    channels_raw = load_channels(token, src_guild)
    if not channels_raw:
        log("ไม่สามารถโหลด Channels ได้", "err")
        sys.exit(1)

    # จัดประเภท
    categories  = {c["id"]: c for c in channels_raw if c["type"] == 4}
    text_channels = [c for c in channels_raw if c["type"] == 0]
    text_channels.sort(key=lambda c: (c.get("position", 0),))

    log(f"พบ {len(categories)} categories, {len(text_channels)} text channels", "ok")

    # แสดงรายการ
    print()
    for cat_id, cat in sorted(categories.items(), key=lambda x: x[1].get("position",0)):
        print(f"  {M}▸ {cat['name'].upper()}{RESET}")
        for ch in text_channels:
            if ch.get("parent_id") == cat_id:
                print(f"    {DIM}#{ch['name']}{RESET}")
    no_cat = [c for c in text_channels if not c.get("parent_id")]
    if no_cat:
        print(f"  {M}▸ (ไม่มี Category){RESET}")
        for ch in no_cat:
            print(f"    {DIM}#{ch['name']}{RESET}")

    print(f"\n  {Y}จะดึงข้อความทุก channel ที่เข้าถึงได้ (ไม่จำกัดจำนวน){RESET}")
    confirm = input(f"\n  {W}ยืนยันเริ่มต้น? (y/n){RESET}: ").strip().lower()
    if confirm != "y":
        print(f"\n{Y}  ยกเลิก{RESET}\n")
        sys.exit(0)

    # ── Copy Mode: สร้าง Structure ──
    cat_map = {}  # source cat id → target cat id
    ch_map  = {}  # source ch id  → target ch id

    if copy_mode:
        header("สร้าง Structure ใน Target Server")
        # สร้าง categories
        for cat_id, cat in sorted(categories.items(), key=lambda x: x[1].get("position",0)):
            used = any(c.get("parent_id") == cat_id for c in text_channels)
            if not used:
                continue
            log(f"สร้าง Category: {cat['name']}", "info")
            new_cat = create_channel(token, dst_guild, cat["name"], ch_type=4)
            if new_cat:
                cat_map[cat_id] = new_cat["id"]
                log(f"  → {new_cat['name']} ({new_cat['id']})", "ok")
            time.sleep(0.8)

        # สร้าง text channels
        for ch in text_channels:
            parent_id = ch.get("parent_id")
            target_parent = cat_map.get(parent_id) if parent_id else None
            log(f"สร้าง Channel: #{ch['name']}", "info")
            new_ch = create_channel(token, dst_guild, ch["name"], ch_type=0, parent_id=target_parent)
            if new_ch:
                ch_map[ch["id"]] = new_ch["id"]
                log(f"  → #{new_ch['name']} ({new_ch['id']})", "ok")
            time.sleep(0.8)

    # ── ดึงและ (ส่ง) ข้อความ ──
    header("ดึงข้อความ" + (" + Copy" if copy_mode else ""))

    all_data = {}
    total_msgs = 0
    errors = 0

    for i, ch in enumerate(text_channels, 1):
        ch_name = ch["name"]
        ch_id   = ch["id"]
        pct = int((i / len(text_channels)) * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)

        print(f"\n  {B}[{i}/{len(text_channels)}]{RESET} {W}#{ch_name}{RESET}  {DIM}[{bar}] {pct}%{RESET}")

        # ดึงข้อความ
        try:
            msgs = fetch_all_messages(token, ch_id, ch_name)
        except (PermissionError, ConnectionError) as e:
            log(str(e), "err")
            errors += 1
            continue

        log(f"ดึงได้ {G}{len(msgs)}{RESET} ข้อความ", "ok")
        total_msgs += len(msgs)

        # เก็บข้อมูล
        all_data[ch_name] = []
        for m in msgs:
            all_data[ch_name].append({
                "id":        m.get("id"),
                "author":    m.get("author", {}),
                "content":   m.get("content", ""),
                "timestamp": m.get("timestamp", ""),
                "attachments": [a.get("url","") for a in m.get("attachments", [])],
                "embeds":    len(m.get("embeds", [])),
                "mentions":  [u.get("username","") for u in m.get("mentions", [])]
            })

        # Copy Mode: ส่งข้อความ
        if copy_mode and ch_id in ch_map:
            target_ch_id = ch_map[ch_id]
            sent = 0
            skipped = 0
            for m in msgs:
                content = m.get("content", "").strip()
                if not content:
                    skipped += 1
                    continue
                author = m.get("author", {}).get("username", "?")
                formatted = f"**[{author}]** {content}"
                ok = send_message(token, target_ch_id, formatted)
                if ok:
                    sent += 1
                    print(f"\r    {C}ส่งแล้ว {sent}/{len(msgs)}{RESET}  ", end="", flush=True)
                time.sleep(send_delay)
            print()
            log(f"ส่งสำเร็จ {sent} ข้อความ (ข้าม {skipped} embed/ว่าง)", "send")

    # ── สรุป ──
    header("สรุปผล")
    print(f"""
  {G}{BOLD}เสร็จสิ้น!{RESET}
  ├─ Channels สำเร็จ : {G}{len(all_data)}{RESET} / {len(text_channels)}
  ├─ ข้อความทั้งหมด  : {G}{BOLD}{total_msgs:,}{RESET}
  ├─ Errors          : {R if errors else G}{errors}{RESET}
  └─ Mode            : {"Copy → Target Server" if copy_mode else "Fetch Only"}
""")

    # ── บันทึกไฟล์ ──
    header("บันทึกไฟล์")
    folder, json_path, txt_path = save_results(all_data, guild_name)

    print(f"""
  {G}ไฟล์ถูกบันทึกที่:{RESET}
  📁 {W}{folder}/{RESET}
     ├─ all_messages.json  (ข้อมูลดิบ JSON)
     ├─ all_messages.txt   (อ่านง่าย แยก Channel)
     └─ summary.txt        (สรุปจำนวน)
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Y}  ยกเลิกโดยผู้ใช้{RESET}\n")
        sys.exit(0)
