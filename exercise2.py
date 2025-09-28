from enum import unique, IntEnum
from typing import List, Dict, Tuple
from dataclasses import dataclass

@unique
class Priority(IntEnum):
    COURSE   = 1  # курсові/дипломні
    LAB      = 2  # лабораторні
    PERSONAL = 3  # особисті


@dataclass
class PrintJob:
    id: str
    volume: float
    priority: Priority
    print_time: int

@dataclass
class PrinterConstraints:
    max_volume: float
    max_items: int

def _cast_priority(value, *, job_id="<?>") -> Priority:
    try:
        return Priority(value)  # IntEnum підкине ValueError, якщо значення не з переліку
    except ValueError:
        allowed = ", ".join(f"{p.value} ({p.name})" for p in Priority)
        raise ValueError(f"Некоректний пріоритет: {value} (id={job_id}). Дозволені: {allowed}.")


def _validate_jobs(jobs: List[PrintJob]) -> None:
    if not jobs:
        raise ValueError("Список завдань порожній.")
    for j in jobs:
        if j.volume <= 0:
            raise ValueError(f"Об'єм має бути > 0 (id={j.id}).")
        if j.print_time <= 0:
            raise ValueError(f"Час друку має бути > 0 (id={j.id}).")

def _validate_constraints(c: PrinterConstraints) -> None:
    if c.max_volume <= 0:
        raise ValueError("max_volume має бути > 0.")
    if c.max_items <= 0:
        raise ValueError("max_items має бути > 0.")

def _greedy_batches_for_priority(jobs: List[PrintJob], c: PrinterConstraints) -> Tuple[List[str], int]:
    order: List[str] = []
    total_time = 0
    batch: List[PrintJob] = []
    items, vol, tmax = 0, 0.0, 0

    def flush():
        nonlocal order, total_time, batch, items, vol, tmax
        if batch:
            order.extend(j.id for j in batch)
            total_time += tmax
            batch, items, vol, tmax = [], 0, 0.0, 0

    for j in jobs:
        if j.volume > c.max_volume or c.max_items < 1:
            raise ValueError(f"Завдання {j.id} не вміщується в обмеження принтера.")
        fits = (items + 1) <= c.max_items and (vol + j.volume) <= c.max_volume
        if not fits:
            flush()
        batch.append(j)
        items += 1
        vol += j.volume
        tmax = max(tmax, j.print_time)
        if items == c.max_items:
            flush()
    flush()
    return order, total_time

def optimize_printing(print_jobs: List[Dict], constraints: Dict) -> Dict:
    jobs = [
        PrintJob(
            id=j["id"],
            volume=j["volume"],
            priority=_cast_priority(j["priority"], job_id=j["id"]),  # ← чиста валідація
            print_time=j["print_time"],
        )
        for j in print_jobs
    ]
    c = PrinterConstraints(**constraints)

    _validate_jobs(jobs)
    _validate_constraints(c)

    final_order: List[str] = []
    total_time = 0

    # Явно фіксуємо порядок рангів числовим сортуванням (на випадок, якщо додаси 0=URGENT)
    for pr in sorted(list(Priority), key=int):  # 1→2→3
        block = [j for j in jobs if j.priority is pr]
        if not block:
            continue
        o, t = _greedy_batches_for_priority(block, c)
        final_order.extend(o)
        total_time += t

    return {"print_order": final_order, "total_time": total_time}

# Тестування
def test_printing_optimization():
    # Тест 1: Моделі однакового пріоритету
    test1_jobs = [
        {"id": "M1", "volume": 100, "priority": 1, "print_time": 120},
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},
        {"id": "M3", "volume": 120, "priority": 1, "print_time": 150}
    ]

    # Тест 2: Моделі різних пріоритетів
    test2_jobs = [
        {"id": "M1", "volume": 100, "priority": 2, "print_time": 120},  # лабораторна
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},   # дипломна
        {"id": "M3", "volume": 120, "priority": 3, "print_time": 150}   # особистий проєкт
    ]

    # Тест 3: Перевищення обмежень об'єму (жодна пара не поміщається)
    test3_jobs = [
        {"id": "M1", "volume": 250, "priority": 1, "print_time": 180},
        {"id": "M2", "volume": 200, "priority": 1, "print_time": 150},
        {"id": "M3", "volume": 180, "priority": 2, "print_time": 120}
    ]

    constraints = {
        "max_volume": 300,
        "max_items": 2
    }

    print("Тест 1 (однаковий пріоритет):")
    result1 = optimize_printing(test1_jobs, constraints)
    print(f"Порядок друку: {result1['print_order']}")
    print(f"Загальний час: {result1['total_time']} хвилин")

    print("\nТест 2 (різні пріоритети):")
    result2 = optimize_printing(test2_jobs, constraints)
    print(f"Порядок друку: {result2['print_order']}")
    print(f"Загальний час: {result2['total_time']} хвилин")

    print("\nТест 3 (перевищення обмежень):")
    result3 = optimize_printing(test3_jobs, constraints)
    print(f"Порядок друку: {result3['print_order']}")
    print(f"Загальний час: {result3['total_time']} хвилин")

if __name__ == "__main__":
    test_printing_optimization()
