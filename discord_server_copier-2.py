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
R    = "\033[91m"
G    = "\033[92m"
Y    = "\033[93m"
B    = "\033[94m"
M    = "\033[95m"
C    = "\033[96m"
W    = "\033[97m"
DIM  = "\033[2m"
RESET = "\033[0m"
BOLD  = "\033[1m"

BASE = "https://discord.com/api/v9"

# ───────────────────────────────────────────────────────────────

def banner():
    print(f"""
{M}{BOLD}╔══════════════════════════════════════════════════════════════╗
║       Discord Server Copier  v3.0  (Python Edition)         ║
╚══════════════════════════════════════════════════════════════╝{RESET}
{R}  ⚠️  WARNING: ใช้ User Token ผิด Discord TOS → อาจโดน ban     {RESET}
{DIM}  สำหรับทดลอง/ศึกษาเท่านั้น ใช้กับบัญชี dev ของตัวเองเท่านั้น{RESET}
""")

def log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {
        "info": f"{B}[*]{RESET}",
        "ok":   f"{G}[✓]{RESET}",
        "warn": f"{Y}[!]{RESET}",
        "err":  f"{R}[✗]{RESET}",
        "send": f"{C}[→]{RESET}",
        "dim":  f"{DIM}[-]{RESET}",
        "role": f"{M}[♦]{RESET}",
    }
    icon = icons.get(level, icons["info"])
    print(f"  {DIM}{ts}{RESET} {icon} {msg}")

def header(title):
    line = "─" * max(1, 52 - len(title))
    print(f"\n{M}{BOLD}  ── {title} {line}{RESET}")

def ask_yn(question, default="y"):
    hint = f"{G}Y{RESET}/{DIM}n{RESET}" if default == "y" else f"{DIM}y{RESET}/{G}N{RESET}"
    ans = input(f"  {W}{question}{RESET} [{hint}]: ").strip().lower()
    if not ans:
        return default == "y"
    return ans == "y"

# ─── Discord API ────────────────────────────────────────────────

def api_get(endpoint, token, params=None):
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
            return None
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

# ─── ดึงข้อความ ──────────────────────────────────────────────────

def fetch_all_messages(token, channel_id, channel_name="?"):
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
            log(f"ไม่มีสิทธิ์อ่าน #{channel_name} — ข้าม", "warn")
            break

        if not batch:
            break

        messages.extend(batch)
        before = batch[-1]["id"]
        print(f"\r    {DIM}หน้า {page} | {len(messages)} ข้อความ...{RESET}", end="", flush=True)

        if len(batch) < 100:
            break

        time.sleep(0.4)

    print()
    messages.reverse()
    return messages

# ─── ส่งข้อความ ──────────────────────────────────────────────────

def send_message(token, channel_id, content):
    result = api_post(f"/channels/{channel_id}/messages", token, {"content": content[:2000]})
    return result is not None

# ─── สร้าง Channel ───────────────────────────────────────────────

def create_channel(token, guild_id, name, ch_type=0, parent_id=None):
    payload = {"name": name, "type": ch_type}
    if parent_id:
        payload["parent_id"] = parent_id
    return api_post(f"/guilds/{guild_id}/channels", token, payload)

# ─── โหลดข้อมูล Server ───────────────────────────────────────────

def load_guild_info(token, guild_id):
    return api_get(f"/guilds/{guild_id}", token)

def load_channels(token, guild_id):
    return api_get(f"/guilds/{guild_id}/channels", token)

def load_roles(token, guild_id):
    return api_get(f"/guilds/{guild_id}/roles", token)

# ─── คัดลอก Roles ────────────────────────────────────────────────

def copy_roles(token, src_guild_id, dst_guild_id):
    """ดึง Roles จาก source แล้วสร้างใน target"""
    header("คัดลอก Roles")

    src_roles = load_roles(token, src_guild_id)
    if not src_roles:
        log("ไม่สามารถโหลด Roles ได้", "err")
        return {}

    # กรอง @everyone และเรียงตาม position
    src_roles = [r for r in src_roles if r["name"] != "@everyone"]
    src_roles.sort(key=lambda r: r.get("position", 0))

    log(f"พบ {len(src_roles)} roles ใน Source Server", "ok")
    print()
    for r in src_roles:
        color_hex = f"#{r['color']:06X}" if r["color"] else "no color"
        hoist_icon = "📌" if r.get("hoist") else "  "
        mention_icon = "🔔" if r.get("mentionable") else "  "
        print(f"    {M}♦{RESET} {W}{r['name']:<25}{RESET}  {DIM}{color_hex}  {hoist_icon}{mention_icon}{RESET}")
    print()

    role_map = {}  # source role name → new role id

    for i, role in enumerate(src_roles, 1):
        print(f"\r  {DIM}สร้าง role {i}/{len(src_roles)}: {role['name']}{RESET}  ", end="", flush=True)

        payload = {
            "name":        role["name"],
            "permissions": role.get("permissions", "0"),
            "color":       role.get("color", 0),
            "hoist":       role.get("hoist", False),
            "mentionable": role.get("mentionable", False),
        }

        new_role = api_post(f"/guilds/{dst_guild_id}/roles", token, payload)
        if new_role:
            role_map[role["name"]] = new_role["id"]
        else:
            log(f"สร้าง role '{role['name']}' ไม่สำเร็จ", "warn")

        time.sleep(0.6)

    print()
    log(f"สร้าง Roles สำเร็จ {len(role_map)}/{len(src_roles)}", "ok")
    return role_map

# ─── บันทึกไฟล์ ──────────────────────────────────────────────────

def save_results(all_data, roles_data, guild_name, include_roles):
    safe_name = "".join(c for c in guild_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"discord_{safe_name}_{ts_str}"
    os.makedirs(folder, exist_ok=True)

    saved_files = []

    # messages.json
    if all_data:
        json_path = os.path.join(folder, "messages.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        log(f"บันทึก: {json_path}", "ok")
        saved_files.append("messages.json")

        # messages.txt
        txt_path = os.path.join(folder, "messages.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            for ch_name, msgs in all_data.items():
                f.write(f"\n{'='*60}\n# {ch_name}  ({len(msgs)} ข้อความ)\n{'='*60}\n")
                for m in msgs:
                    ts_m = m.get("timestamp", "")[:19].replace("T", " ")
                    author = m.get("author", {}).get("username", "?")
                    content = m.get("content") or "[embed/attachment]"
                    f.write(f"[{ts_m}] {author}: {content}\n")
        log(f"บันทึก: {txt_path}", "ok")
        saved_files.append("messages.txt")

    # roles.json
    if include_roles and roles_data:
        roles_path = os.path.join(folder, "roles.json")
        with open(roles_path, "w", encoding="utf-8") as f:
            json.dump(roles_data, f, ensure_ascii=False, indent=2)
        log(f"บันทึก: {roles_path}", "ok")
        saved_files.append("roles.json")

    # summary.txt
    summary_path = os.path.join(folder, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        total = sum(len(v) for v in all_data.values()) if all_data else 0
        f.write(f"Server  : {guild_name}\n")
        f.write(f"Export  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Channels: {len(all_data)}\n")
        f.write(f"Messages: {total}\n")
        f.write(f"Roles   : {len(roles_data)}\n\n")
        if all_data:
            f.write("─── Channels ───\n")
            for ch, msgs in all_data.items():
                f.write(f"  #{ch}: {len(msgs)} ข้อความ\n")
        if roles_data:
            f.write("\n─── Roles ───\n")
            for r in roles_data:
                f.write(f"  {r.get('name','?')}\n")
    log(f"บันทึก: {summary_path}", "ok")
    saved_files.append("summary.txt")

    return folder, saved_files

# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    banner()

    # ── รับ Input ──
    header("กรอกข้อมูล")
    print(f"  {DIM}Target Server ID: กด Enter เพื่อข้าม (Fetch Only mode){RESET}\n")

    token     = input(f"  {C}Token{RESET}           : ").strip()
    src_guild = input(f"  {C}Source Server ID{RESET} : ").strip()
    dst_guild = input(f"  {C}Target Server ID{RESET} : ").strip()

    if not token or not src_guild:
        print(f"\n{R}  ✗ กรุณากรอก Token และ Source Server ID{RESET}\n")
        sys.exit(1)

    copy_mode = bool(dst_guild)

    # ── ถามตัวเลือก ──
    header("เลือกสิ่งที่ต้องการคัดลอก")
    print()

    copy_messages   = ask_yn("📝 คัดลอกข้อความ  (Messages)?", default="y")
    copy_roles_flag = ask_yn("♦  คัดลอกบทบาท   (Roles)?",    default="y")

    if not copy_messages and not copy_roles_flag:
        print(f"\n{Y}  ไม่ได้เลือกอะไรเลย ยกเลิก{RESET}\n")
        sys.exit(0)

    send_delay = 1.5
    if copy_mode and copy_messages:
        delay_input = input(f"\n  {W}Delay ระหว่างส่งข้อความ (วินาที) [{send_delay}]{RESET}: ").strip()
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

    categories    = {c["id"]: c for c in channels_raw if c["type"] == 4}
    text_channels = sorted([c for c in channels_raw if c["type"] == 0],
                           key=lambda c: c.get("position", 0))

    log(f"พบ {len(categories)} categories, {len(text_channels)} text channels", "ok")

    # โหลด roles ถ้าต้องการ
    roles_raw = []
    if copy_roles_flag:
        roles_raw = load_roles(token, src_guild) or []
        roles_raw = [r for r in roles_raw if r["name"] != "@everyone"]
        log(f"พบ {len(roles_raw)} roles", "ok")

    # แสดงโครงสร้าง channels
    print()
    printed_cats = set()
    for ch in text_channels:
        pid = ch.get("parent_id")
        if pid and pid not in printed_cats:
            cat = categories.get(pid, {})
            print(f"  {M}▸ {cat.get('name','?').upper()}{RESET}")
            printed_cats.add(pid)
        elif not pid and None not in printed_cats:
            print(f"  {M}▸ (ไม่มี Category){RESET}")
            printed_cats.add(None)
        print(f"    {DIM}#{ch['name']}{RESET}")

    # แสดง roles
    if roles_raw:
        print(f"\n  {M}▸ ROLES{RESET}")
        for r in sorted(roles_raw, key=lambda x: x.get("position", 0)):
            color_hex = f"#{r['color']:06X}" if r["color"] else "no color"
            print(f"    {M}♦{RESET} {r['name']:<25}  {DIM}{color_hex}{RESET}")

    # สรุป
    print(f"\n  {Y}{'─'*40}{RESET}")
    print(f"  {'✓' if copy_messages   else '✗'} ข้อความ: {len(text_channels)} channels (ไม่จำกัดจำนวน)")
    print(f"  {'✓' if copy_roles_flag else '✗'} Roles  : {len(roles_raw)} roles")
    print(f"  Mode: {W}{'Copy → ' + dst_guild if copy_mode else 'Fetch Only (บันทึกไฟล์)'}{RESET}")
    print()

    confirm = input(f"  {W}ยืนยันเริ่มต้น? (y/n){RESET}: ").strip().lower()
    if confirm != "y":
        print(f"\n{Y}  ยกเลิก{RESET}\n")
        sys.exit(0)

    # ─────────────────────────────────────────────────────────────
    all_data   = {}
    roles_data = []
    total_msgs = 0
    errors     = 0
    cat_map    = {}
    ch_map     = {}

    # ── 1. คัดลอก Roles ──
    if copy_roles_flag:
        roles_data = roles_raw  # เก็บไว้บันทึกไฟล์เสมอ
        if copy_mode:
            copy_roles(token, src_guild, dst_guild)

    # ── 2. สร้าง Structure (copy mode) ──
    if copy_mode and copy_messages:
        header("สร้าง Channels ใน Target Server")
        for cat_id, cat in sorted(categories.items(), key=lambda x: x[1].get("position", 0)):
            used = any(c.get("parent_id") == cat_id for c in text_channels)
            if not used:
                continue
            log(f"สร้าง Category: {cat['name']}", "info")
            new_cat = create_channel(token, dst_guild, cat["name"], ch_type=4)
            if new_cat:
                cat_map[cat_id] = new_cat["id"]
                log(f"  → {new_cat['name']}", "ok")
            time.sleep(0.8)

        for ch in text_channels:
            parent_id = ch.get("parent_id")
            target_parent = cat_map.get(parent_id) if parent_id else None
            log(f"สร้าง Channel: #{ch['name']}", "info")
            new_ch = create_channel(token, dst_guild, ch["name"], ch_type=0, parent_id=target_parent)
            if new_ch:
                ch_map[ch["id"]] = new_ch["id"]
                log(f"  → #{new_ch['name']}", "ok")
            time.sleep(0.8)

    # ── 3. ดึง + ส่ง ข้อความ ──
    if copy_messages:
        header("ดึงข้อความ" + (" + ส่ง" if copy_mode else ""))

        for i, ch in enumerate(text_channels, 1):
            ch_name = ch["name"]
            ch_id   = ch["id"]
            pct = int((i / len(text_channels)) * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\n  {B}[{i}/{len(text_channels)}]{RESET} {W}#{ch_name}{RESET}  {DIM}[{bar}] {pct}%{RESET}")

            try:
                msgs = fetch_all_messages(token, ch_id, ch_name)
            except (PermissionError, ConnectionError) as e:
                log(str(e), "err")
                errors += 1
                continue

            log(f"ดึงได้ {G}{len(msgs)}{RESET} ข้อความ", "ok")
            total_msgs += len(msgs)

            all_data[ch_name] = []
            for m in msgs:
                all_data[ch_name].append({
                    "id":          m.get("id"),
                    "author":      m.get("author", {}),
                    "content":     m.get("content", ""),
                    "timestamp":   m.get("timestamp", ""),
                    "attachments": [a.get("url", "") for a in m.get("attachments", [])],
                    "embeds":      len(m.get("embeds", [])),
                    "mentions":    [u.get("username", "") for u in m.get("mentions", [])],
                })

            # ส่งข้อความ (copy mode)
            if copy_mode and ch_id in ch_map:
                target_ch_id = ch_map[ch_id]
                sent = 0
                skipped = 0
                for m in msgs:
                    content = (m.get("content") or "").strip()
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

    # ── สรุปผล ──
    header("สรุปผล")
    print(f"""
  {G}{BOLD}เสร็จสิ้น!{RESET}
  ├─ Channels   : {G}{len(all_data)}{RESET} / {len(text_channels)}
  ├─ ข้อความ    : {G}{BOLD}{total_msgs:,}{RESET}
  ├─ Roles      : {G}{len(roles_data)}{RESET}
  ├─ Errors     : {R if errors else G}{errors}{RESET}
  └─ Mode       : {"Copy → Target Server" if copy_mode else "Fetch Only"}
""")

    # ── บันทึกไฟล์ ──
    header("บันทึกไฟล์")
    folder, saved_files = save_results(all_data, roles_data, guild_name, copy_roles_flag)

    file_list = "\n".join(f"     ├─ {f}" for f in saved_files)
    print(f"""
  {G}ไฟล์ถูกบันทึกที่:{RESET}
  📁 {W}{folder}/{RESET}
{file_list}
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Y}  ยกเลิกโดยผู้ใช้{RESET}\n")
        sys.exit(0)
