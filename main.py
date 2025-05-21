import time

from constants import DXF_DIR
from convert_dxf import convert_dxf_with_bulge
from process_dxf_utils import get_all_dxf_files, read_index, write_index_safely

# 📁 Настройки
INPUT_DIR = DXF_DIR
INDEX_JSON = "index.json"
CHECK_INTERVAL = 3  # каждые 5 минут
DELAY_BETWEEN_FILES = 5


def main_loop():
    print("🌀 Запуск обработчика DXF...")
    while True:
        try:
            index = read_index(INDEX_JSON)
            updated_index = index.copy()

            for input_path in get_all_dxf_files(INPUT_DIR):
                rel_path = input_path.relative_to(INPUT_DIR).as_posix()
                current_mtime = input_path.stat().st_mtime

                if rel_path not in index or index[rel_path] != current_mtime:
                    print(f"📂 Обработка: {rel_path}")
                    try:
                        convert_dxf_with_bulge(str(input_path), str(input_path))
                        updated_mtime = input_path.stat().st_mtime
                        updated_index[rel_path] = updated_mtime
                        print(f"✅ Успешно: {rel_path}")
                        time.sleep(DELAY_BETWEEN_FILES)
                    except Exception as e:
                        print(f"❌ Ошибка при обработке {rel_path}: {e}")

            # после for input_path in get_all_dxf_files(...), собрать всё в set
            existing_files = {f.relative_to(INPUT_DIR).as_posix() for f in get_all_dxf_files(INPUT_DIR)}

            # удалить из index.json все записи, которых больше нет в input/
            for key in list(updated_index.keys()):
                if key not in existing_files:
                    print(f"🧹 Удалён из index.json (файла уже нет): {key}")
                    del updated_index[key]
                    time.sleep(DELAY_BETWEEN_FILES)  # ⏱ пауза, если ты отправляешь уведомление

            write_index_safely(updated_index, INDEX_JSON)
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("🛑 Остановка пользователем (Ctrl+C)")
            break
        except Exception as loop_ex:
            print(f"‼️ Ошибка основного цикла: {loop_ex}")
            time.sleep(10)


if __name__ == "__main__":
    main_loop()
