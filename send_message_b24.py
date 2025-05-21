from io import BytesIO

import requests

from constants import BASE_WEBHOOK

# 🔹 Укажите свой вебхук
SEND_MESSAGE_URL = f"{BASE_WEBHOOK}im.message.add.json"
UPLOAD_FILE_URL = f"{BASE_WEBHOOK}im.disk.folder.uploadfile.json"


def send_message(chat_id: str, message: str, user_id: int = None) -> dict:
    """
    Отправляет сообщение в чат Bitrix24 с опциональным упоминанием пользователя.

    :param chat_id: ID чата (например, "chat27946")
    :param message: Текст сообщения
    :param user_id: (опционально) ID пользователя Bitrix24
    :return: Ответ от Bitrix API
    """
    if user_id:
        full_message = f"[USER={user_id}][/USER], {message}"
    else:
        full_message = message

    payload = {
        "DIALOG_ID": chat_id,
        "MESSAGE": full_message
    }

    response = requests.post(SEND_MESSAGE_URL, json=payload)
    return response.json()


def upload_file_to_folder(folder_id: str, file_buffer: BytesIO, filename: str = "screenshot.png"):
    # 1. Запрос на получение upload URL
    url = f"{BASE_WEBHOOK}disk.folder.uploadfile.json"
    params = {
        "id": folder_id,
        "data": {"NAME": filename},
        "generateUniqueName": "Y"
    }

    resp = requests.post(url, params=params)
    upload_url = resp.json().get("result", {}).get("uploadUrl")
    if not upload_url:
        raise Exception("Не удалось получить upload URL")

    # 2. Загрузка файла по uploadUrl
    file_buffer.seek(0)
    files = {
        "file": (filename, file_buffer, "image/png")
    }

    upload_response = requests.post(upload_url, files=files)
    return upload_response.json()


def get_public_link(file_id: str):
    url = f"{BASE_WEBHOOK}disk.file.getExternalLink.json"
    response = requests.post(url, params={"id": file_id})

    try:
        data = response.json()
    except Exception as e:
        print("Ошибка при парсинге JSON:", e)
        print("response.status_code =", response.status_code)
        print("response.text =", response.text)
        raise

    return data.get("result")  # Просто .get() без вложенного .get("LINK")


if __name__ == "__main__":
    # wer = send_chat_message("chat27946", "eadrfgewarg")
    # print(wer)
    #
    # werwe = send_chat_message("chat27946", "!!!!!!", user_id=43)
    # print(werwe)

    buf = BytesIO(b"Hello from memory!")  # Эмуляция содержимого файла
    # Шаг 1: Загрузка файла
    result = upload_file_to_folder("2435016", buf, "screenshot.png")
    file_id = result.get("result", {}).get("ID")

    # Шаг 2: Получение ссылки
    link = get_public_link(file_id)

    # Шаг 3: Отправка в чат
    send_message("43", f"📎 Скриншот: {link}")
