import aiohttp
import asyncio
import logging
import time
import os
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from telethon import TelegramClient, errors
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonCopyright,
    InputReportReasonGeoIrrelevant,
    InputReportReasonFake,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails,
    InputReportReasonOther
)
from telethon.tl.functions.channels import JoinChannelRequest
from datetime import datetime, timedelta
import re

from config import api_id, api_hash, clients, bot_token, donate_url, admin_chat_id, CRYPTO_PAY_TOKEN, senders, receivers, smtp_servers
from proxies import proxies
from user_agents import user_agents
from emails import mail, phone_numbers
from telethon.tl.types import InputReportReasonOther

class InputReportReasonThreats:
    def __init__(self):
        self.reason = "threats"

class InputReportReasonInsults:
    def __init__(self):
        self.reason = "insults"

class InputReportReasonLinkSpam:
    def __init__(self):
        self.reason = "link_spam"
        
from telethon.tl.types import InputReportReasonOther

class InputReportReasonTerrorism:
    def __init__(self):
        self.reason = "terrorism"

class InputReportReasonNoViolationButDelete:
    def __init__(self):
        self.reason = "no_violation_but_delete"

class InputReportReasonDislike:
    def __init__(self):
        self.reason = "dislike"

class InputReportReasonPhishing:
    def __init__(self):
        self.reason = "phishing"        
        
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

script_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(script_dir, 'Session')
if not os.path.exists(session_dir):
    os.makedirs(session_dir)
# для прыватных чтобы нельза было снести 
private_users = {
    "ids": [6734328612, 6838685902],  # тут id
    "usernames": ["CTPAX_MAMOK", "TokioKiya1333"]  # тут user и без @ 
}

class ComplaintStates(StatesGroup):
    subject = State()
    body = State()
    photos = State()
    count = State()
    text_for_site = State()
    count_for_site = State()

class RestoreAccountStates(StatesGroup):
    phone = State()
    send_count = State()

class SupportStates(StatesGroup):
    message = State()

class CreateAccountStates(StatesGroup):
    client = State()
    phone = State()
    code = State()
    password = State()

class ReportStates(StatesGroup):
    message_link = State()
    reason = State()
    user_id = State()
    message_count = State()
    report_count = State()

banned_users_file = 'banned_users.txt'
class BanState(StatesGroup):
    waiting_for_ban_user_id = State()
    waiting_for_unban_user_id = State()
def load_banned_users():
    try:
        with open(banned_users_file, 'r') as file:
            return set(map(int, file.read().splitlines()))
    except FileNotFoundError:
        return set()
def save_banned_users(banned_users):
    with open(banned_users_file, 'w') as file:
        for user_id in banned_users:
            file.write(f'{user_id}\n')

banned_users = load_banned_users()
class SendMessage(StatesGroup):
    text = State()
    media_type = State()
    media = State()

async def write_user_data(user_id, first_name, last_name, username):
    if not os.path.exists('users.txt'):
        with open('users.txt', 'w', encoding='utf-8') as file:
            pass  
    with open('users.txt', 'a', encoding='utf-8') as file:
        file.write(f"{user_id} {first_name} {last_name} {username}\n")

async def is_user_in_file(user_id):
    if not os.path.exists('users.txt'):
        return False  
    with open('users.txt', 'r', encoding='utf-8') as file:
        for line in file:
            if str(user_id) in line:
                return True
    return False

CURRENCY_PRICES = {
    "1_day": {
        "TON": 1.5,
        "BTC": 0.0001,
        "ETH": 0.001,
        "USDT": 2.0,
        "BNB": 0.01,
        "LTC": 0.02,
        "DOGE": 50,
        "TRX": 10,
        "NOT": 2,
    },
    "2_days": {
        "TON": 2.5,
        "BTC": 0.0002,
        "ETH": 0.002,
        "USDT": 3.0,
        "BNB": 0.02,
        "LTC": 0.03,
        "DOGE": 75,
        "TRX": 15,
        "NOT": 3,
    },
    "5_days": {
        "TON": 5.0,
        "BTC": 0.0005,
        "ETH": 0.005,
        "USDT": 5.0,
        "BNB": 0.05,
        "LTC": 0.05,
        "DOGE": 100,
        "TRX": 20,
        "NOT": 5,
    },
    "30_days": {
        "TON": 10.0,
        "BTC": 0.001,
        "ETH": 0.01,
        "USDT": 10.0,
        "BNB": 0.1,
        "LTC": 0.1,
        "DOGE": 200,
        "TRX": 30,
        "NOT": 10,
    },
    "1_year": {
        "TON": 50.0,
        "BTC": 0.005,
        "ETH": 0.05,
        "USDT": 50.0,
        "BNB": 0.5,
        "LTC": 0.5,
        "DOGE": 500,
        "TRX": 100,
        "NOT": 50,
    },
}

async def check_payment(user_id):
    if not os.path.exists('paid_users.txt'):
        print("Файл paid_users.txt не существует.")
        return False
    
    with open('paid_users.txt', 'r') as file:
        lines = file.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        try:
            paid_user_id, expiry_time_str = line.split(',')
            if paid_user_id == str(user_id):
                expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%d %H:%M:%S')
                print(f"Найден пользователь {user_id}, время истечения: {expiry_time_str}, текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if expiry_time > datetime.now():
                    print("Подписка активна.")
                    return True
                else:
                    print("Подписка истекла.")
                    return False
        except ValueError as e:
            print(f"Ошибка при обработке строки '{line}': {e}")
            continue
    
    print(f"Пользователь {user_id} не найден в файле.")
    return False
    
from datetime import datetime, timedelta

async def save_paid_user(user_id, duration_days):
    expiry_time = datetime.now() + timedelta(days=duration_days)
    expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
    
    if not os.path.exists('paid_users.txt'):
        with open('paid_users.txt', 'w') as file:
            file.write(f"{user_id},{expiry_time_str}\n")
        return
    
    with open('paid_users.txt', 'r') as file:
        lines = file.readlines()
    
    updated = False
    updated_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        try:
            paid_user_id, paid_expiry_time_str = line.split(',')
            paid_expiry_time = datetime.strptime(paid_expiry_time_str, '%Y-%m-%d %H:%M:%S')
            if paid_user_id == str(user_id):
                if paid_expiry_time > datetime.now():
                    expiry_time += paid_expiry_time - datetime.now()
                    expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
                updated_lines.append(f"{paid_user_id},{expiry_time_str}\n")
                updated = True
            else:
                updated_lines.append(line + '\n')
        except ValueError as e:
            print(f"Ошибка при обработке строки '{line}': {e}")
            continue
    
    if not updated:
        updated_lines.append(f"{user_id},{expiry_time_str}\n")
    
    with open('paid_users.txt', 'w') as file:
        file.writelines(updated_lines)

async def update_time():
    if not os.path.exists('paid_users.txt'):
        return
    with open('paid_users.txt', 'r') as file:
        lines = file.readlines()
    updated_lines = []
    for line in lines:
        user_id, expiry_time_str = line.strip().split(',')
        expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%d %H:%M:%S')
        if expiry_time > datetime.now():
            expiry_time -= timedelta(seconds=1)
            expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
        updated_lines.append(f"{user_id},{expiry_time_str}\n")
    with open('paid_users.txt', 'w') as file:
        file.writelines(updated_lines)

async def check_and_notify():
    if not os.path.exists('paid_users.txt'):
        return
    with open('paid_users.txt', 'r') as file:
        lines = file.readlines()
    for line in lines:
        user_id, expiry_time_str = line.strip().split(',')
        expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%d %H:%M:%S')
        if expiry_time <= datetime.now():
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Купить время", callback_data="go_to_payment"))
            await bot.send_message(user_id, "⏳ Ваше время истекло. Пожалуйста, купите дополнительное время.", reply_markup=markup)

def create_invoice(asset, amount, description):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": asset,
        "amount": str(amount),
        "description": description,
        "payload": "custom_payload"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Ошибка при создании счета: {response.status_code} - {response.text}")
        return None

def check_invoice_status(invoice_id):
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN,
        "Content-Type": "application/json"
    }
    params = {"invoice_ids": invoice_id}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Ошибка при проверке статуса счета: {response.status_code} - {response.text}")
        return None

@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    
    if not os.path.exists('paid_users.txt'):
        with open('paid_users.txt', 'w') as file:
            pass

    if not await check_payment(user_id) and str(user_id) != admin_chat_id:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Перейти к оплате", callback_data="go_to_payment"))
        
        await message.reply_photo(
            photo=open('unnamed.jpg', 'rb'),
            caption="🚀 Чтобы получить доступ к боту, необходимо оплатить подписку. Нажмите кнопку ниже, чтобы перейти к оплате.",
            reply_markup=markup
        )
        return
    
    user = message.from_user
    first_name = user.first_name if user.first_name else ''
    last_name = user.last_name if user.last_name else ''
    username = f"@{user.username}" if user.username else f"id{user.id}"
    
    welcome_message = f"🎉 Добро пожаловать, {first_name} {last_name} {username} 🎉\nМы рады видеть вас здесь. Если у вас есть вопросы или нужна помощь, не стесняйтесь обращаться к поддержке!\n 📢Каналы📢\n- https://t.me/pylogg\n- https://t.me/pylogg\nНаписал бот: 👑 @CTPAX_MAMOK 👑"
    
    await send_menu(message.chat.id, welcome_message)

async def on_startup(dp):
    asyncio.create_task(start_timer())

async def send_menu(chat_id: int, welcome_message: str):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_support = InlineKeyboardButton('📢Написать поддержку📢', callback_data='support')
    btn_donate = InlineKeyboardButton('💳Донат💳', url=donate_url)
    btn_email_complaint = InlineKeyboardButton('📫Email-Снос📫', callback_data='email_complaint')
    btn_website_complaint = InlineKeyboardButton('💻Web-Снос💻', callback_data='website_complaint')
    btn_create_account = InlineKeyboardButton('🔑Создать session🔑', callback_data='create_account')
    btn_report_message = InlineKeyboardButton('🚨Ботнет-Снос🚨', callback_data='report_message')
    btn_spam_code = InlineKeyboardButton('🔥Спам-Снос🔥', callback_data='spam_code')
    btn_restore_account = InlineKeyboardButton('🔄Восстановить аккаунт🔄', callback_data='restore_account')
    btn_my_time = InlineKeyboardButton('⏳Моё время', callback_data='my_time')
    
    if str(chat_id) == admin_chat_id:
        btn_admin_panel = InlineKeyboardButton('🛠Админ панель🛠', callback_data='admin_panel')
        markup.add(btn_admin_panel)
    
    markup.add(btn_support, btn_donate, btn_email_complaint, btn_website_complaint, btn_create_account, btn_report_message, btn_spam_code, btn_restore_account, btn_my_time)
    
    await bot.send_photo(
        chat_id=chat_id,
        photo=open('welcome_photo.jpg', 'rb'),
        caption=welcome_message,
        reply_markup=markup
    )
    
@dp.callback_query_handler(lambda c: c.data == 'admin_panel', state='*')
async def admin_panel_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    markup = InlineKeyboardMarkup(row_width=2)
    btn_ban = InlineKeyboardButton('🚫 Бан', callback_data='ban_user')
    btn_unban = InlineKeyboardButton('🔓 Снять бан', callback_data='unban_user')
    btn_extract_users = InlineKeyboardButton('📥 Извлечь ID пользователей', callback_data='extract_users')
    btn_stats = InlineKeyboardButton('📊 Статистика', callback_data='stats')
    btn_send_message = InlineKeyboardButton('📨 Отправить сообщение', callback_data='send_message')
    btn_add_private = InlineKeyboardButton('➕ Добавить прывата', callback_data='add_private')
    btn_remove_private = InlineKeyboardButton('➖ Удалить прывата', callback_data='remove_private')
    btn_view_private = InlineKeyboardButton('👀 Кто под прыватом', callback_data='view_private')
    markup.add(btn_ban, btn_unban, btn_extract_users, btn_stats, btn_send_message, btn_add_private, btn_remove_private, btn_view_private)
    await callback_query.message.answer('👑 Админ панель:', reply_markup=markup)
    
@dp.callback_query_handler(lambda c: c.data == 'add_private', state='*')
async def add_private_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("➕ Введите ID или username пользователя для добавления в прыват:")
    await state.set_state("waiting_for_private_add")
    
@dp.message_handler(state="waiting_for_private_add")
async def process_add_private(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.isdigit():
        private_users["ids"].append(int(user_input))
    else:
        private_users["usernames"].append(user_input.lstrip('@'))
    await message.answer(f"✅ Пользователь {user_input} успешно добавлен в прыват.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'remove_private', state='*')
async def remove_private_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("➖ Введите ID или username пользователя для удаления из прывата:")
    await state.set_state("waiting_for_private_remove")

@dp.message_handler(state="waiting_for_private_remove")
async def process_remove_private(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input.isdigit():
        if int(user_input) in private_users["ids"]:
            private_users["ids"].remove(int(user_input))
            await message.answer(f"✅ Пользователь {user_input} успешно удален из прывата.")
        else:
            await message.answer(f"❌ Пользователь {user_input} не найден в прывате.")
    else:
        if user_input.lstrip('@') in private_users["usernames"]:
            private_users["usernames"].remove(user_input.lstrip('@'))
            await message.answer(f"✅ Пользователь {user_input} успешно удален из прывата.")
        else:
            await message.answer(f"❌ Пользователь {user_input} не найден в прывате.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'view_private', state='*')
async def view_private_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    users_list = "👥 Список пользователей под прыватом:\n"
    users_list += "🆔 IDs: " + ", ".join(map(str, private_users["ids"])) + "\n"
    users_list += "📛 Usernames: " + ", ".join(private_users["usernames"])
    await callback_query.message.answer(users_list)    

@dp.callback_query_handler(lambda c: c.data == 'extract_users', state='*')
async def extract_users_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    with open('users.txt', 'r', encoding='utf-8') as file:
        users_data = file.read()
    user_count = len(users_data.splitlines())
    document = types.InputFile('users.txt')
    await callback_query.message.answer_document(document)
    await callback_query.message.answer(f'📝В файле содержится {user_count} пользователей.')

@dp.callback_query_handler(lambda c: c.data == 'stats', state='*')
async def stats_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    with open('users.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
        total_users = len(lines)
        active_users = sum(1 for line in lines if 'id' not in line)
    await callback_query.message.answer(f'📊Статистика:\n\n👤Всего пользователей: {total_users}\n✅Активных пользователей: {active_users}')

@dp.callback_query_handler(lambda c: c.data == 'send_message', state='*')
async def send_message_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer('Введите текст сообщения:')
    await SendMessage.text.set()

@dp.message_handler(state=SendMessage.text)
async def process_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    markup = InlineKeyboardMarkup(row_width=2)
    btn_yes = InlineKeyboardButton('Да', callback_data='yes')
    btn_no = InlineKeyboardButton('Нет', callback_data='no')
    markup.add(btn_yes, btn_no)
    await message.answer('Хотите добавить фото или видео?', reply_markup=markup)
    await SendMessage.media_type.set()

@dp.callback_query_handler(lambda c: c.data in ['yes', 'no'], state=SendMessage.media_type)
async def process_media_type(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    async with state.proxy() as data:
        if callback_query.data == 'yes':
            await callback_query.message.answer('Отправьте фото или видео:')
            await SendMessage.media.set()
        else:
            await send_message_to_users(data['text'], None, None)
            await state.finish()
            await callback_query.message.answer('✅Сообщение отправлено всем пользователям.')

@dp.message_handler(content_types=['photo', 'video'], state=SendMessage.media)
async def process_media(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.photo:
            data['media_type'] = 'photo'
            data['media'] = message.photo[-1].file_id
        elif message.video:
            data['media_type'] = 'video'
            data['media'] = message.video.file_id
        await send_message_to_users(data['text'], data['media_type'], data['media'])
        await state.finish()
        await message.answer('✅Сообщение отправлено всем пользователям.')

async def send_message_to_users(text, media_type, media_id):
    with open('users.txt', 'r', encoding='utf-8') as file:
        for line in file:
            user_id = line.split()[0]
            try:
                if media_type == 'photo':
                    await bot.send_photo(user_id, media_id, caption=text)
                elif media_type == 'video':
                    await bot.send_video(user_id, media_id, caption=text)
                else:
                    await bot.send_message(user_id, text)
            except Exception as e:
                logging.error(f'Error sending message to user {user_id}: {e}')

@dp.callback_query_handler(lambda c: c.data == 'ban_user', state='*')
async def ban_user_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer('📝Введите ID пользователя, которого хотите забанить:')
    await BanState.waiting_for_ban_user_id.set()

@dp.message_handler(state=BanState.waiting_for_ban_user_id)
async def ban_user_input(message: types.Message, state: FSMContext):
    user_id = message.text
    if user_id.isdigit():
        user_id = int(user_id)
        if user_id in banned_users:
            await message.answer(f'🚫 Пользователь с ID {user_id} уже забанен.')
        else:
            banned_users.add(user_id)
            save_banned_users(banned_users)
            await message.answer(f'✅ Пользователь с ID {user_id} забанен.')
            try:
                await bot.send_message(user_id, '📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
            except Exception as e:
                logging.error(f'Error sending ban message to user {user_id}: {e}')
    else:
        await message.answer('❌ Неверный формат ID. Пожалуйста, введите числовой ID.')
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'unban_user', state='*')
async def unban_user_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer('📝Введите ID пользователя, которого хотите разбанить:')
    await BanState.waiting_for_unban_user_id.set()

@dp.message_handler(state=BanState.waiting_for_unban_user_id)
async def unban_user_input(message: types.Message, state: FSMContext):
    user_id = message.text
    if user_id.isdigit():
        user_id = int(user_id)
        if user_id not in banned_users:
            await message.answer(f'🚫 Пользователь с ID {user_id} не забанен.')
        else:
            banned_users.remove(user_id)
            save_banned_users(banned_users)
            await message.answer(f'✅ Пользователь с ID {user_id} разбанен.')
            try:
                await bot.send_message(user_id, '📢Ваш аккаунт был разбанен администратором📢')
            except Exception as e:
                logging.error(f'Error sending unban message to user {user_id}: {e}')
    else:
        await message.answer('❌ Неверный формат ID. Пожалуйста, введите числовой ID.')
    await state.finish()        

@dp.callback_query_handler(lambda c: c.data == "go_to_payment")
async def process_go_to_payment(callback_query: types.CallbackQuery):
    await callback_query.answer()
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1 день 🕐", callback_data="period_1_day"))
    markup.add(InlineKeyboardButton("2 дня 🕑", callback_data="period_2_days"))
    markup.add(InlineKeyboardButton("5 дней 🕔", callback_data="period_5_days"))
    markup.add(InlineKeyboardButton("30 дней 🗓️", callback_data="period_30_days"))
    markup.add(InlineKeyboardButton("1 год 📅", callback_data="period_1_year"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_start"))
    
    if callback_query.message.photo:
        await callback_query.message.edit_caption(
            caption="💸 *Выберите период доступа:* 💸",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        await callback_query.message.edit_text(
            text="💸 *Выберите период доступа:* 💸",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@dp.callback_query_handler(lambda c: c.data.startswith('period_'))
async def process_callback_period(callback_query: types.CallbackQuery):
    period = callback_query.data.split('_')[1] + "_" + callback_query.data.split('_')[2]
    keyboard = InlineKeyboardMarkup(row_width=2)
    for currency, price in CURRENCY_PRICES[period].items():
        keyboard.add(InlineKeyboardButton(f"{currency} 💳 ({price})", callback_data=f"pay_{period}_{currency}"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_periods"))
    
    await bot.answer_callback_query(callback_query.id)
    if callback_query.message.photo:
        await callback_query.message.edit_caption(
            caption=f"💸 *Выберите валюту для оплаты* ({period.replace('_', ' ')}) 💸",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await callback_query.message.edit_text(
            text=f"💸 *Выберите валюту для оплаты* ({period.replace('_', ' ')}) 💸",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def process_callback_currency(callback_query: types.CallbackQuery):
    parts = callback_query.data.split('_')
    period = parts[1] + "_" + parts[2]
    asset = parts[3]
    amount = CURRENCY_PRICES[period].get(asset, 0)
    duration_days = int(period.split('_')[0])  
    invoice = create_invoice(asset=asset, amount=amount, description=f"Оплата через CryptoBot на {duration_days} дней")
    
    if invoice and 'result' in invoice:
        invoice_id = invoice['result']['invoice_id']
        pay_url = invoice['result']['pay_url']
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💳 Оплатить", url=pay_url))
        markup.add(InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_{invoice_id}_{duration_days}"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_currencies_{period}"))
        
        await bot.answer_callback_query(callback_query.id)
        if callback_query.message.photo:
            await callback_query.message.edit_caption(
                caption="💸 *Оплатите по кнопке ниже и нажмите кнопку 'Проверить оплату'* 💸",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await callback_query.message.edit_text(
                text="💸 *Оплатите по кнопке ниже и нажмите кнопку 'Проверить оплату'* 💸",
                reply_markup=markup,
                parse_mode="Markdown"
            )
    else:
        await bot.answer_callback_query(callback_query.id, "❌ Ошибка при создании счета")

@dp.callback_query_handler(lambda c: c.data.startswith('back_to_'))
async def process_callback_back(callback_query: types.CallbackQuery):
    data = callback_query.data.split('_')
    if data[2] == "periods":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("1 день 🕐", callback_data="period_1_day"))
        markup.add(InlineKeyboardButton("2 дня 🕑", callback_data="period_2_days"))
        markup.add(InlineKeyboardButton("5 дней 🕔", callback_data="period_5_days"))
        markup.add(InlineKeyboardButton("30 дней 🗓️", callback_data="period_30_days"))
        markup.add(InlineKeyboardButton("1 год 📅", callback_data="period_1_year"))
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_start"))
        
        if callback_query.message.photo:
            await callback_query.message.edit_caption(
                caption="💸 *Выберите период доступа:* 💸",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await callback_query.message.edit_text(
                text="💸 *Выберите период доступа:* 💸",
                reply_markup=markup,
                parse_mode="Markdown"
            )
    elif data[2] == "currencies":
        period = data[3] + "_" + data[4]
        keyboard = InlineKeyboardMarkup(row_width=2)
        for currency, price in CURRENCY_PRICES[period].items():
            keyboard.add(InlineKeyboardButton(f"{currency} 💳 ({price})", callback_data=f"pay_{period}_{currency}"))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_periods"))
        
        await bot.answer_callback_query(callback_query.id)
        if callback_query.message.photo:
            await callback_query.message.edit_caption(
                caption=f"💸 *Выберите валюту для оплаты* ({period.replace('_', ' ')}) 💸",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await callback_query.message.edit_text(
                text=f"💸 *Выберите валюту для оплаты* ({period.replace('_', ' ')}) 💸",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    elif data[2] == "start":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Перейти к оплате", callback_data="go_to_payment"))
        
        if callback_query.message.photo:
            await callback_query.message.edit_caption(
                caption="🚀 Чтобы получить доступ к боту, необходимо оплатить подписку. Нажмите кнопку ниже, чтобы перейти к оплате.",
                reply_markup=markup
            )
        else:
            await callback_query.message.edit_text(
                text="🚀 Чтобы получить доступ к боту, необходимо оплатить подписку. Нажмите кнопку ниже, чтобы перейти к оплате.",
                reply_markup=markup
            )


import asyncio

@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def process_callback_check(callback_query: types.CallbackQuery):
    logging.info(f"Processing callback with data: {callback_query.data}")  
    parts = callback_query.data.split('_')
    if len(parts) != 3:
        logging.error(f"Invalid callback data format: {callback_query.data}")
        await bot.answer_callback_query(callback_query.id, "❌ Ошибка: неверный формат данных.")
        return

    invoice_id = parts[1]
    duration_days = int(parts[2])
    logging.info(f"Checking invoice status for ID: {invoice_id}")
    status = check_invoice_status(invoice_id)
    if status and 'result' in status:
        invoice_status = status['result']['items'][0]['status']
        logging.info(f"Invoice status: {invoice_status}")
        if invoice_status == 'paid':
            await save_paid_user(callback_query.from_user.id, duration_days)
            await bot.answer_callback_query(callback_query.id)
            await bot.send_message(callback_query.from_user.id, "✅ Оплата подтверждена! Теперь вы можете пользоваться ботом.",
                                  reply_markup=InlineKeyboardMarkup().add(
                                      InlineKeyboardButton("Запуск", callback_data="start")
                                  ))
        elif invoice_status == 'active':
            await bot.answer_callback_query(callback_query.id)
            msg = await bot.send_message(callback_query.from_user.id, "❌ Оплата еще не выполнена. Пожалуйста, оплатите чек и нажмите 'Проверить оплату' снова.")
            await asyncio.sleep(3)
            await bot.delete_message(callback_query.from_user.id, msg.message_id)
        elif invoice_status in ['expired', 'failed']:
            await bot.answer_callback_query(callback_query.id)
            msg = await bot.send_message(callback_query.from_user.id, "❌ Вы не оплатили чек. Пожалуйста, оплатите чек для начала.")
            await asyncio.sleep(3)
            await bot.delete_message(callback_query.from_user.id, msg.message_id)
    else:
        await bot.answer_callback_query(callback_query.id)
        msg = await bot.send_message(callback_query.from_user.id, "❌ Вы не оплатили чек. Пожалуйста, оплатите чек для начала.")
        await asyncio.sleep(3)
        await bot.delete_message(callback_query.from_user.id, msg.message_id)

async def save_paid_user(user_id, duration_days):
    expiry_time = datetime.now() + timedelta(days=duration_days)
    expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
    
    if not os.path.exists('paid_users.txt'):
        with open('paid_users.txt', 'w') as file:
            file.write(f"{user_id},{expiry_time_str}\n")
        return
    
    with open('paid_users.txt', 'r') as file:
        lines = file.readlines()
    
    updated = False
    updated_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        try:
            paid_user_id, paid_expiry_time_str = line.split(',')
            paid_expiry_time = datetime.strptime(paid_expiry_time_str, '%Y-%m-%d %H:%M:%S')
            if paid_user_id == str(user_id):
                if paid_expiry_time > datetime.now():
                    expiry_time += paid_expiry_time - datetime.now()
                    expiry_time_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
                updated_lines.append(f"{paid_user_id},{expiry_time_str}\n")
                updated = True
            else:
                updated_lines.append(line + '\n')
        except ValueError as e:
            print(f"Ошибка при обработке строки '{line}': {e}")
            continue
    
    if not updated:
        updated_lines.append(f"{user_id},{expiry_time_str}\n")
    
    with open('paid_users.txt', 'w') as file:
        file.writelines(updated_lines)

async def get_remaining_time(user_id):
    if str(user_id) == admin_chat_id:
        return "∞ (Администратор)"
    if not os.path.exists('paid_users.txt'):
        return "Нет доступа"
    with open('paid_users.txt', 'r') as file:
        lines = file.readlines()
        for line in lines:
            paid_user_id, expiry_time_str = line.strip().split(',')
            if paid_user_id == str(user_id):
                expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%d %H:%M:%S')
                remaining_time = expiry_time - datetime.now()
                if remaining_time.total_seconds() > 0:
                    days = remaining_time.days
                    hours, remainder = divmod(remaining_time.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    return f"{days} дней, {hours} часов, {minutes} минут, {seconds} секунд"
                else:
                    return "Время истекло"
    return "Нет доступа"

@dp.callback_query_handler(lambda c: c.data == 'my_time')
async def process_callback_my_time(callback_query: types.CallbackQuery):
    remaining_time = await get_remaining_time(callback_query.from_user.id)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"⏳ Ваше оставшееся время: {remaining_time}")

@dp.callback_query_handler(lambda call: True)
async def handle_callbacks(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id    
    if str(user_id) == admin_chat_id:
        pass
    else:
        if user_id in banned_users:
            await call.answer('🚨 Вы забанены администратором 🚨')
            return
        if call.data != 'pay' and not await check_payment(user_id):
            await call.answer('⏳ Ваше время доступа истекло. Пожалуйста, оплатите снова.')
            await call.message.answer(
                "⏳ Ваше время доступа истекло. Пожалуйста, оплатите снова.",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("Оплатить", callback_data="go_to_payment")  
                )
            )
            return
    
    if call.data == 'support':
        await call.message.answer('📝 Пожалуйста, напишите ваше сообщение для поддержки:')
        await SupportStates.message.set()
    elif call.data == 'email_complaint':
        await call.message.answer('📧 Введите тему письма:')
        await ComplaintStates.subject.set()
    elif call.data == 'website_complaint':
        await call.message.answer('🌐 Введите текст для отправки на сайт:')
        await ComplaintStates.text_for_site.set()
    elif call.data == 'create_account':
        await call.message.answer('📱 Введите ваш номер телефона:')
        await CreateAccountStates.phone.set()
    elif call.data == 'report_message':
        await call.message.answer('🔗 Введите ссылку на сообщение:')
        await ReportStates.message_link.set()
    elif call.data == 'spam_code':
        await call.message.answer('📞 Введите номер телефона и количество отправлений в формате: +79991234567 10')
        await SpamCodeStates.phone_and_count.set()
    elif call.data == 'restore_account':
        await call.message.answer('📱 Введите номер телефона для восстановления аккаунта:')
        await RestoreAccountStates.phone.set()
    elif call.data == 'go_to_payment':  
        await call.message.answer("ℹ️ Выберите способ оплаты:", reply_markup=payment_keyboard)
    await call.answer()

@dp.message_handler(state=RestoreAccountStates.phone)
async def process_restore_phone(message: types.Message, state: FSMContext):
    phone_number = message.text
    await state.update_data(phone_number=phone_number)
    await message.answer("📝Введите количество отправок:")
    await RestoreAccountStates.send_count.set()

@dp.message_handler(state=RestoreAccountStates.send_count)
async def process_send_count(message: types.Message, state: FSMContext):
    try:
        send_count = int(message.text)
        if send_count <= 0:
            raise ValueError("Количество отправок должно быть больше 0")
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}. Пожалуйста, введите корректное число.")
        return

    data = await state.get_data()
    phone_number = data.get("phone_number")
    target_email = "recover@telegram.org"
    subject = f"Banned phone number: {phone_number}"
    body = (
        f"I'm trying to use my mobile phone number: {phone_number}\n"
        "But Telegram says it's banned. Please help.\n\n"
        "App version: 11.4.3 (54732)\n"
        "OS version: SDK 33\n"
        "Device Name: samsungSM-A325F\n"
        "Locale: ru"
    )

    for _ in range(send_count):
        sender_email, sender_password = random.choice(list(senders.items()))
        success, result = await send_email(
            receiver=target_email,
            sender_email=sender_email,
            sender_password=sender_password,
            subject=subject,
            body=body
        )
        if success:
            await message.answer(f'✅ Письмо успешно отправлено на [{target_email}] от [{sender_email}]')
        else:
            await message.answer(f'❌ Ошибка при отправке письма на [{target_email}] от [{sender_email}]: {result}')
            break

    await state.finish()


@dp.message_handler(lambda message: ' ' in message.text)
async def process_spam_code_input(message: types.Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    try:
        phone_number, num_sendings = message.text.split()
        num_sendings = int(num_sendings)
        await send_code_requests(phone_number, num_sendings, message.chat.id)
    except ValueError:
        await message.reply('❌Неверный формат ввода. Используйте: +79991234567 10')

async def send_code_requests(phone_number, num_sendings, chat_id):
    for _ in range(num_sendings):
        client_data = random.choice(clients)     
        client = None
        try:
            client = TelegramClient(client_data["name"], client_data["api_id"], client_data["api_hash"])
            await client.connect()            
            await client.send_code_request(phone_number)
            await bot.send_message(chat_id, f"✅Код подтверждения отправлен через клиент {client_data['name']}✅")
        except Exception as e:
            await bot.send_message(chat_id, f"❌Ошибка при использовании клиента {client_data['name']}: {e}❌")
        finally:
            if client:
                await client.disconnect()
                client.session.delete()
        await asyncio.sleep(1)

async def send_site_requests(phone_number, num_sendings, chat_id):
    for _ in range(num_sendings):
        site = random.choice(sites)
        proxy = random.choice(proxies)
        user_agent = random.choice(user_agents)
        headers = {'User-Agent': user_agent}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(site, proxy=proxy, headers=headers) as response:
                    if response.status == 200:
                        await bot.send_message(chat_id, f"✅Код подтверждения отправлен через сайт {site} отправлен через прокси {proxy}✅")
                    else:
                        await bot.send_message(chat_id, f"❌Ошибка при отправке запроса на сайт {site}: {response.status}❌")
            except Exception as e:
                await bot.send_message(chat_id, f"❌Ошибка при отправке запроса на сайт {site}: {e}❌")
        await asyncio.sleep(1)

@dp.message_handler(lambda message: ' ' in message.text)
async def process_spam_code_input(message: types.Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    try:
        phone_number, num_sendings = message.text.split()
        num_sendings = int(num_sendings)
        await send_code_requests(phone_number, num_sendings, message.chat.id)
        await send_site_requests(phone_number, num_sendings, message.chat.id)
    except ValueError:
        await message.reply('❌Неверный формат ввода. Используйте: +79991234567 10')

@dp.message_handler(state=CreateAccountStates.phone)
async def process_phone_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    phone = message.text.replace('+', '') 
    if not phone or not phone.isdigit():
        await message.answer('❌ Введите корректный номер телефона.')
        return
    
    session_name = f"session_{phone}"
    session_path = os.path.join(session_dir, session_name)
    client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash)
    
    await client.connect()
    if not await client.is_user_authorized():
        try:
            result = await client.send_code_request(phone)
            phone_code_hash = result.phone_code_hash
            async with state.proxy() as data:
                data['phone'] = phone
                data['phone_code_hash'] = phone_code_hash
            await message.answer('📩 Введите код подтверждения:', reply_markup=create_code_keyboard())
            await CreateAccountStates.next()
        except errors.PhoneNumberInvalidError:
            await message.answer('❌ Неверный номер телефона. Пожалуйста, попробуйте еще раз.')
        finally:
            await client.disconnect()
    else:
        await message.answer('❌ Аккаунт уже авторизован.')
        await state.finish()
        await client.disconnect()

def create_code_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.row(
        InlineKeyboardButton("1", callback_data="code_1"),
        InlineKeyboardButton("2", callback_data="code_2"),
        InlineKeyboardButton("3", callback_data="code_3")
    )
    keyboard.row(
        InlineKeyboardButton("4", callback_data="code_4"),
        InlineKeyboardButton("5", callback_data="code_5"),
        InlineKeyboardButton("6", callback_data="code_6")
    )
    keyboard.row(
        InlineKeyboardButton("7", callback_data="code_7"),
        InlineKeyboardButton("8", callback_data="code_8"),
        InlineKeyboardButton("9", callback_data="code_9")
    )
    keyboard.row(
        InlineKeyboardButton("Очистить", callback_data="code_clear"),
        InlineKeyboardButton("0", callback_data="code_0"),
        InlineKeyboardButton("Подтвердить", callback_data="code_confirm")
    )
    return keyboard

@dp.callback_query_handler(lambda c: c.data.startswith('code_'), state=CreateAccountStates.code)
async def process_code_callback(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data.split('_')[1]
    async with state.proxy() as data:
        code = data.get('code', '')
        
        if action == 'clear':
            code = ''
        elif action == 'confirm':
            if len(code) == 5:
                data['code'] = code
                await bot.answer_callback_query(callback_query.id)
                await process_code_step(callback_query.message, state)
                return
            else:
                await bot.answer_callback_query(callback_query.id, text="Код должен состоять из 5 цифр.")
                return
        else:
            if len(code) < 5:
                code += action
        
        data['code'] = code
    
    await bot.edit_message_text(f'📩 Введите код подтверждения: {code}', callback_query.from_user.id, callback_query.message.message_id, reply_markup=create_code_keyboard())

@dp.message_handler(state=CreateAccountStates.code)
async def process_code_step(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        code = data.get('code', '')
    
    if not code or len(code) != 5:
        await message.answer('❌ Введите корректный код подтверждения.')
        return
    
    async with state.proxy() as data:
        phone = data['phone']
        phone_code_hash = data['phone_code_hash']
    session_name = f"session_{phone}"
    session_path = os.path.join(session_dir, session_name)
    client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash)
    
    await client.connect()
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
    except errors.SessionPasswordNeededError:
        await message.answer('🔒 Введите пароль от 2FA:')
        await CreateAccountStates.next()
    except Exception as e:
        await message.answer(f'❌ Ошибка при авторизации: {e}')
        await state.finish()
    else:
        await message.answer(f'✅ Аккаунт успешно создан и сохранен как {session_name}.session')
        await state.finish()
    finally:
        await client.disconnect()

@dp.message_handler(state=CreateAccountStates.password)
async def process_password_step(message: types.Message, state: FSMContext):
    password = message.text
    async with state.proxy() as data:
        phone = data['phone']
    session_name = f"session_{phone}"
    session_path = os.path.join(session_dir, session_name)
    client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash)
    
    await client.connect()
    try:
        await client.sign_in(password=password)
    except Exception as e:
        await message.answer(f'❌ Ошибка при авторизации: {e}')
    else:
        await message.answer(f'✅ Аккаунт успешно создан и сохранен как {session_name}.session')
    finally:
        await state.finish()
        await client.disconnect()

@dp.message_handler(state=ReportStates.message_link)
async def process_message_link_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    message_links = message.text.split()
    if not all(re.match(r'^https://t\.me/[^/]+/\d+(/\d+)?$|^https://t\.me/c/\d+/\d+$', link) for link in message_links):
        await message.answer('❌ Неверный формат ссылки на сообщение. Пожалуйста, введите ссылки в формате https://t.me/username/message_id или https://t.me/username/message_id/additional_info или https://t.me/c/channel_id/message_id')
        return
    
    async with state.proxy() as data:
        data['message_links'] = message_links
    
    session_files = [f for f in os.listdir(session_dir) if f.endswith('.session')]
    if not session_files:
        await message.answer('❌ Нет доступных сессий. Пожалуйста, создайте аккаунт сначала.')
        await state.finish()
        return
    
    client = TelegramClient(os.path.join(session_dir, session_files[0]), api_id=api_id, api_hash=api_hash)
    await client.connect()
    
    try:
        users_info = {}
        target_user_ids = set()

        for message_link in message_links:
            parts = message_link.split('/')
            if parts[3] == 'c':
                chat_id = int(f"-100{parts[4]}")
                message_id = int(parts[5])
            else:
                chat_username = parts[3]
                message_id = int(parts[4])
                chat = await client.get_entity(chat_username)
                await client(JoinChannelRequest(chat))
            
            target_message = await client.get_messages(chat_id if parts[3] == 'c' else chat, ids=message_id)
            if not target_message:
                await message.answer(f'❌ Сообщение по ссылке {message_link} не найдено. Пожалуйста, проверьте правильность ссылки.')
                continue
            
            user_id = target_message.sender_id
            user = await client.get_entity(user_id)
            user_info = f"@{user.username}" if user.username else f"ID: {user.id}"            
            if user.id in private_users["ids"] or (user.username and user.username in private_users["usernames"]):
                await message.answer(f'❌ Это приватный пользователь: {user_info}. Жалоба на него невозможна.')
                continue
            
            premium_status = "✅" if user.premium else "❌"
            is_bot = " Бот🤖" if user.bot else " Человек👤"
            
            chat_title = (await client.get_entity(chat_id if parts[3] == 'c' else chat)).title
            
            if user_info not in users_info:
                users_info[user_info] = {
                    "premium_status": premium_status,
                    "is_bot": is_bot,
                    "chat_title": chat_title,
                    "messages": []
                }
            
            message_type = target_message.media.__class__.__name__ if target_message.media else 'text'
            message_text = target_message.text if message_type == 'text' else f"{message_type.capitalize()}"
            
            users_info[user_info]["messages"].append(f"{message_text} (ID: {message_id})")
            target_user_ids.add(user_id)
        
        async with state.proxy() as data:
            data['target_user_ids'] = list(target_user_ids)
        
        report_message = ""
        for user_info, details in users_info.items():
            messages_text = "\n".join(details["messages"])
            report_message += (f"👤 Пользователь: {user_info}\n"
                               f"📄 Сообщение: {messages_text}\n"
                               f"✅ Робочих сессий: {len(session_files)}\n"
                               f"👑Премиум{details['premium_status']}\n"
                               f"👤/🤖: {details['is_bot']}\n"
                               f"👥 Группа: {details['chat_title']}\n\n")
        
        await message.answer(report_message.strip())
        
        markup = InlineKeyboardMarkup(row_width=2)
        btn_spam = InlineKeyboardButton('🚫 Спам', callback_data='reason_1')
        btn_violence = InlineKeyboardButton('🔪 Насилие', callback_data='reason_2')
        btn_child_abuse = InlineKeyboardButton('👶 Насилие над детьми', callback_data='reason_3')
        btn_pornography = InlineKeyboardButton('🔞 Порнография', callback_data='reason_4')
        btn_copyright = InlineKeyboardButton('©️ Нарушение авторских прав', callback_data='reason_5')
        btn_personal_details = InlineKeyboardButton('👤 Публикация личных данных', callback_data='reason_6')
        btn_other = InlineKeyboardButton('📝 Другое', callback_data='reason_7')
        btn_geo_irrelevant = InlineKeyboardButton('🌍 Геонерелевантный контент', callback_data='reason_8')
        btn_fake = InlineKeyboardButton('🎭 Фальшивка', callback_data='reason_9')
        btn_illegal_drugs = InlineKeyboardButton('💊 Незаконные наркотики', callback_data='reason_10')
        btn_threats = InlineKeyboardButton('🔪 Угрозы', callback_data='reason_11')
        btn_insults = InlineKeyboardButton('🤬 Оскорбления', callback_data='reason_12')
        btn_link_spam = InlineKeyboardButton('🔗 Спам ссылок', callback_data='reason_13')
        btn_terrorism = InlineKeyboardButton('💣 Терроризм', callback_data='reason_14')
        btn_no_violation_but_delete = InlineKeyboardButton('🗑 Нет нарушения, но удалить', callback_data='reason_15')
        btn_dislike = InlineKeyboardButton('👎 Не нравится', callback_data='reason_16')
        btn_phishing = InlineKeyboardButton('🎣 Фишинг', callback_data='reason_17')

        markup.add(btn_spam, btn_violence, btn_child_abuse, btn_pornography, btn_copyright, btn_personal_details, btn_other, btn_geo_irrelevant, btn_fake, btn_illegal_drugs, btn_threats, btn_insults, btn_link_spam, btn_terrorism, btn_no_violation_but_delete, btn_dislike, btn_phishing)
        
        await message.answer('🚨Выберите причину репорта:', reply_markup=markup)
        await ReportStates.next()
    except errors.FloodWaitError as e:
        await asyncio.sleep(e.seconds)
        await message.answer('❌ Ошибка при получении сообщений. Попробуйте позже.')
        await state.finish()
    except Exception as e:
        await message.answer('❌ Ошибка при получении сообщений.')
        await state.finish()
    finally:
        await client.disconnect()

@dp.callback_query_handler(lambda c: c.data.startswith('reason_'), state=ReportStates.reason)
async def process_reason_step(call: types.CallbackQuery, state: FSMContext):
    reason_code = call.data.split('_')[1]
    reason_mapping = {
        '1': 'spam',
        '2': 'violence',
        '3': 'child_abuse',
        '4': 'pornography',
        '5': 'copyright',
        '6': 'geo_irrelevant',
        '7': 'fake',
        '8': 'illegal_drugs',
        '9': 'personal_details',
        '10': 'other',
        '11': 'threats',  
        '12': 'insults',  
        '13': 'link_spam',  
        '14': 'terrorism',  
        '15': 'no_violation_but_delete',  
        '16': 'dislike',  
        '17': 'phishing'  
    }

    reason = reason_mapping.get(reason_code)
    if not reason:
        await call.message.answer('❌ Неверный код причины. Пожалуйста, выберите причину из списка.')
        return

    async with state.proxy() as data:
        data['reason'] = reason

    await call.message.answer('🚨Начинаем отправку репортов...🚨')
    
    await send_reports(call, call.message, state)

async def send_reports(call: types.CallbackQuery, message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        message_links = data['message_links']
        reason = data['reason']
    
    session_files = [f for f in os.listdir(session_dir) if f.endswith('.session')]
    if not session_files:
        await message.answer('❌ Нет доступных сессий. Пожалуйста, создайте аккаунт сначала.')
        await state.finish()
        return
    
    total_reports = 0
    failed_reports = 0
    session_count = 0
    target_user_ids = set()
    private_users_skipped = []  
    prev_total_reports = total_reports
    prev_failed_reports = failed_reports
    prev_session_count = session_count

    result_message = await message.answer(f"✅ Успешно отправлено репортов: {total_reports}\n"
                                          f"❌ Неудачно отправлено репортов: {failed_reports}\n"
                                          f"🔄 Отправлено с сессий: {session_count}")

    async def process_message_link(message_link, session_file):
        nonlocal total_reports, failed_reports
        parts = message_link.split('/')
        chat_username = parts[3]
        message_id = int(parts[4])
        
        session_name = session_file.replace('.session', '')
        client = TelegramClient(os.path.join(session_dir, session_file), api_id=api_id, api_hash=api_hash)
        
        try:
            await client.connect()

            if not await client.is_user_authorized():
                failed_reports += 1
                return

            try:
                chat = await client.get_entity(chat_username)
                target_message = await client.get_messages(chat, ids=message_id)
                if not target_message:
                    failed_reports += 1
                    return
                user = await client.get_entity(target_message.sender_id)
                if user.id in private_users["ids"] or (user.username and user.username in private_users["usernames"]):
                    private_users_skipped.append(f"❌ Это приватный пользователь: {user.username or user.id}. Репорт на него не отправлен.")
                    return
                
                await client(ReportRequest(
                    peer=chat,
                    id=[message_id],
                    option='',
                    message=''
                ))
                total_reports += 1
                target_user_ids.add(target_message.sender_id)
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                failed_reports += 1
            except errors.UsernameNotOccupiedError:
                failed_reports += 1
            except errors.ChatWriteForbiddenError:
                failed_reports += 1
            except Exception as e:
                failed_reports += 1
        finally:
            await client.disconnect()

    for session_file in session_files:
        for link in message_links:
            await process_message_link(link, session_file)
            if total_reports != prev_total_reports or failed_reports != prev_failed_reports or session_count != prev_session_count:
                try:
                    private_users_info = "\n".join(private_users_skipped) if private_users_skipped else ""
                    await result_message.edit_text(f"✅ Успешно отправлено репортов: {total_reports}\n"
                                                  f"❌ Неудачно отправлено репортов: {failed_reports}\n"
                                                  f"🔄 Отправлено с сессий: {session_count}\n"
                                                  f"{private_users_info}")
                    prev_total_reports = total_reports
                    prev_failed_reports = failed_reports
                    prev_session_count = session_count
                except exceptions.MessageNotModified:
                    pass  

        session_count += 1
        if total_reports != prev_total_reports or failed_reports != prev_failed_reports or session_count != prev_session_count:
            try:
                private_users_info = "\n".join(private_users_skipped) if private_users_skipped else ""
                await result_message.edit_text(f"✅ Успешно отправлено репортов: {total_reports}\n"
                                              f"❌ Неудачно отправлено репортов: {failed_reports}\n"
                                              f"🔄 Отправлено с сессий: {session_count}\n"
                                              f"{private_users_info}")
                prev_total_reports = total_reports
                prev_failed_reports = failed_reports
                prev_session_count = session_count
            except exceptions.MessageNotModified:
                pass  

    async with state.proxy() as data:
        data['target_user_ids'] = list(target_user_ids)
    try:
        private_users_info = "\n".join(private_users_skipped) if private_users_skipped else ""
        await result_message.edit_text(f"✅ Репорты отправлены: {total_reports} удачных с сессиями {session_count}\n"
                                      f"{private_users_info}")
    except exceptions.MessageNotModified:
        pass  
    async with state.proxy() as data:
        user_id = call.from_user.id
        target_user_ids = data.get('target_user_ids', [])
        tracking_list = load_tracking_list()

        new_accounts_added = 0  

        for target_user_id in target_user_ids:
            if target_user_id in private_users["ids"]:
                private_users_skipped.append(f'❌ Это приватный пользователь: ID {target_user_id}. Добавление в список отслеживания невозможно.')
                continue

            if target_user_id in tracking_list.get(user_id, []):
                await call.message.answer(f"🚨 Вы уже следите за аккаунтом {target_user_id}.")
            else:
                await add_to_tracking_list(user_id, target_user_id)
                await call.message.answer(f"✅ Вы начали следить за аккаунтом {target_user_id}.")
                new_accounts_added += 1

        if new_accounts_added > 0:
            await call.message.answer(f"✅ Вы начали следить за {new_accounts_added} аккаунтами.")
                        
async def add_to_tracking_list(user_id, target_user_id):
    tracking_list = load_tracking_list()
    if user_id not in tracking_list:
        tracking_list[user_id] = []
    if target_user_id not in tracking_list[user_id]:
        tracking_list[user_id].append(target_user_id)
        save_tracking_list(tracking_list)


def save_tracking_list(tracking_list):
    with open('tracking_list.txt', 'w') as file:
        for user_id, target_user_ids in tracking_list.items():
            file.write(f"{user_id}:{','.join(map(str, target_user_ids))}\n")


def load_tracking_list():
    try:
        with open('tracking_list.txt', 'r') as file:
            tracking_list = {}
            for line in file:
                user_id, target_user_ids = line.strip().split(':')
                tracking_list[int(user_id)] = [int(uid) for uid in target_user_ids.split(',')]
            return tracking_list
    except FileNotFoundError:
        with open('tracking_list.txt', 'w') as file:
            pass
        return {}
    except (ValueError, PermissionError, IsADirectoryError) as e:
        print(f"Error loading tracking list: {e}")
        return {}


async def notify_users_about_status():
    tracking_list = load_tracking_list()
    for user_id, target_user_ids in tracking_list.items():
        for target_user_id in target_user_ids:
            status, _ = await check_account_status(target_user_id)
            if status is False:
                await bot.send_message(user_id, f"✅ Аккаунт {target_user_id} был успешно удален.")
                tracking_list[user_id].remove(target_user_id)
                if not tracking_list[user_id]:
                    del tracking_list[user_id]
    save_tracking_list(tracking_list)


async def background_status_checker():
    while True:
        await notify_users_about_status()
        await asyncio.sleep(3600)


async def on_startup(dp):
    asyncio.create_task(background_status_checker())

@dp.message_handler(state=ComplaintStates.subject)
async def process_subject_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    async with state.proxy() as data:
        data['subject'] = message.text
    await message.answer('📝 Введите текст жалобы:')
    await ComplaintStates.next()

@dp.message_handler(state=ComplaintStates.body)
async def process_body_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    async with state.proxy() as data:
        data['body'] = message.text
    await message.answer('🖼 Хотите добавить фотографии? (Да/Нет):')
    await ComplaintStates.next()

@dp.message_handler(state=ComplaintStates.photos)
async def process_photo_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    add_photo = message.text.lower()
    if add_photo == 'да':
        await message.answer('📎 Пожалуйста, отправьте фотографии:')
        await ComplaintStates.next()
    elif add_photo == 'нет':
        await message.answer('🔢 Введите количество отправок (не больше 50):')
        await ComplaintStates.next()
    else:
        await message.answer('❌ Неверный ввод. Пожалуйста, ответьте "Да" или "Нет":')

@dp.message_handler(content_types=['photo'], state=ComplaintStates.photos)
async def process_photos_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    photos = []
    for photo in message.photo:
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        photos.append(downloaded_file)
    async with state.proxy() as data:
        data['photos'] = photos
    await message.answer('🔢 Введите количество отправок (не больше 50):')
    await ComplaintStates.next()

@dp.message_handler(state=ComplaintStates.count)
async def process_count_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    try:
        count = int(message.text)
        if count > 50:
            await message.answer('🚫 Количество отправок не должно превышать 50. Повторите ввод:')
            return
    except ValueError:
        await message.answer('🔢 Пожалуйста, введите число. Повторите ввод:')
        return
    
    async with state.proxy() as data:
        subject = data['subject']
        body = data['body']
        photos = data.get('photos')
    
    for word in body.split():
        if word.startswith('@') and word[1:] in private_users["usernames"]:
            await message.answer(f'❌ Это приватный пользователь: {word}. Жалоба на него невозможна.')
            return
        if word.isdigit() and int(word) in private_users["ids"]:
            await message.answer(f'❌ Это приватный пользователь: ID {word}. Жалоба на него невозможна.')
            return
    
    for _ in range(count):
        receiver = random.choice(receivers)
        sender_email, sender_password = random.choice(list(senders.items()))
        success, result_message = await send_email(receiver, sender_email, sender_password, subject, body, photos)
        if success:
            photo_status = 'с фотографией' if photos else 'без фотографии'
            await message.answer(f'✅ Письмо успешно отправлено на [{receiver}] от [{sender_email}]\nС текстом: {body}\nОтправитель: [{sender_email}]\n{photo_status}')
        else:
            await message.answer(result_message)
    
    await state.finish()
    
@dp.message_handler(state=ComplaintStates.text_for_site)
async def process_text_for_site_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    async with state.proxy() as data:
        data['text_for_site'] = message.text
    await message.answer('🔢 Введите количество отправок (не больше 50):')
    await ComplaintStates.next()

@dp.message_handler(state=ComplaintStates.count_for_site)
async def process_count_for_site_step(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    try:
        count = int(message.text)
        if count > 50:
            await message.answer('🚫 Количество отправок не должно превышать 50. Повторите ввод:')
            return
    except ValueError:
        await message.answer('🔢 Пожалуйста, введите число. Повторите ввод:')
        return
    
    async with state.proxy() as data:
        text = data['text_for_site']
    words = text.split()
    for word in words:
        if word.isdigit() and int(word) in private_users["ids"]:
            await message.answer('🚫 Нельзя отправлять жалобы на приватных пользователей.')
            await state.finish()
            return
        if word in private_users["usernames"]:
            await message.answer('🚫 Нельзя отправлять жалобы на приватных пользователей.')
            await state.finish()
            return
    
    for _ in range(count):
        email = random.choice(mail)
        phone = random.choice(phone_numbers)
        proxy = await get_working_proxy()
        if not proxy:
            await message.answer('❌ В данный момент отсутствуют работоспособные прокси для отправки.')
            break
        success = await send_to_site(text, email, phone, proxy)
        if success:
            await message.answer(f'✅ Жалоба отправлена: {text} 📨📮\nПочта [{email}] номер [{phone}]')
        else:
            await message.answer('❌ Ошибка при отправке жалобы.')
    
    await state.finish()

async def get_working_proxy():
    for proxy in proxies:
        try:
            response = requests.get('https://www.google.com', proxies=proxy, timeout=5)
            if response.status_code == 200:
                return proxy
        except Exception as e:
            logging.error(f'Proxy {proxy} is not working: {e}')
    return None

async def send_to_site(text, email, phone, proxy):
    url = "https://telegram.org/support"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": random.choice(user_agents)
    }
    data = {
        "message": text,
        "email": email,
        "phone": phone,
        "setln": "ru"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, proxies=proxy, timeout=10)
        if response.status_code == 200:
            logging.info(f'Data sent to site: {text}, email: {email}, phone: {phone}')
            return True
        else:
            logging.error(f'Error sending data to site: {response.status_code}')
            return False
    except Exception as e:
        logging.error(f'Error sending data to site: {e}')
        return False

@dp.message_handler(content_types=['text', 'photo', 'document', 'audio', 'voice', 'video', 'video_note'], state=SupportStates.message)
async def process_support_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer('📢Администратор посчитал ваш аккаунт подозрительным и вы были забанены📢')
        return
    
    username = message.from_user.username or f'id{user_id}'
    content_type = message.content_type
    text = message.text or message.caption

    if content_type == 'text':
        await bot.send_message(admin_chat_id, f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')
    elif content_type == 'photo':
        await bot.send_photo(admin_chat_id, message.photo[-1].file_id, caption=f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')
    elif content_type == 'document':
        await bot.send_document(admin_chat_id, message.document.file_id, caption=f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')
    elif content_type == 'audio':
        await bot.send_audio(admin_chat_id, message.audio.file_id, caption=f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')
    elif content_type == 'voice':
        await bot.send_voice(admin_chat_id, message.voice.file_id, caption=f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')
    elif content_type == 'video':
        await bot.send_video(admin_chat_id, message.video.file_id, caption=f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')
    elif content_type == 'video_note':
        await bot.send_video_note(admin_chat_id, message.video_note.file_id, caption=f'Сообщение от @{username} (ID: {user_id}):\n\n{text}')

    await message.answer('✅ Ваше сообщение отправлено в поддержку.')
    await state.finish()

import asyncio

async def check_and_clean_sessions():
    session_files = [f for f in os.listdir(session_dir) if f.endswith('.session')]
    for session_file in session_files:
        session_path = os.path.join(session_dir, session_file)
        client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logging.info(f"Сессия {session_file} не авторизована. Удаляем.")
                os.remove(session_path)
            else:
                user = await client.get_me()
                if isinstance(user, types.User) and hasattr(user, 'is_bot') and user.is_bot:
                    logging.info(f"Сессия {session_file} принадлежит боту. Удаляем.")
                    os.remove(session_path)
        except errors.AuthKeyDuplicatedError:
            logging.error(f"Сессия {session_file} была использована под разными IP-адресами. Удаляем.")
            os.remove(session_path)
        except errors.FloodWaitError as e:
            logging.warning(f"FloodWaitError для сессии {session_file}: {e}. Повтор через {e.seconds} секунд.")
            await asyncio.sleep(e.seconds)
        except errors.RPCError as e:
            if "database is locked" in str(e):
                logging.warning(f"База данных заблокирована для сессии {session_file}. Повтор через 5 секунд.")
                await asyncio.sleep(5)
                continue
            else:
                logging.error(f"Ошибка при проверке сессии {session_file}: {e}")
                os.remove(session_path)
        except Exception as e:
            logging.error(f"Ошибка при проверке сессии {session_file}: {e}")
            os.remove(session_path)
        finally:
            try:
                await client.disconnect()
            except Exception as e:
                if "disk I/O error" in str(e):
                    logging.error(f"Ошибка при отключении сессии {session_file}: {e}. Повтор через 5 секунд.")
                    await asyncio.sleep(5)
                    try:
                        await client.disconnect()
                    except Exception as e:
                        logging.error(f"Ошибка при повторном отключении сессии {session_file}: {e}")
                else:
                    logging.error(f"Ошибка при отключении сессии {session_file}: {e}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()    
    loop.run_until_complete(check_and_clean_sessions())
    executor.start_polling(dp, skip_updates=True)
    asyncio.set_event_loop(loop)
    loop.create_task(start_background_tasks())
    try:
        executor.start_polling(dp, skip_updates=True)
    finally:
        loop.close()
    
