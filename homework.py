import logging
import os
import time
from logging import FileHandler, StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileHandler(__file__ + '.log'))
logger.addHandler(StreamHandler())

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
REQUEST_PERIOD = 5 * 60
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
NOTIFICATION = 'У вас проверили работу "{name}"!\n\n'
VERDICTS = {
    'rejected': (NOTIFICATION + 'К сожалению, в работе нашлись ошибки.'),
    'approved': (NOTIFICATION + 'Ревьюеру всё понравилось, работа зачтена!'),
    'reviewing': 'Работа {name} взята в ревью', }
INVALID_STATUS = 'Неожиданный статус {status}'
SERVER_FAILURE = ('Отказ сервера {key} {text} '
                  'параметры запроса: URL - {url}; '
                  'headers - {headers}; params - {params}')
NET_WORK_PROBLEMS = ('Сбой сети {mistake} параметры запроса: URL - {url}; '
                     'headers - {headers}; params - {params}')
LOG_BOT_STARTED = 'Бот запущен'
LOG_BOT_PROBLEMS = 'При работе Бота возникла ошибка {mistake}'
LOG_SENT_MESSAGE = 'Отправлено сообщение {message}'

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def parse_homework_status(homework):
    status = homework['status']
    if status not in VERDICTS:
        raise ValueError(INVALID_STATUS.format(status=status))
    message = VERDICTS[status]
    return message.format(name=homework['homework_name'])


def get_homeworks(current_timestamp):
    request_parameters = dict(
        url=URL, headers=HEADERS, params={'from_date': current_timestamp}
    )
    try:
        homework_statues = requests.get(**request_parameters)
    except RequestException as mistake:
        raise ConnectionError(NET_WORK_PROBLEMS.format(
            mistake=mistake, **request_parameters))
    response = homework_statues.json()
    for server_problem in ['code', 'error']:
        if server_problem in response:
            raise RuntimeError(SERVER_FAILURE.format(
                key=server_problem, text=response[server_problem],
                **request_parameters))
    return response


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())
    logger.debug(LOG_BOT_STARTED)
    while True:
        try:
            response = get_homeworks(current_timestamp)
            homework = response['homeworks']
            if not homework:
                continue
            message = parse_homework_status(homework[0])
            send_message(message)
            logger.info(LOG_SENT_MESSAGE.format(message=message))
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as mistake:
            logger.exception(LOG_BOT_PROBLEMS.format(mistake=mistake))
        finally:
            time.sleep(REQUEST_PERIOD)


if __name__ == '__main__':
    main()
