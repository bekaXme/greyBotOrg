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
API_TOKEN = '7713134448:AAF8t-OZPCRfkYPC6PM0VGYyKXNDZytyZCM'
ADMIN_ID = [5703082829, 2100140929]  # Replace with actual admin IDs
PHONE_NUMBER = "+998910151402"
EXCHANGE_RATE = 12700
RESTRICTED_CATEGORIES = ["Sigarette", "Cigarettes", "Tobacco"]
SUPPORT_USERNAME = "@bekaXme"
PAYCOM_MERCHANT_ID = "371317599:TEST:1740663904243"  # Paycom test merchant ID
logging.basicConfig(level=logging.INFO)

# Bot initialization
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
app = FastAPI()

# Working hours in Uzbekistan time (UTC+5)
UZBEKISTAN_TZ = pytz.timezone("Asia/Tashkent")
WORKING_HOURS_START = 8  # 8:00 AM
WORKING_HOURS_END = 24   # 12:00 AM (midnight)

# Tashkent boundaries (approximate lat/lon box)
TASHKENT_BOUNDS = {
    "min_lat": 41.2,
    "max_lat": 41.4,
    "min_lon": 69.1,
    "max_lon": 69.4
}

# Language dictionaries (unchanged, truncated for brevity)
LANGUAGES = {
    "uzb": {
        "enter_name": "Iltimos, ismingizni kiriting:",
        "send_phone": "Iltimos, telefon raqamingizni yuboring:",
        "reg_complete": "Ro'yxatdan o'tish tugallandi!\nIsm: {name}\nTelefon: {phone}",
        "order_prompt": "Buyurtma berish uchun tugmani bosing:",
        "location_prompt": "Joylashuvingizni yuboring:",
        "enter_podyezd": "Podyezd (kirish) raqamini kiriting:",
        "enter_floor": "Qavat raqamini kiriting:",
        "enter_door": "Eshik raqamini kiriting:",
        "outside_tashkent": "Kechirasiz, bu bot faqat Toshkent shahrida ishlaydi.",
        # ... (rest unchanged)
    },
    "eng": {
        "enter_name": "Please enter your name:",
        "send_phone": "Please send your phone number:",
        "reg_complete": "Registration completed!\nName: {name}\nPhone: {phone}",
        "order_prompt": "Press the button to start ordering:",
        "location_prompt": "Send your location:",
        "enter_podyezd": "Enter your entrance (podyezd) number:",
        "enter_floor": "Enter your floor number:",
        "enter_door": "Enter your door number:",
        "outside_tashkent": "Sorry, this bot only works in Tashkent.",
        # ... (rest unchanged)
    },
    "rus": {
        "enter_name": "Пожалуйста, введите ваше имя:",
        "send_phone": "Пожалуйста, отправьте ваш номер телефона:",
        "reg_complete": "Регистрация завершена!\nИмя: {name}\nТелефон: {phone}",
        "order_prompt": "Нажмите кнопку, чтобы начать заказ:",
        "location_prompt": "Отправьте ваше местоположение:",
        "enter_podyezd": "Введите номер подъезда:",
        "enter_floor": "Введите номер этажа:",
        "enter_door": "Введите номер двери:",
        "outside_tashkent": "Извините, этот бот работает только в Ташкенте.",
        # ... (rest unchanged)
    }
}

# States (updated with new states for detailed location info)
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

# Database setup
def get_db_connection():
    conn = sqlite3.connect("store.db")
    conn.row_factory = sqlite3.Row
    return conn

# Cache for stores to reduce DB queries
STORES_CACHE = None

def setup_db():
    global STORES_CACHE
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, latitude REAL, longitude REAL, language TEXT DEFAULT 'uzb')""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS stores (
        id INTEGER PRIMARY KEY, name TEXT, latitude REAL, longitude REAL)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, store TEXT, category TEXT, brand TEXT, name TEXT, price REAL, description TEXT, image_url TEXT)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, cart_text TEXT, total_uzs REAL, discount REAL DEFAULT 0, 
        promo_code TEXT, payment_method TEXT, age TEXT, latitude REAL, longitude REAL, podyezd TEXT, floor TEXT, door TEXT, 
        delivery_time INTEGER DEFAULT NULL, status TEXT DEFAULT 'pending')""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY, discount_type TEXT, discount_value REAL)""")
    
    # Add new columns if they don’t exist
    for column in ["latitude", "longitude", "discount", "promo_code", "payment_method", "podyezd", "floor", "door"]:
        try:
            c.execute(f"ALTER TABLE orders ADD COLUMN {column} REAL" if column in ["latitude", "longitude", "discount"] else f"ALTER TABLE orders ADD COLUMN {column} TEXT")
        except sqlite3.OperationalError:
            pass
    
    # Updated store data
    c.execute("INSERT OR REPLACE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (1, 'ЦУМ', 41.306151, 69.268823))  # Updated to ЦУМ
    c.execute("INSERT OR REPLACE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (2, 'Store 2', 41.008238, 28.978359))  # Kept as is for example
    
    # Cache stores
    c.execute("SELECT name, latitude, longitude FROM stores")
    STORES_CACHE = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('ЦУМ', 'Electronics', 'Samsung', 'Galaxy S23', 12699999, 'Latest smartphone'))
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('Store 2', 'Clothing', 'Nike', 'Air Max', 1530350, 'Running shoes'))
    
    conn.commit()
    conn.close()

# Helper functions
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

def is_within_tashkent(lat, lon):
    return (TASHKENT_BOUNDS["min_lat"] <= lat <= TASHKENT_BOUNDS["max_lat"] and 
            TASHKENT_BOUNDS["min_lon"] <= lon <= TASHKENT_BOUNDS["max_lon"])

def get_nearest_store(user_lat, user_lon):
    if not STORES_CACHE:
        return None
    nearest_store = None
    min_distance = float("inf")
    for store in STORES_CACHE:
        store_distance = geopy.distance.geodesic((user_lat, user_lon), (store['latitude'], store['longitude'])).km
        if store_distance < min_distance:
            min_distance = store_distance
            nearest_store = store['name']
    return nearest_store

def is_within_working_hours():
    now = datetime.now(UZBEKISTAN_TZ)
    return WORKING_HOURS_START <= now.hour < WORKING_HOURS_END

def calculate_discount(total_uzs, promo_code):
    if not promo_code:
        return 0
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT discount_type, discount_value FROM promo_codes WHERE code = ?", (promo_code,))
    promo = c.fetchone()
    conn.close()
    return (promo['discount_value'] if promo['discount_type'] == 'fixed' else 
            round(total_uzs * (promo['discount_value'] / 100))) if promo else 0

async def auto_set_delivery_time(order_id: int, user_id: int, cart_text: str, total_uzs: float, discount: float, 
                                promo_code: str, payment_method: str, age: str, podyezd: str, floor: str, door: str, state: FSMContext):
    await asyncio.sleep(20)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT delivery_time, status FROM orders WHERE id = ? AND status = 'pending'", (order_id,))
    order = c.fetchone()
    
    if order and order['status'] == 'pending' and order['delivery_time'] is None:
        default_delivery_time = 35
        c.execute("UPDATE orders SET delivery_time = ?, status = 'confirmed' WHERE id = ?", (default_delivery_time, order_id))
        conn.commit()
        
        lang = get_user_language(user_id)
        total_usd = convert_to_usd(total_uzs)
        order_message = LANGUAGES[lang]["order_summary"].format(
            cart_text=cart_text, total_uzs=total_uzs, total_usd=total_usd, discount=discount, 
            age=age, payment_method=payment_method, delivery_time=default_delivery_time)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]])
        await bot.send_message(user_id, f"Admin didn’t respond. Default delivery time set to 35 minutes.\n{order_message}", reply_markup=keyboard)
        for admin_id in ADMIN_ID:
            await bot.send_message(admin_id, f"Order #{order_id} auto-confirmed with 35-minute delivery.")
        logging.info(f"Order #{order_id} auto-confirmed.")
    
    conn.close()
    await state.clear()

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
    lang = callback.data.split(":")[1]
    set_user_language(callback.from_user.id, lang)
    await state.update_data(language=lang)
    await callback.message.edit_text(LANGUAGES[lang]["enter_name"])
    await state.set_state(RegisterState.waiting_for_name)
    await callback.answer()

@router.message(RegisterState.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uzb")
    if not message.text or not message.text.strip():
        await message.answer(LANGUAGES[lang]["name_empty"])
        return
    await state.update_data(name=message.text.strip())
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📞 Send Phone", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
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
    if not is_within_working_hours():
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
        await callback.answer()
        return
    lang = get_user_language(callback.from_user.id)
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Send Location", request_location=True)]], resize_keyboard=True, one_time_keyboard=True)
    await bot.send_message(callback.from_user.id, LANGUAGES[lang]["location_prompt"], reply_markup=keyboard)
    await state.set_state(OrderState.waiting_for_location)
    await callback.answer()

@router.message(F.location, OrderState.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    if not is_within_working_hours():
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["outside_working_hours"], reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    user_lat, user_lon = message.location.latitude, message.location.longitude
    if not is_within_tashkent(user_lat, user_lon):
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["outside_tashkent"], reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    store = get_nearest_store(user_lat, user_lon)
    lang = get_user_language(message.from_user.id)
    
    if not store:
        await message.answer(LANGUAGES[lang]["no_stores"], reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    await state.update_data(store=store, cart=[], user_id=message.from_user.id, latitude=user_lat, longitude=user_lon)
    await message.answer(LANGUAGES[lang]["enter_podyezd"], reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.waiting_for_podyezd)

@router.message(OrderState.waiting_for_podyezd)
async def process_podyezd(message: Message, state: FSMContext):
    podyezd = message.text.strip()
    if not podyezd:
        lang = get_user_language(message.from_user.id)
        await message.answer("Please enter a valid entrance number.")
        return
    await state.update_data(podyezd=podyezd)
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["enter_floor"])
    await state.set_state(OrderState.waiting_for_floor)

@router.message(OrderState.waiting_for_floor)
async def process_floor(message: Message, state: FSMContext):
    floor = message.text.strip()
    if not floor:
        lang = get_user_language(message.from_user.id)
        await message.answer("Please enter a valid floor number.")
        return
    await state.update_data(floor=floor)
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["enter_door"])
    await state.set_state(OrderState.waiting_for_door)

@router.message(OrderState.waiting_for_door)
async def process_door(message: Message, state: FSMContext):
    door = message.text.strip()
    if not door:
        lang = get_user_language(message.from_user.id)
        await message.answer("Please enter a valid door number.")
        return
    await state.update_data(door=door)
    data = await state.get_data()
    store = data["store"]
    lang = get_user_language(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="order_start")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
    ])
    await message.answer(f"Nearest store: {store}", reply_markup=keyboard)
    await state.set_state(OrderState.selecting_action)

@router.callback_query(F.data == "order_start", OrderState.selecting_action)
async def start_ordering(callback: types.CallbackQuery, state: FSMContext):
    if not is_within_working_hours():
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
        await callback.answer()
        return
    user_data = await state.get_data()
    store = user_data.get("store")
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

@router.callback_query(F.data.startswith("cat:"), OrderState.selecting_category)
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    if not is_within_working_hours():
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
        await callback.answer()
        return
    _, store, category = callback.data.split(":")
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

@router.callback_query(F.data.startswith("brand:"), OrderState.selecting_brand)
async def process_brand(callback: types.CallbackQuery, state: FSMContext):
    _, store, category, brand = callback.data.split(":")
    lang = get_user_language(callback.from_user.id)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, price, description FROM products WHERE store = ? AND category = ? AND brand = ?", (store, category, brand))
    products = c.fetchall()
    conn.close()
    
    if not products:
        await callback.message.edit_text(LANGUAGES[lang]["no_products_brand"].format(store=store, category=category, brand=brand))
        await state.clear()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['name']} - {p['price']} UZS", callback_data=f"prod:{store}:{category}:{brand}:{p['id']}")]
        for p in products
    ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_brand")]])
    
    await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
    await state.set_state(OrderState.selecting_product)
    await callback.answer()

@router.callback_query(F.data.startswith("prod:"), OrderState.selecting_product)
async def process_product(callback: types.CallbackQuery, state: FSMContext):
    _, store, category, brand, product_id = callback.data.split(":")
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
    
    cart = (await state.get_data()).get("cart", [])
    cart.append({"name": product["name"], "price": product["price"], "description": product["description"]})
    await state.update_data(cart=cart)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 View Cart", callback_data="view_cart")],
        [InlineKeyboardButton(text="➕ Add More", callback_data=f"more:{store}")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
    ])
    await callback.message.edit_text(
        LANGUAGES[lang]["added_to_cart"].format(
            name=product["name"], price_uzs=product["price"], price_usd=convert_to_usd(product["price"]), description=product["description"]
        ),
        reply_markup=keyboard
    )
    await state.set_state(OrderState.cart_management)
    await callback.answer()

@router.callback_query(F.data == "view_cart", OrderState.cart_management)
async def view_cart(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    cart = user_data.get("cart", [])
    store = user_data.get("store")
    discount = user_data.get("discount", 0)
    lang = get_user_language(callback.from_user.id)
    
    if not cart:
        await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
        await state.clear()
        return
    
    cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
    total_uzs = sum(item["price"] for item in cart)
    final_total = total_uzs - discount
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
        [InlineKeyboardButton(text="🚀 Checkout", callback_data="checkout")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
    ])
    await callback.message.edit_text(
        f"Cart:\n{cart_text}\nTotal: {total_uzs} UZS\nDiscount: {discount} UZS\nFinal Total: {final_total} UZS",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("more:"), OrderState.cart_management)
async def continue_shopping(callback: types.CallbackQuery, state: FSMContext):
    store = callback.data.split(":")[1]
    lang = get_user_language(callback.from_user.id)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM products WHERE store = ?", (store,))
    categories = c.fetchall()
    conn.close()
    
    if not categories:
        await callback.message.edit_text(LANGUAGES[lang]["no_categories"].format(store=store))
        await state.clear()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat['category'], callback_data=f"cat:{store}:{cat['category']}")]
        for cat in categories
    ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_cart")]])
    
    await callback.message.edit_text(LANGUAGES[lang]["select_category"].format(store=store), reply_markup=keyboard)
    await state.set_state(OrderState.selecting_category)
    await callback.answer()

@router.callback_query(F.data == "apply_promo", OrderState.cart_management)
async def apply_promo_prompt(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(LANGUAGES[lang]["enter_promo"])
    await state.set_state(OrderState.waiting_for_promo)
    await callback.answer()

@router.message(OrderState.waiting_for_promo)
async def process_promo_code(message: Message, state: FSMContext):
    promo_code = message.text.strip()
    user_data = await state.get_data()
    cart = user_data.get("cart", [])
    store = user_data.get("store")
    lang = get_user_language(message.from_user.id)

    if not cart:
        await message.answer(LANGUAGES[lang]["cart_empty"])
        await state.clear()
        return

    total_uzs = sum(item["price"] for item in cart)
    discount = calculate_discount(total_uzs, promo_code)

    if discount == 0:
        await message.answer(LANGUAGES[lang]["promo_invalid"])
        cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
            [InlineKeyboardButton(text="🚀 Checkout", callback_data="checkout")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
        ])
        await message.answer(f"Cart:\n{cart_text}", reply_markup=keyboard)
        await state.set_state(OrderState.cart_management)
        return

    await state.update_data(promo_code=promo_code, discount=discount)
    cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
    total_uzs = sum(item["price"] for item in cart)
    final_total = total_uzs - discount
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
        [InlineKeyboardButton(text="🚀 Checkout", callback_data="checkout")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
    ])
    await message.answer(LANGUAGES[lang]["promo_applied"].format(discount=discount))
    await message.answer(f"Cart:\n{cart_text}\nTotal: {total_uzs} UZS\nDiscount: {discount} UZS\nFinal Total: {final_total} UZS", reply_markup=keyboard)
    await state.set_state(OrderState.cart_management)

@router.callback_query(F.data == "checkout", OrderState.cart_management)
async def checkout(callback: types.CallbackQuery, state: FSMContext):
    if not is_within_working_hours():
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
        await callback.answer()
        return

    user_data = await state.get_data()
    cart = user_data.get("cart", [])
    store = user_data.get("store")
    discount = user_data.get("discount", 0)

    if not cart:
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
        await state.clear()
        return

    lang = get_user_language(callback.from_user.id)
    cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
    total_uzs = sum(item["price"] for item in cart)
    final_total = total_uzs - discount

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Proceed to Payment", callback_data="select_payment")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_cart")]
    ])

    await callback.message.edit_text(
        f"Cart:\n{cart_text}\nTotal: {total_uzs} UZS\nDiscount: {discount} UZS\nFinal Total: {final_total} UZS",
        reply_markup=keyboard
    )
    await state.set_state(OrderState.cart_management)
    await callback.answer()

@router.callback_query(F.data == "select_payment", OrderState.cart_management)
async def select_payment_method(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["pay_cash"], callback_data="payment_cash")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_cart")]
    ])
    await callback.message.edit_text(LANGUAGES[lang]["select_payment"], reply_markup=keyboard)
    await state.set_state(OrderState.waiting_for_payment_method)
    await callback.answer()

@router.callback_query(F.data == "payment_cash", OrderState.waiting_for_payment_method)
async def process_cash_payment(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    cart = user_data.get("cart", [])
    user_id = user_data["user_id"]
    age = user_data.get("age", "Not provided")
    latitude = user_data["latitude"]
    longitude = user_data["longitude"]
    podyezd = user_data["podyezd"]
    floor = user_data["floor"]
    door = user_data["door"]
    store = user_data["store"]
    username = callback.from_user.username or "Not available"
    discount = user_data.get("discount", 0)
    promo_code = user_data.get("promo_code", None)
    lang = get_user_language(user_id)

    if not cart or not user_id or not store:
        await callback.message.edit_text("Error: Missing order data.")
        await state.clear()
        return

    total_uzs = sum(item["price"] for item in cart)
    total_usd = convert_to_usd(total_uzs)
    cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, latitude, longitude, podyezd, floor, door, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, cart_text, total_uzs, discount, promo_code, "Cash", age, latitude, longitude, podyezd, floor, door, "pending")
    )
    order_id = c.lastrowid
    conn.commit()

    c.execute("SELECT name, phone FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()

    if not user:
        await callback.message.edit_text("Error: User not found.")
        await state.clear()
        return

    user_message = (
        f"Your order #{order_id}:\n"
        f"{cart_text}\n"
        f"Total: {total_uzs} UZS ({total_usd} USD)\n"
        f"Discount: {discount} UZS\n"
        f"Final Total: {total_uzs - discount} UZS\n"
        f"Payment: Cash\n"
        f"Waiting for admin to set delivery time (20 seconds timeout)..."
    )
    await callback.message.edit_text(user_message)

    admin_message = (
        f"New Order #{order_id} from {user['name']}:\n"
        f"Username: @{username}\n"
        f"Phone: {user['phone']}\n"
        f"Order Details:\n{cart_text}\n"
        f"Total: {total_uzs} UZS ({total_usd} USD)\n"
        f"Discount: {discount} UZS (Promo: {promo_code or 'None'})\n"
        f"Final Total: {total_uzs - discount} UZS\n"
        f"Age: {age}\n"
        f"Payment: Cash\n"
        f"Location Details:\nPodyezd: {podyezd}\nFloor: {floor}\nDoor: {door}\n"
        f"Please set delivery time within 20 seconds or default 35 minutes will be set."
    )
    for admin_id in ADMIN_ID:
        await bot.send_message(
            admin_id,
            admin_message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Set Delivery Time", callback_data=f"set_delivery:{order_id}")]
            ])
        )
        await bot.send_location(admin_id, latitude=latitude, longitude=longitude)

    asyncio.create_task(auto_set_delivery_time(order_id, user_id, cart_text, total_uzs - discount, discount, promo_code, "Cash", age, podyezd, floor, door, state))
    await state.set_state(OrderState.waiting_for_delivery_time)
    await callback.answer()

@router.callback_query(F.data.startswith("set_delivery:"), OrderState.waiting_for_delivery_time)
async def set_delivery_time(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        await callback.message.edit_text(LANGUAGES["eng"]["admin_no_perm"])
        await callback.answer()
        return
    
    order_id = int(callback.data.split(":")[1])
    lang = get_user_language(callback.from_user.id)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM orders WHERE id = ? AND status = 'pending'", (order_id,))
    order = c.fetchone()
    conn.close()
    
    if not order:
        await callback.message.edit_text("Order not found or already processed.")
        await state.clear()
        return
    
    await state.update_data(order_id=order_id)
    await callback.message.edit_text(LANGUAGES[lang]["delivery_time_prompt"])
    await callback.answer()

@router.message(OrderState.waiting_for_delivery_time)
async def process_delivery_time(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    try:
        delivery_time = int(message.text.strip())
        if delivery_time <= 0:
            await message.answer("Delivery time must be positive.")
            return
        
        data = await state.get_data()
        order_id = data.get("order_id")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT user_id, cart_text, total_uzs, discount, payment_method, age FROM orders WHERE id = ? AND status = 'pending'", (order_id,))
        order = c.fetchone()
        
        if not order:
            await message.answer("Order not found or already processed.")
            await state.clear()
            conn.close()
            return
        
        user_id, cart_text, total_uzs, discount, payment_method, age = order
        c.execute("UPDATE orders SET delivery_time = ?, status = 'confirmed' WHERE id = ?", (delivery_time, order_id))
        conn.commit()
        conn.close()
        
        lang = get_user_language(user_id)
        total_usd = convert_to_usd(total_uzs)
        order_message = LANGUAGES[lang]["order_summary"].format(
            cart_text=cart_text, total_uzs=total_uzs, total_usd=total_usd, discount=discount,
            age=age, payment_method=payment_method, delivery_time=delivery_time
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]])
        await bot.send_message(user_id, order_message, reply_markup=keyboard)
        await message.answer(f"Delivery time set for Order #{order_id}!")
        await state.clear()
    except ValueError:
        await message.answer("Please enter a valid numeric delivery time!")
    except Exception as e:
        logging.error(f"Error in process_delivery_time: {e}")
        await message.answer("Something went wrong.")

@router.callback_query(F.data.startswith("rate_delivery:"))
async def rate_delivery(callback: types.CallbackQuery, state: FSMContext):
    order_id = callback.data.split(":")[1]
    lang = get_user_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1", callback_data=f"rate:{order_id}:1")],
        [InlineKeyboardButton(text="⭐⭐ 2", callback_data=f"rate:{order_id}:2")],
        [InlineKeyboardButton(text="⭐⭐⭐ 3", callback_data=f"rate:{order_id}:3")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐ 4", callback_data=f"rate:{order_id}:4")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ 5", callback_data=f"rate:{order_id}:5")]
    ])
    await callback.message.edit_text(LANGUAGES[lang]["rate_delivery"].format(phone=PHONE_NUMBER), reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("rate:"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    _, order_id, rating = callback.data.split(":")
    rating_int = int(rating)
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(f"Thank you for rating the delivery: {rating} stars!")
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE orders SET status = 'rated' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    
    for admin_id in ADMIN_ID:
        await bot.send_message(admin_id, f"User {callback.from_user.id} rated Order #{order_id} delivery: {rating} stars")
    
    if rating_int < 4:
        await bot.send_message(callback.from_user.id, LANGUAGES[lang]["feedback_prompt"])
        await state.update_data(user_id=callback.from_user.id, rating=rating, order_id=order_id)
        await state.set_state(OrderState.waiting_for_feedback)
    else:
        await state.clear()
    await callback.answer()

@router.message(OrderState.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)
    feedback = message.text.strip()
    data = await state.get_data()
    user_id = data["user_id"]
    rating = data["rating"]
    order_id = data["order_id"]
    
    for admin_id in ADMIN_ID:
        await bot.send_message(admin_id, f"User {user_id} rated Order #{order_id} {rating} stars with feedback:\n{feedback}")
    
    await message.answer(LANGUAGES[lang]["feedback_sent"])
    await state.clear()

@router.message(Command("add_product"))
async def add_product_command(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ЦУМ", callback_data="store:ЦУМ")],
        [InlineKeyboardButton(text="Store 2", callback_data="store:Store 2")]
    ])
    await message.answer(LANGUAGES["eng"]["select_store"], reply_markup=keyboard)
    await state.set_state(AddProductState.waiting_for_store)

@router.callback_query(F.data.startswith("store:"), AddProductState.waiting_for_store)
async def select_store(callback: types.CallbackQuery, state: FSMContext):
    store = callback.data.split(":")[1]
    await state.update_data(store=store)
    await callback.message.edit_text(LANGUAGES["eng"]["enter_category"])
    await state.set_state(AddProductState.waiting_for_category)
    await callback.answer()

@router.message(AddProductState.waiting_for_category)
async def process_category_input(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer(LANGUAGES["eng"]["category_empty"])
        return
    await state.update_data(category=message.text.strip())
    await message.answer(LANGUAGES["eng"]["enter_brand"])
    await state.set_state(AddProductState.waiting_for_brand)

@router.message(AddProductState.waiting_for_brand)
async def process_brand_input(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer(LANGUAGES["eng"]["brand_empty"])
        return
    await state.update_data(brand=message.text.strip())
    await message.answer(LANGUAGES["eng"]["enter_name_prod"])
    await state.set_state(AddProductState.waiting_for_product_name)

@router.message(AddProductState.waiting_for_product_name)
async def process_product_name(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer(LANGUAGES["eng"]["name_empty_prod"])
        return
    await state.update_data(name=message.text.strip())
    await message.answer(LANGUAGES["eng"]["enter_price"])
    await state.set_state(AddProductState.waiting_for_product_price)

@router.message(AddProductState.waiting_for_product_price)
async def process_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer(LANGUAGES["eng"]["price_negative"])
            return
        await state.update_data(price=price)
        await message.answer(LANGUAGES["eng"]["enter_description"])
        await state.set_state(AddProductState.waiting_for_product_description)
    except ValueError:
        await message.answer(LANGUAGES["eng"]["price_invalid"])
        return

@router.message(AddProductState.waiting_for_product_description)
async def process_product_description(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer(LANGUAGES["eng"]["description_empty"])
        return
    await state.update_data(description=message.text.strip())
    await message.answer(LANGUAGES["eng"]["enter_photo"])
    await state.set_state(AddProductState.waiting_for_photo)

@router.message(AddProductState.waiting_for_photo)
async def process_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    image_url = message.photo[-1].file_id if message.photo else None if message.text.strip() == LANGUAGES["eng"]["skip"] else None
    
    if not image_url and message.text.strip() != LANGUAGES["eng"]["skip"]:
        await message.answer(LANGUAGES["eng"]["enter_photo"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO products (store, category, brand, name, price, description, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (data['store'], data['category'], data['brand'], data['name'], data['price'], data['description'], image_url))
    conn.commit()
    conn.close()
    
    await message.answer(LANGUAGES["eng"]["product_added"].format(name=data['name']))
    await state.clear()

@router.message(Command("view_products"))
async def view_products_command(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, store, category, brand, name, price, description, image_url FROM products")
    products = c.fetchall()
    conn.close()
    
    if not products:
        await message.answer(LANGUAGES["eng"]["no_products_admin"])
        return
    
    for p in products:
        response = (
            f"{LANGUAGES['eng']['view_products']}\n"
            f"ID: {p['id']}\n"
            f"Store: {p['store']}\n"
            f"Category: {p['category']}\n"
            f"Brand: {p['brand']}\n"
            f"Name: {p['name']}\n"
            f"Price: {p['price']} UZS ({convert_to_usd(p['price'])} USD)\n"
            f"Description: {p['description']}\n"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES["eng"]["edit_button"], callback_data=f"edit_product:{p['id']}"),
             InlineKeyboardButton(text=LANGUAGES["eng"]["delete_button"], callback_data=f"delete_product:{p['id']}")]
        ])
        if p['image_url']:
            await bot.send_photo(message.chat.id, p['image_url'], caption=response, reply_markup=keyboard)
        else:
            await message.answer(response, reply_markup=keyboard)

@router.callback_query(F.data.startswith("edit_product:"))
async def edit_product_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        await callback.message.edit_text(LANGUAGES["eng"]["admin_no_perm"])
        return
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Store", callback_data="field:store")],
        [InlineKeyboardButton(text="Category", callback_data="field:category")],
        [InlineKeyboardButton(text="Brand", callback_data="field:brand")],
        [InlineKeyboardButton(text="Name", callback_data="field:name")],
        [InlineKeyboardButton(text="Price", callback_data="field:price")],
        [InlineKeyboardButton(text="Description", callback_data="field:description")],
        [InlineKeyboardButton(text="Photo", callback_data="field:image_url")]
    ])
    await callback.message.edit_text(LANGUAGES["eng"]["edit_field"].format(id=product_id), reply_markup=keyboard)
    await state.set_state(EditProductState.waiting_for_field)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_product:"))
async def delete_product_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        await callback.message.edit_text(LANGUAGES["eng"]["admin_no_perm"])
        return
    product_id = int(callback.data.split(":")[1])
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    if not product:
        await callback.message.edit_text(LANGUAGES["eng"]["id_not_found"])
        await state.clear()
        return
    
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(LANGUAGES["eng"]["product_deleted"].format(name=product['name'], id=product_id))
    await state.clear()
    await callback.answer()

@router.message(Command("delete_product"))
async def delete_product_command(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    await message.answer(LANGUAGES["eng"]["enter_del_id"])
    await state.set_state(DeleteProductState.waiting_for_product_id)

@router.message(DeleteProductState.waiting_for_product_id)
async def process_delete_product_id(message: Message, state: FSMContext):
    try:
        product_id = int(message.text.strip())
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()
        
        if not product:
            await message.answer(LANGUAGES["eng"]["id_not_found"])
            await state.clear()
            return
        
        c.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES["eng"]["product_deleted"].format(name=product['name'], id=product_id))
        await state.clear()
    except ValueError:
        await message.answer(LANGUAGES["eng"]["id_invalid"])
    except Exception as e:
        logging.error(f"Error in process_delete_product_id: {e}")
        await message.answer("Something went wrong.")

@router.message(Command("edit_product"))
async def edit_product_command(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    await message.answer(LANGUAGES["eng"]["enter_edit_id"])
    await state.set_state(EditProductState.waiting_for_product_id)

@router.message(EditProductState.waiting_for_product_id)
async def process_edit_product_id(message: Message, state: FSMContext):
    try:
        product_id = int(message.text.strip())
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()
        conn.close()
        
        if not product:
            await message.answer(LANGUAGES["eng"]["id_not_found"])
            await state.clear()
            return
        
        await state.update_data(product_id=product_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Store", callback_data="field:store")],
            [InlineKeyboardButton(text="Category", callback_data="field:category")],
            [InlineKeyboardButton(text="Brand", callback_data="field:brand")],
            [InlineKeyboardButton(text="Name", callback_data="field:name")],
            [InlineKeyboardButton(text="Price", callback_data="field:price")],
            [InlineKeyboardButton(text="Description", callback_data="field:description")],
            [InlineKeyboardButton(text="Photo", callback_data="field:image_url")]
        ])
        await message.answer(LANGUAGES["eng"]["edit_field"].format(id=product_id), reply_markup=keyboard)
        await state.set_state(EditProductState.waiting_for_field)
    except ValueError:
        await message.answer(LANGUAGES["eng"]["id_invalid"])
    except Exception as e:
        logging.error(f"Error in process_edit_product_id: {e}")
        await message.answer("Something went wrong.")

@router.callback_query(F.data.startswith("field:"), EditProductState.waiting_for_field)
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    _, field = callback.data.split(":")
    await state.update_data(field=field)
    await callback.message.edit_text(LANGUAGES["eng"]["enter_new_value"].format(field=field))
    await state.set_state(EditProductState.waiting_for_new_value)
    await callback.answer()

@router.message(EditProductState.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data.get("product_id")
    field = data.get("field")
    
    new_value = message.text.strip() if field != "image_url" else (message.photo[-1].file_id if message.photo else None)
    
    if field == "price":
        try:
            new_value = float(new_value)
            if new_value <= 0:
                await message.answer(LANGUAGES["eng"]["price_negative"])
                return
        except ValueError:
            await message.answer(LANGUAGES["eng"]["price_invalid"])
            return
    elif field != "image_url" and (not new_value or not new_value.strip()):
        await message.answer(LANGUAGES["eng"]["value_empty"])
        return
    elif field == "image_url" and not new_value and message.text.strip() != LANGUAGES["eng"]["skip"]:
        await message.answer(LANGUAGES["eng"]["enter_photo"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (new_value, product_id))
    conn.commit()
    conn.close()
    
    await message.answer(LANGUAGES["eng"]["product_updated"].format(id=product_id, field=field))
    await state.clear()

@router.message(OrderState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age < 18:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["age_restriction"])
            await state.clear()
            return
        
        data = await state.get_data()
        store = data["store"]
        category = data["category"]
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT brand FROM products WHERE store = ? AND category = ?", (store, category))
        brands = c.fetchall()
        conn.close()
        
        if not brands:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["no_brands"].format(category=category, store=store))
            await state.clear()
            return
        
        lang = get_user_language(message.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=brand['brand'], callback_data=f"brand:{store}:{category}:{brand['brand']}")]
            for brand in brands
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]])
        
        await message.answer(LANGUAGES[lang]["select_brand"].format(category=category), reply_markup=keyboard)
        await state.update_data(age=age)
        await state.set_state(OrderState.selecting_brand)
    except ValueError:
        await message.answer(LANGUAGES["eng"]["age_invalid"])

@router.callback_query(F.data == "settings")
async def settings_menu(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["change_name"], callback_data="change_name")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["change_phone"], callback_data="change_phone")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["change_language"], callback_data="change_language")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
    ])
    await callback.message.edit_text(LANGUAGES[lang]["settings_menu"], reply_markup=keyboard)
    await state.set_state(SettingsState.waiting_for_choice)
    await callback.answer()

@router.callback_query(F.data == "change_name", SettingsState.waiting_for_choice)
async def change_name_prompt(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(LANGUAGES[lang]["enter_new_name"])
    await state.set_state(SettingsState.waiting_for_new_name)
    await callback.answer()

@router.message(SettingsState.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    if not new_name:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["name_empty"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, message.from_user.id))
    conn.commit()
    conn.close()
    
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["name_updated"].format(name=new_name))
    await state.clear()

@router.callback_query(F.data == "change_phone", SettingsState.waiting_for_choice)
async def change_phone_prompt(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📞 Send New Phone", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await callback.message.edit_text(LANGUAGES[lang]["send_new_phone"], reply_markup=keyboard)
    await state.set_state(SettingsState.waiting_for_new_phone)
    await callback.answer()

@router.message(SettingsState.waiting_for_new_phone)
async def process_new_phone(message: Message, state: FSMContext):
    if not message.contact:
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["use_button"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET phone = ? WHERE user_id = ?", (message.contact.phone_number, message.from_user.id))
    conn.commit()
    conn.close()
    
    lang = get_user_language(message.from_user.id)
    await message.answer(LANGUAGES[lang]["phone_updated"].format(phone=message.contact.phone_number), reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

@router.callback_query(F.data == "change_language", SettingsState.waiting_for_choice)
async def change_language_prompt(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'zbek", callback_data="new_lang:uzb")],
        [InlineKeyboardButton(text="English", callback_data="new_lang:eng")],
        [InlineKeyboardButton(text="Русский", callback_data="new_lang:rus")]
    ])
    await callback.message.edit_text("Choose your new language:", reply_markup=keyboard)
    await state.set_state(SettingsState.waiting_for_new_language)
    await callback.answer()

@router.callback_query(F.data.startswith("new_lang:"), SettingsState.waiting_for_new_language)
async def process_new_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    set_user_language(callback.from_user.id, lang)
    await callback.message.edit_text(LANGUAGES[lang]["language_updated"])
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_command(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    help_text = LANGUAGES[lang]["help_text"].format(support=SUPPORT_USERNAME, phone=PHONE_NUMBER)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]])
    await callback.message.edit_text(help_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
         InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
    ])
    await callback.message.edit_text(LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
    await state.set_state(RegisterState.waiting_for_order)
    await callback.answer()

@router.callback_query(F.data == "back_to_action")
async def back_to_action(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    store = data.get("store")
    lang = get_user_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="order_start")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
    ])
    await callback.message.edit_text(f"Nearest store: {store}", reply_markup=keyboard)
    await state.set_state(OrderState.selecting_action)
    await callback.answer()

@router.callback_query(F.data == "back_to_category")
async def back_to_category(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    store = data.get("store")
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

@router.callback_query(F.data == "back_to_brand")
async def back_to_brand(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    store = data.get("store")
    category = data.get("category")
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

@router.callback_query(F.data == "back_to_product")
async def back_to_product(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    store = data.get("store")
    category = data.get("category")
    brand = data.get("brand")
    lang = get_user_language(callback.from_user.id)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, price, description FROM products WHERE store = ? AND category = ? AND brand = ?", (store, category, brand))
    products = c.fetchall()
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['name']} - {p['price']} UZS", callback_data=f"prod:{store}:{category}:{brand}:{p['id']}")]
        for p in products
    ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_brand")]])
    
    await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
    await state.set_state(OrderState.selecting_product)
    await callback.answer()

@router.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    store = data.get("store")
    discount = data.get("discount", 0)
    lang = get_user_language(callback.from_user.id)
    
    if not cart:
        await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
        await state.clear()
        return
    
    cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
    total_uzs = sum(item["price"] for item in cart)
    final_total = total_uzs - discount
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
        [InlineKeyboardButton(text="🚀 Checkout", callback_data="checkout")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
    ])
    await callback.message.edit_text(
        f"Cart:\n{cart_text}\nTotal: {total_uzs} UZS\nDiscount: {discount} UZS\nFinal Total: {final_total} UZS",
        reply_markup=keyboard
    )
    await state.set_state(OrderState.cart_management)
    await callback.answer()

@router.message(Command("add_promo"))
async def add_promo_command(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    await message.answer(LANGUAGES["eng"]["enter_promo_code"])
    await state.set_state(AddPromoState.waiting_for_code)

@router.message(AddPromoState.waiting_for_code)
async def process_promo_code_input(message: Message, state: FSMContext):
    promo_code = message.text.strip()
    if not promo_code:
        await message.answer(LANGUAGES["eng"]["promo_empty"])
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT code FROM promo_codes WHERE code = ?", (promo_code,))
    if c.fetchone():
        await message.answer(LANGUAGES["eng"]["promo_exists"])
        conn.close()
        return
    conn.close()
    
    await state.update_data(promo_code=promo_code)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Fixed", callback_data="discount_type:fixed")],
        [InlineKeyboardButton(text="Percentage", callback_data="discount_type:percentage")]
    ])
    await message.answer(LANGUAGES["eng"]["select_discount_type"], reply_markup=keyboard)
    await state.set_state(AddPromoState.waiting_for_discount_type)

@router.callback_query(F.data.startswith("discount_type:"), AddPromoState.waiting_for_discount_type)
async def process_discount_type(callback: types.CallbackQuery, state: FSMContext):
    discount_type = callback.data.split(":")[1]
    await state.update_data(discount_type=discount_type)
    await callback.message.edit_text(LANGUAGES["eng"]["enter_discount_value"])
    await state.set_state(AddPromoState.waiting_for_discount_value)
    await callback.answer()

@router.message(AddPromoState.waiting_for_discount_value)
async def process_discount_value(message: Message, state: FSMContext):
    try:
        discount_value = float(message.text.strip())
        if discount_value <= 0:
            await message.answer(LANGUAGES["eng"]["discount_negative"])
            return
        
        data = await state.get_data()
        promo_code = data["promo_code"]
        discount_type = data["discount_type"]
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO promo_codes (code, discount_type, discount_value) VALUES (?, ?, ?)",
                  (promo_code, discount_type, discount_value))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES["eng"]["promo_added"].format(code=promo_code, type=discount_type, value=discount_value))
        await state.clear()
    except ValueError:
        await message.answer(LANGUAGES["eng"]["discount_invalid"])

# Main execution
async def main():
    setup_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"An error occurred: {e}")