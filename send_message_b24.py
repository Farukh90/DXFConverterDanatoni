import requests

from constants import BASE_WEBHOOK

# 🔹 Укажите свой вебхук
SEND_MESSAGE_URL = f"{BASE_WEBHOOK}im.message.add.json"


def send_chat_message(chat_id: str, message: str, user_id: int = None) -> dict:
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


def send_private_message(user_id: int, message: str) -> dict:
    """
    Отправляет личное сообщение пользователю в Bitrix24.

    :param user_id: ID пользователя Bitrix24
    :param message: Текст сообщения
    :return: Ответ от Bitrix API
    """
    payload = {
        "DIALOG_ID": str(user_id),  # Прямой диалог с пользователем
        "MESSAGE": message
    }

    response = requests.post(SEND_MESSAGE_URL, json=payload)
    return response.json()


if __name__ == "__main__":
    # wer = send_chat_message("chat27946", "eadrfgewarg")
    # print(wer)
    #
    # werwe = send_chat_message("chat27946", "!!!!!!", user_id=262)
    # print(werwe)

    # Отправка личного сообщения пользователю с ID 262
    send_private_message(284, "Просто проверка")