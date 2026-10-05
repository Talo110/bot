#!/usr/bin/env python3
import fs_guard as _vx_fs_guard
_vx_fs_guard.install()
del _vx_fs_guard
try:
    import vx_extras as _vx_extras
    _vx_extras.install()
except Exception:
    pass  # optional feature — never block the bot from starting over this
import fs_guard as _vx_fs_guard
_vx_fs_guard.install()
del _vx_fs_guard
# -*- coding: utf-8 -*-

import io
import zipfile
import telebot
from telebot import types
import requests
import json
import base64
import hashlib
import os
import time
import random
import re
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import gzip
import warnings
import sys
import tempfile

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ==========================================
# BOT SETTINGS
# ==========================================
BOT_TOKEN = ""
bot = telebot.(BOT_TOKEN)
ADMIN_ID = 8254935096
ADMIN_USERNAME = "@GLITCHYN"
GROUP_LINK = "https://t.me/glitchyncpmgiveaway"

# ==========================================
# GLOBAL VARIABLES
# ==========================================
user_data = {}

# ==========================================
# JSON FILES & UTILS
# ==========================================
USER_FILE = "users.json"
SUBSCRIPTION_FILE = "subscriptions.json"   # NEW: stores days remaining per user
ANNOUNCEMENT_FILE = "announcements.json"

def load_json(file_path, default_type=dict):
    """
    Load JSON data safely. If the file is missing or corrupted, it resets to default.
    """
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default_type(), f)
        return default_type()

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            if isinstance(data, default_type):
                return data
            else:
                # File exists but wrong type → reset
                with open(file_path, "w") as f:
                    json.dump(default_type(), f)
                return default_type()
    except json.JSONDecodeError:
        # Corrupted file → back up and reset
        backup_path = file_path + ".bak"
        try:
            os.replace(file_path, backup_path)   # Keep old file as backup
        except Exception:
            pass
        with open(file_path, "w") as f:
            json.dump(default_type(), f)
        print(f"⚠️ {file_path} was corrupted and has been reset. Backup: {backup_path}")
        return default_type()
    except Exception as e:
        # Any other error → reset
        print(f"⚠️ Unexpected error loading {file_path}: {e}")
        with open(file_path, "w") as f:
            json.dump(default_type(), f)
        return default_type()

def save_json(file_path, data):
    """
    Save JSON atomically to avoid corruption.
    """
    if os.path.dirname(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(file_path) or ".")
    with os.fdopen(tmp_fd, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp_path, file_path)

# ==========================================
# DAY SUBSCRIPTION SYSTEM (replaces points)
# ==========================================
def get_days_remaining(user_id):
    subs = load_json(SUBSCRIPTION_FILE, dict)
    return subs.get(str(user_id), 0)

def set_days_remaining(user_id, days):
    subs = load_json(SUBSCRIPTION_FILE, dict)
    subs[str(user_id)] = days
    save_json(SUBSCRIPTION_FILE, subs)

def add_days(user_id, days):
    current = get_days_remaining(user_id)
    set_days_remaining(user_id, current + days)
    return current + days

def has_active_subscription(user_id):
    return get_days_remaining(user_id) > 0

# ==========================================
# ES3 ENCRYPTION
# ==========================================
def es3_decrypt(file_data, key_str):
    salt = file_data[:16]
    encrypted = file_data[16:]
    key = PBKDF2(key_str.encode(), salt, 16, count=100, hmac_hash_module=SHA1)
    cipher = AES.new(key, AES.MODE_CBC, salt)
    decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
    if len(decrypted) > 2 and decrypted[0] == 0x1f and decrypted[1] == 0x8b:
        decrypted = gzip.decompress(decrypted)
    return decrypted

def es3_encrypt(plain_data, key_str):
    salt = get_random_bytes(16)
    key = PBKDF2(key_str.encode(), salt, 16, count=100, hmac_hash_module=SHA1)
    cipher = AES.new(key, AES.MODE_CBC, salt)
    encrypted = cipher.encrypt(pad(plain_data, AES.block_size))
    return salt + encrypted

# ==========================================
# FIREBASE LOGIN (ES3)
# ==========================================
def login(email, password, api_key):
    url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={api_key}"
    r = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=15)
    data = r.json()
    if "idToken" in data:
        return data["idToken"], data["localId"]
    return None, None

def decode_es3_filename(name):
    try:
        padding = len(name) % 4
        if padding != 0:
            name += "=" * (4 - padding)
        return base64.b64decode(name).decode("utf-8")
    except:
        return name

def es3_key_uret(dosya_adi, local_id):
    gercek_dosya_adi = decode_es3_filename(dosya_adi)
    es3_first3 = gercek_dosya_adi[:3]
    return es3_first3 + local_id[:3]

# ==========================================
# MENUS & KEYBOARDS
# ==========================================
def back_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main"))
    return markup

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 CPM1 → CPM2 Transfer", callback_data="transfer"),
        types.InlineKeyboardButton("🔑 Gen CPM1 ES3 Key", callback_data="cpm1_key")
    )
    markup.add(
        types.InlineKeyboardButton("🔑 Gen CPM2 ES3 Key", callback_data="cpm2_key"),
        types.InlineKeyboardButton("📢 Announcements", callback_data="announcements")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 Giveaway", callback_data="giveaway"),
        types.InlineKeyboardButton("ℹ️ About Us", callback_data="about")
    )
    markup.add(
        types.InlineKeyboardButton("📖 User Guide", callback_data="guide"),
        types.InlineKeyboardButton("🛞 Mileage Reset", callback_data="km_reset")
    )
    markup.add(
        types.InlineKeyboardButton("🔧 Remove Bumper", callback_data="bumper_menu"),
        types.InlineKeyboardButton("🔓 Unlock Menu", callback_data="unlock_menu")
    )
    return markup

def bumper_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔧 Remove Front Bumper", callback_data="front_bumper"),
        types.InlineKeyboardButton("🔧 Remove Rear Bumper", callback_data="rear_bumper")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
    return markup

def unlock_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🪁 Air Suspension", callback_data="unlock_air"),
        types.InlineKeyboardButton("🚨 Police", callback_data="unlock_police")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Days", callback_data="admin_add_days"),
        types.InlineKeyboardButton("📢 Make Announcement", callback_data="admin_announcement")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 Start Giveaway", callback_data="admin_giveaway"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")
    )
    return markup

# ==========================================
# BOT COMMANDS
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    
    # Initialize user in JSON if not exists
    days = get_days_remaining(user_id)
    set_days_remaining(user_id, days)   # ensures the user is present in subscriptions.json

    if user_id not in user_data:
        user_data[user_id] = {"step": "menu"}
    
    bot.send_message(
        message.chat.id,
        "👑 **GLITCHYN OFFICIAL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: {first_name}\n"
        f"📅 Days Remaining: {days}\n\n"
        "👇 **Select an option from the menu:**",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is only for admins!")
        return
    bot.send_message(
        message.chat.id,
        "⚙️ **ADMIN PANEL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nAdmin access only!",
        parse_mode="Markdown",
        reply_markup=admin_panel()
    )

# ==========================================
# CALLBACK HANDLER
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global user_data
    user_id = call.from_user.id
    msg = call.message
    
    if user_id not in user_data:
        user_data[user_id] = {"step": "menu"}

    # ---------------- ADMIN COMMANDS ----------------
    if call.data == "admin_add_days":
        if user_id != ADMIN_ID: return
        bot.edit_message_text("➕ **Add Days**\n\nEnter the Target User ID:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "admin_add_days_id"}

    elif call.data == "admin_announcement":
        if user_id != ADMIN_ID: return
        bot.edit_message_text("📢 **Make Announcement**\n\nSend the text for the global announcement:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "admin_ann_text"}

    elif call.data == "admin_stats":
        if user_id != ADMIN_ID: return
        subs_db = load_json(SUBSCRIPTION_FILE, dict)
        total_users = len(subs_db)
        total_days = sum(subs_db.values())
        bot.edit_message_text(f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n📅 Total Days Granted: {total_days}", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())

    elif call.data == "admin_giveaway":
        if user_id != ADMIN_ID: return
        bot.answer_callback_query(call.id, "Coming soon in next update!", show_alert=True)

    # ---------------- USER COMMANDS ----------------
    elif call.data == "back_main":
        user_data[user_id] = {"step": "menu"}
        days = get_days_remaining(user_id)
        bot.edit_message_text(
            f"👑 **GLITCHYN OFFICIAL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Days Remaining: {days}\n\n"
            "👇 **Select an option from the menu:**",
            chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=main_menu()
        )

    elif call.data == "transfer":
        bot.edit_message_text(
            "🔄 **CPM1 → CPM2 Transfer**\n\n📁 Send your CPM1 ES3 file:",
            chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup()
        )
        user_data[user_id] = {"step": "cpm1_file"}

    elif call.data == "cpm1_key":
        bot.edit_message_text(
            "🔑 **Generate CPM1 ES3 Key**\n\n📁 Send your CPM1 ES3 file:",
            chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup()
        )
        user_data[user_id] = {"step": "cpm1_key_file"}

    elif call.data == "cpm2_key":
        bot.edit_message_text(
            "🔑 **Generate CPM2 ES3 Key**\n\n📁 Send your CPM2 ES3 file:",
            chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup()
        )
        user_data[user_id] = {"step": "cpm2_key_file"}

    elif call.data == "km_reset":
        bot.edit_message_text("🛞 **Mileage Reset**\n\n📁 Send your ES3 file:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "km_file", "operation": "km_reset"}

    elif call.data == "bumper_menu":
        bot.edit_message_text("🔧 **Bumper Removal Menu**\n\nWhich bumper do you want to remove?", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=bumper_menu())

    elif call.data == "unlock_menu":
        bot.edit_message_text("🔓 **Unlock Menu**\n\nWhat do you want to unlock?", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=unlock_menu())

    elif call.data == "front_bumper":
        bot.edit_message_text("🔧 **Front Bumper Removal**\n\n📁 Send your ES3 file:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "km_file", "operation": "front_bumper"}

    elif call.data == "rear_bumper":
        bot.edit_message_text("🔧 **Rear Bumper Removal**\n\n📁 Send your ES3 file:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "km_file", "operation": "rear_bumper"}

    elif call.data == "unlock_air":
        bot.edit_message_text("🪁 **Unlock Air Suspension**\n\n📁 Send your ES3 file:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "km_file", "operation": "unlock_air"}

    elif call.data == "unlock_police":
        bot.edit_message_text("🚨 **Unlock Police**\n\n📁 Send your ES3 file:", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id] = {"step": "km_file", "operation": "unlock_police"}

    elif call.data == "guide":
        bot.edit_message_text(
            "📖 **User Guide**\n\n"
            "1️⃣ CPM1 → CPM2 Transfer\n"
            "2️⃣ Generate ES3 Key\n"
            "3️⃣ Subscription System – get days from admin or giveaways",
            chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup()
        )

    elif call.data == "announcements":
        announcements = load_json(ANNOUNCEMENT_FILE, list)
        if not announcements:
            bot.edit_message_text("📢 **Announcements**\n\nNo announcements yet!", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())
        else:
            bot.edit_message_text(f"📢 **LATEST ANNOUNCEMENT**\n\n{announcements[-1]}", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())

    elif call.data == "giveaway":
        bot.edit_message_text("🎁 **Giveaway**\n\nNew giveaways starting soon!", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())

    elif call.data == "about":
        bot.edit_message_text(f"ℹ️ **About Us**\n\n👨‍💻 Admin: {ADMIN_USERNAME}\n📢 Group: {GROUP_LINK}", chat_id=msg.chat.id, message_id=msg.message_id, parse_mode="Markdown", reply_markup=back_markup())

# ==========================================
# TEXT HANDLER
# ==========================================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    global user_data
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {"step": "menu"}
    
    step = user_data[user_id].get("step", "menu")

    # ---------------- ADMIN TEXT HANDLING ----------------
    if step == "admin_add_days_id":
        if user_id != ADMIN_ID: return
        user_data[user_id]["target_id"] = message.text.strip()
        bot.send_message(message.chat.id, "➕ **How many days to add?**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "admin_add_days_amount"

    elif step == "admin_add_days_amount":
        if user_id != ADMIN_ID: return
        try:
            days = int(message.text.strip())
            target_id = user_data[user_id]["target_id"]
            add_days(target_id, days)
            bot.send_message(message.chat.id, f"✅ Successfully added {days} day(s) to User ID `{target_id}`.", parse_mode="Markdown", reply_markup=back_markup())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Error: Please enter a valid number.", reply_markup=back_markup())
        user_data[user_id] = {"step": "menu"}

    elif step == "admin_ann_text":
        if user_id != ADMIN_ID: return
        ann_text = message.text.strip()
        announcements = load_json(ANNOUNCEMENT_FILE, list)
        announcements.append(ann_text)
        save_json(ANNOUNCEMENT_FILE, announcements)
        bot.send_message(message.chat.id, "✅ Announcement successfully published!", reply_markup=back_markup())
        user_data[user_id] = {"step": "menu"}

    # ---------------- ES3 OPERATIONS ----------------
    elif step == "cpm1_email":
        user_data[user_id]["cpm1_email"] = message.text.strip()
        bot.send_message(message.chat.id, "🔐 **Enter your CPM1 Password:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm1_password"

    elif step == "cpm1_password":
        user_data[user_id]["cpm1_password"] = message.text.strip()
        bot.send_message(message.chat.id, "📁 **Send an empty CPM2 ES3 file:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm2_file"

    elif step == "cpm2_email":
        user_data[user_id]["cpm2_email"] = message.text.strip()
        bot.send_message(message.chat.id, "🔐 **Enter your CPM2 Password:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm2_password"

    elif step == "cpm2_password":
        user_data[user_id]["cpm2_password"] = message.text.strip()
        bot.send_message(message.chat.id, "⏳ **Processing...**", parse_mode="Markdown")
        islem_yap(user_id)

    elif step == "km_key":
        es3_key = message.text.strip()
        user_data[user_id]["es3_key"] = es3_key
        bot.send_message(message.chat.id, "⏳ **Processing...**", parse_mode="Markdown")
        es3_islem(message.chat.id, user_id)

    elif step == "cpm1_key_email":
        user_data[user_id]["cpm1_key_email"] = message.text.strip()
        bot.send_message(message.chat.id, "🔐 **Enter your CPM1 Password:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm1_key_password"

    elif step == "cpm1_key_password":
        user_data[user_id]["cpm1_key_password"] = message.text.strip()
        islem_key_cpm1(user_id)

    elif step == "cpm2_key_email":
        user_data[user_id]["cpm2_key_email"] = message.text.strip()
        bot.send_message(message.chat.id, "🔐 **Enter your CPM2 Password:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm2_key_password"

    elif step == "cpm2_key_password":
        user_data[user_id]["cpm2_key_password"] = message.text.strip()
        islem_key_cpm2(user_id)

# ==========================================
# FILE HANDLER
# ==========================================
@bot.message_handler(content_types=['document'])
def handle_document(message):
    global user_data
    user_id = message.from_user.id
    step = user_data.get(user_id, {}).get("step")

    if step == "cpm1_file":
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        user_data[user_id]["cpm1_file"] = downloaded
        user_data[user_id]["cpm1_filename"] = message.document.file_name
        bot.send_message(message.chat.id, "📧 **Enter CPM1 Email:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm1_email"

    elif step == "cpm2_file":
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        user_data[user_id]["cpm2_file"] = downloaded
        user_data[user_id]["cpm2_filename"] = message.document.file_name
        bot.send_message(message.chat.id, "📧 **Enter CPM2 Email:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "cpm2_email"

    elif step == "km_file":
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        user_data[user_id]["es3_file"] = downloaded
        user_data[user_id]["es3_filename"] = message.document.file_name
        bot.send_message(message.chat.id, "🔑 **Enter ES3 Key:**", parse_mode="Markdown", reply_markup=back_markup())
        user_data[user_id]["step"] = "km_key"

# ==========================================
# OPERATIONS (now require active subscription, no cost)
# ==========================================
def islem_yap(user_id):
    data = user_data[user_id]
    
    # Check subscription
    if not has_active_subscription(user_id):
        bot.send_message(user_id, "❌ **You need an active subscription!**\nContact admin to get days.", reply_markup=back_markup())
        return
        
    cpm1_token, cpm1_local_id = login(data["cpm1_email"], data["cpm1_password"], "AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM")
    if not cpm1_token:
        bot.send_message(user_id, "❌ CPM1 login failed!", reply_markup=back_markup())
        return
        
    cpm1_key = es3_key_uret(data["cpm1_filename"], cpm1_local_id)
    cpm2_token, cpm2_local_id = login(data["cpm2_email"], data["cpm2_password"], "AIzaSyCQDz9rgjgmvmFkvVfmvr2-7fT4tfrzRRQ")
    
    if not cpm2_token:
        bot.send_message(user_id, "❌ CPM2 login failed!", reply_markup=back_markup())
        return
        
    cpm2_key = es3_key_uret(data["cpm2_filename"], cpm2_local_id)
    decrypted_cpm1 = es3_decrypt(data["cpm1_file"], cpm1_key)
    cpm1_data = json.loads(decrypted_cpm1.decode('utf-8'))
    encrypted = es3_encrypt(json.dumps(cpm1_data).encode('utf-8'), cpm2_key)
    
    bot.send_document(user_id, encrypted, visible_file_name=data["cpm2_filename"], caption="✅ **Transfer completed!**", reply_markup=back_markup())
    user_data[user_id] = {"step": "menu"}

def islem_key_cpm1(user_id):
    data = user_data[user_id]
    
    if not has_active_subscription(user_id):
        bot.send_message(user_id, "❌ **You need an active subscription!**", reply_markup=back_markup())
        return
        
    cpm1_token, cpm1_local_id = login(data["cpm1_key_email"], data["cpm1_key_password"], "AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM")
    if not cpm1_token:
        bot.send_message(user_id, "❌ CPM1 login failed!", reply_markup=back_markup())
        return
        
    cpm1_key = es3_key_uret(data["cpm1_key_filename"], cpm1_local_id)
    bot.send_message(user_id, f"✅ **CPM1 Key:** `{cpm1_key}`", parse_mode="Markdown", reply_markup=back_markup())
    user_data[user_id] = {"step": "menu"}

def islem_key_cpm2(user_id):
    data = user_data[user_id]
    
    if not has_active_subscription(user_id):
        bot.send_message(user_id, "❌ **You need an active subscription!**", reply_markup=back_markup())
        return
        
    cpm2_token, cpm2_local_id = login(data["cpm2_key_email"], data["cpm2_key_password"], "AIzaSyCQDz9rgjgmvmFkvVfmvr2-7fT4tfrzRRQ")
    if not cpm2_token:
        bot.send_message(user_id, "❌ CPM2 login failed!", reply_markup=back_markup())
        return
        
    cpm2_key = es3_key_uret(data["cpm2_key_filename"], cpm2_local_id)
    bot.send_message(user_id, f"✅ **CPM2 Key:** `{cpm2_key}`", parse_mode="Markdown", reply_markup=back_markup())
    user_data[user_id] = {"step": "menu"}

def es3_islem(chat_id, user_id):
    data = user_data[user_id]
    operation = data.get("operation", "")
    
    # No cost, just require active subscription
    if not has_active_subscription(user_id):
        bot.send_message(chat_id, "❌ **You need an active subscription!**", reply_markup=back_markup())
        return
        
    es3_key = data.get("es3_key", "")
    decrypted = es3_decrypt(data["es3_file"], es3_key)
    text = decrypted.decode('utf-8', errors='ignore')
    
    if operation == "km_reset":
        text = re.sub(r'(?i)("mileage"\s*:\s*)[\d.]+', r'\g<1>0', text)
        islem_adi = "🛞 Mileage Reset Completed"
    elif operation == "front_bumper":
        text = re.sub(r'"FrontBumperId"\s*:\s*[^,}]+?', '"FrontBumperId" : -1', text)
        islem_adi = "🔧 Front Bumper Removed"
    elif operation == "rear_bumper":
        text = re.sub(r'"RearBumperId"\s*:\s*[^,}]+?', '"RearBumperId" : -1', text)
        islem_adi = "🔧 Rear Bumper Removed"
    elif operation == "unlock_air":
        text = re.sub(r'"AirSuspension"\s*:\s*\{[^}]*"Bought"\s*:\s*false[^}]*"Installed"\s*:\s*false[^}]*\}', '"AirSuspension" : {"Bought" : true, "Installed" : true}', text)
        islem_adi = "🪁 Air Suspension Unlocked"
    elif operation == "unlock_police":
        text = re.sub(r'"IsPolice"\s*:\s*false', '"IsPolice" : true', text)
        islem_adi = "🚨 Police Unlocked"
    else:
        return
    
    encrypted = es3_encrypt(text.encode('utf-8'), es3_key)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(data["es3_filename"], encrypted)
    zip_buffer.seek(0)
    
    bot.send_document(chat_id, zip_buffer, visible_file_name="edited_es3.zip", caption=f"✅ **{islem_adi}!**", reply_markup=back_markup())
    user_data[user_id] = {"step": "menu"}

# ==========================================
# START UP
# ==========================================
bot.set_my_commands([
    telebot.types.BotCommand("/start", "Start Bot & Open Menu"),
    telebot.types.BotCommand("/admin", "Open Admin Panel")
])

print("🤖 GLITCHYN OFFICIAL Bot is running... (Day Subscription System)")
bot.polling(non_stop=True)