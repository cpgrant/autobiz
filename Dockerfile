FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system autobiz && adduser --system --ingroup autobiz autobiz

COPY pyproject.toml README.md ./
COPY autobiz ./autobiz
COPY apps ./apps
COPY manage.py ./manage.py

RUN pip install --no-cache-dir .

USER autobiz
EXPOSE 8000

CMD ["gunicorn", "autobiz.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
