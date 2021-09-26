import logging
from logging import FileHandler, StreamHandler
import os
import time

from dotenv import load_dotenv
import requests
import telegram
from telegram.error import Unauthorized


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

headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}


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
        params={'from_date': current_timestamp}
    )
    return homework_statues.json()


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())  # Начальное значение timestamp
    logger.debug('Бот запущен')
    while True:
        try:
            # Получить статус проверки работы
            homework_status = get_homeworks(
                current_timestamp).get('homeworks')
            # Если работа не проверена список пустой
            if len(homework_status) == 0:
                logger.info('Статус работы не известен')
                time.sleep(REQUEST_PERIOD)  # Опрашивать раз в пять минут
            else:  # Иначе работа проверена
                # Последний ответ по статусу работы
                homework = homework_status[0]
                message = parse_homework_status(homework)
                send_message(message)
                logger.info(f'Отправлено сообщение: {message}')
                current_timestamp = int(time.time())
        except Unauthorized:
            logger.exception('Бот остановлен пользователем')
            time.sleep(REQUEST_PERIOD)
        except Exception as e:
            logger.exception(f'Бот упал с ошибкой: {e}')
            send_message(f'Бот упал с ошибкой: {e}')
            logger.info(f'Отправлено сообщение об ошибке {e}')
            time.sleep(10)


if __name__ == '__main__':
    main()
