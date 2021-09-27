import logging
from logging import FileHandler, StreamHandler
import os
import time

from dotenv import load_dotenv
import requests
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
            'reviewing': 'Работа {homework_name} взята в ревью'}
REVIEW_STATUS = 'У вас проверили работу "{homework_name}"!\n\n{verdict}'
INVALID_STATUS = 'Неожиданный статус {status}'
SERVER_FAILURE = ('Отказ сервера, {status_code}, '
                  '{server_problem}''параметры запроса {params}')
NET_WORK_PROBLEMS = 'Сбой сети'
LOGGER_MESSAGE = {'bot_started': 'Бот запущен',
                  'unknown_status': 'Статус работы неизвестен',
                  'sent_message': 'Отправлено сообщение {message}',
                  'bot_fell': 'Бот упал с ошибкой {mistake}'}


def parse_homework_status(homework):
    if homework['status'] not in VERDICTS:
        raise ValueError(INVALID_STATUS.format(
            status=homework['status']))
    elif homework['status'] == 'reviewing':
        return VERDICTS[homework['status']].format(
            homework_name=homework['homework_name'])
    else:
        return REVIEW_STATUS.format(homework_name=homework['homework_name'],
                                    verdict=VERDICTS[homework['status']])


def get_homeworks(current_timestamp):
    try:
        homework_statues = requests.get(
            URL,
            headers=HEADERS,
            params={'from_date': current_timestamp}
        )
        for server_problem in ['code', 'error']:
            if server_problem in homework_statues.json():
                raise Exception(SERVER_FAILURE[0].format(
                    status_code=homework_statues.status_code,
                    server_problem=server_problem,
                    params=current_timestamp)
                )
    except ConnectionError:
        raise ConnectionError(NET_WORK_PROBLEMS)
    else:
        return homework_statues.json()


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())  # Начальное значение timestamp
    logger.debug(LOGGER_MESSAGE['bot_started'])
    while True:
        try:
            homeworks, current_date = get_homeworks(
                current_timestamp).values()
            # Получить статус проверки работы
            homework_status = homeworks
            current_timestamp = current_date
            # Если работа не проверена список пустой
            if not homework_status:
                logger.info(LOGGER_MESSAGE['unknown_status'])
            else:  # Иначе работа проверена
                # Последний ответ по статусу работы
                homework = homework_status[0]
                message = parse_homework_status(homework)
                send_message(message)
                logger.info(LOGGER_MESSAGE['sent_message'].format(
                    message=message))
            time.sleep(REQUEST_PERIOD)  # Опрашивать раз в пять минут
        except Exception:
            logger.exception(LOGGER_MESSAGE['bot_fell'].format(
                mistake=Exception))
            time.sleep(REQUEST_PERIOD)


if __name__ == '__main__':
    main()
