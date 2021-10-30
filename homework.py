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

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_message(bot, message):
    """Метод отправляет сообщение в Телеграм."""
    logger.info('Отправляем сообщение в Телеграм.')
    try:
        return bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception:
        logger.error('Бот не смог отправить сообщение', exc_info=True)


def get_api_answer(url, current_timestamp):
    """Метод отправляет запрос к API домашки на эндпоинт."""
    logger.info('Отправляем запрос к API домашки.')
    if current_timestamp is None:
        current_timestamp = int(time.time())
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS,
                                params={'from_date': current_timestamp})
        status_code = response.status_code
    except Exception:
        logger.critical('Всё упало! API недоступен')

    if status_code != HTTPStatus.OK:
        message = f'Эндпоинт {url} недоступен. Код ответа: {status_code}'
        raise ConnectionResetError(message, 'ERROR')
    if response.json() is not None:
        return response.json()


def parse_status(homework):
    """Метод проверяет статус проверки ДЗ."""
    logger.info('Проверяем статус ДЗ.')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error('Не удалось получить данные дз, homework_name is None')
        raise ValueError('Не удалось получить данные дз, homework_name is None')
    status = homework.get('status')
    if status is None:
        logger.error('Не удалось получить данные дз, status is None')
        raise ValueError('Не удалось получить данные дз, status is None')
    if status in VERDICTS:
        verdict = VERDICTS[status]
    else:
        logger.error(f'Неизвестный статус - {status}')
        return f'Неизвестный статус - {status}'

    return VERDICTS.format(homework_name=homework_name, verdict=verdict)


def check_response(response):
    """Метод проверяет полученный ответ на корректность.
    Проверяет, не изменился ли статус
    """
    logger.info('Проверяем ответ от сервера.')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('API вернул пустой словарь', 'ERROR')
    if not homeworks:
        return None
    homework = homeworks[0]
    verdict = VERDICTS.get(homework.get('status'))
    if verdict is None:
        raise AssertionError('Убедитесь, что функция check_response'
                             'правильно работает при недокументированном'
                             'статусе домашней работы в ответе от API')

    return parse_status(homeworks[0])


def main():
    """Запуск бота."""
    logger.debug('Запуск бота.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            new_homework = get_api_answer(ENDPOINT, current_timestamp)
            message = check_response(new_homework)
            if message:
                send_message(parse_status(new_homework.get('homeworks')[0]))
            current_date = new_homework.get('current_date')
            current_timestamp = new_homework.get(current_date)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
