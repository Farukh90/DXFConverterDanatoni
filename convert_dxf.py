import math

import ezdxf
from ezdxf.math import Vec3


def is_close(p1, p2, tol=1e-2):
    """
    Проверяет, находятся ли две точки p1 и p2 близко друг к другу в 2D.
    p1, p2 могут быть объектами Vec3 или кортежами/списками. Используются только координаты X и Y.
    """
    # Убедимся, что сравниваем 2D координаты
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    return math.dist((x1, y1), (x2, y2)) <= tol


def arc_bulge(start_pt_tuple, end_pt_tuple, center_pt_tuple):
    """Вычисляет bulge (выпуклость) для дуги, определённой начальной, конечной точками и центром."""

    def angle_between_vectors(v1, v2):
        # Угол между векторами v1 и v2 (от v1 к v2)
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        det = v1[0] * v2[1] - v1[1] * v2[0]
        return math.atan2(det, dot)

    # Вектор от центра к начальной точке дуги
    vec_center_to_start = (start_pt_tuple[0] - center_pt_tuple[0], start_pt_tuple[1] - center_pt_tuple[1])
    # Вектор от центра к конечной точке дуги
    vec_center_to_end = (end_pt_tuple[0] - center_pt_tuple[0], end_pt_tuple[1] - center_pt_tuple[1])

    # Центральный угол дуги
    angle = angle_between_vectors(vec_center_to_start, vec_center_to_end)

    # Bulge = tan(центральный_угол / 4)
    bulge = math.tan(angle / 4.0)
    return bulge


def convert_dxf_with_bulge(input_path, output_path, tol=1e-2):
    """
    Конвертирует DXF файл, объединяя LINE, ARC и CIRCLE в замкнутые LWPOLYLINE с bulge.
    Круги разбиваются на две дуги по 180 градусов.
    """
    print(f"Чтение файла: {input_path}")
    try:
        doc = ezdxf.readfile(input_path)
    except IOError:
        print(f"Не удалось открыть файл: {input_path}")
        return
    except ezdxf.DXFStructureError:
        print(f"Ошибка структуры DXF файла: {input_path}")
        return

    msp = doc.modelspace()

    # 1. Конвертация CIRCLE (Кругов) в ARC (Дуги)
    circles_to_convert = list(msp.query("CIRCLE"))  # Материализуем запрос перед изменением msp
    print(f"Найдено исходных CIRCLE: {len(circles_to_convert)}")

    newly_created_arcs_from_circles = []
    for circle in circles_to_convert:
        center = circle.dxf.center  # Vec3
        radius = circle.dxf.radius

        # Сохраняем атрибуты оригинального круга для новых дуг
        attribs = {}
        if circle.dxf.hasattr("layer"):
            attribs["layer"] = circle.dxf.layer
        else:
            attribs["layer"] = "0"  # Слой по умолчанию
        if circle.dxf.hasattr("color"):
            attribs["color"] = circle.dxf.color
        # При необходимости можно добавить другие атрибуты

        # Создаем 2 дуги по 180 градусов для каждого круга
        # Углы в градусах, против часовой стрелки от оси X
        for i in range(2):  # Цикл дважды для двух дуг
            start_angle_deg = i * 180.0
            end_angle_deg = (i + 1) * 180.0
            if end_angle_deg >= 360.0:
                end_angle_deg = 359.9999  # FIX: избегаем исчезновения дуги

            new_arc = msp.add_arc(center=center, radius=radius,
                                  start_angle=start_angle_deg, end_angle=end_angle_deg,
                                  dxfattribs=attribs)

            newly_created_arcs_from_circles.append(new_arc)
        msp.delete_entity(circle)
    print(f"Удалено CIRCLE: {len(circles_to_convert)}, создано ARC из них: {len(newly_created_arcs_from_circles)}")

    # 2. Сбор всех объектов LINE и ARC для построения цепочек
    # Этот запрос теперь включает оригинальные дуги и дуги, созданные из кругов
    all_lines = list(msp.query("LINE"))
    all_arcs = list(msp.query("ARC"))
    all_entities = all_lines + all_arcs

    print(f"Всего для обработки: {len(all_lines)} LINE, {len(all_arcs)} ARC. Суммарно: {len(all_entities)} объектов.")

    # 3. Построение цепочек (контуров)
    processed_entity_indices = set()  # Индексы объектов, уже включенных в финальные цепочки
    final_chains = []  # Список успешно построенных замкнутых цепочек

    for i, current_entity in enumerate(all_entities):
        if i in processed_entity_indices:
            continue

        # Начало новой цепочки
        # Формат цепочки: список из (Vec3_вершина, bulge_от_этой_вершины_к_следующей)
        current_chain_candidate = []

        # Объекты (их индексы), использованные при текущей попытке построения цепочки
        # Они добавляются в processed_entity_indices только если цепочка финализирована
        temp_used_indices_for_this_chain = {i}

        # Инициализация первого сегмента цепочки
        p1_vec, p2_vec = None, None  # Vec3
        bulge_for_first_segment = 0.0

        if current_entity.dxftype() == "LINE":
            p1_vec = Vec3(current_entity.dxf.start)  # Гарантируем Vec3
            p2_vec = Vec3(current_entity.dxf.end)
            bulge_for_first_segment = 0.0
        else:  # ARC
            p1_vec = Vec3(current_entity.start_point)
            p2_vec = Vec3(current_entity.end_point)
            center_vec = Vec3(current_entity.dxf.center)
            # Конвертируем в кортежи для arc_bulge
            p1_tuple = (p1_vec.x, p1_vec.y)
            p2_tuple = (p2_vec.x, p2_vec.y)
            center_tuple = (center_vec.x, center_vec.y)
            bulge_for_first_segment = arc_bulge(p1_tuple, p2_tuple, center_tuple)

        current_chain_candidate.append((p1_vec, bulge_for_first_segment))
        current_chain_candidate.append((p2_vec, None))  # Bulge от p2_vec изначально неизвестен

        # Пытаемся расширить цепочку
        chain_extended_in_iteration = True
        while chain_extended_in_iteration:
            chain_extended_in_iteration = False

            # Конечная точка текущей попытки построения цепочки (последняя добавленная вершина)
            chain_tip_vertex_vec = current_chain_candidate[-1][0]
            chain_tip_vertex_tuple = (chain_tip_vertex_vec.x, chain_tip_vertex_vec.y)

            # Проверяем, не замкнулась ли цепочка (последняя точка близка к начальной)
            if len(current_chain_candidate) > 2:  # Нужно как минимум 2 сегмента для замыкания
                if is_close(chain_tip_vertex_tuple, (current_chain_candidate[0][0].x, current_chain_candidate[0][0].y),
                            tol):
                    break  # Цепочка замкнулась, прекращаем её расширение

            for j, next_entity in enumerate(all_entities):
                if j in temp_used_indices_for_this_chain:  # Уже использован в этой цепочке
                    continue

                next_e_p1_vec, next_e_p2_vec, next_e_center_vec = None, None, None
                next_e_is_arc = False

                if next_entity.dxftype() == "LINE":
                    next_e_p1_vec = Vec3(next_entity.dxf.start)
                    next_e_p2_vec = Vec3(next_entity.dxf.end)
                else:  # ARC
                    next_e_p1_vec = Vec3(next_entity.start_point)
                    next_e_p2_vec = Vec3(next_entity.end_point)
                    next_e_center_vec = Vec3(next_entity.dxf.center)
                    next_e_is_arc = True

                next_e_p1_tuple = (next_e_p1_vec.x, next_e_p1_vec.y)
                next_e_p2_tuple = (next_e_p2_vec.x, next_e_p2_vec.y)

                # Пытаемся соединить chain_tip_vertex_tuple с next_e_p1_tuple или next_e_p2_tuple
                connected_new_endpoint_vec = None
                calculated_bulge_for_chain_tip = 0.0

                # Порядок точек для bulge: от chain_tip_vertex_tuple к новой конечной точке
                if is_close(chain_tip_vertex_tuple, next_e_p1_tuple, tol):
                    # Соединение: chain_tip -> next_e_p1 -> next_e_p2
                    # Добавляемый сегмент: от chain_tip (эффективно next_e_p1) к next_e_p2
                    connected_new_endpoint_vec = next_e_p2_vec
                    if next_e_is_arc:
                        center_tuple = (next_e_center_vec.x, next_e_center_vec.y)
                        calculated_bulge_for_chain_tip = arc_bulge(next_e_p1_tuple, next_e_p2_tuple, center_tuple)
                    else:  # Линия
                        calculated_bulge_for_chain_tip = 0.0

                elif is_close(chain_tip_vertex_tuple, next_e_p2_tuple, tol):
                    # Соединение: chain_tip -> next_e_p2 -> next_e_p1
                    # Добавляемый сегмент: от chain_tip (эффективно next_e_p2) к next_e_p1
                    connected_new_endpoint_vec = next_e_p1_vec
                    if next_e_is_arc:
                        center_tuple = (next_e_center_vec.x, next_e_center_vec.y)
                        calculated_bulge_for_chain_tip = arc_bulge(next_e_p2_tuple, next_e_p1_tuple, center_tuple)
                    else:  # Линия
                        calculated_bulge_for_chain_tip = 0.0

                if connected_new_endpoint_vec is not None:
                    # Найдено соединение
                    # Обновляем bulge текущей последней точки в current_chain_candidate
                    current_chain_candidate[-1] = (chain_tip_vertex_vec, calculated_bulge_for_chain_tip)

                    # Добавляем новую конечную точку
                    current_chain_candidate.append((connected_new_endpoint_vec, None))  # Bulge для неё пока неизвестен

                    temp_used_indices_for_this_chain.add(j)
                    chain_extended_in_iteration = True
                    break  # Перезапускаем поиск следующего сегмента от новой конечной точки цепочки

            # После итерации по всем all_entities, если chain_extended_in_iteration == False, внутренний цикл while завершается.

        # Попытка расширения цепочки завершена. Проверяем замыкание.
        # Последняя добавленная точка: current_chain_candidate[-1][0].
        # Первая точка цепочки: current_chain_candidate[0][0].
        chain_start_vec = current_chain_candidate[0][0]
        chain_end_vec = current_chain_candidate[-1][0]  # Это (потенциально) замыкающая точка

        # Замкнутая цепочка должна иметь как минимум 2 сегмента.
        # Это значит, что current_chain_candidate будет содержать 3 элемента: (P1,b1), (P2,b2_to_P1), (P1_дубликат, None)
        if len(current_chain_candidate) > 2 and \
                is_close((chain_start_vec.x, chain_start_vec.y), (chain_end_vec.x, chain_end_vec.y), tol):
            # Цепочка замкнута. Добавляем в final_chains.
            # Bulge для замыкающего сегмента (от current_chain_candidate[-2][0] к chain_start_vec)
            # должен был быть установлен, когда chain_end_vec (дубликат chain_start_vec) был добавлен.
            final_chains.append(list(current_chain_candidate))  # Сохраняем копию
            processed_entity_indices.update(temp_used_indices_for_this_chain)  # Помечаем объекты как использованные
        # else: Цепочка не замкнута или слишком коротка, отбрасываем эту попытку.
        # Объекты из temp_used_indices_for_this_chain (если не добавлены в processed_entity_indices)
        # будут доступны для начала новых цепочек или расширения других.

    print(f"Найдено замкнутых контуров: {len(final_chains)}")

    # 4. Удаление использованных оригинальных объектов, которые теперь являются частью цепочек
    entities_to_delete = []
    # Собираем объекты для удаления по их индексам из all_entities
    for idx in sorted(list(processed_entity_indices), reverse=True):
        entities_to_delete.append(all_entities[idx])

    for ent_to_del in entities_to_delete:
        if ent_to_del.is_alive:  # Проверяем, существует ли объект еще в чертеже
            try:
                msp.delete_entity(ent_to_del)
            except ezdxf.DXFTypeError:
                # Это может произойти, если объект уже был удален (например, исходный CIRCLE)
                print(f"Предупреждение: Не удалось удалить объект {ent_to_del.dxf.handle}, возможно, уже удален.")
    print(f"Удалено использованных объектов LINE/ARC: {len(entities_to_delete)}")

    # 5. Добавление LWPOLYLINE для найденных цепочек
    for chain_idx, complete_chain in enumerate(final_chains):
        vertices_for_lwpolyline = []
        # complete_chain имеет вид [(v1,b1), (v2,b2), ..., (vk, bk_to_v1), (v1_дубликат, None)]
        # Нам нужны точки v1, v2, ..., vk с их соответствующими bulge b1, b2, ..., bk_to_v1.
        # Поэтому итерируем до предпоследнего элемента complete_chain.
        for i in range(len(complete_chain) - 1):
            point_vec = complete_chain[i][0]
            bulge_val = complete_chain[i][1]

            if bulge_val is None:
                # Этого не должно происходить для сегментов в завершенной цепочке, кроме bulge последнего элемента-заполнителя.
                # Однако, диапазон цикла len(complete_chain)-1 уже исключает этот последний элемент.
                # Если это произошло, значит bulge сегмента не был вычислен. По умолчанию ставим 0.
                print(f"Предупреждение: Обнаружен None bulge в цепочке {chain_idx}, вершина {i}. Используется 0.")
                bulge_val = 0.0

            vertices_for_lwpolyline.append((point_vec.x, point_vec.y, bulge_val))

        if vertices_for_lwpolyline:
            # Добавляем LWPolyline (легковесную полилинию)
            lw = msp.add_lwpolyline(
                points=vertices_for_lwpolyline,
                format='xyb',  # Формат точек: x, y, bulge
                close=True,  # Помечаем полилинию как замкнутую
                dxfattribs={"layer": "CUT"}  # Назначаем слой "CUT"
            )
        else:
            print(f"Предупреждение: Цепочка {chain_idx} пуста, LWPOLYLINE не создан.")

    doc.saveas(output_path)
    print(f"Сохранено как: {output_path}")


# --- Пример использования ---
if __name__ == "__main__":
    # При необходимости создайте фиктивный DXF для тестирования
    # Или используйте ваш существующий "тест.DXF"

    # Для тестирования можно создать простой DXF файл:
    # try:
    #     doc_test = ezdxf.new('R2010')
    #     msp_test = doc_test.modelspace()
    #     # Внешний квадрат
    #     msp_test.add_line((0,0), (10,0))
    #     msp_test.add_line((10,0), (10,10))
    #     msp_test.add_line((10,10), (0,10))
    #     msp_test.add_line((0,10), (0,0))
    #     # Внутренний круглый вырез
    #     msp_test.add_circle((5,5), radius=2)
    #     # Дуга
    #     msp_test.add_arc(center=(15,5), radius=3, start_angle=0, end_angle=90)
    #     msp_test.add_line((15+3, 5), (18,0)) # соединение с концом дуги
    #     msp_test.add_line((18,0), (15,2))    # соединение с началом дуги (для примера незамкнутой фигуры)

    #     doc_test.saveas("тест_sample.dxf")
    #     print("Создан тестовый файл тест_sample.dxf")
    #     convert_dxf_with_bulge("тест_sample.dxf", "тест_sample__prepared.DXF", tol=1e-3)

    # except ImportError:
    #    print("Библиотека ezdxf не установлена. Не могу создать тестовый файл.")
    # except Exception as e:
    #    print(f"Ошибка при создании тестового файла: {e}")

    # Обработка вашего файла
    # Убедитесь, что "тест.DXF" находится в той же папке, что и скрипт, или укажите полный путь.
    input_file = "2.DXF"
    output_file = "тест_2.DXF"  # Изменил имя выходного файла для новой версии

    # Возможно, вам потребуется настроить допуск 'tol' в зависимости от точности вашего чертежа и единиц измерения.
    # 1e-2 это 0.01. Если единицы чертежа - миллиметры, это 0.01мм.
    # Если единицы - метры, это 1см, что может быть слишком большим допуском.
    # Для ЧПУ, более высокая точность, например 1e-4 или 1e-6, может быть предпочтительнее, если чертежи точны.
    convert_dxf_with_bulge(input_file, output_file, tol=1e-3)