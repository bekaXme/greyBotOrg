import logging
import sqlite3
import asyncio
import random
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
import geopy.distance

logging.basicConfig(level=logging.DEBUG)

# Configuration
logging.basicConfig(level=logging.DEBUG)
API_TOKEN = '7713134448:AAF8t-OZPCRfkYPC6PM0VGYyKXNDZytyZCM'
ADMIN_ID = [5703082829, 2100140929]
PHONE_NUMBER = "+998910151402"
EXCHANGE_RATE = 12700
RESTRICTED_CATEGORIES = ["Sigarette", "Cigarettes", "Tobacco"]
SUPPORT_USERNAME = "@bekaXme"
UZBEKISTAN_TZ = pytz.timezone("Asia/Tashkent")
WORKING_HOURS_START = 8  # 8:00 AM
WORKING_HOURS_END = 24   # 12:00 AM (midnight)

# Bot initialization
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Language dictionaries (unchanged)
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
        "select_category": "Eng yaqin do'kon: {store}\nKategoriyani tanlang:",
        "no_brands": "{store} da {category} uchun brendlar mavjud emas.",
        "select_brand": "Kategoriya: {category}\nBrendni tanlang:",
        "no_products_brand": "{store} da {category} uchun {brand} mahsulotlari mavjud emas.",
        "select_product": "Brend: {brand}\nMahsulotni tanlang:",
        "product_not_found": "Mahsulot topilmadi. Qaytadan urinib ko'ring.",
        "added_to_cart": "Savatga qo'shildi:\n{name}\nNarx: {price_uzs} UZS ({price_usd} USD)\nTavsif: {description}",
        "no_categories": "{store} da kategoriyalar mavjud emas.",
        "cart_empty": "Savatingiz bo'sh!",
        "order_summary": "Sizning buyurtmangiz:\n{cart_text}\nJami: {total_uzs} UZS ({total_usd} USD)\nChegirma: {discount} UZS\nYosh: {age}\nTo'lov: {payment_method}\nYetkazib berish: {delivery_time} daqiqada",
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
        "help_text": "Bu bot sizga yaqin atrofdagi do'konlardan mahsulot buyurtma qilish imkonini beradi.\nYordam uchun: {support}",
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
        "cancel_button": "Bekor qilish",
    },
    "eng": {
        "enter_name": "Please enter your name:",
        "name_empty": "Name cannot be empty. Please enter your name:",
        "send_phone": "Please send your phone number:",
        "use_button": "Please use the button!",
        "reg_complete": "Registration completed!\nName: {name}\nPhone: {phone}",
        "order_prompt": "Press the button to start ordering:",
        "no_stores": "No stores found nearby.",
        "no_products": "No products available in {store}. Please try again later or contact support.",
        "select_category": "Nearest store: {store}\nSelect a category:",
        "no_brands": "No brands available in {category} at {store}.",
        "select_brand": "Category: {category}\nSelect a brand:",
        "no_products_brand": "No products available for {brand} in {category} at {store}.",
        "select_product": "Brand: {brand}\nSelect a product:",
        "product_not_found": "Product not found. Please try again.",
        "added_to_cart": "Added to cart:\n{name}\nPrice: {price_uzs} UZS ({price_usd} USD)\nDescription: {description}",
        "no_categories": "No categories available in {store}.",
        "cart_empty": "Your cart is empty!",
        "order_summary": "Your order:\n{cart_text}\nTotal: {total_uzs} UZS ({total_usd} USD)\nDiscount: {discount} UZS\nAge: {age}\nPayment: {payment_method}\nDelivery in: {delivery_time} minutes",
        "admin_no_perm": "You don't have permission to perform this action!",
        "select_store": "Select a store:",
        "enter_category": "Enter product category:",
        "category_empty": "Category cannot be empty. Please enter a category:",
        "enter_brand": "Enter product brand:",
        "brand_empty": "Brand cannot be empty. Please enter a brand:",
        "enter_name_prod": "Enter product name:",
        "name_empty_prod": "Product name cannot be empty. Please enter a name:",
        "enter_price": "Enter product price (UZS):",
        "price_invalid": "Please enter a valid numeric price!",
        "price_negative": "Price must be positive. Please enter a valid price:",
        "enter_description": "Enter product description:",
        "description_empty": "Description cannot be empty. Please enter a description:",
        "enter_photo": "Send product photo (optional, type /skip if none):",
        "product_added": "Product {name} added successfully!",
        "view_products": "All Products:",
        "no_products_admin": "No products available.",
        "enter_del_id": "Please enter the product ID you want to delete (use /view_products to see IDs):",
        "id_invalid": "Please enter a valid numeric product ID!",
        "id_not_found": "Product ID not found. Please check the ID and try again.",
        "product_deleted": "Product '{name}' (ID: {id}) deleted successfully!",
        "enter_edit_id": "Please enter the product ID you want to edit (use /view_products to see IDs):",
        "edit_field": "Editing Product ID {id}. Select a field to edit:",
        "enter_new_value": "Enter the new value for {field}:",
        "value_empty": "Value cannot be empty. Please enter a new value:",
        "product_updated": "Product ID {id} updated: {field} set to {value}",
        "skip": "/skip",
        "delivery_time_prompt": "Enter delivery time in minutes (e.g., 45):",
        "rate_delivery": "Rate the delivery:\nContact us: {phone}",
        "order_button": "Order",
        "back_button": "Back",
        "location_prompt": "Send your location:",
        "edit_button": "Edit",
        "delete_button": "Delete",
        "enter_age": "Please enter your age:",
        "age_invalid": "Please enter a valid numeric age (e.g., 25):",
        "age_restricted": "Sorry, only users above 18 can purchase items in this category.",
        "help_button": "Help",
        "settings_button": "Settings",
        "help_text": "This bot helps you order products from nearby stores.\nFor support: {support}",
        "settings_prompt": "What would you like to change?",
        "change_name": "Change Name",
        "change_phone": "Change Phone",
        "change_language": "Change Language",
        "feedback_prompt": "What was the problem with the delivery? Please leave your comment:",
        "feedback_sent": "Thank you for your feedback! We'll work on improving.",
        "outside_working_hours": "Sorry, the bot operates only from 08:00 to 00:00 (Uzbekistan time). Please try again later.",
        "apply_promo": "Apply Promo Code",
        "enter_promo": "Enter promo code:",
        "promo_applied": "Promo code applied! Discount: {discount} UZS",
        "promo_invalid": "Invalid promo code. Please try again.",
        "add_promo": "Add Promo Code",
        "enter_promo_code": "Enter new promo code:",
        "enter_discount_type": "Select discount type:",
        "discount_fixed": "Fixed Amount",
        "discount_percent": "Percentage",
        "enter_discount_value": "Enter discount value ({type}):",
        "promo_added": "Promo code '{code}' added successfully! Discount: {value} ({type})",
        "promo_exists": "This promo code already exists. Try a different code.",
        "select_payment": "Select payment method:",
        "pay_cash": "Cash",
        "pay_card": "By Card",
        "cancel_button": "Cancel",
    },
    "rus": {
        "enter_name": "Пожалуйста, введите ваше имя:",
        "name_empty": "Имя не может быть пустым. Пожалуйста, введите ваше имя:",
        "send_phone": "Пожалуйста, отправьте ваш номер телефона:",
        "use_button": "Пожалуйста, используйте кнопку!",
        "reg_complete": "Регистрация завершена!\nИмя: {name}\nТелефон: {phone}",
        "order_prompt": "Нажмите кнопку, чтобы начать заказ:",
        "no_stores": "Поблизости магазинов не найдено.",
        "no_products": "В {store} нет доступных товаров. Попробуйте позже или свяжитесь с поддержкой.",
        "select_category": "Ближайший магазин: {store}\nВыберите категорию:",
        "no_brands": "В {store} нет брендов для {category}.",
        "select_brand": "Категория: {category}\nВыберите бренд:",
        "no_products_brand": "Нет товаров для {brand} в {category} в {store}.",
        "select_product": "Бренд: {brand}\nВыберите товар:",
        "product_not_found": "Товар не найден. Попробуйте снова.",
        "added_to_cart": "Добавлено в корзину:\n{name}\nЦена: {price_uzs} UZS ({price_usd} USD)\nОписание: {description}",
        "no_categories": "В {store} нет категорий.",
        "cart_empty": "Ваша корзина пуста!",
        "order_summary": "Ваш заказ:\n{cart_text}\nИтого: {total_uzs} UZS ({total_usd} USD)\nСкидка: {discount} UZS\nВозраст: {age}\nОплата: {payment_method}\nДоставка через: {delivery_time} минут",
        "admin_no_perm": "У вас нет разрешения на выполнение этого действия!",
        "select_store": "Выберите магазин:",
        "enter_category": "Введите категорию товара:",
        "category_empty": "Категория не может быть пустой. Введите категорию:",
        "enter_brand": "Введите бренд товара:",
        "brand_empty": "Бренд не может быть пустым. Введите бренд:",
        "enter_name_prod": "Введите название товара:",
        "name_empty_prod": "Название товара не может быть пустым. Введите название:",
        "enter_price": "Введите цену товара (UZS):",
        "price_invalid": "Пожалуйста, введите корректную числовую цену!",
        "price_negative": "Цена должна быть положительной. Введите корректную цену:",
        "enter_description": "Введите описание товара:",
        "description_empty": "Описание не может быть пустым. Введите описание:",
        "enter_photo": "Отправьте фото товара (опционально, напишите /skip, если нет):",
        "product_added": "Товар {name} успешно добавлен!",
        "view_products": "Все товары:",
        "no_products_admin": "Товаров нет.",
        "enter_del_id": "Введите ID товара, который хотите удалить (см. ID в /view_products):",
        "id_invalid": "Пожалуйста, введите корректный числовой ID товара!",
        "id_not_found": "ID товара не найден. Проверьте ID и попробуйте снова.",
        "product_deleted": "Товар '{name}' (ID: {id}) успешно удален!",
        "enter_edit_id": "Введите ID товара, который хотите отредактировать (см. ID в /view_products):",
        "edit_field": "Редактирование товара ID {id}. Выберите поле для редактирования:",
        "enter_new_value": "Введите новое значение для {field}:",
        "value_empty": "Значение не может быть пустым. Введите новое значение:",
        "product_updated": "Товар ID {id} обновлен: {field} изменено на {value}",
        "skip": "/skip",
        "delivery_time_prompt": "Введите время доставки в минутах (например, 45):",
        "rate_delivery": "Оцените доставку:\nСвяжитесь с нами: {phone}",
        "order_button": "Заказать",
        "back_button": "Назад",
        "location_prompt": "Отправьте ваше местоположение:",
        "edit_button": "Редактировать",
        "delete_button": "Удалить",
        "enter_age": "Пожалуйста, введите ваш возраст:",
        "age_invalid": "Пожалуйста, введите корректный числовой возраст (например, 25):",
        "age_restricted": "Извините, только пользователи старше 18 могут покупать товары в этой категории.",
        "help_button": "Помощь",
        "settings_button": "Настройки",
        "help_text": "Этот бот помогает заказывать товары из ближайших магазинов.\nДля поддержки: {support}",
        "settings_prompt": "Что вы хотите изменить?",
        "change_name": "Изменить имя",
        "change_phone": "Изменить телефон",
        "change_language": "Изменить язык",
        "feedback_prompt": "В чем была проблема с доставкой? Пожалуйста, оставьте ваш комментарий:",
        "feedback_sent": "Спасибо за ваш отзыв! Мы будем работать над улучшением.",
        "outside_working_hours": "Извините, бот работает только с 08:00 до 00:00 (время Узбекистана). Попробуйте позже.",
        "apply_promo": "Применить промокод",
        "enter_promo": "Введите промокод:",
        "promo_applied": "Промокод применен! Скидка: {discount} UZS",
        "promo_invalid": "Неверный промокод. Попробуйте еще раз.",
        "add_promo": "Добавить промокод",
        "enter_promo_code": "Введите новый промокод:",
        "enter_discount_type": "Выберите тип скидки:",
        "discount_fixed": "Фиксированная сумма",
        "discount_percent": "Процент",
        "enter_discount_value": "Введите значение скидки ({type}):",
        "promo_added": "Промокод '{code}' успешно добавлен! Скидка: {value} ({type})",
        "promo_exists": "Этот промокод уже существует. Введите другой код.",
        "select_payment": "Выберите способ оплаты:",
        "pay_cash": "Наличными",
        "pay_card": "Картой",
        "cancel_button": "Отменить",
    }
}

# States
class RegisterState(StatesGroup):
    waiting_for_language = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_order = State()

class OrderState(StatesGroup):
    waiting_for_location = State()
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

def setup_db():
    conn = get_db_connection()
    c = conn.cursor()
    logging.info("Setting up database...")
    # ... (rest of the function)
    conn.commit()
    logging.info("Database setup completed.")
    conn.close()
    
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
    logging.debug("Users table created or already exists.")

    c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY,
            name TEXT,
            latitude REAL,
            longitude REAL
        )
    """)
    logging.debug("Stores table created or already exists.")

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
    logging.debug("Products table created or already exists.")

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
            delivery_time INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    logging.debug("Orders table created or already exists.")

    c.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount_type TEXT,
            discount_value REAL
        )
    """)
    
    # Commenting out the cards table creation since we're disabling card functionality
    """
    c.execute(
        CREATE TABLE IF NOT EXISTS cards (
            user_id INTEGER,
            card_number TEXT,
            expiry_date TEXT,
            cvc TEXT,
            phone TEXT,
            verified INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, card_number)
        )
    )
    """
    
    # Add missing columns if they don't exist
    try:
        c.execute("ALTER TABLE orders ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN discount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN promo_code TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT")
    except sqlite3.OperationalError:
        pass
    
    c.execute("INSERT OR IGNORE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (1, 'ЦУМ', 41.3111, 69.2797))
    c.execute("INSERT OR IGNORE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (2, 'Sergeli', 41.2595, 69.2231))
    logging.debug("Default stores inserted or already present.")

    # Insert default products if none exist
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('ЦУМ', 'Electronics', 'Samsung', 'Galaxy S23', 12699999, 'Latest smartphone'))
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('Sergeli', 'Clothing', 'Nike', 'Air Max', 1530350, 'Running shoes'))
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('Sergeli', 'Electronics', 'Apple', 'iPhone 14', 13999999, 'Latest iPhone model'))
        
    conn.commit()
    c.execute("SELECT store, category, name FROM products WHERE store = 'Sergeli'")
    products = c.fetchall()
    print("Products for Sergeli after setup:", products)
    conn.close()
    logging.debug("Database setup completed.")

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

def get_nearest_store(user_lat, user_lon):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, latitude, longitude FROM stores")
    stores = c.fetchall()
    conn.close()
    
    if not stores:
        return None
    
    nearest_store = None
    min_distance = float("inf")
    for store in stores:
        store_distance = geopy.distance.geodesic((user_lat, user_lon), (store['latitude'], store['longitude'])).km
        if store_distance < min_distance:
            min_distance = store_distance
            nearest_store = store['name']
    return nearest_store

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
    if discount_type == 'fixed':
        return discount_value
    elif discount_type == 'percent':
        return round(total_uzs * (discount_value / 100))
    return 0

async def auto_set_delivery_time(order_id: int, user_id: int, cart_text: str, total_uzs: float, discount: float, promo_code: str, payment_method: str, age: str, state: FSMContext):
    await asyncio.sleep(20)
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
                payment_method=payment_method,
                delivery_time=default_delivery_time
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]
            ])
            await bot.send_message(user_id, f"Admin didn't respond in time. Default delivery time set to 35 minutes.\n{order_message}", reply_markup=keyboard)
            for admin_id in ADMIN_ID:
                await bot.send_message(admin_id, f"Order #{order_id} auto-confirmed with 35-minute delivery due to no response.")
            logging.info(f"Order #{order_id} auto-confirmed with 35-minute delivery.")
        
        conn.close()
        await state.clear()
    except Exception as e:
        logging.error(f"Error in auto_set_delivery_time for order {order_id}: {e}")

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
        log_exception(e, "process_language")
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

@router.message(Command("order"))
async def order_command(message: Message, state: FSMContext):
    if not is_fully_registered(message.from_user.id):
        await message.answer("Please register first using /start")
        return
        
    lang = get_user_language(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="start_ordering"),
         InlineKeyboardButton(text=LANGUAGES[lang]["settings_button"], callback_data="settings")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["help_button"], callback_data="help")]
    ])
    await message.answer(LANGUAGES[lang]["order_prompt"], reply_markup=keyboard)
    await state.set_state(RegisterState.waiting_for_order)

@router.message(F.location, OrderState.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["outside_working_hours"], reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return

        user_lat, user_lon = message.location.latitude, message.location.longitude
        store = get_nearest_store(user_lat, user_lon)
        lang = get_user_language(message.from_user.id)
        
        if not store:
            await message.answer(LANGUAGES[lang]["no_stores"], reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
        
        await state.update_data(store=store, cart=[], user_id=message.from_user.id, latitude=user_lat, longitude=user_lon)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="order_start")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
        ])
        await message.answer(f"Nearest store: {store}", reply_markup=keyboard)
        await state.set_state(OrderState.selecting_action)
    except Exception as e:
        logging.error(f"Error in process_location: {e}")
        await message.answer("Something went wrong while processing your location.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

@router.callback_query(F.data == "order_start", OrderState.selecting_action)
async def start_ordering(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        store = user_data.get("store")
        lang = get_user_language(callback.from_user.id)
        
        if not store:
            await callback.message.edit_text("Store not found. Please restart with /order.")
            await state.clear()
            return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM products WHERE store = ?", (store,))
        categories = c.fetchall()
        conn.close()
        
        logging.debug(f"Categories for {store}: {[cat['category'] for cat in categories]}")
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
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
        ])
        await callback.message.edit_text(f"Nearest store: {store}", reply_markup=keyboard)
        await state.set_state(OrderState.selecting_action)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_action_from_category: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_main", OrderState.selecting_action)
async def back_to_main_from_action(callback: types.CallbackQuery, state: FSMContext):
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
        logging.error(f"Error in back_to_main_from_action: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("cat:"), OrderState.selecting_category)
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        store, category = parts[1], parts[2]
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
            
            logging.debug(f"Brands for {store}/{category}: {[b['brand'] for b in brands]}")
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
            await state.update_data(age=age)
        except ValueError:
            await message.answer(LANGUAGES[lang]["age_invalid"])
            return
        
        user_data = await state.get_data()
        store = user_data["store"]
        category = user_data["category"]
        
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
        await state.set_state(OrderState.selecting_brand)
    except Exception as e:
        logging.error(f"Error in process_age: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("brand:"), OrderState.selecting_brand)
async def process_brand(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        store, category, brand = parts[1], parts[2], parts[3]
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, price, description, image_url FROM products WHERE store = ? AND category = ? AND brand = ?", 
                  (store, category, brand))
        products = c.fetchall()
        conn.close()
        
        logging.debug(f"Products for {store}/{category}/{brand}: {[dict(p) for p in products]}")
        if not products:
            await callback.message.edit_text(LANGUAGES[lang]["no_products_brand"].format(store=store, category=category, brand=brand))
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{p['name']} - {p['price']} UZS", callback_data=f"prod:{store}:{category}:{brand}:{p['id']}")]
            for p in products
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
        await state.update_data(brand=brand)
        await state.set_state(OrderState.selecting_product)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_brand: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_category", OrderState.selecting_product)
async def back_to_category_from_product(callback: types.CallbackQuery, state: FSMContext):
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
        logging.error(f"Error in back_to_category_from_product: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("prod:"), OrderState.selecting_product)
async def process_product(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        store, category, brand, product_id = parts[1], parts[2], parts[3], parts[4]
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name, price, description, image_url FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()
        conn.close()
        
        if not product:
            await callback.message.edit_text(LANGUAGES[lang]["product_not_found"])
            await state.clear()
            return
        
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        cart.append({"id": product_id, "name": product["name"], "price": product["price"], "quantity": 1})
        await state.update_data(cart=cart)
        
        price_usd = convert_to_usd(product["price"])
        message_text = LANGUAGES[lang]["added_to_cart"].format(
            name=product["name"], price_uzs=product["price"], price_usd=price_usd, description=product["description"]
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 View Cart", callback_data="view_cart")],
            [InlineKeyboardButton(text="➕ Add More", callback_data=f"back_to_brand:{store}:{category}:{brand}")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]
        ])
        
        if product["image_url"]:
            await bot.send_photo(callback.from_user.id, photo=product["image_url"], caption=message_text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(message_text, reply_markup=keyboard)
        
        await state.set_state(OrderState.cart_management)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_product: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("back_to_brand:"), OrderState.cart_management)
async def back_to_brand(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        store, category, brand = parts[1], parts[2], parts[3]
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, price FROM products WHERE store = ? AND category = ? AND brand = ?", 
                  (store, category, brand))
        products = c.fetchall()
        conn.close()
        
        if not products:
            await callback.message.edit_text(LANGUAGES[lang]["no_products_brand"].format(store=store, category=category, brand=brand))
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{p['name']} - {p['price']} UZS", callback_data=f"prod:{store}:{category}:{brand}:{p['id']}")]
            for p in products
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_category")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_product)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_brand: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "view_cart", OrderState.cart_management)
async def view_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        lang = get_user_language(callback.from_user.id)
        
        if not cart:
            await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
            await state.clear()
            return
        
        cart_text = "\n".join([f"{item['name']} - {item['price']} UZS x {item['quantity']}" for item in cart])
        total_uzs = sum(item["price"] * item["quantity"] for item in cart)
        total_usd = convert_to_usd(total_uzs)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Checkout", callback_data="checkout")],
            [InlineKeyboardButton(text="➕ Add More", callback_data="back_to_category_from_cart")],
            [InlineKeyboardButton(text="🗑️ Clear Cart", callback_data="clear_cart")]
        ])
        
        await callback.message.edit_text(
            f"Your Cart:\n{cart_text}\n\nTotal: {total_uzs} UZS ({total_usd} USD)",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in view_cart: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_category_from_cart", OrderState.cart_management)
async def back_to_category_from_cart(callback: types.CallbackQuery, state: FSMContext):
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
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="view_cart")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_category"].format(store=store), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_category)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_category_from_cart: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "clear_cart", OrderState.cart_management)
async def clear_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        await state.update_data(cart=[])
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["order_button"], callback_data="order_start")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_main")]
        ])
        await callback.message.edit_text("Cart cleared!", reply_markup=keyboard)
        await state.set_state(OrderState.selecting_action)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in clear_cart: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "checkout", OrderState.cart_management)
async def checkout(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        lang = get_user_language(callback.from_user.id)
        
        if not cart:
            await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["pay_cash"], callback_data="payment:cash")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["pay_card"], callback_data="payment:card")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="view_cart")]
        ])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_payment"], reply_markup=keyboard)
        await state.set_state(OrderState.waiting_for_payment_method)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in checkout: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("payment:"), OrderState.waiting_for_payment_method)
async def process_payment_method(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_method = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        total_uzs = sum(item["price"] * item["quantity"] for item in cart)
        
        await state.update_data(payment_method=payment_method)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
            [InlineKeyboardButton(text="Continue without promo", callback_data="skip_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="checkout")]
        ])
        
        await callback.message.edit_text(
            f"Total: {total_uzs} UZS\nPayment method: {payment_method}\nWould you like to apply a promo code?",
            reply_markup=keyboard
        )
        await state.set_state(OrderState.waiting_for_promo)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_payment_method: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "apply_promo", OrderState.waiting_for_promo)
async def prompt_promo_code(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["enter_promo"])
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in prompt_promo_code: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_promo)
async def apply_promo_code(message: Message, state: FSMContext):
    try:
        promo_code = message.text.strip()
        lang = get_user_language(message.from_user.id)
        user_data = await state.get_data()
        total_uzs = sum(item["price"] * item["quantity"] for item in user_data.get("cart", []))
        
        discount = calculate_discount(total_uzs, promo_code)
        if discount == 0:
            await message.answer(LANGUAGES[lang]["promo_invalid"])
            return
        
        await state.update_data(promo_code=promo_code, discount=discount)
        await message.answer(LANGUAGES[lang]["promo_applied"].format(discount=discount))
        
        await finalize_order(message, state)
    except Exception as e:
        logging.error(f"Error in apply_promo_code: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "skip_promo", OrderState.waiting_for_promo)
async def skip_promo(callback: types.CallbackQuery, state: FSMContext):
    try:
        await state.update_data(promo_code=None, discount=0)
        await finalize_order(callback.message, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in skip_promo: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

async def finalize_order(message_or_callback: Message | types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        user_id = user_data.get("user_id")
        lang = get_user_language(user_id)
        total_uzs = sum(item["price"] * item["quantity"] for item in cart)
        discount = user_data.get("discount", 0)
        promo_code = user_data.get("promo_code")
        payment_method = user_data.get("payment_method")
        age = user_data.get("age", "N/A")
        latitude = user_data.get("latitude")
        longitude = user_data.get("longitude")
        
        cart_text = "\n".join([f"{item['name']} - {item['price']} UZS x {item['quantity']}" for item in cart])
        total_usd = convert_to_usd(total_uzs)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO orders (user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, latitude, longitude))
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        
        for admin_id in ADMIN_ID:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Set Delivery Time", callback_data=f"set_delivery:{order_id}")]
            ])
            await bot.send_message(admin_id, f"New Order #{order_id}:\n{cart_text}\nTotal: {total_uzs} UZS\nDiscount: {discount} UZS", reply_markup=keyboard)
        
        await bot.send_message(user_id, f"Order #{order_id} placed! Waiting for admin to set delivery time.")
        
        asyncio.create_task(auto_set_delivery_time(order_id, user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, state))
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer("Order processing...")
        else:
            await message_or_callback.edit_text("Order processing...")
    except Exception as e:
        logging.error(f"Error in finalize_order: {e}")
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer("Something went wrong. Please try again.")
        else:
            await message_or_callback.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("set_delivery:"), OrderState.waiting_for_delivery_time)
async def prompt_delivery_time(callback: types.CallbackQuery, state: FSMContext):
    try:
        if callback.from_user.id not in ADMIN_ID:
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["admin_no_perm"])
            await callback.answer()
            return
        
        order_id = callback.data.split(":")[1]
        await state.update_data(order_id=order_id)
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["delivery_time_prompt"])
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in prompt_delivery_time: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_delivery_time)
async def set_delivery_time(message: Message, state: FSMContext):
    try:
        if message.from_user.id not in ADMIN_ID:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["admin_no_perm"])
            return
        
        user_data = await state.get_data()
        order_id = user_data.get("order_id")
        lang = get_user_language(message.from_user.id)
        
        try:
            delivery_time = int(message.text.strip())
            if delivery_time <= 0:
                raise ValueError("Delivery time must be positive")
        except ValueError:
            await message.answer("Please enter a valid number of minutes (e.g., 45)")
            return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT user_id, cart_text, total_uzs, discount, promo_code, payment_method, age FROM orders WHERE id = ?", (order_id,))
        order = c.fetchone()
        if not order:
            await message.answer("Order not found.")
            await state.clear()
            return
        
        c.execute("UPDATE orders SET delivery_time = ?, status = 'confirmed' WHERE id = ?", (delivery_time, order_id))
        conn.commit()
        conn.close()
        
        total_usd = convert_to_usd(order["total_uzs"])
        order_message = LANGUAGES[lang]["order_summary"].format(
            cart_text=order["cart_text"],
            total_uzs=order["total_uzs"],
            total_usd=total_usd,
            discount=order["discount"],
            age=order["age"],
            payment_method=order["payment_method"],
            delivery_time=delivery_time
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]
        ])
        await bot.send_message(order["user_id"], order_message, reply_markup=keyboard)
        await message.answer(f"Delivery time for Order #{order_id} set to {delivery_time} minutes.")
        await state.clear()
    except Exception as e:
        logging.error(f"Error in set_delivery_time: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("rate_delivery:"))
async def rate_delivery(callback: types.CallbackQuery, state: FSMContext):
    try:
        order_id = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👍 Good", callback_data=f"feedback:{order_id}:good")],
            [InlineKeyboardButton(text="👎 Bad", callback_data=f"feedback:{order_id}:bad")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["rate_delivery"].format(phone=PHONE_NUMBER), reply_markup=keyboard)
        await state.set_state(OrderState.waiting_for_feedback)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in rate_delivery: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("feedback:"))
async def process_feedback(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        order_id, feedback = parts[1], parts[2]
        lang = get_user_language(callback.from_user.id)
        
        if feedback == "bad":
            await callback.message.edit_text(LANGUAGES[lang]["feedback_prompt"])
            await state.update_data(order_id=order_id)
        else:
            await callback.message.edit_text(LANGUAGES[lang]["feedback_sent"])
            for admin_id in ADMIN_ID:
                await bot.send_message(admin_id, f"Order #{order_id} rated as Good!")
            await state.clear()
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_feedback: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_feedback)
async def save_feedback(message: Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        order_id = user_data.get("order_id")
        lang = get_user_language(message.from_user.id)
        
        for admin_id in ADMIN_ID:
            await bot.send_message(admin_id, f"Order #{order_id} rated as Bad!\nFeedback: {message.text}")
        await message.answer(LANGUAGES[lang]["feedback_sent"])
        await state.clear()
    except Exception as e:
        logging.error(f"Error in save_feedback: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("add_product"))
async def add_product_start(message: Message, state: FSMContext):
    try:
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
            [InlineKeyboardButton(text=store["name"], callback_data=f"store:{store['name']}")]
            for store in stores
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["cancel_button"], callback_data="cancel_admin")]])
        
        await message.answer(LANGUAGES[lang]["select_store"], reply_markup=keyboard)
        await state.set_state(AddProductState.waiting_for_store)
    except Exception as e:
        logging.error(f"Error in add_product_start: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("store:"), AddProductState.waiting_for_store)
async def process_store(callback: types.CallbackQuery, state: FSMContext):
    try:
        store = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        await state.update_data(store=store)
        await callback.message.edit_text(LANGUAGES[lang]["enter_category"])
        await state.set_state(AddProductState.waiting_for_category)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_store: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_category)
async def process_category_input(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        if not message.text or not message.text.strip():
            await message.answer(LANGUAGES[lang]["category_empty"])
            return
        await state.update_data(category=message.text.strip())
        await message.answer(LANGUAGES[lang]["enter_brand"])
        await state.set_state(AddProductState.waiting_for_brand)
    except Exception as e:
        logging.error(f"Error in process_category_input: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_brand)
async def process_brand_input(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        if not message.text or not message.text.strip():
            await message.answer(LANGUAGES[lang]["brand_empty"])
            return
        await state.update_data(brand=message.text.strip())
        await message.answer(LANGUAGES[lang]["enter_name_prod"])
        await state.set_state(AddProductState.waiting_for_product_name)
    except Exception as e:
        logging.error(f"Error in process_brand_input: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_product_name)
async def process_product_name(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        if not message.text or not message.text.strip():
            await message.answer(LANGUAGES[lang]["name_empty_prod"])
            return
        await state.update_data(name=message.text.strip())
        await message.answer(LANGUAGES[lang]["enter_price"])
        await state.set_state(AddProductState.waiting_for_product_price)
    except Exception as e:
        logging.error(f"Error in process_product_name: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_product_price)
async def process_product_price(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            price = float(message.text.strip())
            if price < 0:
                await message.answer(LANGUAGES[lang]["price_negative"])
                return
        except ValueError:
            await message.answer(LANGUAGES[lang]["price_invalid"])
            return
        await state.update_data(price=price)
        await message.answer(LANGUAGES[lang]["enter_description"])
        await state.set_state(AddProductState.waiting_for_product_description)
    except Exception as e:
        logging.error(f"Error in process_product_price: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_product_description)
async def process_product_description(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        if not message.text or not message.text.strip():
            await message.answer(LANGUAGES[lang]["description_empty"])
            return
        await state.update_data(description=message.text.strip())
        await message.answer(LANGUAGES[lang]["enter_photo"])
        await state.set_state(AddProductState.waiting_for_photo)
    except Exception as e:
        logging.error(f"Error in process_product_description: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddProductState.waiting_for_photo)
async def process_product_photo(message: Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        lang = get_user_language(message.from_user.id)
        
        image_url = None
        if message.text == "/skip":
            image_url = None
        elif message.photo:
            image_url = message.photo[-1].file_id
        else:
            await message.answer("Please send a photo or type /skip")
            return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO products (store, category, brand, name, price, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_data["store"], user_data["category"], user_data["brand"], 
              user_data["name"], user_data["price"], user_data["description"], image_url))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES[lang]["product_added"].format(name=user_data["name"]))
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_product_photo: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "cancel_admin")
async def cancel_admin_action(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text("Action cancelled.")
        await state.clear()
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in cancel_admin_action: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("view_products"))
async def view_products(message: Message, state: FSMContext):
    try:
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
        
        products_text = "\n".join([f"ID: {p['id']} | {p['store']} | {p['category']} | {p['brand']} | {p['name']} - {p['price']} UZS" 
                                 for p in products])
        await message.answer(f"{LANGUAGES[lang]['view_products']}\n{products_text}")
    except Exception as e:
        logging.error(f"Error in view_products: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("delete_product"))
async def delete_product_start(message: Message, state: FSMContext):
    try:
        if message.from_user.id not in ADMIN_ID:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["admin_no_perm"])
            return
        
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["enter_del_id"])
        await state.set_state(DeleteProductState.waiting_for_product_id)
    except Exception as e:
        logging.error(f"Error in delete_product_start: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(DeleteProductState.waiting_for_product_id)
async def process_delete_product(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            product_id = int(message.text.strip())
        except ValueError:
            await message.answer(LANGUAGES[lang]["id_invalid"])
            return
        
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
    except Exception as e:
        logging.error(f"Error in process_delete_product: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("edit_product"))
async def edit_product_start(message: Message, state: FSMContext):
    try:
        if message.from_user.id not in ADMIN_ID:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["admin_no_perm"])
            return
        
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["enter_edit_id"])
        await state.set_state(EditProductState.waiting_for_product_id)
    except Exception as e:
        logging.error(f"Error in edit_product_start: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(EditProductState.waiting_for_product_id)
async def process_edit_product_id(message: Message, state: FSMContext):
    try:
        lang = get_user_language(message.from_user.id)
        try:
            product_id = int(message.text.strip())
        except ValueError:
            await message.answer(LANGUAGES[lang]["id_invalid"])
            return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not c.fetchone():
            await message.answer(LANGUAGES[lang]["id_not_found"])
            conn.close()
            return
        conn.close()
        
        await state.update_data(product_id=product_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Name", callback_data="field:name")],
            [InlineKeyboardButton(text="Price", callback_data="field:price")],
            [InlineKeyboardButton(text="Description", callback_data="field:description")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["cancel_button"], callback_data="cancel_admin")]
        ])
        await message.answer(LANGUAGES[lang]["edit_field"].format(id=product_id), reply_markup=keyboard)
        await state.set_state(EditProductState.waiting_for_field)
    except Exception as e:
        logging.error(f"Error in process_edit_product_id: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("field:"), EditProductState.waiting_for_field)
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    try:
        field = callback.data.split(":")[1]
        lang = get_user_language(callback.from_user.id)
        await state.update_data(field=field)
        await callback.message.edit_text(LANGUAGES[lang]["enter_new_value"].format(field=field))
        await state.set_state(EditProductState.waiting_for_new_value)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_edit_field: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(EditProductState.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        product_id = user_data["product_id"]
        field = user_data["field"]
        lang = get_user_language(message.from_user.id)
        
        if not message.text or not message.text.strip():
            await message.answer(LANGUAGES[lang]["value_empty"])
            return
        
        value = message.text.strip()
        if field == "price":
            try:
                value = float(value)
                if value < 0:
                    await message.answer(LANGUAGES[lang]["price_negative"])
                    return
            except ValueError:
                await message.answer(LANGUAGES[lang]["price_invalid"])
                return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES[lang]["product_updated"].format(id=product_id, field=field, value=value))
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_new_value: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(Command("add_promo"))
async def add_promo_start(message: Message, state: FSMContext):
    try:
        if message.from_user.id not in ADMIN_ID:
            lang = get_user_language(message.from_user.id)
            await message.answer(LANGUAGES[lang]["admin_no_perm"])
            return
        
        lang = get_user_language(message.from_user.id)
        await message.answer(LANGUAGES[lang]["enter_promo_code"])
        await state.set_state(AddPromoState.waiting_for_code)
    except Exception as e:
        logging.error(f"Error in add_promo_start: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddPromoState.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    try:
        code = message.text.strip()
        lang = get_user_language(message.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT code FROM promo_codes WHERE code = ?", (code,))
        if c.fetchone():
            await message.answer(LANGUAGES[lang]["promo_exists"])
            conn.close()
            return
        conn.close()
        
        await state.update_data(code=code)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["discount_fixed"], callback_data="discount_type:fixed")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["discount_percent"], callback_data="discount_type:percent")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["cancel_button"], callback_data="cancel_admin")]
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
        await callback.message.edit_text(LANGUAGES[lang]["enter_discount_value"].format(type=discount_type))
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
            value = float(message.text.strip())
            if value <= 0:
                await message.answer("Discount value must be positive!")
                return
        except ValueError:
            await message.answer("Please enter a valid numeric value!")
            return
        
        user_data = await state.get_data()
        code = user_data["code"]
        discount_type = user_data["discount_type"]
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO promo_codes (code, discount_type, discount_value) VALUES (?, ?, ?)", 
                  (code, discount_type, value))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES[lang]["promo_added"].format(code=code, value=value, type=discount_type))
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_discount_value: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

# Main function to run the bot
async def main():
    setup_db()
    await dp.start_polling(bot)

import logging
logger = logging.getLogger(__name__)
def log_exception(e: Exception, context: str):
    logger.error(f"Error in {context}: {str(e)}", exc_info=True)
if __name__ == "__main__":
    asyncio.run(main())