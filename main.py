# pip install aiogram
# pip install python-dotenv

from aiogram import executor, Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, LabeledPrice
from keyboards import *
from dotenv import load_dotenv
import os
from database import *
from datetime import datetime

load_dotenv()
TOKEN = os.getenv('TOKEN')
PAYMENT = os.getenv('PAYMENT')
bot = Bot(TOKEN, parse_mode='HTML')

dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def command_start(message: Message):
    await message.answer(f'Здравствуйте <b>{message.from_user.full_name}</b>\nВас приветствует бот, Вкусный доставщик')
    await register_user(message)


async def register_user(message: Message):
    chat_id = message.chat.id
    full_name = message.from_user.full_name
    user = first_select_user(chat_id)
    if user:
        await message.answer('Авторизация прошла успешно')
        await show_main_menu(message)

    else:
        first_register_user(chat_id, full_name)
        await message.answer('Для регистраии нажмите на кнопку', reply_markup=send_phone_button())


@dp.message_handler(content_types=['contact'])
async def finish_register(message: Message):
    chat_id = message.chat.id
    phone = message.contact.phone_number
    update_user_to_finish_register(chat_id, phone)
    await create_cart_for_user(message)
    await message.answer('Регистарация прошла успешно')
    await show_main_menu(message)


async def create_cart_for_user(message: Message):
    chat_id = message.chat.id
    try:
        insert_to_cart(chat_id)
    except:
        pass


async def show_main_menu(message: Message):
    await message.answer('Выберите напровление', reply_markup=generate_main_menu())


# @dp.message_handler(regexp=r'✔ Сделать заказ')
@dp.message_handler(lambda message: '✔ Сделать заказ' in message.text)
async def make_order(message: Message):
    await message.answer('Выберите категорию: ', reply_markup=generate_category_menu())


@dp.callback_query_handler(lambda call: 'category' in call.data)
async def show_products(call: CallbackQuery):
    cha_id = call.message.chat.id
    message_id = call.message.message_id
    # category_1
    _, category_id = call.data.split('_')
    category_id = int(category_id)
    await bot.edit_message_text('Выберите продукт: ', cha_id, message_id,
                                reply_markup=generate_products_by_category(category_id))


@dp.callback_query_handler(lambda call: 'main_menu' in call.data)
async def return_to_main_menu(call: CallbackQuery):
    cha_id = call.message.chat.id
    message_id = call.message.message_id
    await bot.edit_message_text(chat_id=cha_id,
                                message_id=message_id,
                                text='Выберите категорию: ',
                                reply_markup=generate_category_menu()
                                )


@dp.callback_query_handler(lambda call: 'product' in call.data)
async def show_detail_product(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    _, product_id = call.data.split('_')
    product_id = int(product_id)

    product = get_product_detail(product_id)
    print(product)
    await bot.delete_message(chat_id, message_id)
    with open(product[-1], mode='rb') as img:
        await bot.send_photo(chat_id=chat_id,
                             photo=img,
                             caption=f'''{product[2]}

Ингридиенты: {product[4]}

Цена: {product[3]}''', reply_markup=generate_product_detail_menu(product_id=product_id, category_id=product[1]))


@dp.callback_query_handler(lambda call: 'back' in call.data)
async def return_to_category(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    _, category_id = call.data.split('_')
    await bot.delete_message(chat_id, message_id)
    await bot.send_message(chat_id, 'Выберите продукт: ', reply_markup=generate_products_by_category(category_id))


# Реализовать добавление товара в корзину, если он есть то заменить на то кол-во которое указали

@dp.callback_query_handler(lambda call: call.data.startswith('cart'))
async def add_product_cart(call: CallbackQuery):
    chat_id = call.message.chat.id
    _, product_id, quantity = call.data.split('_')  # cart_1_2
    product_id, quantity = int(product_id), int(quantity)

    cart_id = get_user_cart_id(chat_id)
    product = get_product_detail(product_id)
    final_price = product[3] * quantity

    if insert_or_update_cart_product(cart_id, product[2], quantity, final_price):
        await bot.answer_callback_query(call.id, 'Продукт успешно добавлен')
    else:
        await bot.answer_callback_query(call.id, 'Количество успешно изменено')


@dp.message_handler(regexp=r'🛒 Корзина')
async def show_cart(message: Message, edit_message: bool = False):
    chat_id = message.chat.id
    cart_id = get_user_cart_id(chat_id)

    try:
        update_total_product_total_price(cart_id)
    except Exception as e:
        print(e)
        await message.answer('Корзина не доступна. Обратитесь в тех поддержку')
        return

    cart_products = get_cart_products(cart_id)
    total_products, total_price = get_total_product_price(cart_id)

    text = 'Ваша карзина \n\n'
    i = 0
    for product_name, quantity, final_price in cart_products:
        i += 1
        text += f'''{i}. {product_name}
Количество: {quantity}
Общая стоимость: {final_price}\n\n'''

    text += f'''Общее количество продуктов: {0 if total_products is None else total_products}
Общая стоимость корзины: {0 if total_price is None else total_price}'''

    if edit_message:
        await bot.edit_message_text(text, chat_id, message.message_id, reply_markup=generate_cart_menu(cart_id))
    else:
        await bot.send_message(chat_id, text, reply_markup=generate_cart_menu(cart_id))


@dp.callback_query_handler(lambda call: 'delete' in call.data)
async def delete_cart_product(call: CallbackQuery):
    _, cart_product_id = call.data.split('_')
    message = call.message
    cart_product_id = int(cart_product_id)

    delete_cart_product_from(cart_product_id)

    await bot.answer_callback_query(call.id, text='Продукт успешно удалён')
    await show_cart(message, edit_message=True)


@dp.callback_query_handler(lambda call: 'order' in call.data)
async def create_order(call: CallbackQuery):
    chat_id = call.message.chat.id

    time_now = datetime.now().strftime('%H:%M')
    newdate = datetime.now().strftime('%d.%m.%Y')

    _, cart_id = call.data.split('_')
    cart_id = int(cart_id)

    cart_products = get_cart_products(cart_id)
    total_products, total_price = get_total_product_price(cart_id)

    save_order_total(cart_id, total_products, total_price, time_now, newdate)
    orders_total_id = orders_total_price_id(cart_id)

    text = 'Ваша заказ \n\n'
    i = 0

    for product_name, quantity, final_price in cart_products:
        i += 1
        text += f'''{i}. {product_name}
Количество: {quantity}
Общая стоимость: {final_price}\n\n'''
        save_order(orders_total_id, product_name, quantity, final_price)
    text += f'''Общее количество продуктов: {0 if total_products is None else total_products}
Общая стоимость корзины: {0 if total_price is None else total_price}'''


    await bot.send_invoice(
        chat_id=chat_id,
        title=f'Заказ №{cart_id}',
        description=text,
        payload='bot-defined invoice payload',
        provider_token=PAYMENT,
        currency='UZS',
        prices=[
            LabeledPrice(label='Общая стоимость', amount=int(total_price*100)),
            LabeledPrice(label='Доставка', amount=1000000)
        ],
        start_parameter='start_parameter'
    )


@dp.pre_checkout_query_handler(lambda query: True)
async def checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True, error_message='Ошибка оплата не прошла')


@dp.message_handler(content_types=['successful_payment'])
async def get_payment(message: Message):
    chat_id = message.chat.id
    cart_id = get_user_cart_id(chat_id)
    await bot.send_message(chat_id, 'Ура оплата прошла успешно. Мы вас кинули на бабло')
    drop_cart_products_default(cart_id)


@dp.message_handler(lambda message: '📙 История' in message.text)
async def show_history_orders(message: Message):
    chat_id = message.chat.id
    cart_id = get_user_cart_id(chat_id)
    orders_total_price = get_orders_total_price(cart_id)
    print(orders_total_price)
    for i in orders_total_price:
        text = f'''Дата заказа: {i[-1]}
Время заказа: {i[-2]}
Общее кол-во товара: {i[3]}
Сумма щёта: {i[2]}\n\n'''
        detail_product = get_detail_product(i[0])
        for j in detail_product:
            text += f''' Продукт: {j[0]}
Количество: {j[1]}
Общая стоимость: {j[2]}\n\n'''
        await bot.send_message(chat_id, text)














executor.start_polling(dp)
