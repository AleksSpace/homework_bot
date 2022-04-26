# Учебный проект "homework_bot"

Проект homework_bot - это один из проекто на Я.Практикуме, где нужно было написать 
Telegram-бота, который будет обращаться к API сервиса Практикум.Домашка и 
узнавать статус вашей домашней работы: взята ли ваша домашка в ревью, 
проверена ли она, а если проверена — то принял её ревьюер или вернул на доработку.

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone git@github.com:AleksSpace/homework_bot.git
```

```
cd homework_bot
```

Cоздать и активировать виртуальное окружение:

```
python -m venv env
```

```
. env/Scripts/activate
```

Установить зависимости из файла requirements.txt:

```
python -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

Выполнить миграции:

```
python3 manage.py migrate
```
