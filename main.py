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

# Language dictionaries
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
        "enter_card_number": "Karta raqamingizni kiriting (XXXX XXXX XXXX XXXX):",
        "enter_card_expiry": "Karta amal qilish muddatini kiriting (MM/YY):",
        "enter_card_cvc": "Karta CVC kodini kiriting (3 raqam):",
        "enter_card_phone": "Karta bilan bog'liq telefon raqamini kiriting (+998XXXXXXXXX):",
        "card_verification_code": "Karta tasdiqlash kodi SMS orqali yuborildi. Kodni kiriting:",
        "card_verification_failed": "Tasdiqlash kodi noto'g'ri. Qaytadan urinib ko'ring.",
        "card_added": "Karta muvaffaqiyatli qo'shildi!",
        "card_failed": "Karta qo'shishda xatolik yuz berdi. Qaytadan urinib ko'ring.",
        "payment_success": "To'lov muvaffaqiyatli amalga oshirildi!",
        "payment_failed": "To'lov amalga oshmadi. Iltimos, qaytadan urinib ko'ring.",
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
        "enter_card_number": "Enter your card number (XXXX XXXX XXXX XXXX):",
        "enter_card_expiry": "Enter card expiry date (MM/YY):",
        "enter_card_cvc": "Enter card CVC code (3 digits):",
        "enter_card_phone": "Enter phone number linked to the card (+998XXXXXXXXX):",
        "card_verification_code": "A verification code has been sent to your phone. Enter the code:",
        "card_verification_failed": "Verification code is incorrect. Please try again.",
        "card_added": "Card added successfully!",
        "card_failed": "Failed to add card. Please try again.",
        "payment_success": "Payment successful!",
        "payment_failed": "Payment failed. Please try again.",
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
        "enter_card_number": "Введите номер карты (XXXX XXXX XXXX XXXX):",
        "enter_card_expiry": "Введите срок действия карты (MM/YY):",
        "enter_card_cvc": "Введите CVC код карты (3 цифры):",
        "enter_card_phone": "Введите номер телефона, связанный с картой (+998XXXXXXXXX):",
        "card_verification_code": "Код подтверждения отправлен на ваш телефон. Введите код:",
        "card_verification_failed": "Код подтверждения неверный. Попробуйте снова.",
        "card_added": "Карта успешно добавлена!",
        "card_failed": "Ошибка при добавлении карты. Попробуйте снова.",
        "payment_success": "Оплата успешно выполнена!",
        "payment_failed": "Оплата не удалась. Попробуйте снова.",
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
    waiting_for_card_number = State()
    waiting_for_card_expiry = State()
    waiting_for_card_cvc = State()
    waiting_for_card_phone = State()
    waiting_for_verification_code = State()
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
            delivery_time INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount_type TEXT,  -- 'fixed' or 'percent'
            discount_value REAL
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            user_id INTEGER,
            card_number TEXT,
            expiry_date TEXT,
            cvc TEXT,
            phone TEXT,
            verified INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, card_number)
        )
    """)
    
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
              (1, 'Store 1', 41.291848, 69.211190))
    c.execute("INSERT OR IGNORE INTO stores (id, name, latitude, longitude) VALUES (?, ?, ?, ?)", 
              (2, 'Store 2', 41.008238, 28.978359))
    
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (store, category, brand, name, price, description) VALUES (?, ?, ?, ?, ?, ?)",
                  ('Store 1', 'Electronics', 'Samsung', 'Galaxy S23', 12699999, 'Latest smartphone'))
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

def generate_verification_code():
    return str(random.randint(1000, 9999))

def send_verification_sms(phone, code):
    # This is a placeholder for SMS sending logic.
    # In a real application, integrate with an SMS gateway (e.g., Twilio, Nexmo)
    logging.info(f"Sending SMS to {phone}: Verification code is {code}")
    return True

def process_payment_paycom(amount, card_details):
    # This is a placeholder for Paycom payment processing
    # Replace with actual Paycom API integration
    try:
        # Example Paycom API call (simulated)
        payload = {
            "merchant_id": PAYCOM_MERCHANT_ID,
            "amount": int(amount),
            "card_number": card_details['card_number'].replace(" ", ""),
            "expiry_date": card_details['expiry_date'],
            "cvc": card_details['cvc'],
        }
        # Replace with actual API endpoint and headers
        response = {"status": "success"}  # Simulated response
        logging.info(f"Simulated Paycom API response: {response}")
        return response.get("status") == "success"
    except Exception as e:
        logging.error(f"Paycom payment error: {e}")
        return False

async def auto_set_delivery_time(order_id: int, user_id: int, cart_text: str, total_uzs: float, discount: float, promo_code: str, payment_method: str, age: str, state: FSMContext):
    await asyncio.sleep(20)  # Wait 20 seconds
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
            await bot.send_message(user_id, f"Admin didn’t respond in time. Default delivery time set to 35 minutes.\n{order_message}", reply_markup=keyboard)
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
        age = int(message.text.strip())
        if age < 18:
            await message.answer(LANGUAGES[lang]["age_restricted"])
            await state.clear()
            return
        
        user_data = await state.get_data()
        store = user_data.get("store")
        category = user_data.get("category")
        if not store or not category:
            raise ValueError("Store or category not found in state data")
        await state.update_data(age=age)
        
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
    except ValueError as ve:
        await message.answer(LANGUAGES[lang]["age_invalid"])
    except Exception as e:
        logging.error(f"Error in process_age: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("brand:"), OrderState.selecting_brand)
async def process_brand(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        if len(parts) != 4:
            raise ValueError("Invalid callback data format")
        _, store, category, brand = parts
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name, price FROM products WHERE store = ? AND category = ? AND brand = ?",
                  (store, category, brand))
        products = c.fetchall()
        conn.close()
        
        if not products:
            await callback.message.edit_text(LANGUAGES[lang]["no_products_brand"].format(brand=brand, category=category, store=store))
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{p['name']} - {p['price']} UZS ({convert_to_usd(p['price'])} USD)", 
                                  callback_data=f"add:{store}:{category}:{brand}:{p['name']}")]
            for p in products
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

@router.callback_query(F.data.startswith("add:"), OrderState.selecting_product)
async def add_to_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        if len(parts) != 5:
            raise ValueError("Invalid callback data format")
        _, store, category, brand, product_name = parts
        lang = get_user_language(callback.from_user.id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT price, description FROM products WHERE store = ? AND category = ? AND brand = ? AND name = ?",
                  (store, category, brand, product_name))
        product = c.fetchone()
        conn.close()
        
        if not product:
            await callback.message.edit_text(LANGUAGES[lang]["product_not_found"])
            await state.clear()
            return
        
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        cart.append({"store": store, "name": product_name, "price": product['price']})
        await state.update_data(cart=cart)
        logging.info(f"Cart updated: {cart}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
            [InlineKeyboardButton(text="🚀 Checkout", callback_data="proceed_to_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
        ])
        
        await callback.message.edit_text(
            LANGUAGES[lang]["added_to_cart"].format(
                name=product_name, 
                price_uzs=product['price'], 
                price_usd=convert_to_usd(product['price']), 
                description=product['description']
            ),
            reply_markup=keyboard
        )
        await state.set_state(OrderState.cart_management)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in add_to_cart: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_product", OrderState.cart_management)
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
        c.execute("SELECT name, price FROM products WHERE store = ? AND category = ? AND brand = ?",
                  (store, category, brand))
        products = c.fetchall()
        conn.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{p['name']} - {p['price']} UZS ({convert_to_usd(p['price'])} USD)", 
                                  callback_data=f"add:{store}:{category}:{brand}:{p['name']}")]
            for p in products
        ] + [[InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_brand")]])
        
        await callback.message.edit_text(LANGUAGES[lang]["select_product"].format(brand=brand), reply_markup=keyboard)
        await state.set_state(OrderState.selecting_product)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_product: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("more:"), OrderState.cart_management)
async def continue_shopping(callback: types.CallbackQuery, state: FSMContext):
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

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
    except Exception as e:
        logging.error(f"Error in continue_shopping: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "back_to_cart", OrderState.selecting_category)
async def back_to_cart(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        store = user_data.get("store")
        if not store:
            raise ValueError("Store not found in state data")
        lang = get_user_language(callback.from_user.id)
        
        if not cart:
            await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
            await state.clear()
            return
        
        cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
            [InlineKeyboardButton(text="🚀 Checkout", callback_data="checkout")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
        ])
        await callback.message.edit_text(f"Cart:\n{cart_text}", reply_markup=keyboard)
        await state.set_state(OrderState.cart_management)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in back_to_cart: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "apply_promo", OrderState.cart_management)
async def apply_promo_prompt(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        await callback.message.edit_text(LANGUAGES[lang]["enter_promo"])
        await state.set_state(OrderState.waiting_for_promo)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in apply_promo_prompt: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_promo)
async def process_promo_code(message: Message, state: FSMContext):
    try:
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
                [InlineKeyboardButton(text="🚀 Checkout", callback_data="select_payment")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
            ])
            await message.answer(f"Cart:\n{cart_text}", reply_markup=keyboard)
            await state.set_state(OrderState.cart_management)
            return

        await state.update_data(promo_code=promo_code, discount=discount)
        cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add more", callback_data=f"more:{store}")],
            [InlineKeyboardButton(text="🚀 Checkout", callback_data="select_payment")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_product")]
        ])
        await message.answer(LANGUAGES[lang]["promo_applied"].format(discount=discount))
        await message.answer(f"Cart:\n{cart_text}", reply_markup=keyboard)
        await state.set_state(OrderState.cart_management)
    except Exception as e:
        logging.error(f"Error in process_promo_code: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "select_payment", OrderState.cart_management)
async def select_payment_method(callback: types.CallbackQuery, state: FSMContext):
    try:
        lang = get_user_language(callback.from_user.id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES[lang]["pay_cash"], callback_data="payment_cash")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["pay_card"], callback_data="payment_card")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_cart")]
        ])
        await callback.message.edit_text(LANGUAGES[lang]["select_payment"], reply_markup=keyboard)
        await state.set_state(OrderState.waiting_for_payment_method)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in select_payment_method: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "payment_cash", OrderState.waiting_for_payment_method)
async def process_cash_payment(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    cart = user_data.get("cart", [])
    user_id = user_data["user_id"]
    age = user_data.get("age", "Not provided")
    latitude = user_data["latitude"]
    longitude = user_data["longitude"]
    store = user_data["store"]
    username = callback.from_user.username or "Not available"
    discount = user_data.get("discount", 0)
    promo_code = user_data.get("promo_code", None)
    lang = get_user_language(user_id)

    total_uzs = sum(item["price"] for item in cart)
    total_usd = convert_to_usd(total_uzs)
    cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, latitude, longitude, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, cart_text, total_uzs, discount, promo_code, "Cash", age, latitude, longitude, "pending")
    )
    order_id = c.lastrowid
    conn.commit()

    c.execute("SELECT name, phone FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()

    user_message = (
        f"Your order #{order_id}:\n"
        f"{cart_text}\n"
        f"Total: {total_uzs} UZS ({total_usd} USD)\n"
        f"Discount: {discount} UZS\n"
        f"Final Total: {total_uzs - discount} UZS"
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
        f"Please set delivery time within 20 seconds or default 35 minutes will be set."
    )
    for admin_id in ADMIN_ID:
        try:
            await bot.send_message(
                admin_id,
                admin_message,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Set Delivery Time", callback_data=f"set_delivery:{order_id}")]
                ])
            )
            await bot.send_location(admin_id, latitude=latitude, longitude=longitude)
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

    asyncio.create_task(auto_set_delivery_time(order_id, user_id, cart_text, total_uzs - discount, discount, promo_code, "Cash", age, state))
    await state.set_state(OrderState.waiting_for_delivery_time)
    await callback.answer()

@router.callback_query(F.data == "payment_card", OrderState.waiting_for_payment_method)
async def process_card_payment(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = get_user_language(user_id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT card_number FROM cards WHERE user_id = ? AND verified = 1", (user_id,))
        card = c.fetchone()
        conn.close()
        
        if card:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Use Existing Card", callback_data="use_existing_card")],
                [InlineKeyboardButton(text="Add New Card", callback_data="add_new_card")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="select_payment")]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Add New Card", callback_data="add_new_card")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="select_payment")]
            ])
        
        await callback.message.edit_text("Do you want to add a new card or use an existing one?", reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_card_payment: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "add_new_card", OrderState.waiting_for_payment_method)
async def add_card_number(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_language(callback.from_user.id)
    await callback.message.edit_text(LANGUAGES[lang]["enter_card_number"])
    await state.set_state(OrderState.waiting_for_card_number)
    await callback.answer()

@router.message(OrderState.waiting_for_card_number)
async def process_card_number(message: Message, state: FSMContext):
    card_number = message.text.strip()
    lang = get_user_language(message.from_user.id)
    if not card_number or len(card_number.replace(" ", "")) != 16 or not card_number.replace(" ", "").isdigit():
        await message.answer("Please enter a valid card number (16 digits).")
        return
    await state.update_data(card_number=card_number)
    await message.answer(LANGUAGES[lang]["enter_card_expiry"])
    await state.set_state(OrderState.waiting_for_card_expiry)

@router.message(OrderState.waiting_for_card_expiry)
async def process_card_expiry(message: Message, state: FSMContext):
    expiry_date = message.text.strip()
    lang = get_user_language(message.from_user.id)
    if not expiry_date or not expiry_date.match(r"^\d{2}/\d{2}$"):
        await message.answer("Please enter a valid expiry date (MM/YY).")
        return
    await state.update_data(expiry_date=expiry_date)
    await message.answer(LANGUAGES[lang]["enter_card_cvc"])
    await state.set_state(OrderState.waiting_for_card_cvc)

@router.message(OrderState.waiting_for_card_cvc)
async def process_card_cvc(message: Message, state: FSMContext):
    cvc = message.text.strip()
    lang = get_user_language(message.from_user.id)
    if not cvc or len(cvc) != 3 or not cvc.isdigit():
        await message.answer("Please enter a valid CVC code (3 digits).")
        return
    await state.update_data(cvc=cvc)
    await message.answer(LANGUAGES[lang]["enter_card_phone"])
    await state.set_state(OrderState.waiting_for_card_phone)

@router.message(OrderState.waiting_for_card_phone)
async def process_card_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    lang = get_user_language(message.from_user.id)
    if not phone or not phone.match(r"^\+998\d{9}$"):
        await message.answer("Please enter a valid phone number in the format +998XXXXXXXXX.")
        return
    
    verification_code = generate_verification_code()
    if send_verification_sms(phone, verification_code):
        await state.update_data(card_phone=phone, verification_code=verification_code)
        await message.answer(LANGUAGES[lang]["card_verification_code"])
        await state.set_state(OrderState.waiting_for_verification_code)
    else:
        await message.answer("Failed to send verification code. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_verification_code)
async def process_verification_code(message: Message, state: FSMContext):
    user_code = message.text.strip()
    data = await state.get_data()
    lang = get_user_language(message.from_user.id)
    if user_code != data.get("verification_code"):
        await message.answer(LANGUAGES[lang]["card_verification_failed"])
        return
    
    user_id = message.from_user.id
    card_number = data.get("card_number")
    expiry_date = data.get("expiry_date")
    cvc = data.get("cvc")
    phone = data.get("card_phone")
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO cards (user_id, card_number, expiry_date, cvc, phone, verified) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, card_number, expiry_date, cvc, phone, 1))
    conn.commit()
    conn.close()
    
    await message.answer(LANGUAGES[lang]["card_added"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Proceed with Payment", callback_data="use_existing_card")],
        [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="select_payment")]
    ])
    await message.answer("Do you want to proceed with this card?", reply_markup=keyboard)
    await state.set_state(OrderState.waiting_for_payment_method)

@router.callback_query(F.data == "use_existing_card", OrderState.waiting_for_payment_method)
async def use_existing_card(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        lang = get_user_language(user_id)
        
        conn = get_db_connection()
        c = conn.cursor()
        # Get user details first
        c.execute("SELECT name, phone FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        # Then get card details
        c.execute("SELECT card_number, expiry_date, cvc FROM cards WHERE user_id = ? AND verified = 1", (user_id,))
        card = c.fetchone()
        conn.close()
        
        if not card:
            await callback.message.edit_text("No verified card found. Please add a new card.")
            await callback.answer()
            return
        
        user_data = await state.get_data()
        cart = user_data.get("cart", [])
        age = user_data.get("age", "Not provided")
        latitude = user_data["latitude"]
        longitude = user_data["longitude"]
        store = user_data["store"]
        username = callback.from_user.username or "Not available"
        discount = user_data.get("discount", 0)
        promo_code = user_data.get("promo_code", None)

        total_uzs = sum(item["price"] for item in cart)
        total_usd = convert_to_usd(total_uzs)
        cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)

        # Process payment
        card_details = {"card_number": card["card_number"], "expiry_date": card["expiry_date"], "cvc": card["cvc"]}
        if process_payment_paycom(total_uzs - discount, card_details):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "INSERT INTO orders (user_id, cart_text, total_uzs, discount, promo_code, payment_method, age, latitude, longitude, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, cart_text, total_uzs, discount, promo_code, "Card", age, latitude, longitude, "pending")
            )
            order_id = c.lastrowid
            conn.commit()
            conn.close()
            
            await callback.message.edit_text(LANGUAGES[lang]["payment_success"])
            user_message = (
                f"Your order #{order_id}:\n"
                f"{cart_text}\n"
                f"Total: {total_uzs} UZS ({total_usd} USD)\n"
                f"Discount: {discount} UZS\n"
                f"Final Total: {total_uzs - discount} UZS\n"
                f"Payment: Card\n"
                f"Waiting for admin to set delivery time (20 seconds timeout)..."
            )
            await bot.send_message(user_id, user_message)

            admin_message = (
                f"New Order #{order_id} from {user['name']}:\n"
                f"Username: @{username}\n"
                f"Phone: {user['phone']}\n"
                f"Order Details:\n{cart_text}\n"
                f"Total: {total_uzs} UZS ({total_usd} USD)\n"
                f"Discount: {discount} UZS (Promo: {promo_code or 'None'})\n"
                f"Final Total: {total_uzs - discount} UZS\n"
                f"Age: {age}\n"
                f"Payment: Card\n"
                f"Please set delivery time within 20 seconds or default 35 minutes will be set."
            )
            for admin_id in ADMIN_ID:
                try:
                    await bot.send_message(
                        admin_id,
                        admin_message,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Set Delivery Time", callback_data=f"set_delivery:{order_id}")]
                        ])
                    )
                    await bot.send_location(admin_id, latitude=latitude, longitude=longitude)
                except Exception as e:
                    logging.error(f"Failed to notify admin {admin_id}: {e}")

            asyncio.create_task(auto_set_delivery_time(order_id, user_id, cart_text, total_uzs - discount, discount, promo_code, "Card", age, state))
            await state.set_state(OrderState.waiting_for_delivery_time)
        else:
            await callback.message.edit_text(LANGUAGES[lang]["payment_failed"])
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Try Again", callback_data="payment_card")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="select_payment")]
            ])
            await callback.message.edit_text("Payment failed. Try again?", reply_markup=keyboard)
        
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in use_existing_card: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data == "checkout", OrderState.cart_management)
async def checkout(callback: types.CallbackQuery, state: FSMContext):
    logging.info(f"Checkout triggered by user {callback.from_user.id}")
    try:
        if not is_within_working_hours():
            lang = get_user_language(callback.from_user.id)
            await callback.message.edit_text(LANGUAGES[lang]["outside_working_hours"])
            await callback.answer()
            return

        user_data = await state.get_data()
        logging.info(f"State data: {user_data}")
        
        required_keys = ["cart", "user_id", "latitude", "longitude", "store"]
        missing_keys = [key for key in required_keys if key not in user_data or user_data[key] is None]
        if missing_keys:
            logging.error(f"Missing state data: {missing_keys}")
            await callback.message.edit_text("Error: Incomplete order data. Please start over.")
            await state.clear()
            return

        cart = user_data["cart"]
        lang = get_user_language(callback.from_user.id)
        
        if not cart or not isinstance(cart, list) or len(cart) == 0:
            logging.warning(f"Cart is empty or invalid: {cart}")
            await callback.message.edit_text(LANGUAGES[lang]["cart_empty"])
            await state.clear()
            return

        cart_text = "\n".join(f"{item['name']} - {item['price']} UZS ({convert_to_usd(item['price'])} USD)" for item in cart)
        total_uzs = sum(item["price"] for item in cart)
        discount = user_data.get("discount", 0)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Proceed to Payment", callback_data="select_payment")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["apply_promo"], callback_data="apply_promo")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["back_button"], callback_data="back_to_cart")]
        ])
        await callback.message.edit_text(
            f"Cart:\n{cart_text}\nTotal: {total_uzs} UZS\nDiscount: {discount} UZS\nFinal Total: {total_uzs - discount} UZS",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in checkout: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("set_delivery:"), OrderState.waiting_for_delivery_time)
async def set_delivery_time(callback: types.CallbackQuery, state: FSMContext):
    try:
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
    except Exception as e:
        logging.error(f"Error in set_delivery_time: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_delivery_time)
async def process_delivery_time(message: Message, state: FSMContext):
    try:
        if message.from_user.id not in ADMIN_ID:
            await message.answer(LANGUAGES["eng"]["admin_no_perm"])
            return
        
        delivery_time = int(message.text.strip())
        if delivery_time <= 0:
            await message.answer("Delivery time must be positive. Please enter a valid time:")
            return
        
        data = await state.get_data()
        order_id = data.get("order_id")
        if not order_id:
            await message.answer("No order selected. Please try again.")
            await state.clear()
            return
        
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
            cart_text=cart_text,
            total_uzs=total_uzs,
            total_usd=total_usd,
            discount=discount,
            age=age,
            payment_method=payment_method,
            delivery_time=delivery_time
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Rate Delivery", callback_data=f"rate_delivery:{order_id}")]
        ])
        try:
            await bot.send_message(user_id, order_message, reply_markup=keyboard)
            await message.answer(f"Delivery time set for Order #{order_id} and sent to user!")
        except Exception as e:
            logging.error(f"Failed to send order confirmation to user {user_id}: {e}")
            await message.answer("Failed to notify user. They may have blocked the bot.")
        
        await state.clear()
    except ValueError:
        await message.answer("Please enter a valid numeric delivery time!")
    except Exception as e:
        logging.error(f"Error in process_delivery_time: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("rate_delivery:"))
async def rate_delivery(callback: types.CallbackQuery, state: FSMContext):
    try:
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
    except Exception as e:
        logging.error(f"Error in rate_delivery: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("rate:"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid callback data format")
        _, order_id, rating = parts
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
    except Exception as e:
        logging.error(f"Error in process_rating: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(OrderState.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    try:
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
    except Exception as e:
        logging.error(f"Error in process_feedback: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

# Admin handlers for products
@router.message(Command("add_product"))
async def add_product_command(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer(LANGUAGES["eng"]["admin_no_perm"])
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Store 1", callback_data="store:Store 1")],
        [InlineKeyboardButton(text="Store 2", callback_data="store:Store 2")]
    ])
    await message.answer(LANGUAGES["eng"]["select_store"], reply_markup=keyboard)
    await state.set_state(AddProductState.waiting_for_store)

@router.callback_query(F.data.startswith("store:"), AddProductState.waiting_for_store)
async def select_store(callback: types.CallbackQuery, state: FSMContext):
    try:
        store = callback.data.split(":")[1]
        await state.update_data(store=store)
        await callback.message.edit_text(LANGUAGES["eng"]["enter_category"])
        await state.set_state(AddProductState.waiting_for_category)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in select_store: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

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
    try:
        data = await state.get_data()
        image_url = None
        if message.photo:
            image_url = message.photo[-1].file_id
        elif message.text.strip() != LANGUAGES["eng"]["skip"]:
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
    except Exception as e:
        logging.error(f"Error in process_product_photo: {e}")
        await message.answer("Something went wrong. Please try again.")
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
    try:
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
    except Exception as e:
        logging.error(f"Error in edit_product_callback: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("delete_product:"))
async def delete_product_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
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
    except Exception as e:
        logging.error(f"Error in delete_product_callback: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

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
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

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
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

@router.callback_query(F.data.startswith("field:"), EditProductState.waiting_for_field)
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, field = callback.data.split(":")
        await state.update_data(field=field)
        await callback.message.edit_text(LANGUAGES["eng"]["enter_new_value"].format(field=field))
        await state.set_state(EditProductState.waiting_for_new_value)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_edit_field: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(EditProductState.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        product_id = data.get("product_id")
        field = data.get("field")
        if not product_id or not field:
            raise ValueError("Product ID or field not found in state data")
        
        new_value = message.text.strip() if field != "image_url" else (message.photo[-1].file_id if message.photo else None)
        
        if not new_value and field != "image_url":
            await message.answer(LANGUAGES["eng"]["value_empty"])
            return
        elif field == "image_url" and not message.photo and message.text.strip() != LANGUAGES["eng"]["skip"]:
            await message.answer(LANGUAGES["eng"]["enter_photo"])
            return
        
        if field == "price":
            try:
                new_value = float(new_value)
                if new_value <= 0:
                    await message.answer(LANGUAGES["eng"]["price_negative"])
                    return
            except ValueError:
                await message.answer(LANGUAGES["eng"]["price_invalid"])
                return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (new_value, product_id))
        conn.commit()
        conn.close()
        
        await message.answer(LANGUAGES["eng"]["product_updated"].format(id=product_id, field=field, value=new_value))
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_new_value: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

# Admin handlers for promo codes
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
        await message.answer("Promo code cannot be empty. Please try again.")
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
        [InlineKeyboardButton(text=LANGUAGES["eng"]["discount_fixed"], callback_data="discount_type:fixed")],
        [InlineKeyboardButton(text=LANGUAGES["eng"]["discount_percent"], callback_data="discount_type:percent")]
    ])
    await message.answer(LANGUAGES["eng"]["enter_discount_type"], reply_markup=keyboard)
    await state.set_state(AddPromoState.waiting_for_discount_type)

@router.callback_query(F.data.startswith("discount_type:"), AddPromoState.waiting_for_discount_type)
async def process_discount_type(callback: types.CallbackQuery, state: FSMContext):
    try:
        discount_type = callback.data.split(":")[1]
        await state.update_data(discount_type=discount_type)
        display_type = "UZS" if discount_type == "fixed" else "%"
        await callback.message.edit_text(LANGUAGES["eng"]["enter_discount_value"].format(type=display_type))
        await state.set_state(AddPromoState.waiting_for_discount_value)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_discount_type: {e}")
        await callback.message.edit_text("Something went wrong. Please try again.")
        await state.clear()

@router.message(AddPromoState.waiting_for_discount_value)
async def process_discount_value(message: Message, state: FSMContext):
    try:
        discount_value = float(message.text.strip())
        if discount_value <= 0:
            await message.answer("Discount value must be positive. Please try again.")
            return
        
        data = await state.get_data()
        promo_code = data.get("promo_code")
        discount_type = data.get("discount_type")
        
        if discount_type == "percent" and discount_value > 100:
            await message.answer("Percentage discount cannot exceed 100%. Please try again.")
            return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO promo_codes (code, discount_type, discount_value) VALUES (?, ?, ?)",
                  (promo_code, discount_type, discount_value))
        conn.commit()
        conn.close()
        
        display_type = "UZS" if discount_type == "fixed" else "%"
        await message.answer(LANGUAGES["eng"]["promo_added"].format(code=promo_code, value=discount_value, type=display_type))
        await state.clear()
    except ValueError:
        await message.answer("Please enter a valid numeric value!")
    except Exception as e:
        logging.error(f"Error in process_discount_value: {e}")
        await message.answer("Something went wrong. Please try again.")
        await state.clear()

# FastAPI endpoint
@app.get("/products/{store}")
async def get_products(store: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT category, brand, name, price, description, image_url FROM products WHERE store = ?", (store,))
    products = [{"category": row[0], "brand": row[1], "name": row[2], "price_uzs": row[3], "price_usd": convert_to_usd(row[3]), "description": row[4], "image_url": row[5]}
                for row in c.fetchall()]
    conn.close()
    return products

# Main
async def main():
    setup_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Starting the bot application...")
    asyncio.run(main())
    print("Bot application has finished.")