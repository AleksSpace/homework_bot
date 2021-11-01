import logging
from logging.handlers import RotatingFileHandler
import os
import time
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

# Здесь задана глобальная конфигурация для всех логгеров
logging.basicConfig(level=logging.ERROR,
                    filename='app.log',
                    filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')
# А тут установлены настройки логгера для текущего файла
logger = logging.getLogger(__name__)
# Устанавливаем уровень, с которого логи будут сохраняться в файл
logger.setLevel(logging.INFO)
# Указываем обработчик логов
handler = RotatingFileHandler('app.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

LOG_DEBUG_BOT_MESSAGE = 'Попытка отправить сообщение "{message}"'
LOG_DEBUG_BOT_ERROE_MESSAGE = 'Ошибка отправки сообщения: {message}'
LOG_DEBUG_ENDPOINT_QUERY = 'Запрос информации с эндпойнта "{url}"'
LOG_DEBUG_ENDPOINT_ERROR_QUERY = ('Эндпоинт "{url}" недоступен.'
                                  'Код ответа: "{status_code}"')
LOG_DEBUG_HW_CHECK = 'Проверка словаря homework'
LOG_DEBUG_HW_VALID = 'Получен невалидный ответ. Нет ключа "homeworks"'
LOG_DEBUG_HW_EMPTY = 'Словарь homework пустой'
LOG_DEBUG_HW_CHECK_STATUS = 'Проверка статуса ДЗ'
LOG_DEBUG_HW_UNKNOWN_STATUS = 'Неизвестный статус ДЗ'
LOG_DEBUG_HW_NO_NAME = 'Не определено название домашней работы!'
LOG_DEBUG_HW_NO_STATUS = 'Не удалось получить статус дз'
LOG_DEBUG_INCORRECT_STRUCTURE = 'Неверная структура homeworks'
LOG_DEBUG_START_BOT = 'Запуск бота'
LOG_DEBUG_HW_NO_DOC_STATUS = ('Убедитесь, что функция check_response'
                              'правильно работает при недокументированном'
                              'статусе домашней работы в ответе от API')
LOG_DEBUG_ENV_CHECK = 'Проверка env-переменных для подключения'
STATUS_CHANGE = ('Изменился статус проверки работы "{homework_name}". '
                 '{verdict}')

try:
    logger.info(LOG_DEBUG_ENV_CHECK)
    PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
except KeyError as error:
    logger.critical(f'Отсутствует обязательная переменная окружения: {error}!')
    quit()

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
LAST_ERROR = ''


HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_message(bot, message):
    """Метод отправляет сообщение в Телеграм."""
    logger.info(LOG_DEBUG_BOT_MESSAGE)
    if message != LAST_ERROR:
        try:
            bot.send_message(chat_id=CHAT_ID, text=message)
        except telegram.error.TelegramError:
            logger.error(LOG_DEBUG_BOT_ERROE_MESSAGE)


def get_api_answer(url, current_timestamp):
    """Метод отправляет запрос к API домашки на эндпоинт."""
    logger.info(LOG_DEBUG_ENDPOINT_QUERY)
    if current_timestamp is None:
        current_timestamp = int(time.time())
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS,
                                params={'from_date': current_timestamp})
        status_code = response.status_code
    except Exception:
        raise ConnectionResetError(LOG_DEBUG_ENDPOINT_ERROR_QUERY)

    if status_code != HTTPStatus.OK:
        raise ConnectionResetError(LOG_DEBUG_ENDPOINT_ERROR_QUERY)
    if response.json() is not None:
        return response.json()


def parse_status(homework):
    """Метод проверяет статус проверки ДЗ."""
    logger.info(LOG_DEBUG_HW_CHECK_STATUS)
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error(LOG_DEBUG_HW_NO_NAME)
        raise ValueError(LOG_DEBUG_HW_NO_NAME)
    status = homework.get('status')
    if status is None:
        logger.error(LOG_DEBUG_HW_NO_STATUS)
        raise ValueError(LOG_DEBUG_HW_NO_STATUS)
    if status in VERDICTS:
        verdict = VERDICTS[status]
    if status not in VERDICTS:
        logger.error(LOG_DEBUG_HW_UNKNOWN_STATUS)
        raise ValueError(LOG_DEBUG_HW_UNKNOWN_STATUS)
    return STATUS_CHANGE.format(homework_name=homework_name, verdict=verdict)


def check_response(response):
    """Метод проверяет полученный ответ на корректность.
    Проверяет, не изменился ли статус
    """
    logger.info(LOG_DEBUG_HW_CHECK)
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError(LOG_DEBUG_HW_VALID)
    if not homeworks:
        logger.debug(LOG_DEBUG_HW_EMPTY)
        return None
    if isinstance(homeworks, list) and len(homeworks) > 0:
        status = parse_status(homeworks[0])
        return status
    elif isinstance(homeworks, list) and len(homeworks) == 0:
        return False
    else:
        raise TypeError(LOG_DEBUG_INCORRECT_STRUCTURE)


def main():
    """Запуск бота."""
    logger.debug(LOG_DEBUG_START_BOT)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            new_homework = get_api_answer(ENDPOINT, current_timestamp)
            message = check_response(new_homework)
            if message:
                send_message(bot, message)
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.ERROR,
        filename='app.log',
        filemode='w',
        format='%(name)s - %(levelname)s - %(message)s')
    main()
