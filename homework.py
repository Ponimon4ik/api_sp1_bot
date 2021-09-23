import os
import time
import requests
import telegram
from telegram.ext import Updater, CommandHandler
from dotenv import load_dotenv
import logging
from logging import FileHandler, StreamHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileHandler('main.log'))
logger.addHandler(StreamHandler())

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
REQUEST_PERIOD = 5 * 60

bot = telegram.Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
params = {'from_date': 0}


def parse_homework_status(homework):
    homework_name = homework['homework_name']
    if homework['status'] == 'rejected':
        verdict = 'К сожалению, в работе нашлись ошибки.'
    else:
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    homework_statues = requests.get(
        URL,
        headers=headers,
        params=current_timestamp
    )
    return homework_statues.json().get('homeworks')


def send_message(context, message):
    return context.bot.send_message(CHAT_ID, message)


def main(update, context):
    text = update.effective_message.text
    if text == '/start':
        logger.debug('Бот запущен пользователем')
    current_timestamp = int(time.time())  # Начальное значение timestamp
    while True:
        try:
            params['from_date'] = current_timestamp
            homework_status = get_homeworks(params)
            if len(homework_status) == 0:
                logger.info('Статус работы не известен')
                time.sleep(REQUEST_PERIOD)  # Опрашивать раз в пять минут
            else:
                homework = homework_status[0]
                message = parse_homework_status(homework)
                send_message(context, message)
                logger.info(f'Отправлено сообщение: {message}')
                current_timestamp += REQUEST_PERIOD - 1
        except telegram.error.Unauthorized:
            logger.exception('Бот остановлен пользователем')
            break
        except Exception as e:
            logger.exception(f'Бот упал с ошибкой: {e}')
            send_message(context, f'Бот упал с ошибкой: {e}')
            logger.info(f'Отправлено сообщение об ошибке {e}')
            time.sleep(10)


if __name__ == '__main__':
    updater.dispatcher.add_handler(CommandHandler('start', main))
    updater.start_polling()
    updater.idle()
