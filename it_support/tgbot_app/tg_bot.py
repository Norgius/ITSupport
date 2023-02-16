from typing import Callable

from django.db.models import Q
from django.db.transaction import atomic
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater
)
from telegram.error import TelegramError

from support_app.models import BotUser
from support_app.models import Contractor
from support_app.models import Client
from support_app.models import Manager
from support_app.models import Order

from telegram.utils import request


def get_user(func):
    def wrapper(update, context):
        chat_id = update.effective_chat.id
        username = update.effective_user.username

        try:
            user = BotUser.objects.get(
                Q(status=BotUser.Status.active) & (Q(tg_nick=username) | Q(telegram_id=chat_id))
            )
        except BotUser.DoesNotExist:
            user = None

        context.user_data['user'] = user
        return func(update, context)

    return wrapper


class TgBot(object):

    def __init__(self, tg_token: str, states_functions: dict[str, dict[str, Callable]]) -> None:
        self.tg_token = tg_token
        self.states_functions = states_functions
        self.updater = Updater(token=tg_token, use_context=True)
        self.updater.dispatcher.add_handler(CommandHandler('start', get_user(self.handle_users_reply)))
        self.updater.dispatcher.add_handler(CommandHandler('help', self.help_handler))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(get_user(self.handle_users_reply)))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, get_user(self.handle_users_reply)))
        self.updater.dispatcher.add_error_handler(self.error)
        self.job_queue = self.updater.job_queue

        self.job_queue.run_repeating(
            self.handle_warning_orders_not_in_work,
            interval=60,
            first=10,
            name='handle_warning_orders_not_in_work'
        )

        self.job_queue.run_repeating(
            self.handle_warning_orders_not_closed,
            interval=60,
            first=20,
            name='handle_warning_orders_not_closed'
        )

    def handle_users_reply(self, update, context):
        user = context.user_data['user']

        if user is None:
            self.states_functions['unknown']['START'](update, context)
            return

        if update.message:
            user_reply = update.message.text
        elif update.callback_query:
            user_reply = update.callback_query.data
        else:
            return

        chat_id = update.effective_chat.id

        if user_reply == '/start':
            user_state = 'START'
        else:
            user_state = user.bot_state
            user_state = user_state if user_state else 'START'

        state_handler = self.states_functions[user.role][user_state]
        next_state = state_handler(update, context)
        user.bot_state = next_state
        user.save()

    def error(self, update, context):
        print(f'Update "{update}" caused error "{context.error}"')
        raise context.error

    def help_handler(self, update, context):
        update.message.reply_text("Используйте /start для того, что бы перезапустить бот")

    def handle_warning_orders_not_in_work(self, context):
        """
        Каждому менеджеру отправить сообщение по каждому не взятому заказу
        В сообщении указать задачу (поле task у заказа) и контакты заказчика (поле client.tg_nick у заказа) не забыв добавить @
        """
        warning_orders_not_in_work = Order.objects.get_warning_orders_not_in_work()
        # managers = Manager.objects.active()

        # warning_orders_not_in_work.update(not_in_work_manager_informed=True)  # это в конце вызывается

    def handle_warning_orders_not_closed(self, context):
        """
        Каждому менеджеру отправить сообщение по каждому не выполненному заказу
        В сообщении указать задачу (поле task у заказа) и
        контакты заказчика (поле client.tg_nick у заказа) и
        подрядчика (поле contractor.tg_nick у заказа) не забыв добавить @
        """
        warning_orders_not_closed = Order.objects.get_warning_orders_not_closed()
        # managers = Manager.objects.active()

        # warning_orders_not_closed.update(late_work_manager_informed=True)  # это в конце вызывается


def start_not_found(update, context):
    """Ответ для неизвестного, что мы его не знаем ему нужно связаться с админами"""
    return 'START'


# Функции для менеджера
def start_manager(update, context):
    """Ответ для менеджера с кнопками (пока одна)"""
    keyboard = [
        [
            InlineKeyboardButton(
                "контакты доступных подрядчиков",
                callback_data="contacts_available_contractors"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id
    context.bot.send_message(
        text='Нажмите',
        reply_markup=reply_markup,
        chat_id=chat_id
    )
    return 'HANDLE_CONTACTS'


def handle_contacts_manager(update, context):
    """
    Из модели подрядчика и заказа достать всех подрядчиков, у которых нет активных заказов.
    Ответить списком их имен телеграм (в БД они хранятся без @, нужно добавить).
    Проверить, что менеджер нажал кнопку
    Если не нажал, то сообщить что неизвестный ввод, но все равно вернуть на старт
    """
    available_contractors = Contractor.objects.get_available()  # список доступных подрядчиков
    # по свойству tg_nick лежат их имена
    chat_id = update.effective_chat.id
    query = update.callback_query
    if query.data == 'contacts_available_contractors':
        message = ''
        for name in available_contractors:
            message += f'@{name.tg_nick}\n'
        context.bot.send_message(text=message, chat_id=chat_id)
    else:
        message = 'неизвестный ввод'
        context.bot.send_message(text=message, chat_id=chat_id)
    return start_manager(update, context)


# Функции для клиента
def start_client(update, context):
    """Ответ для клиента"""
    return ''  # TODO: придумать название


# Функции для подрядчика
def start_contractor(update, context):
    """Ответ для подрядчика"""
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton('Посмотреть заказы', callback_data='watch_orders')],
        [InlineKeyboardButton('Написать заказчику', callback_data='send_message_to_client')],
        [InlineKeyboardButton('Завершить заказ', callback_data='close_order')],
        [InlineKeyboardButton('Мой заработок за месяц', callback_data='my_salary')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(text='Выберите действие', reply_markup=reply_markup, chat_id=chat_id)
    return 'HANDLE_MENU_CONTRACTOR'


def handle_menu_contractor(update, context):
    return 'HANDLE_MENU_CONTRACTOR'


# Функции для владельца
def start_owner(update, context):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton('Биллинг подрядчиков за прошлый месяц', callback_data='contractor_billing_prev_month')],
        [InlineKeyboardButton('Статистика по заказам', callback_data='orders_stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(text='Что вас интересует', reply_markup=reply_markup, chat_id=chat_id)
    return 'HANDLE_BUTTONS'


def handle_buttons_owner(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    if query.data == 'contractor_billing_prev_month':
        billing = [
            f'{contractor_billing["contractor__tg_nick"]}\t{contractor_billing["count_orders"]}'
            for contractor_billing
            in Order.objects.calculate_billing()
        ]
        message = 'Подрядчик\tВыполненных заказов\n' + '-' * 50 + '\n' + '\n'.join(billing)
    elif query.data.startswith('orders_stats'):
        stats = [
            f'{stat[0]}\t{stat[1]}\t{stat[2]}'
            for stat
            in Order.objects.calculate_average_orders_in_month()
        ]
        message = 'Начало биллинга\tКлиент\tЧисло заказов\n' + '-' * 50 + '\n' + '\n'.join(stats)
    else:
        message = 'Я вас не понял, нажмите одну из предложенных кнопок'
    context.bot.send_message(text=message, chat_id=chat_id)
    return start_owner(update, context)
