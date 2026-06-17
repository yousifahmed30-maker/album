import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import json
import os

# ================= الإعدادات الأساسية =================
TOKEN = '8779220241:AAF9vLopP7CudzGny4CWAeJNWQHdJxIw8Ic'
ADMIN_ID = 6288025184  # ضع أيدي حسابك هنا لتكون المشرف على البوت

bot = telebot.TeleBot(TOKEN)

# قائمة المنتخبات المطلوبة
COUNTRIES = ['مصر', 'السودان', 'الجزائر', 'المغرب', 'موريتانيا', 'ليبيا', 
             'السعودية', 'اليمن', 'عمان', 'العراق', 'سوريا', 'فلسطين']

# أعلام الدول
FLAGS = {
    'مصر': '🇪🇬', 'السودان': '🇸🇩', 'الجزائر': '🇩🇿', 'المغرب': '🇲🇦',
    'موريتانيا': '🇲🇷', 'ليبيا': '🇱🇾', 'السعودية': '🇸🇦', 'اليمن': '🇾🇪',
    'عمان': '🇴🇲', 'العراق': '🇮🇶', 'سوريا': '🇸🇾', 'فلسطين': '🇵🇸'
}

# ================= قاعدة البيانات (محفوظة على الديسك) =================
DATA_FILE = "gamedata.json"

db_users = {}
db_inventory = {}
db_settings = {}
db_msg_owner = {}       # message_id -> user_id (مؤقت)
db_admin_card = {}      # admin_id -> target_user_id (مؤقت)
db_admin_national = {}  # admin_id -> target_user_id (مؤقت)

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "users":     {str(k): v for k, v in db_users.items()},
                "inventory": {str(k): v for k, v in db_inventory.items()},
                "settings":  db_settings
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_data error] {e}")

def load_data():
    global db_users, db_inventory, db_settings
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        db_users     = {int(k): v for k, v in data.get("users", {}).items()}
        db_inventory = {int(k): v for k, v in data.get("inventory", {}).items()}
        db_settings  = data.get("settings", {})
        print(f"[load_data] تم تحميل بيانات {len(db_users)} لاعب.")
    except Exception as e:
        print(f"[load_data error] {e}")

load_data()

def set_msg_owner(message_id, user_id):
    db_msg_owner[message_id] = user_id

def check_owner(call):
    owner = db_msg_owner.get(call.message.message_id)
    if owner is not None and owner != call.from_user.id:
        bot.answer_callback_query(call.id, "🚫 هذه الرسالة ليست لك!", show_alert=True)
        return False
    return True

# ================= دوال مساعدة =================
def _init_user(user_id):
    if user_id not in db_users:
        db_users[user_id] = {"keys": 0, "name": "", "album_completed": False, "national_team": "", "national_gift_claimed": False, "free_keys_claimed": False}
    else:
        if "national_team" not in db_users[user_id]:
            db_users[user_id]["national_team"] = ""
        if "national_gift_claimed" not in db_users[user_id]:
            db_users[user_id]["national_gift_claimed"] = False
        if "free_keys_claimed" not in db_users[user_id]:
            db_users[user_id]["free_keys_claimed"] = False

def get_user_keys(user_id):
    _init_user(user_id)
    return db_users[user_id]["keys"]

def save_user_name(user):
    _init_user(user.id)
    name = (user.first_name or "")
    if user.last_name:
        name += " " + user.last_name
    db_users[user.id]["name"] = name.strip() or f"مستخدم {user.id}"
    save_data()

def add_keys(user_id, amount):
    _init_user(user_id)
    db_users[user_id]["keys"] += amount
    save_data()

def get_inventory(user_id):
    return {c: n for c, n in db_inventory.get(user_id, {}).items() if n > 0}

def add_card(user_id, country, amount=1):
    if user_id not in db_inventory:
        db_inventory[user_id] = {}
    db_inventory[user_id][country] = db_inventory[user_id].get(country, 0) + amount
    save_data()

def get_setting(key):
    return db_settings.get(key)

def set_setting(key, value):
    db_settings[key] = str(value)
    save_data()

def check_and_congratulate(user_id, chat_id, user_name=""):
    _init_user(user_id)
    if db_users[user_id]["album_completed"]:
        return
    inventory = get_inventory(user_id)
    if all(inventory.get(c, 0) > 0 for c in COUNTRIES):
        db_users[user_id]["album_completed"] = True
        save_data()
        name_str = f"**{user_name}**" if user_name else "اللاعب"
        text = (
            "🎊🏆 **تهانينا! اكتمل الألبوم!** 🏆🎊\n\n"
            f"🎩 {name_str} جمع جميع المنتخبات الـ 12 في كأس العرب 2026!\n\n"
            "🇪🇬 🇸🇩 🇩🇿 🇲🇦 🇲🇷 🇱🇾\n"
            "🇸🇦 🇾🇪 🇴🇲 🇮🇶 🇸🇾 🇵🇸\n\n"
            "👑 أنت بطل الألبوم! مبروك عليك هذا الإنجاز!"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")

# ================= أوامر الأدمن =================
@bot.message_handler(commands=['setarabalbum'])
def admin_settings(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط.")
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    btn_group = InlineKeyboardButton("⚙️ تحديد المجموعة", callback_data="admin_set_group")
    btn_countries = InlineKeyboardButton("📸 إضافة صور المنتخبات", callback_data="admin_set_countries")
    btn_pack = InlineKeyboardButton("📦 إضافة صورة البكجات (المتجر)", callback_data="admin_set_pack")
    btn_keys = InlineKeyboardButton("🔑 إضافة مفاتيح للاعب", callback_data="admin_add_keys")
    btn_card = InlineKeyboardButton("🃏 إضافة بطاقة محددة للاعب", callback_data="admin_add_card")
    btn_national = InlineKeyboardButton("🌍 تحديد/إلغاء دولة الدعم للاعب", callback_data="admin_set_national")
    btn_collections = InlineKeyboardButton("📊 معرفة تجميعات اللاعبين", callback_data="admin_view_collections")
    btn_allkeys = InlineKeyboardButton("🔑 معرفة مفاتيح اللاعبين", callback_data="admin_view_keys")
    markup.add(btn_group, btn_countries, btn_pack, btn_keys, btn_card, btn_national, btn_collections, btn_allkeys)

    bot.reply_to(message, "🛠 **لوحة تحكم كأس العرب 2026**\nاختر من الإعدادات التالية:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return

    if call.data == "admin_set_group":
        msg = bot.send_message(call.message.chat.id, "ارسل الآن آيدي (ID) المجموعة المسموح بها:")
        bot.register_next_step_handler(msg, save_group_id)

    elif call.data == "admin_set_pack":
        msg = bot.send_message(call.message.chat.id, "ارسل رابط أو صورة البكج (المتجر):")
        bot.register_next_step_handler(msg, save_pack_image)

    elif call.data == "admin_set_countries":
        markup = InlineKeyboardMarkup(row_width=2)
        buttons = [InlineKeyboardButton(c, callback_data=f"setpic_{c}") for c in COUNTRIES]
        markup.add(*buttons)
        bot.send_message(call.message.chat.id, "اختر المنتخب الذي تريد إضافة صورته:", reply_markup=markup)

    elif call.data == "admin_add_keys":
        msg = bot.send_message(call.message.chat.id, "أرسل الآيدي الخاص باللاعب (User ID):")
        bot.register_next_step_handler(msg, admin_ask_keys_amount)

    elif call.data == "admin_add_card":
        msg = bot.send_message(call.message.chat.id, "🃏 أرسل الآيدي الخاص باللاعب (User ID):")
        bot.register_next_step_handler(msg, admin_ask_card_uid)

    elif call.data == "admin_set_national":
        msg = bot.send_message(call.message.chat.id, "🌍 أرسل الآيدي الخاص باللاعب (User ID):")
        bot.register_next_step_handler(msg, admin_ask_national_uid)

    elif call.data == "admin_view_collections":
        admin_show_collections(call.message.chat.id)

    elif call.data == "admin_view_keys":
        admin_show_keys(call.message.chat.id)

def _send_long_message(chat_id, text):
    """إرسال رسالة طويلة مقسّمة إذا تجاوزت حد تيليجرام."""
    limit = 4000
    if len(text) <= limit:
        bot.send_message(chat_id, text, parse_mode="Markdown")
        return
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > limit:
            bot.send_message(chat_id, chunk, parse_mode="Markdown")
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk.strip():
        bot.send_message(chat_id, chunk, parse_mode="Markdown")

def admin_show_collections(chat_id):
    players = []
    for uid, inv in db_inventory.items():
        collected = [c for c, n in inv.items() if n > 0]
        if not collected:
            continue
        name = db_users.get(uid, {}).get("name") or f"لاعب {uid}"
        players.append((name, collected))
    players.sort(key=lambda x: len(x[1]), reverse=True)
    if not players:
        bot.send_message(chat_id, "📭 لا يوجد لاعبون لديهم بطاقات بعد.")
        return
    text = f"📊 **تجميعات اللاعبين** \\- {len(players)} لاعب\n\n"
    for name, collected in players:
        flags_str = " ".join(FLAGS.get(c, c) for c in collected)
        text += f"👤 **{name}** `{len(collected)}/12`\n{flags_str}\n\n"
    _send_long_message(chat_id, text)

def admin_show_keys(chat_id):
    players = []
    for uid, data in db_users.items():
        keys = data.get("keys", 0)
        if keys <= 0:
            continue
        name = data.get("name") or f"لاعب {uid}"
        players.append((name, keys))
    players.sort(key=lambda x: x[1], reverse=True)
    if not players:
        bot.send_message(chat_id, "📭 لا يوجد لاعبون لديهم مفاتيح بعد.")
        return
    text = f"🔑 **أرصدة المفاتيح** \\- {len(players)} لاعب\n\n"
    for name, keys in players:
        text += f"👤 **{name}**: `{keys}` مفتاح\n"
    _send_long_message(chat_id, text)

def save_group_id(message):
    set_setting("allowed_group", message.text.strip())
    bot.reply_to(message, "✅ تم حفظ آيدي المجموعة بنجاح.")

def save_pack_image(message):
    if message.photo:
        set_setting("pack_image", message.photo[-1].file_id)
    else:
        set_setting("pack_image", message.text)
    bot.reply_to(message, "✅ تم حفظ صورة المتجر بنجاح.")

def admin_ask_keys_amount(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.strip() if message.text else ""
    try:
        target_id = int(text)
    except ValueError:
        bot.reply_to(message, "❌ الآيدي غير صحيح، أرسل رقماً صحيحاً.")
        return
    msg = bot.reply_to(message, f"✅ آيدي اللاعب: `{target_id}`\nالآن أرسل عدد المفاتيح التي تريد إضافتها:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_save_keys, target_id)

def admin_save_keys(message, target_id):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.strip() if message.text else ""
    try:
        amount = int(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❌ أدخل عدداً صحيحاً أكبر من صفر.")
        return
    add_keys(target_id, amount)
    new_total = get_user_keys(target_id)
    bot.reply_to(message, f"✅ تم إضافة `{amount}` مفتاح للاعب `{target_id}`\n🔑 رصيده الآن: `{new_total}` مفتاح.", parse_mode="Markdown")

# --- إضافة بطاقة محددة للاعب ---
def admin_ask_card_uid(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.strip() if message.text else ""
    try:
        target_id = int(text)
    except ValueError:
        bot.reply_to(message, "❌ الآيدي غير صحيح.")
        return
    db_admin_card[message.from_user.id] = target_id
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(f"{FLAGS.get(c,'')} {c}", callback_data=f"admincard_{c}") for c in COUNTRIES]
    markup.add(*buttons)
    bot.reply_to(message, f"✅ اللاعب: `{target_id}`\nاختر المنتخب الذي تريد إضافة بطاقته:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admincard_"))
def admin_give_card(call):
    if call.from_user.id != ADMIN_ID: return
    country = call.data.split("admincard_")[1]
    target_id = db_admin_card.get(call.from_user.id)
    if not target_id:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة، أعد المحاولة.", show_alert=True)
        return
    if country not in COUNTRIES:
        bot.answer_callback_query(call.id, "❌ منتخب غير صالح.", show_alert=True)
        return
    add_card(target_id, country)
    flag = FLAGS.get(country, "")
    count = db_inventory.get(target_id, {}).get(country, 0)
    db_admin_card.pop(call.from_user.id, None)
    bot.edit_message_text(
        f"✅ تم إضافة بطاقة **{flag} {country}** للاعب `{target_id}`\n🃏 لديه الآن `{count}` بطاقة من هذا المنتخب.",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown"
    )
    check_and_congratulate(target_id, call.message.chat.id)

# --- تحديد/إلغاء دولة الدعم للاعب ---
def admin_ask_national_uid(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.strip() if message.text else ""
    try:
        target_id = int(text)
    except ValueError:
        bot.reply_to(message, "❌ الآيدي غير صحيح.")
        return
    db_admin_national[message.from_user.id] = target_id
    _init_user(target_id)
    current = db_users[target_id].get("national_team", "") or "لا يوجد"
    flag = FLAGS.get(current, "") if current != "لا يوجد" else ""
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(f"{FLAGS.get(c,'')} {c}", callback_data=f"adminnation_{c}") for c in COUNTRIES]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("🗑 إلغاء دولة الدعم", callback_data="adminnation_CLEAR"))
    bot.reply_to(message,
        f"🌍 اللاعب: `{target_id}`\nدولة دعمه الحالية: **{flag} {current}**\n\nاختر الدولة الجديدة أو ألغِها:",
        reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adminnation_"))
def admin_set_national_team(call):
    if call.from_user.id != ADMIN_ID: return
    target_id = db_admin_national.get(call.from_user.id)
    if not target_id:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة، أعد المحاولة.", show_alert=True)
        return
    value = call.data.split("adminnation_")[1]
    _init_user(target_id)
    if value == "CLEAR":
        db_users[target_id]["national_team"] = ""
        db_users[target_id]["national_gift_claimed"] = False
        db_admin_national.pop(call.from_user.id, None)
        save_data()
        bot.edit_message_text(
            f"✅ تم إلغاء دولة الدعم للاعب `{target_id}`\nويمكنه الآن استخدام زر الهدية مجدداً.",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
    elif value in COUNTRIES:
        db_users[target_id]["national_team"] = value
        db_users[target_id]["national_gift_claimed"] = True
        flag = FLAGS.get(value, "")
        db_admin_national.pop(call.from_user.id, None)
        save_data()
        bot.edit_message_text(
            f"✅ تم تعيين دولة الدعم للاعب `{target_id}` إلى **{flag} {value}**.",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ اختيار غير صالح.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('setpic_'))
def ask_country_pic(call):
    if call.from_user.id != ADMIN_ID: return
    country = call.data.split('_')[1]
    msg = bot.send_message(call.message.chat.id, f"ارسل الآن صورة منتخب {country}:")
    bot.register_next_step_handler(msg, save_country_image, country)

def save_country_image(message, country):
    if message.photo:
        set_setting(f"pic_{country}", message.photo[-1].file_id)
    else:
        set_setting(f"pic_{country}", message.text)
    bot.reply_to(message, f"✅ تم حفظ صورة منتخب {country} بنجاح.")

# ================= أوامر اللاعبين =================
def _main_menu_text_markup(user_id):
    _init_user(user_id)
    user_data = db_users[user_id]
    national_team = user_data.get("national_team", "")
    gift_claimed = user_data.get("national_gift_claimed", False)
    keys = get_user_keys(user_id)
    name_str = user_data.get("name") or f"لاعب {user_id}"
    if national_team:
        flag = FLAGS.get(national_team, "")
        name_display = f"{name_str} {flag} {national_team}"
    else:
        name_display = name_str
    text = (
        f"🎩 **مرحباً {name_display}!**\n"
        f"🔑 مفاتيحك: `{keys}`\n\n"
        "اختر ما تريد فعله:"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📘 ألبومي", callback_data="menu_album"),
        InlineKeyboardButton("🛒 المتجر", callback_data="menu_store")
    )
    if not gift_claimed:
        markup.add(InlineKeyboardButton("🎁 هدية الدعم الوطني", callback_data="national_gift"))
    if not db_users[user_id].get("free_keys_claimed", False):
        markup.add(InlineKeyboardButton("🎀 استلم هديتك 100 مفتاح", callback_data="free_keys"))
    return text, markup

@bot.message_handler(commands=['myalbum'])
def my_album_menu(message):
    save_user_name(message.from_user)
    text, markup = _main_menu_text_markup(message.from_user.id)
    sent = bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")
    set_msg_owner(sent.message_id, message.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data in ['menu_album', 'menu_store'])
def main_menus(call):
    if not check_owner(call): return
    user_id = call.from_user.id

    if call.data == 'menu_album':
        inventory = get_inventory(user_id)
        markup = InlineKeyboardMarkup(row_width=3)
        buttons = []
        for c in COUNTRIES:
            status = "✅" if inventory.get(c, 0) > 0 else "❌"
            buttons.append(InlineKeyboardButton(f"{c} {status}", callback_data=f"view_{c}"))
        markup.add(*buttons)
        album_text = "📘 **ألبوم منتخباتك:**\nاضغط على المنتخب لعرضه:"
        try:
            bot.edit_message_text(album_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            sent = bot.send_message(call.message.chat.id, album_text, reply_markup=markup, parse_mode="Markdown")
            set_msg_owner(sent.message_id, user_id)

    elif call.data == 'menu_store':
        keys = get_user_keys(user_id)
        pack_pic = get_setting("pack_image")

        user_inv = db_inventory.get(user_id, {})
        total_extras = sum(c - 1 for c in user_inv.values() if c > 1)
        extras_keys = total_extras * 100

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("📦 فتح باكة (500 مفتاح)", callback_data="open_pack"))
        if total_extras > 0:
            markup.add(InlineKeyboardButton(
                f"💰 بيع جميع الزوائد ({total_extras} بطاقة = {extras_keys} مفتاح)",
                callback_data="sell_all"
            ))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))

        text = f"🛒 **المتجر**\n\n🔑 مفاتيحك: `{keys}`\n🎁 الباكة تعطيك بطاقة من منتخب عشوائي بـ 500 مفتاح."

        if pack_pic:
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            sent = bot.send_photo(call.message.chat.id, pack_pic, caption=text, reply_markup=markup, parse_mode="Markdown")
            set_msg_owner(sent.message_id, user_id)
        else:
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            except Exception:
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass
                sent = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
                set_msg_owner(sent.message_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    text, markup = _main_menu_text_markup(user_id)
    sent = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    set_msg_owner(sent.message_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "national_gift")
def national_gift_select(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    _init_user(user_id)
    if db_users[user_id].get("national_gift_claimed", False):
        bot.answer_callback_query(call.id, "✅ لقد استلمت الهدية مسبقاً!", show_alert=True)
        return
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(f"{FLAGS.get(c,'')} {c}", callback_data=f"picknation_{c}") for c in COUNTRIES]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
    try:
        bot.edit_message_text(
            "🎁 **هدية الدعم الوطني**\n\nاختر المنتخب الذي تدعمه في كأس العرب 2026!\nستحصل على **500 مفتاح** هدية 🔑\n\n_(لا يمكن تغيير اختيارك لاحقاً)_",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("picknation_"))
def pick_national_team(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    _init_user(user_id)
    if db_users[user_id].get("national_gift_claimed", False):
        bot.answer_callback_query(call.id, "✅ لقد استلمت الهدية مسبقاً!", show_alert=True)
        return
    country = call.data.split("picknation_")[1]
    if country not in COUNTRIES:
        bot.answer_callback_query(call.id, "❌ اختيار غير صالح.", show_alert=True)
        return
    db_users[user_id]["national_team"] = country
    db_users[user_id]["national_gift_claimed"] = True
    add_keys(user_id, 500)
    flag = FLAGS.get(country, "")
    bot.answer_callback_query(call.id, f"🎉 أنت تدعم {flag} {country}!\nتم إضافة 500 مفتاح لرصيدك!", show_alert=True)
    # إعادة القائمة الرئيسية مع إخفاء زر الهدية
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    text, markup = _main_menu_text_markup(user_id)
    sent = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    set_msg_owner(sent.message_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "free_keys")
def claim_free_keys(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    _init_user(user_id)
    if db_users[user_id].get("free_keys_claimed", False):
        bot.answer_callback_query(call.id, "✅ لقد استلمت الهدية مسبقاً!", show_alert=True)
        return
    db_users[user_id]["free_keys_claimed"] = True
    add_keys(user_id, 100)
    bot.answer_callback_query(call.id, "🎀 تم إضافة 100 مفتاح لرصيدك!", show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    text, markup = _main_menu_text_markup(user_id)
    sent = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    set_msg_owner(sent.message_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_country(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    country = call.data.split('_')[1]

    count = db_inventory.get(user_id, {}).get(country, 0)

    if count == 0:
        bot.answer_callback_query(call.id, "❌ لم تحصل على هذا المنتخب بعد!", show_alert=True)
        return

    pic = get_setting(f"pic_{country}")
    text = f"🎩 **منتخب {country}**\n\n🃏 تمتلك منها: `{count}` بطاقة"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔙 رجوع للألبوم", callback_data="menu_album"))

    if pic:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        sent = bot.send_photo(call.message.chat.id, pic, caption=text, reply_markup=markup, parse_mode="Markdown")
        set_msg_owner(sent.message_id, user_id)
    else:
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            sent = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
            set_msg_owner(sent.message_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sell_') and call.data != 'sell_all')
def sell_extra_cards(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    country = call.data.split('_')[1]
    
    count = db_inventory.get(user_id, {}).get(country, 0)

    if count > 1:
        extras = count - 1
        earned_keys = extras * 100
        db_inventory[user_id][country] = 1
        add_keys(user_id, earned_keys)
        
        bot.answer_callback_query(call.id, f"✅ تم بيع {extras} بطاقة وربحت {earned_keys} مفتاح!", show_alert=True)
        # إعادة تحميل صفحة المنتخب
        call.data = f"view_{country}"
        view_country(call)
    else:
        bot.answer_callback_query(call.id, "❌ لا تملك بطاقات زائدة للبيع!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "sell_all")
def sell_all_extras(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    user_inv = db_inventory.get(user_id, {})
    extras_map = {c: n for c, n in user_inv.items() if n > 1}
    if not extras_map:
        bot.answer_callback_query(call.id, "❌ لا تملك بطاقات زائدة للبيع!", show_alert=True)
        return
    total_extras = sum(n - 1 for n in extras_map.values())
    earned_keys = total_extras * 100
    for c in extras_map:
        db_inventory[user_id][c] = 1
    add_keys(user_id, earned_keys)
    bot.answer_callback_query(call.id, f"✅ تم بيع {total_extras} بطاقة زائدة وربحت {earned_keys} مفتاح!", show_alert=True)
    call.data = "menu_store"
    main_menus(call)

@bot.callback_query_handler(func=lambda call: call.data == "open_pack")
def open_pack(call):
    if not check_owner(call): return
    user_id = call.from_user.id
    keys = get_user_keys(user_id)
    
    if keys < 500:
        bot.answer_callback_query(call.id, "❌ مفاتيحك لا تكفي لفتح باكة! تحتاج 500 مفتاح.", show_alert=True)
        return
    
    # خصم المفاتيح وإضافة كارت عشوائي
    add_keys(user_id, -500)
    won_country = random.choice(COUNTRIES)
    add_card(user_id, won_country)
    
    bot.answer_callback_query(call.id, f"🎉 مبروك! حصلت على بطاقة منتخب: {won_country}", show_alert=True)

    # إرسال صورة البطاقة إن وُجدت
    card_pic = get_setting(f"pic_{won_country}")
    card_text = f"🎉 حصلت على بطاقة **{won_country}**!"
    if card_pic:
        bot.send_photo(call.message.chat.id, card_pic, caption=card_text, parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, card_text, parse_mode="Markdown")

    user_name = call.from_user.first_name or ""
    if call.from_user.last_name:
        user_name += " " + call.from_user.last_name
    check_and_congratulate(user_id, call.message.chat.id, user_name.strip())

    # تحديث واجهة المتجر
    call.data = "menu_store"
    main_menus(call)

# ================= نظام التفاعل في الجروب =================
@bot.message_handler(func=lambda m: m.text and ('اضف 70 دولار' in m.text or 'اضف ٧٠ دولار' in m.text) and m.chat.type in ['group', 'supergroup'])
def group_reward_trigger(message):
    sender_id = message.from_user.id
    allowed_group = get_setting("allowed_group")

    if allowed_group and str(message.chat.id) != allowed_group:
        bot.reply_to(message, "❌ هذا الجروب غير مفعّل للألبوم.")
        return

    is_admin = False
    if sender_id == ADMIN_ID:
        is_admin = True
    else:
        try:
            chat_member = bot.get_chat_member(message.chat.id, sender_id)
            if chat_member.status in ['administrator', 'creator', 'anonymous_admin']:
                is_admin = True
        except Exception:
            pass
    if not is_admin:
        return

    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ يجب أن تكتب الأمر **رداً** على رسالة الشخص الذي تريد منحه المكافأة.", parse_mode="Markdown")
        return

    target_user = message.reply_to_message.from_user

    if target_user.is_bot:
        bot.reply_to(message, "❌ لا يمكن منح مكافأة لبوت.")
        return

    # حساب النسبة (25% بطاقة, 75% مفاتيح)
    chance = random.randint(1, 100)

    target_name = (target_user.first_name or "")
    if target_user.last_name:
        target_name += " " + target_user.last_name
    target_name = target_name.strip()
    save_user_name(target_user)

    if chance <= 50:
        won_country = random.choice(COUNTRIES)
        add_card(target_user.id, won_country)
        card_pic = get_setting(f"pic_{won_country}")
        card_text = f"🎁 المشرف منحك بطاقة عشوائية!\n🎉 حصلت على: **{won_country}**"
        if card_pic:
            bot.send_photo(message.chat.id, card_pic, caption=card_text, parse_mode="Markdown",
                           reply_to_message_id=message.reply_to_message.message_id)
        else:
            bot.reply_to(message.reply_to_message, card_text, parse_mode="Markdown")
        check_and_congratulate(target_user.id, message.chat.id, target_name)
    else:
        add_keys(target_user.id, 50)
        bot.reply_to(message.reply_to_message, "🔑 المشرف منحك **50 مفتاح**!\nيمكنك استخدامها في المتجر.", parse_mode="Markdown")

# ================= ترتيب المتصدرين =================
@bot.message_handler(commands=['arableaderboard'])
def arab_leaderboard(message):
    save_user_name(message.from_user)
    # بناء قائمة المتصدرين من الذاكرة
    leaderboard = []
    for uid, inv in db_inventory.items():
        collected = {c for c, n in inv.items() if n > 0}
        unique = len(collected)
        if unique == 0:
            continue
        name = db_users.get(uid, {}).get("name") or f"لاعب {uid}"
        leaderboard.append((uid, name, unique, collected))

    leaderboard.sort(key=lambda x: x[2], reverse=True)
    leaderboard = leaderboard[:10]

    if not leaderboard:
        bot.reply_to(message, "📭 لا يوجد لاعبون في القائمة بعد!")
        return

    medals = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
    text = "🏆 **ترتيب المتصدرين - كأس العرب 2026**\n"
    text += "_(أكثر اللاعبين جمعاً لمنتخبات مختلفة)_\n\n"

    for i, (uid, name, unique_count, collected) in enumerate(leaderboard):
        bar = " ".join(FLAGS.get(c, "⬜") if c in collected else "⬜" for c in COUNTRIES)
        text += f"{medals[i]} **{name}** `{unique_count}/12`\n"
        text += f"{bar}\n\n"

    bot.reply_to(message, text, parse_mode="Markdown")


# ================= تعيين المجموعة الرسمية =================
@bot.message_handler(commands=['arabalbumg'])
def set_official_group(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ هذا الأمر يُستخدم داخل المجموعة فقط.")
        return

    chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ['administrator', 'creator'] and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ هذا الأمر مخصص للمشرفين فقط.")
        return

    set_setting("allowed_group", str(message.chat.id))
    group_name = message.chat.title or "هذه المجموعة"
    bot.reply_to(message, f"✅ تم تعيين **{group_name}** كالمجموعة الرسمية لكأس العرب 2026!\n\n"
                          f"🆔 آيدي المجموعة: `{message.chat.id}`", parse_mode="Markdown")


# تشغيل البوت
print("Bot is running...")
bot.infinity_polling()