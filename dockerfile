FROM python:3.12.4

ENV PYTHONIOENCODING=utf-8

WORKDIR /app

COPY . .

# install
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# run Flask
CMD ["python", "app.py"]
