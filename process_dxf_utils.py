import json
import os
import shutil
import tempfile
from pathlib import Path


def read_index(index_json: str):
    if not os.path.exists(index_json):
        return {}
    try:
        with open(index_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"‼️ Не удалось прочитать index.json: {e}")
        return {}


def write_index_safely(index_data, index_json: str):
    try:
        # 🔐 Бэкап перед перезаписью
        if os.path.exists(index_json):
            shutil.copy(index_json, index_json + ".bak")

        # 💾 Безопасная запись через временный файл
        with tempfile.NamedTemporaryFile("w", delete=False, dir=".", suffix=".json", encoding="utf-8") as tmp:
            json.dump(index_data, tmp, ensure_ascii=False, indent=2)
        os.replace(tmp.name, index_json)

    except Exception as e:
        print(f"‼️ Ошибка при сохранении index.json: {e}")


def get_all_dxf_files(root):
    return Path(root).rglob("*.dxf")
