import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.ERROR, filename='app.log', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
payload = {'from_date': 1549962000}

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

# Делаем GET-запрос к эндпоинту url с заголовком headers и параметрами params
homework_statuses = requests.get(ENDPOINT, headers=headers, params=payload)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_message(bot, message):
    """Метод отправляет сообщение в Телеграм."""
    logging.info('Отправляем сообщение в Телеграм.')
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        return bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as error:
        print(f'Не удалось отправить сообщение: {error}')
        logging.error("Exception occurred", exc_info=True)


def get_api_answer(url, current_timestamp):
    """Метод отправляет запрос к API домашки на эндпоинт."""
    logging.info('Отправляем запрос к API домашки.')
    if current_timestamp is None:
        current_timestamp = payload
    try:
        response = requests.get(url=ENDPOINT, headers=headers,
                                params={'from_date': current_timestamp})
        status_code = response.status_code

        if status_code != HTTPStatus.OK:
            message = f'Эндпоинт {url} недоступен. Код ответа: {status_code}'
            raise ConnectionResetError(message, 'ERROR')
    except Exception as error:
        message = f'Эндпоинт {url} недоступен. {error}'
        raise ConnectionResetError(message, 'ERROR')
    else:
        return response.json()


def parse_status(homework):
    """Метод проверяет статус проверки ДЗ."""
    logging.info('Проверяем статус ДЗ.')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('Не удалось получить данные дз, homework_name is None')
        return 'Не удалось получить данные дз, homework_name is None'
    status = homework.get('status')
    if status is None:
        logging.error('Не удалось получить данные дз, status is None')
        return 'Не удалось получить данные дз, status is None'
    if status in HOMEWORK_STATUSES:
        if status == 'reviewing':
            verdict = HOMEWORK_STATUSES['reviewing']
        if status == 'rejected':
            verdict = HOMEWORK_STATUSES['rejected']
        if status == 'approved':
            verdict = HOMEWORK_STATUSES['approved']
    else:
        logging.error(f'Неизвестный статус - {status}')
        return f'Неизвестный статус - {status}'

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Метод проверяет полученный ответ на корректность.
    Проверяет, не изменился ли статус
    """
    logging.info('Проверяем ответ от сервера.')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('API вернул пустой словарь', 'ERROR')
    if not homeworks:
        return None
    homework = response.get('homeworks')[0]
    verdict = HOMEWORK_STATUSES.get(homework.get('status'))
    if verdict is None:
        raise AssertionError('Убедитесь, что функция check_response'
                             'правильно работает при недокументированном'
                             'статусе домашней работы в ответе от API')

    return parse_status(homeworks[0])


def main():
    """Запуск бота."""
    logging.debug('Запуск бота.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    url = ENDPOINT
    while True:
        try:
            new_homework = get_api_answer(url, current_timestamp)
            message = check_response(new_homework)
            if message:
                send_message(parse_status(new_homework.get('homeworks')[0]))
            current_date = new_homework.get('current_date')
            current_timestamp = new_homework.get(current_date)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
