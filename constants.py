import os

from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

BASE_WEBHOOK = os.getenv("BASE_WEBHOOK")
DXF_DIR = os.getenv("DXF_DIR")
CHAT_ID_KO = os.getenv("CHAT_ID_KO")
CHAT_ID_KTO = os.getenv("CHAT_ID_KTO")