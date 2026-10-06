FROM python:3.12-slim

WORKDIR /my_code
COPY requirements.txt ./

COPY app/ ./app/

RUN python -m pip install --no-cache -r requirements.txt

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]