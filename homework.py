import logging
from logging import FileHandler, StreamHandler
import os
import sys
import time

from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException
import telegram

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
VERDICTS = {'rejected': 'К сожалению, в работе нашлись ошибки.',
            'approved': 'Ревьюеру всё понравилось, работа зачтена!',
            'reviewing': 'Работа {name} взята в ревью'}
CHECKING_HOMEWORK = 'reviewing'
REVIEW_STATUS = 'У вас проверили работу "{name}"!\n\n{verdict}'
INVALID_STATUS = 'Неожиданный статус {status}'
SERVER_FAILURE = ('Отказ сервера {text} '
                  'параметры запроса: URL{URL}; '
                  'headers - {headers}; params - {params}')
NET_WORK_PROBLEMS = ('Сбой сети {type_exception} {text} '
                     'параметры запроса: URL - {url}; '
                     'headers - {headers}; params - {params}')
LOG_BOT_STARTED = 'Бот запущен'
LOG_BOT_FELL = 'Бот упал с ошибкой {type_exception} {mistake}'
LOG_SENT_MESSAGE = 'Отправлено сообщение {message}'

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def parse_homework_status(homework):
    status_homework = homework['status']
    if status_homework not in VERDICTS:
        raise ValueError(INVALID_STATUS.format(status=status_homework))
    name_homework = homework['homework_name']
    message = REVIEW_STATUS.format(name=name_homework,
                                   verdict=VERDICTS[status_homework])
    if status_homework == CHECKING_HOMEWORK:
        message = VERDICTS[status_homework].format(name=name_homework)
    return message


def get_homeworks(current_timestamp):
    try:
        homework_statues = requests.get(
            URL,
            headers=HEADERS,
            params={'from_date': current_timestamp}
        )
    except RequestException:
        type_exception, exception_text = sys.exc_info()[:2]
        raise ConnectionError(NET_WORK_PROBLEMS.format(
            type_exception=type_exception, text=exception_text,
            url=URL, headers=HEADERS, params=current_timestamp))
    response = homework_statues.json()
    for server_problem in ['code', 'error']:
        if server_problem in response:
            raise Exception(SERVER_FAILURE[0].format(
                text=response[server_problem], url=URL,
                headers=HEADERS, params=current_timestamp)
            )
    return response


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())
    logger.debug(LOG_BOT_STARTED)
    while True:
        time.sleep(REQUEST_PERIOD)
        try:
            response = get_homeworks(current_timestamp)
            current_timestamp = response['current_date']
            homework = response['homeworks']
            if not homework:
                continue
            else:
                message = parse_homework_status(homework[0])
                send_message(message)
                logger.info(LOG_SENT_MESSAGE.format(message=message))
        except Exception:
            type_exception, exception_text = sys.exc_info()[:2]
            logger.exception(LOG_BOT_FELL.format(type_exception=type_exception,
                                                 mistake=exception_text)
                             )


if __name__ == '__main__':
    main()
