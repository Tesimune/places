# Django Application

A Django web application for managing tokens and places, using PostgreSQL for the database and Redis for caching.

## Table of Contents

* [Features](#features)
* [Requirements](#requirements)
* [Installation](#installation)
* [Configuration](#configuration)
* [Database Setup](#database-setup)
* [Running the Application](#running-the-application)
* [Admin Access](#admin-access)
* [Redis Setup](#redis-setup)
* [License](#license)

---

## Features

* Token management system
* Place management with latitude and longitude
* Automatic timestamp tracking (`created_at` and `updated_at`)
* PostgreSQL database support
* Redis caching support
* Google Maps API integration

---

## Requirements

* Python 3.10+
* PostgreSQL 12+
* Redis 6+
* Docker & Docker Compose (optional, for local dev)

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/tesimune/places.git
cd places
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

3. **Install dependencies from `requirements.txt`**

```bash
pip install -r requirements.txt
```

---

## Configuration

1. **Copy `.env.example` to `.env`**

```bash
cp .env.example .env
```

2. **Update environment variables** in `.env` as needed (SECRET_KEY, database credentials, Redis URL, Google API key).

3. **Make sure `settings.py` loads environment variables**, e.g., using `python-decouple`:

```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config('REDIS_LOCATION'),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
```

---

## Database Setup

1. **Ensure PostgreSQL is running** (local or Docker).
2. **Create the database** (if not using Docker, adjust accordingly):

```sql
CREATE DATABASE auth;
CREATE USER postgres;
```

3. **Apply Django migrations**

```bash
python manage.py makemigrations
python manage.py migrate
```

4. **Create a superuser**

```bash
python manage.py createsuperuser
```

---

## Running the Application

```bash
python manage.py runserver
```

Access the application at: `http://127.0.0.1:8000/`

---

## Admin Access

* Navigate to `http://127.0.0.1:8000/admin/`
* Log in with the superuser credentials
* Manage Tokens and Places via the admin panel

---

## Redis Setup

1. Ensure Redis is running (local or Docker).
2. `django-redis` is already installed and configured via `.env`.

Redis can be used for caching or background tasks like Celery.

---

## License

MIT License © 2025 Teslim

---

If you want, I can also create a **Docker Compose setup** in the README so PostgreSQL, Redis, and Django can all run with a single `docker-compose up` command. It makes local dev super smooth. Do you want me to include that?
