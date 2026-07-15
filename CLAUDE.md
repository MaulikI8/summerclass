# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django marketplace web app ("Islington marketplace"). Dependencies are managed with Pipenv (Python 3.12, Django is the only package). The database is SQLite (`db.sqlite3`, committed in the repo).

## Commands

```bash
pipenv install                                # install dependencies
pipenv run python manage.py runserver         # run dev server at http://127.0.0.1:8000
pipenv run python manage.py makemigrations    # generate migrations after model changes
pipenv run python manage.py migrate           # apply migrations
pipenv run python manage.py test              # run all tests
pipenv run python manage.py test products     # run tests for one app
pipenv run python manage.py createsuperuser   # create admin user for /admin
```

(Alternatively run `pipenv shell` once, then drop the `pipenv run` prefix.)

## Architecture

- `marketplace/` — the Django project package: `settings.py`, root `urls.py`, and a `views.py` holding the site-level `home` view (routed at `/`).
- `products/` — the single Django app. Models are `Category` and `Product` (Product has a FK to Category); both are registered in `products/admin.py`. App URLs are included under `/products/` via `products/urls.py`.
- `Templates/` — project-level templates directory. `master/base.html` is the base layout; pages extend it and fill the `title` and `content` blocks (see `home/home.html`).

## Gotchas

- The templates directory on disk is `Templates/` (capital T) but `settings.py` points to `'templates'`. This works on Windows (case-insensitive filesystem) but will break on Linux/macOS or in a container — keep the casing consistent if deploying.
- `STATICFILES_DIRS` in `settings.py` references a `static/` directory that does not exist yet (and is declared with `{}` — a set — rather than a list).
- The `dockerfile` is a Node.js image (npm, port 3000) and does not build this Django project.
