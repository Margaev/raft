FROM python:3.11.5-bullseye
WORKDIR /opt/app
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3", "main.py"]
