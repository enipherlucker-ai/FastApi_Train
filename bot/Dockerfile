FROM python:3.12-slim

WORKDIR /tg_bot
COPY bot/requirements.txt ./
RUN python -m pip install --no-cache -r requirements.txt

COPY bot/ ./bot/

CMD ["python", "-m", "bot.main"]