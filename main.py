import logging
import sqlite3
import asyncio
import random
import requests
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram import F
from fastapi import FastAPI
import geopy.distance

# Configuration
API_TOKEN = '7713134448:AAF8t-OZPCRfkYPC6PM0VGYyKXNDZytyZCM'  # Replace with your bot token
ADMIN_ID = [5703082829, 2100140929]  # Replace with actual admin IDs
PHONE_NUMBER = "+998910151402"
EXCHANGE_RATE = 12700
RESTRICTED_CATEGORIES = ["Sigarette", "Cigarettes", "Tobacco"]
SUPPORT_USERNAME = "@bekaXme"
PAYCOM_MERCHANT_ID = "371317599:TEST:1740663904243"  # Paycom test merchant ID
logging.basicConfig(level=logging.INFO)

# Bot initialization with optimizations
bot = Bot(token=API_TOKEN, timeout=30)  # Increased timeout for hosting stability
dp = Dispatcher()
router = Router()
dp.include_router(router)
app = FastAPI()

# Tashkent boundaries (approximate lat/lon box)
TASHKENT_BOUNDS = {
    'min_lat': 41.15,
    'max_lat': 41.45,
    'min_lon': 69.10,
    'max_lon': 69.40
}

# Working hours in Uzbekistan time (UTC+5)
UZBEKISTAN_TZ = pytz.timezone("Asia/Tashkent")
WORKING_HOURS_START = 8  # 8:00 AM
WORKING_HOURS_END = 24   # 12:00 AM (midnight)

# Language dictionaries (unchanged, omitted for brevity)
LANGUAGES = {
    "uzb": {
        "enter_name": "Iltimos, ismingizni kiriting:",
        "name_empty": "Ism bo'sh bo'lmasligi kerak. Iltimos, ismingizni kiriting:",
        "send_phone": "Iltimos, telefon raqamingizni yuboring:",
        "use_button": "Iltimos, tugmani ishlating!",
        "reg_complete": "Ro'yxatdan o'tish tugallandi!\nIsm: {name}\nTelefon: {phone}",
        "order_prompt": "Buyurtma berish uchun tugmani bosing:",
        "no_stores": "Yaqin atrofda do'konlar topilmadi.",
        "no_products": "{store} da mahsulotlar mavjud emas. Keyinroq urinib ko'ring yoki qo'llab-quvvatlash xizmatiga murojaat qiling.",
        "select_category": "Do'kon: {store}\nKategoriyani tanlang:",
        "no_brands": "{store} da {category} uchun brendlar mavjud emas.",
        "select_brand": "Kategoriya: {category}\nBrendni tanlang:",
        "no_products_brand": "{store} da {category} uchun {brand} mahsulotlari mavjud emas.",
        "select_product": "Brend: {brand}\nMahsulotni tanlang:",
        "product_not_found": "Mahsulot topilmadi. Qaytadan urinib ko'ring.",
        "added_to_cart": "Savatga qo'shildi:\n{name}\nNarx: {price_uzs} UZS ({price_usd} USD)\nTavsif: {description}",
        "no_categories": "{store} da kategoriyalar mavjud emas.",
        "cart_empty": "Savatingiz bo'sh!",
        "order_summary": "Sizning buyurtmangiz:\n{cart_text}\nJami: {total_uzs} UZS ({total_usd} USD)\nChegirma: {discount} UZS\nYosh: {age}\nTo'lov: {payment_method}\nYetkazib berish: {delivery_time} daqiqada\nPodyezd: {podyezd}\nQavat: {floor}\nEshik: {door}",
        "admin_no_perm": "Sizda bu amalni bajarish uchun ruxsat yo'q!",
        "select_store": "Do'konni tanlang:",
        "enter_category": "Mahsulot kategoriyasini kiriting:",
        "category_empty": "Kategoriya bo'sh bo'lmasligi kerak. Iltimos, kategoriyani kiriting:",
        "enter_brand": "Mahsulot brendini kiriting:",
        "brand_empty": "Brend bo'sh bo'lmasligi kerak. Iltimos, brendni kiriting:",
        "enter_name_prod": "Mahsulot nomini kiriting:",
        "name_empty_prod": "Mahsulot nomi bo'sh bo'lmasligi kerak. Iltimos, nomni kiriting:",
        "enter_price": "Mahsulot narxini kiriting (UZS):",
        "price_invalid": "Iltimos, to'g'ri raqamli narx kiriting!",
        "price_negative": "Narx musbat bo'lishi kerak. Iltimos, to'g'ri narx kiriting:",
        "enter_description": "Mahsulot tavsifini kiriting:",
        "description_empty": "Tavsif bo'sh bo'lmasligi kerak. Iltimos, tavsifni kiriting:",
        "enter_photo": "Mahsulot rasmini yuboring (ixtiyoriy, agar yo'q bo'lsa /skip deb yozing):",
        "product_added": "Mahsulot {name} muvaffaqiyatli qo'shildi!",
        "view_products": "Barcha mahsulotlar:",
        "no_products_admin": "Mahsulotlar mavjud emas.",
        "enter_del_id": "O'chirmoqchi bo'lgan mahsulot ID sini kiriting (/view_products bilan ID larni ko'ring):",
        "id_invalid": "Iltimos, to'g'ri raqamli mahsulot ID kiriting!",
        "id_not_found": "Mahsulot ID topilmadi. Iltimos, ID ni tekshirib qaytadan urining.",
        "product_deleted": "Mahsulot '{name}' (ID: {id}) muvaffaqiyatli o'chirildi!",
        "enter_edit_id": "Tahrir qilmoqchi bo'lgan mahsulot ID sini kiriting (/view_products bilan ID larni ko'ring):",
        "edit_field": "Mahsulot ID {id} tahrirlanmoqda. Tahrir qilmoqchi bo'lgan maydonni tanlang:",
        "enter_new_value": "{field} uchun yangi qiymatni kiriting:",
        "value_empty": "Qiymat bo'sh bo'lmasligi kerak. Iltimos, yangi qiymatni kiriting:",
        "product_updated": "Mahsulot ID {id} yangilandi: {field} {value} ga o'zgartirildi",
        "skip": "/skip",
        "delivery_time_prompt": "Yetkazib berish vaqtini daqiqalarda kiriting (masalan, 45):",
        "rate_delivery": "Yetkazib berishni baholang:\nBiz bilan bog'lanish: {phone}",
        "order_button": "Buyurtma berish",
        "back_button": "Orqaga",
        "location_prompt": "Joylashuvingizni yuboring:",
        "edit_button": "Tahrirlash",
        "delete_button": "O'chirish",
        "enter_age": "Iltimos, yoshingizni kiriting:",
        "age_invalid": "Iltimos, to'g'ri raqamli yosh kiriting (masalan, 25):",
        "age_restricted": "Kechirasiz, bu kategoriyadagi mahsulotlarni faqat 18 yoshdan oshganlar sotib olishi mumkin.",
        "help_button": "Yordam",
        "settings_button": "Sozlamalar",
        "help_text": "Bu bot sizga mahsulot buyurtma qilish imkonini beradi.\nYordam uchun: {support}",
        "settings_prompt": "Nima o'zgartirmoqchisiz?",
        "change_name": "Ismni o'zgartirish",
        "change_phone": "Telefonni o'zgartirish",
        "change_language": "Tilni o'zgartirish",
        "feedback_prompt": "Yetkazib berish bilan bog'liq muammo nima edi? Iltimos, sharhingizni yozing:",
        "feedback_sent": "Fikringiz uchun rahmat! Biz uni yaxshilash ustida ishlaymiz.",
        "outside_working_hours": "Kechirasiz, bot faqat soat 08:00 dan 00:00 gacha ishlaydi (O'zbekiston vaqti). Iltimos, keyinroq urinib ko'ring.",
        "apply_promo": "Promokodni kiriting",
        "enter_promo": "Promokodni kiriting:",
        "promo_applied": "Promokod qo'llanildi! Chegirma: {discount} UZS",
        "promo_invalid": "Noto'g'ri promokod. Iltimos, qaytadan urinib ko'ring.",
        "add_promo": "Promokod qo'shish",
        "enter_promo_code": "Yangi promokodni kiriting:",
        "enter_discount_type": "Chegirma turini tanlang:",
        "discount_fixed": "Fiks summa",
        "discount_percent": "Foiz",
        "enter_discount_value": "Chegirma qiymatini kiriting ({type}):",
        "promo_added": "Promokod '{code}' muvaffaqiyatli qo'shildi! Chegirma: {value} ({type})",
        "promo_exists": "Bu promokod allaqachon mavjud. Boshqa kod kiriting.",
        "select_payment": "To'lov usulini tanlang:",
        "pay_cash": "Naqd",
        "pay_card": "Karta orqali",
        "location_not_tashkent": "Kechirasiz, bu bot faqat Toshkent shahrida ishlaydi!",
        "enter_podyezd": "Iltimos, подъезд raqamini kiriting:",
        "enter_floor": "Iltimos, qavatni kiriting:",
        "enter_door": "Iltimos, eshik raqamini kiriting:"
    },
    "eng": {
        # English translations omitted for brevity, assumed correct from previous code
    },
    "rus": {
        # Russian translations omitted for brevity, assumed correct from previous code
    }
}

# States (unchanged, omitted for brevity)
class RegisterState(StatesGroup):
    waiting_for_language = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_order = State()

class OrderState(StatesGroup):
    waiting_for_location = State()
    waiting_for_podyezd = State()
    waiting_for_floor = State()
    waiting_for_door = State()
    selecting_store = State()
    selecting_action = State()
    selecting_category = State()
    waiting_for_age = State()
    selecting_brand = State()
    selecting_product = State()
    cart_management = State()
    waiting_for_promo = State()
    waiting_for_payment_method = State()
    waiting_for_delivery_time = State()
    waiting_for_feedback = State()

class AddProductState(StatesGroup):
    waiting_for_store = State()
    waiting_for_category = State()
    waiting_for_brand = State()
    waiting_for_product_name = State()
    waiting_for_product_price = State()
    waiting_for_product_description = State()
    waiting_for_photo = State()

class EditProductState(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_field = State()
    waiting_for_new_value = State()

class DeleteProductState(StatesGroup):
    waiting_for_product_id = State()

class SettingsState(StatesGroup):
    waiting_for_choice = State()
    waiting_for_new_name = State()
    waiting_for_new_phone = State()
    waiting_for_new_language = State()

class AddPromoState(StatesGroup):
    waiting_for_code = State()
    waiting_for_discount_type = State()
    waiting_for_discount_value = State()

# Database setup with explicit store name fix
def get_db_connection():
    conn = sqlite3.connect("store.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def setup_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            latitude REAL,
            longitude REAL,
            language TEXT DEFAULT 'uzb'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY,
            name TEXT,
            latitude REAL,
            longitude REAL
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store TEXT,
            category TEXT,
            brand TEXT,
            name TEXT,
            price REAL,
            description TEXT,
            image_url TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            cart_text TEXT,
            total_uzs REAL,
            discount REAL DEFAULT 0,
            promo_code TEXT,
            payment_method TEXT,
            age TEXT,
            latitude REAL,
            longitude REAL,
            podyezd TEXT,
            floor TEXT,
            door TEXT,
            delivery_time INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount_type TEXT,
            discount_value REAL
        )
    """)
    
    # Ensure stores are correctly named as "ЦУМ" and "Sergeli"
    c.execute("DELETE FROM stores")  # Clear any existing stores to avoid duplicates
    c.execute("INSERT OR REPLACE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (1, 'ЦУМ', 41.306151, 69.268823))  # ЦУМ
    c.execute("INSERT OR REPLACE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (2, 'Sergeli', 41.285642, 69.203804))  # Sergeli
    
    # Sample products for both stores
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('ЦУМ', 'Electronics', 'Samsung', 'Galaxy S23', 12699999, 'Latest smartphone'))
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('ЦУМ', 'Clothing', 'Nike', 'Air Max', 1530350, 'Running shoes'))
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('Sergeli', 'Electronics', 'Apple', 'iPhone 14', 13999999, 'New iPhone model'))
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('Sergeli', 'Clothing', 'Adidas', 'Ultraboost', 1650350, 'Comfortable sneakers'))
    
    conn.commit()
    conn.close()

# Helper functions (unchanged, omitted for brevity)
def is_fully_registered(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, phone FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return bool(result and result['name'] and result['phone'])

def get_user_language(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result['language'] if result else 'uzb'

def set_user_language(user_id, lang):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()

def convert_to_usd(price_uzs):
    return round(price_uzs / EXCHANGE_RATE, 2)

def is_in_tashkent(lat, lon):
    return (TASHKENT_BOUNDS['min_lat'] <= lat <= TASHKENT_BOUNDS['max_lat'] and 
            TASHKENT_BOUNDS['min_lon'] <= lon <= TASHKENT_BOUNDS['max_lon'])

def is_within_working_hours():
    now = datetime.now(UZBEKISTAN_TZ)
    current_hour = now.hour
    return WORKING_HOURS_START <= current_hour < WORKING_HOURS_END

def calculate_discount(total_uzs, promo_code):
    if not promo_code:
        return 0
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT discount_type, discount_value FROM promo_codes WHERE code = ?", (promo_code,))
    promo = c.fetchone()
    conn.close()
    if not promo:
        return 0
    discount_type, discount_value = promo['discount_type'], promo['discount_value']
    return discount_value if discount_type == 'fixed' else round(total_uzs * (discount_value / 100))

# Handlers
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
         InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
    ])
    if is_fully_registered(message.from_user.id):
        await message.answer(LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="O'zbek", callback_data="lang:uzb")],
            [InlineKeyboardButton(text="English", callback_data="lang:eng")],
            [InlineKeyboardButton(text="Русский", callback_data="lang:rus")]
        ])
        await message.answer("Welcome! Please choose your language:", reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_language)

@router.callback_query(F.data.startswith("lang:"), RegisterState.waiting_for_language)
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = callback.data.split(":")[1]
        set_user_language(callback.from_user.id, lang)
        await state.update_data(language=lang)
        await callback.message.edit_text(LANGUAGES[lang]["enter_name"])
        await state.set_state(RegisterState.waiting_for_name)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_language: {e}")
        await callback.message.edit_text("Error occurred. Please try /start again.")
        await state.clear()

@router.message(RegisterState.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uzb")
    if not message.text or not message.text.strip():
        await message.answer(LANGUAGES[lang]["name_empty"])
        return
    await state.update_data(name=message.text.strip())
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Send Phone", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(LANGUAGES[lang]["send_phone"], reply_markup=keyboard)
    await state.set_state(RegisterState.waiting_for_phone)

@router.message(RegisterState.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uzb")
    if not message.contact:
        await message.answer(LANGUAGES[lang]["use_button"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, name, phone, language) VALUES (?, ?, ?, ?)",
              (message.from_user.id, data["name"], message.contact.phone_number, lang))
    conn.commit()
    conn.close()
    
    await message.answer(LANGUAGES[lang]["reg_complete"].format(name=data["name"], phone=message.contact.phone_number),
                         reply_markup=types.ReplyKeyboardRemove())
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
         InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
    ])
    await bot.send_message(message.from_user.id, LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
    await state.set_state(RegisterState.waiting_for_order)

@router.callback_query(F.data == "start_ordering", RegisterState.waiting_for_order)
async def start_ordering_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        lang = get_user_language(callback.from_user.id)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Send Location", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await bot.send_message(callback.from_user.id, LANGUAGES[lang]["location_prompt"], reply_markup=keyboard)
        await state.set_state(OrderState.waiting_for_location)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in start_ordering_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(F.location, OrderState.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["outside_working_hours"], reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return

        user_lat, user_lon = message.location.latitude, message.location.longitude
        if not is_in_tashkent(user_lat, user_lon):
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["location_not_tashkent"], reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
        
        await state.update_data(user_id=message.from_user.id, latitude=user_lat, longitude=user_lon)
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["enter_podyezd"], reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrderState.waiting_for_podyezd)
    except Exception as e:
        logging.error(f"Error in process_location: {e}")
        await message.answer("Something went wrong while processing your location.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

@router.message(OrderState.waiting_for_podyezd)
async def process_podyezd(message: Message, state: FSMContext):
    try:
        podyezd = message.text.strip()
        if not podyezd:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["enter_podyezd"])
            return
        await state.update_data(podyezd=podyezd)
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["enter_floor"])
        await state.set_state(OrderState.waiting_for_floor)
    except Exception as e:
        logging.error(f"Error in process_podyezd: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_floor)
async def process_floor(message: Message, state: FSMContext):
    try:
        floor = message.text.strip()
        if not floor:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["enter_floor"])
            return
        await state.update_data(floor=floor)
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["enter_door"])
        await state.set_state(OrderState.waiting_for_door)
    except Exception as e:
        logging.error(f"Error in process_floor: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_door)
async def process_door(message: Message, state: FSMContext):
    try:
        door = message.text.strip()
        if not door:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["enter_door"])
            return
        await state.update_data(door=door)
        lang = get_user_language(message.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM stores")
        stores = c.fetchall()
        conn.close()
        
        if not stores:
            await message.answer(LANGUAGES[lang]["no_stores"])
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=store['name'], callback_data=f"store:{store['name']}")]
            for store in stores
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]])
        
        await message.answer(LANGUAGES[lang]["select_store"], reply_markup=keyboard)
        await state.set_state(OrderState.selecting_store)
    except Exception as e:
        logging.error(f"Error in process_door: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("store:"), OrderState.selecting_store)
async def process_store(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        store = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        
        await state.update_data(store=store, cart=[])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="order_start")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_store_selection")]
        ])
        await callback.message.edit_text(f"Store: {store}", reply_markup=keyboard)
        await state.set_state(OrderState.selecting_action)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_store: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_store_selection", OrderState.selecting_action)
async def back_to_store_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM stores")
        stores = c.fetchall()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=store['name'], callback_data=f"store:{store['name']}")]
            for store in stores
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_store"], reply_markup=keyboard)
        await state.set_state(OrderState.selecting_store)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_store_selection: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_main", OrderState.selecting_store)
async def back_to_main_from_store(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
             InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_main_from_store: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "order_start", OrderState.selecting_action)
async def start_ordering(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        user_data = await state.get_data()
        store = user_data.get("store")
        if not store:
            raise ValueError("Store not found in state data")
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM products WHERE store = ?", (store,))
        categories = c.fetchall()
        conn.close()
        
        if not categories:
            await callback.message.edit_text(LANGUAGES[lang]["no_products"].format(store=store))
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat['category'], callback_data=f"cat:{store}:{cat['category']}")]
            for cat in categories
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_action")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_category"].format(store=store), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_category)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in start_ordering: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_action", OrderState.selecting_category)
async def back_to_action_from_category(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        store = user_data.get("store")
        if not store:
            raise ValueError("Store not found in state data")
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="order_start")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_store_selection")]
        ])
        await callback.message.edit_text(f"Store: {store}", reply_markup=keyboard)
        await state.set_state(OrderState.selecting_action)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_action_from_category: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("cat:"), OrderState.selecting_category)
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        parts = callback.data.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid callback data format")
        _, store, category = parts
        lang = get_user_language(callback.from_user.id)
        
        if category in RESTRICTED_CATEGORIES:
            await callback.message.edit_text(LANGUAGES[lang]["enter_age"])
            await state.update_data(store=store, category=category)
            await state.set_state(OrderState.waiting_for_age)
        else:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT DISTINCT brand FROM products WHERE store = ? AND category = ?", (store, category))
            brands = c.fetchall()
            conn.close()
            
            if not brands:
                await callback.message.edit_text(LANGUAGES[lang]["no_brands"].format(category=category, store=store))
                await state.clear()
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=brand['brand'], callback_data=f"brand:{store}:{category}:{brand['brand']}")]
                for brand in brands
            ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]])
            
            await callback.message.edit_text(LANGUAGES[lang]["select_brand"].format(category=category), reply_markup=keyboard)
            await state.update_data(category=category)
            await state.set_state(OrderState.selecting_brand)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_category: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            age = int(message.text.strip())
            if age < 18:
                await message.answer(LANGUAGES[lang]["age_restricted"])
                await state.clear()
                return
            user_data = await state.get_data()
            store = user_data.get("store")
            category = user_data.get("category")
            
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT DISTINCT brand FROM products WHERE store = ? AND category = ?", (store, category))
            brands = c.fetchall()
            conn.close()
            
            if not brands:
                await message.answer(LANGUAGES[lang]["no_brands"].format(category=category, store=store))
                await state.clear()
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=brand['brand'], callback_data=f"brand:{store}:{category}:{brand['brand']}")]
                for brand in brands
            ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]])
            
            await message.answer(LANGUAGES[lang]["select_brand"].format(category=category), reply_markup=keyboard)
            await state.update_data(age=age)
            await state.set_state(OrderState.selecting_brand)
        except ValueError:
            await message.answer(LANGUAGES[lang]["age_invalid"])
    except Exception as e:
        logging.error(f"Error in process_age: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_category", OrderState.selecting_brand)
async def back_to_category(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        store = user_data.get("store")
        if not store:
            raise ValueError("Store not found in state data")
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM products WHERE store = ?", (store,))
        categories = c.fetchall()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat['category'], callback_data=f"cat:{store}:{cat['category']}")]
            for cat in categories
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_action")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_category"].format(store=store), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_category)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_category: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("brand:"), OrderState.selecting_brand)
async def process_brand(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        parts = callback.data.split(":")
        if len(parts) != 4:
            raise ValueError("Invalid callback data format")
        _, store, category, brand = parts
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, price, description FROM products WHERE store = ? AND category = ? AND brand = ?", 
                  (store, category, brand))
        products = c.fetchall()
        conn.close()
        
        if not products:
            await callback.message.edit_text(LANGUAGES[lang]["no_products_brand"].format(brand=brand, category=category, store=store))
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{prod['name']} - {prod['price']} UZS", callback_data=f"prod:{prod['id']}")]
            for prod in products
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_brand")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
        await state.update_data(brand=brand)
        await state.set_state(OrderState.selecting_product)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_brand: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_brand", OrderState.selecting_product)
async def back_to_brand(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        store = user_data.get("store")
        category = user_data.get("category")
        if not store or not category:
            raise ValueError("Store or category not found in state data")
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT brand FROM products WHERE store = ? AND category = ?", (store, category))
        brands = c.fetchall()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=brand['brand'], callback_data=f"brand:{store}:{category}:{brand['brand']}")]
            for brand in brands
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_brand"].format(category=category), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_brand)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_brand: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("prod:"), OrderState.selecting_product)
async def process_product(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        product_id = int(callback.data.split(":")[1])
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name, price, description FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()
        conn.close()
        
        if not product:
            await callback.message.edit_text(LANGUAGES[lang]["product_not_found"])
            await state.clear()
            return
        
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        cart.append({"id": product_id, "name": product["name"], "price": product["price"], "description": product["description"]})
        await state.update_data(cart=cart)
        
        price_usd = convert_to_usd(product["price"])
        await callback.message.edit_text(
            LANGUAGES[lang]["added_to_cart"].format(name=product["name"], price_uzs=product["price"], price_usd=price_usd, description=product["description"]),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="view_cart")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
            ])
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_product: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_product", OrderState.selecting_product)
async def back_to_product(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        store = user_data.get("store")
        category = user_data.get("category")
        brand = user_data.get("brand")
        if not store or not category or not brand:
            raise ValueError("Store, category, or brand not found in state data")
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, price, description FROM products WHERE store = ? AND category = ? AND brand = ?", 
                  (store, category, brand))
        products = c.fetchall()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{prod['name']} - {prod['price']} UZS", callback_data=f"prod:{prod['id']}")]
            for prod in products
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_brand")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_product)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_product: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "view_cart", OrderState.selecting_product)
async def view_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        lang = get_user_language(callback.from_user.id)
        
        if not cart:
            await callback.message.edit_text(LANGUAGES[lang]["cart_empty"],
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                                [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
                                            ]))
            return
        
        cart_text = "\n".join([f"{item['name']} - {item['price']} UZS" for item in cart])
        total_uzs = sum(item["price"] for item in cart)
        total_usd = convert_to_usd(total_uzs)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="proceed_to_order")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
        ])
        
        await callback.message.edit_text(f"Your cart:\n{cart_text}\nTotal: {total_uzs} UZS ({total_usd} USD)", reply_markup=keyboard)
        await state.set_state(OrderState.cart_management)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in view_cart: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "apply_promo", OrderState.cart_management)
async def apply_promo_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["enter_promo"],
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="view_cart")]
                                        ]))
        await state.set_state(OrderState.waiting_for_promo)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in apply_promo_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_promo)
async def process_promo(message: Message, state: FSMContext):
    try:
        promo_code = message.text.strip()
        lang = get_user_language(message.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT discount_type, discount_value FROM promo_codes WHERE code = ?", (promo_code,))
        promo = c.fetchone()
        conn.close()
        
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        total_uzs = sum(item["price"] for item in cart)
        
        if not promo:
            await message.answer(LANGUAGES[lang]["promo_invalid"])
            return
        
        discount = calculate_discount(total_uzs, promo_code)
        total_usd = convert_to_usd(total_uzs - discount)
        cart_text = "\n".join([f"{item['name']} - {item['price']} UZS" for item in cart])
        
        await state.update_data(promo_code=promo_code, discount=discount)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="proceed_to_order")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
        ])
        
        await message.answer(LANGUAGES[lang]["promo_applied"].format(discount=discount))
        await message.answer(f"Your cart:\n{cart_text}\nTotal: {total_uzs} UZS ({total_usd} USD)\nDiscount: {discount} UZS", 
                            reply_markup=keyboard)
        await state.set_state(OrderState.cart_management)
    except Exception as e:
        logging.error(f"Error in process_promo: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "proceed_to_order", OrderState.cart_management)
async def proceed_to_order(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["pay_cash"], callback_data="payment:cash")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["pay_card"], callback_data="payment:card")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="view_cart")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["select_payment"], reply_markup=keyboard)
        await state.set_state(OrderState.waiting_for_payment_method)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in proceed_to_order: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("payment:"), OrderState.waiting_for_payment_method)
async def process_payment_method(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_method = callback.data.split(":")[1]
        await state.update_data(payment_method=payment_method)
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        total_uzs = sum(item["price"] for item in cart)
        discount = user_data.get("discount", 0)
        total_usd = convert_to_usd(total_uzs - discount)
        cart_text = "\n".join([f"{item['name']} - {item['price']} UZS" for item in cart])
        age = user_data.get("age", "N/A")
        lang = get_user_language(callback.from_user.id)
        
        order_message = LANGUAGES[lang]["order_summary"].format(
            cart_text=cart_text,
            total_uzs=total_uzs,
            total_usd=total_usd,
            discount=discount,
            age=age,
            payment_method=LANGUAGES[lang][f"pay_{payment_method}"],
            delivery_time="Pending",
            podyezd=user_data["podyezd"],
            floor=user_data["floor"],
            door=user_data["door"]
        )
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO orders (user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, latitude, longitude, podyezd, floor, door)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_data["user_id"], cart_text, total_uzs, discount, user_data.get("promo_code"), payment_method, age,
              user_data["latitude"], user_data["longitude"], user_data["podyezd"], user_data["floor"], user_data["door"]))
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        
        await callback.message.edit_text(order_message + "\n\nWaiting for admin to set delivery time...")
        for admin_id in ADMIN_ID:
            await bot.send_message(admin_id, f"New Order #{order_id}:\n{order_message}\n\nPlease set delivery time with /set_delivery {order_id} <time_in_minutes>")
        
        # Start auto-set delivery time task
        asyncio.create_task(auto_set_delivery_time(order_id, user_data["user_id"], cart_text, total_uzs, discount, 
                                                  user_data.get("promo_code"), payment_method, age, 
                                                  user_data["podyezd"], user_data["floor"], user_data["door"], state))
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_payment_method: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

async def auto_set_delivery_time(order_id: int, user_id: int, cart_text: str, total_uzs: float, discount: float, promo_code: str, payment_method: str, age: str, podyezd: str, floor: str, door: str, state: FSMContext):
    await asyncio.sleep(20)  # Wait 20 seconds before auto-confirming
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT delivery_time, status FROM orders WHERE id = ? AND status = 'pending'", (order_id,))
        order = c.fetchone()
        
        if order and order['status'] == 'pending' and order['delivery_time'] is None:
            default_delivery_time = 35
            c.execute("UPDATE orders SET delivery_time = ?, status = 'confirmed' WHERE id = ?", (default_delivery_time, order_id))
            conn.commit()
            conn.close()
            
            lang = get_user_language(user_id)
            total_usd = convert_to_usd(total_uzs)
            order_message = LANGUAGES[lang]["order_summary"].format(
                cart_text=cart_text,
                total_uzs=total_uzs,
                total_usd=total_usd,
                discount=discount,
                age=age,
                payment_method=LANGUAGES[lang][f"pay_{payment_method}"],
                delivery_time=default_delivery_time,
                podyezd=podyezd,
                floor=floor,
                door=door
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]
            ])
            await bot.send_message(user_id, f"Admin didn’t respond in time. Default delivery time set to 35 minutes.\n{order_message}", reply_markup=keyboard)
            for admin_id in ADMIN_ID:
                await bot.send_message(admin_id, f"Order #{order_id} auto-confirmed with 35-minute delivery due to no response.")
            logging.info(f"Order #{order_id} auto-confirmed with 35-minute delivery.")
        
        conn.close()
        await state.clear()
    except Exception as e:
        logging.error(f"Error in auto_set_delivery_time for order {order_id}: {e}")

@router.message(Command("set_delivery"))
async def set_delivery_time(message: Message, state: FSMContext):
    try:
        if message.from_user.id not in ADMIN_ID:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["admin_no_perm"])
            return
        
        parts = message.text.split()
        if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
            await message.answer("Usage: /set_delivery <order_id> <time_in_minutes>")
            return
        
        order_id, delivery_time = int(parts[1]), int(parts[2])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, podyezd, floor, door FROM orders WHERE id = ? AND status = 'pending'", (order_id,))
        order = c.fetchone()
        
        if not order:
            await message.answer(f"Order #{order_id} not found or already confirmed.")
            conn.close()
            return
        
        c.execute("UPDATE orders SET delivery_time = ?, status = 'confirmed' WHERE id = ?", (delivery_time, order_id))
        conn.commit()
        conn.close()
        
        lang = get_user_language(order['user_id'])
        total_usd = convert_to_usd(order['total_uzs'])
        order_message = LANGUAGES[lang]["order_summary"].format(
            cart_text=order['cart_text'],
            total_uzs=order['total_uzs'],
            total_usd=total_usd,
            discount=order['discount'],
            age=order['age'],
            payment_method=LANGUAGES[lang][f"pay_{order['payment_method']}"],
            delivery_time=delivery_time,
            podyezd=order['podyezd'],
            floor=order['floor'],
            door=order['door']
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]
        ])
        await bot.send_message(order['user_id'], f"Your order has been confirmed!\n{order_message}", reply_markup=keyboard)
        await message.answer(f"Delivery time for Order #{order_id} set to {delivery_time} minutes.")
    except Exception as e:
        logging.error(f"Error in set_delivery_time: {e}")
        await message.answer("Something went wrong. Please try again.")

@router.callback_query(F.data.startswith("rate_delivery:"))
async def rate_delivery_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        order_id = int(callback.data.split(":")[1])
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["rate_delivery"].format(phone=PHONE_NUMBER),
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
                                        ]))
        await state.set_state(OrderState.waiting_for_feedback)
        await state.update_data(order_id=order_id)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in rate_delivery_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        feedback = message.text.strip()
        user_data = await state.get_data()
        order_id = user_data.get("order_id")
        
        for admin_id in ADMIN_ID:
            await bot.send_message(admin_id, f"Feedback for Order #{order_id}:\n{feedback}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
             InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
        ])
        await message.answer(LANGUAGES[lang]["feedback_sent"], reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
    except Exception as e:
        logging.error(f"Error in process_feedback: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("add_product"))
async def add_product_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["admin_no_perm"])
        return
    
    lang = get_user_language(message.from_user.id)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM stores")
    stores = c.fetchall()
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=store['name'], callback_data=f"add_store:{store['name']}")]
        for store in stores
    ])
    await message.answer(LANGUAGES[lang]["select_store"], reply_markup=keyboard)
    await state.set_state(AddProductState.waiting_for_store)

@router.callback_query(F.data.startswith("add_store:"), AddProductState.waiting_for_store)
async def process_add_store(callback: types.CallbackQuery, state: FSMContext):
    try:
        store = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["enter_category"])
        await state.update_data(store=store)
        await state.set_state(AddProductState.waiting_for_category)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_add_store: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_category)
async def process_add_category(message: Message, state: FSMContext):
    try:
        category = message.text.strip()
        lang = get_user_language(message.from_user.id)
        if not category:
            await message.answer(LANGUAGES[lang]["category_empty"])
            return
        await state.update_data(category=category)
        await message.answer(LANGUAGES[lang]["enter_brand"])
        await state.set_state(AddProductState.waiting_for_brand)
    except Exception as e:
        logging.error(f"Error in process_add_category: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_brand)
async def process_add_brand(message: Message, state: FSMContext):
    try:
        brand = message.text.strip()
        lang = get_user_language(message.from_user.id)
        if not brand:
            await message.answer(LANGUAGES[lang]["brand_empty"])
            return
        await state.update_data(brand=brand)
        await message.answer(LANGUAGES[lang]["enter_name_prod"])
        await state.set_state(AddProductState.waiting_for_product_name)
    except Exception as e:
        logging.error(f"Error in process_add_brand: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_product_name)
async def process_add_product_name(message: Message, state: FSMContext):
    try:
        name = message.text.strip()
        lang = get_user_language(message.from_user.id)
        if not name:
            await message.answer(LANGUAGES[lang]["name_empty_prod"])
            return
        await state.update_data(name=name)
        await message.answer(LANGUAGES[lang]["enter_price"])
        await state.set_state(AddProductState.waiting_for_product_price)
    except Exception as e:
        logging.error(f"Error in process_add_product_name: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_product_price)
async def process_add_product_price(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            price = float(message.text.strip())
            if price < 0:
                await message.answer(LANGUAGES[lang]["price_negative"])
                return
            await state.update_data(price=price)
            await message.answer(LANGUAGES[lang]["enter_description"])
            await state.set_state(AddProductState.waiting_for_product_description)
        except ValueError:
            await message.answer(LANGUAGES[lang]["price_invalid"])
    except Exception as e:
        logging.error(f"Error in process_add_product_price: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_product_description)
async def process_add_product_description(message: Message, state: FSMContext):
    try:
        description = message.text.strip()
        lang = get_user_language(message.from_user.id)
        if not description:
            await message.answer(LANGUAGES[lang]["description_empty"])
            return
        await state.update_data(description=description)
        await message.answer(LANGUAGES[lang]["enter_photo"])
        await state.set_state(AddProductState.waiting_for_photo)
    except Exception as e:
        logging.error(f"Error in process_add_product_description: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_photo)
async def process_add_product_photo(message: Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        lang = get_user_language(message.from_user.id)
        
        image_url = None
        if message.text == "/skip":
            image_url = None
        elif message.photo:
            image_url = message.photo[-1].file_id
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO products (store, category, brand, name, price, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_data["store"], user_data["category"], user_data["brand"], user_data["name"], 
              user_data["price"], user_data["description"], image_url))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES[lang]["product_added"].format(name=user_data["name"]))
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_add_product_photo: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("view_products"))
async def view_products(message: Message):
    if message.from_user.id not in ADMIN_ID:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["admin_no_perm"])
        return
    
    lang = get_user_language(message.from_user.id)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, store, category, brand, name, price FROM products")
    products = c.fetchall()
    conn.close()
    
    if not products:
        await message.answer(LANGUAGES[lang]["no_products_admin"])
        return
    
    product_list = "\n".join([f"ID: {p['id']} - {p['store']} - {p['category']} - {p['brand']} - {p['name']} - {p['price']} UZS" for p in products])
    await message.answer(f"{LANGUAGES[lang]['view_products']}\n{product_list}")

@router.message(Command("delete_product"))
async def delete_product_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["admin_no_perm"])
        return
    
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["enter_del_id"])
    await state.set_state(DeleteProductState.waiting_for_product_id)

@router.message(DeleteProductState.waiting_for_product_id)
async def process_delete_product(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            product_id = int(message.text.strip())
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
            product = c.fetchone()
            
            if not product:
                await message.answer(LANGUAGES[lang]["id_not_found"])
                conn.close()
                return
            
            c.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            
            await message.answer(LANGUAGES[lang]["product_deleted"].format(name=product["name"], id=product_id))
            await state.clear()
        except ValueError:
            await message.answer(LANGUAGES[lang]["id_invalid"])
    except Exception as e:
        logging.error(f"Error in process_delete_product: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("edit_product"))
async def edit_product_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["admin_no_perm"])
        return
    
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["enter_edit_id"])
    await state.set_state(EditProductState.waiting_for_product_id)

@router.message(EditProductState.waiting_for_product_id)
async def process_edit_product_id(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            product_id = int(message.text.strip())
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM products WHERE id = ?", (product_id,))
            product = c.fetchone()
            conn.close()
            
            if not product:
                await message.answer(LANGUAGES[lang]["id_not_found"])
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Store", callback_data=f"edit_field:{product_id}:store")],
                [InlineKeyboardButton(text="Category", callback_data=f"edit_field:{product_id}:category")],
                [InlineKeyboardButton(text="Brand", callback_data=f"edit_field:{product_id}:brand")],
                [InlineKeyboardButton(text="Name", callback_data=f"edit_field:{product_id}:name")],
                [InlineKeyboardButton(text="Price", callback_data=f"edit_field:{product_id}:price")],
                [InlineKeyboardButton(text="Description", callback_data=f"edit_field:{product_id}:description")]
            ])
            await message.answer(LANGUAGES[lang]["edit_field"].format(id=product_id), reply_markup=keyboard)
            await state.set_state(EditProductState.waiting_for_field)
        except ValueError:
            await message.answer(LANGUAGES[lang]["id_invalid"])
    except Exception as e:
        logging.error(f"Error in process_edit_product_id: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("edit_field:"), EditProductState.waiting_for_field)
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        product_id, field = parts[1], parts[2]
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["enter_new_value"].format(field=field))
        await state.update_data(product_id=product_id, field=field)
        await state.set_state(EditProductState.waiting_for_new_value)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_edit_field: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(EditProductState.waiting_for_new_value)
async def process_edit_new_value(message: Message, state: FSMContext):
    try:
        new_value = message.text.strip()
        lang = get_user_language(message.from_user.id)
        if not new_value:
            await message.answer(LANGUAGES[lang]["value_empty"])
            return
        
        user_data = await state.get_data()
        product_id = user_data["product_id"]
        field = user_data["field"]
        
        if field == "price":
            try:
                new_value = float(new_value)
                if new_value < 0:
                    await message.answer(LANGUAGES[lang]["price_negative"])
                    return
            except ValueError:
                await message.answer(LANGUAGES[lang]["price_invalid"])
                return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (new_value, product_id))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES[lang]["product_updated"].format(id=product_id, field=field, value=new_value))
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_edit_new_value: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("add_promo"))
async def add_promo_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["admin_no_perm"])
        return
    
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["enter_promo_code"])
    await state.set_state(AddPromoState.waiting_for_code)

@router.message(AddPromoState.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    try:
        promo_code = message.text.strip()
        lang = get_user_language(message.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT code FROM promo_codes WHERE code = ?", (promo_code,))
        if c.fetchone():
            await message.answer(LANGUAGES[lang]["promo_exists"])
            conn.close()
            return
        conn.close()
        
        await state.update_data(promo_code=promo_code)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["discount_fixed"], callback_data="discount_type:fixed")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["discount_percent"], callback_data="discount_type:percent")]
        ])
        await message.answer(LANGUAGES[lang]["enter_discount_type"], reply_markup=keyboard)
        await state.set_state(AddPromoState.waiting_for_discount_type)
    except Exception as e:
        logging.error(f"Error in process_promo_code: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("discount_type:"), AddPromoState.waiting_for_discount_type)
async def process_discount_type(callback: types.CallbackQuery, state: FSMContext):
    try:
        discount_type = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        await state.update_data(discount_type=discount_type)
        await callback.message.edit_text(LANGUAGES[lang]["enter_discount_value"].format(type=LANGUAGES[lang][f"discount_{discount_type}"]))
        await state.set_state(AddPromoState.waiting_for_discount_value)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_discount_type: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddPromoState.waiting_for_discount_value)
async def process_discount_value(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            discount_value = float(message.text.strip())
            if discount_value <= 0:
                await message.answer("Discount value must be positive!")
                return
            
            user_data = await state.get_data()
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO promo_codes (code, discount_type, discount_value) VALUES (?, ?, ?)",
                      (user_data["promo_code"], user_data["discount_type"], discount_value))
            conn.commit()
            conn.close()
            
            await message.answer(LANGUAGES[lang]["promo_added"].format(
                code=user_data["promo_code"], 
                value=discount_value, 
                type=LANGUAGES[lang][f"discount_{user_data['discount_type']}"]
            ))
            await state.clear()
        except ValueError:
            await message.answer("Please enter a valid numeric value!")
    except Exception as e:
        logging.error(f"Error in process_discount_value: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

# Settings Handlers
@router.callback_query(F.data == "settings", RegisterState.waiting_for_order)
async def show_settings(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["change_name"], callback_data="change_name")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["change_phone"], callback_data="change_phone")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["change_language"], callback_data="change_language")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["settings_prompt"], reply_markup=keyboard)
        await state.set_state(SettingsState.waiting_for_choice)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_settings: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "change_name", SettingsState.waiting_for_choice)
async def change_name_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["enter_name"])
        await state.set_state(SettingsState.waiting_for_new_name)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in change_name_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(SettingsState.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        if not message.text or not message.text.strip():
            await message.answer(LANGUAGES[lang]["name_empty"])
            return
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET name = ? WHERE user_id = ?", (message.text.strip(), message.from_user.id))
        conn.commit()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
             InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
        ])
        await message.answer(LANGUAGES[lang]["reg_complete"].format(name=message.text.strip(), phone=PHONE_NUMBER), reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
    except Exception as e:
        logging.error(f"Error in process_new_name: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "change_phone", SettingsState.waiting_for_choice)
async def change_phone_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📞 Send Phone", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await bot.send_message(callback.from_user.id, LANGUAGES[lang]["send_phone"], reply_markup=keyboard)
        await state.set_state(SettingsState.waiting_for_new_phone)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in change_phone_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(SettingsState.waiting_for_new_phone)
async def process_new_phone(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        if not message.contact:
            await message.answer(LANGUAGES[lang]["use_button"])
            return
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET phone = ? WHERE user_id = ?", (message.contact.phone_number, message.from_user.id))
        conn.commit()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
             InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
        ])
        await message.answer(LANGUAGES[lang]["reg_complete"].format(name="User", phone=message.contact.phone_number), 
                            reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
    except Exception as e:
        logging.error(f"Error in process_new_phone: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "change_language", SettingsState.waiting_for_choice)
async def change_language_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="O'zbek", callback_data="new_lang:uzb")],
            [InlineKeyboardButton(text="English", callback_data="new_lang:eng")],
            [InlineKeyboardButton(text="Русский", callback_data="new_lang:rus")]
        ])
        await callback.message.edit_text("Please choose your new language:", reply_markup=keyboard)
        await state.set_state(SettingsState.waiting_for_new_language)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in change_language_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("new_lang:"), SettingsState.waiting_for_new_language)
async def process_new_language(callback: types.CallbackQuery, state: FSMContext):
    try:
        new_lang = callback.data.split(":")[1]
        set_user_language(callback.from_user.id, new_lang)
        lang = new_lang
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
             InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_new_language: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_main", SettingsState.waiting_for_choice)
async def back_to_main_settings(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
             InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
        await state.set_state(RegisterState.waiting_for_order)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_main_settings: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "help", RegisterState.waiting_for_order)
async def show_help(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        help_text = LANGUAGES[lang]["help_text"].format(support=SUPPORT_USERNAME)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
        ])
        await callback.message.edit_text(help_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in show_help: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

# FastAPI endpoint to run the bot
@app.on_event("startup")
async def startup_event():
    setup_db()
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)