FROM python:3.12-slim

WORKDIR /start_code
COPY requirements.txt ./

COPY main.py ./main.py/

RUN python -m pip install --no-cache -r requirements.txt

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]