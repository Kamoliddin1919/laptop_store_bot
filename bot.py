import time

from telebot import TeleBot
from telebot.types import LabeledPrice

from keyboards import generate_main_menu, generate_message_menu, generate_pagination
from db import PostgreSql

import os


token = os.environ.get("TOKEN")
click_token = os.environ.get("CLICK_TOKEN")

bot = TeleBot(token)
CATALOGS = {
    "💻Ноутбуки": "laptops"
}


@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    first_name = message.from_user.first_name
    bot.send_message(chat_id, f'Привет {first_name} !')
    choose_catalog(message)


def choose_catalog(message):
    chat_id = message.chat.id
    user_message = bot.send_message(chat_id, "Выберите каталог : ", reply_markup=generate_main_menu())
    bot.register_next_step_handler(user_message, show_products)


def search_catalog(name_catalog):
    return PostgreSql().select_data(name_catalog)


def show_products(message, product_id=0, products=None):
    chat_id = message.chat.id

    bot.delete_message(chat_id, message.id - 1)
    if message.text == "🔙На главную страницу":
        choose_catalog(message)
        return

    if message.text in CATALOGS.keys() and not products:
        name_catalog = CATALOGS[message.text]
        products = search_catalog(name_catalog)


    if message.text == "⏩Далее" and product_id < len(products):
        product_id += 1

    elif message.text == "⏪Назад" and product_id > 0:
        product_id -= 1

    product = products[product_id]

    brand_name = product[0]
    url = product[1]
    product_image = product[2]
    product_price = product[3]
    configurations = product[4]
    bot.send_message(chat_id, "Catalog product")
    bot.send_photo(chat_id, product_image, caption=f"💻Название продукта:  {brand_name}\n\n💵Стоимость продукта за месяц:  {product_price}\n\n📉Характеристики продукта:  {configurations}",
                   reply_markup=generate_message_menu(url))

    user_message = bot.send_message(chat_id, f"Продуктов на складе осталось : {len(products) - (product_id + 1)}", reply_markup=generate_pagination())

    if message.text == "⏩Далее" and len(products) - (product_id + 1) == 0:
        bot.send_message(chat_id, "На складе продуктов не осталось!")
        product_id -= len(products)

    bot.register_next_step_handler(user_message, show_products, product_id, products)


@bot.callback_query_handler(func=lambda call: True)
def get_callback_data(call):
    chat_id = call.message.chat.id
    if call.data == "buy":
        product_info = call.message.caption
        product_price = product_info[1]
        INVOICE = {
            "title": product_info[0],
            "description": product_info[2],
            "invoice_payload": "bot-defined invoice payload",
            "provider_token": click_token,
            "start_parameter": "pay",
            "currency": "UZS",
            "prices": [LabeledPrice(label=product_info[0], amount=int(product_price + "00"))],
        }

        bot.send_invoice(chat_id, **INVOICE)


@bot.pre_checkout_query_handler(func=lambda query: True)
def invoice_checkout(query):
    """ Проверка чека """
    bot.answer_pre_checkout_query(query.id, ok=True, error_message="Ошибка оплаты !")


@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message):
    """ Отправить сообщение о успешной оплате """
    bot.send_message(message.chat.id, "Оплата прошла успешно !")


while True:
    try:
        print("Бот запущен !")
        bot.polling(none_stop=True)
    except Exception as exp:
        print(f'Произошла ошибка {exp.__class__.__name__}: {exp}')
        bot.stop_polling()
        time.sleep(5)