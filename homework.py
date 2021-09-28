import logging
from logging import FileHandler, StreamHandler
import os
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

bot = telegram.Bot(token=TELEGRAM_TOKEN)

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
NET_WORK_PROBLEMS = ('Сбой сети {text} '
                     'параметры запроса: URL - {url}; '
                     'headers - {headers}; params - {params}')
LOG_BOT_STARTED = 'Бот запущен'
LOG_BOT_FELL = 'Бот упал с ошибкой {mistake}'
LOG_SENT_MESSAGE = 'Отправлено сообщение {message}'
LOG_UNKNOW_STATUS = 'Статус работы неизвестен'


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
        raise ConnectionError(NET_WORK_PROBLEMS.format(
            text=RequestException, url=URL,
            headers=HEADERS, params=current_timestamp))
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
    current_timestamp = 0#int(time.time())  # Начальное значение timestamp
    logger.debug(LOG_BOT_STARTED)
    while True:
        try:
            # Получить статус проверки работы
            homework_status = get_homeworks(
                current_timestamp)
            logger.debug(homework_status)
            current_timestamp = homework_status['current_date']
            if not homework_status:
                continue
            else:
                homework = homework_status['homeworks'][0]
                message = parse_homework_status(homework)
                send_message(message)
                logger.info(LOG_SENT_MESSAGE.format(message=message))
            time.sleep(REQUEST_PERIOD)  # Опрашивать раз в пять минут
        except Exception:
            logger.exception(LOG_BOT_FELL.format(mistake=Exception))
            time.sleep(REQUEST_PERIOD)


if __name__ == '__main__':
    main()
