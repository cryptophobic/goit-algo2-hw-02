from __future__ import annotations
from typing import List, Dict, Tuple, Callable
import random

from exercise2 import optimize_printing


# ---------- Генератори вхідних даних ----------

def gen_random_jobs(
    n: int,
    *,
    id_prefix: str = "M",
    vol_range: Tuple[int, int] = (20, 250),
    time_range: Tuple[int, int] = (30, 240),
    priorities: Tuple[int, ...] = (1, 2, 3),
    seed: int | None = 42
) -> List[Dict]:
    """Простий генератор випадкових задач."""
    if seed is not None:
        random.seed(seed)
    jobs = []
    for i in range(1, n + 1):
        jobs.append({
            "id": f"{id_prefix}{i}",
            "volume": random.randint(*vol_range),
            "priority": random.choice(priorities),
            "print_time": random.randint(*time_range),
        })
    return jobs

def build_edge_tests(constraints: Dict) -> Dict[str, List[Dict]]:
    """Набір показових пограничних сценаріїв (як у QA)."""
    MAXV = constraints["max_volume"]
    MAXI = constraints["max_items"]

    # helpers
    def j(i, v, p, t): return {"id": f"M{i}", "volume": v, "priority": p, "print_time": t}

    tests = {}

    # 1) Рівні пріоритети, точне попадання у сумарний об’єм (одна партія)
    #    Об’єм двох перших рівно MAXV, час партії = max(120, 90)=120
    tests["exact_volume_fit"] = [
        j(1, MAXV - 150, 1, 120),
        j(2, 150,        1,  90),
    ]

    # 2) Спліт через max_items (досягли ліміту кількості, хай навіть є запас по об’єму)
    base_v = max(1, MAXV // MAXI - 1)  # невеличкі, щоб об’єм не заважав
    tests["split_by_item_limit"] = [
        j(1, base_v, 1, 50),
        j(2, base_v, 1, 60),
        j(3, base_v, 1, 70),  # має піти у наступну партію, якщо MAXI=2
    ]

    # 3) Спліт через об’єм (перевищуємо MAXV, хоча по кількості ще можна)
    #    Перші дві разом > MAXV → flush перед другою
    big = MAXV - 10
    tests["split_by_volume_limit"] = [
        j(1, big, 1, 80),
        j(2, 20,  1, 40),
        j(3, 30,  1, 30),
    ]

    # 4) Велика модель рівно MAXV + дрібні навколо (кожна велика займає партію сама)
    tests["single_equals_max_volume"] = [
        j(1, MAXV, 1, 100),
        j(2, 10,   1,  30),
        j(3, 10,   1,  20),
    ]

    # 5) Змішані пріоритети (перевірка, що 1-и йдуть перед 2-ми, а 2-і перед 3-ми)
    tests["mixed_priorities_ordering"] = [
        j(1, 100, 2, 120),
        j(2,  80, 1,  40),
        j(3,  50, 3,  60),
        j(4,  60, 1,  30),
    ]

    # 6) Багато дрібних — кілька партій (і по кількості, і по об’єму)
    unit_v = max(1, MAXV // (MAXI * 2))  # так, щоб уміщалось декілька батчів
    tests["many_small_items"] = [
        j(i, unit_v, 1, 20 + i * 5) for i in range(1, 8)
    ]

    # 7) Один елемент НЕ вміщується сам по собі (очікуємо ValueError)
    tests["single_over_capacity"] = [j(1, MAXV + 1, 1, 100)]

    # 8) max_items == 1 (дегенеративний режим: усе поодинці; сума часів)
    if MAXI >= 1:
        tests["degenerate_items_eq_1"] = [
            j(1, min(MAXV, 50), 1, 10),
            j(2, min(MAXV, 60), 1, 20),
            j(3, min(MAXV, 70), 1, 30),
        ]

    # 9) Стабільність порядку при однакових пріоритетах і часах
    tests["stable_order_same_params"] = [
        j(1, 40, 1, 60),
        j(2, 40, 1, 60),
        j(3, 40, 1, 60),
    ]

    # 10) Невалідні значення volume/print_time (очікуємо ValueError)
    tests["invalid_values"] = [
        j(1, 0,   1, 10),
        j(2, -10, 1, 20),
        j(3, 30,  1,  0),
    ]

    return tests

# ---------- Верифікації/перевірки результатів ----------

def assert_valid_schedule(print_jobs: List[Dict], constraints: Dict, result: Dict, *, forbid_mixing: bool = True):
    ids = [j["id"] for j in print_jobs]
    id_to_job = {j["id"]: j for j in print_jobs}
    order = result["print_order"]
    total_time = result["total_time"]

    assert len(order) == len(ids), f"Довжина порядку не збігається: {len(order)} != {len(ids)}"
    assert set(order) == set(ids), f"Набори id різні: {set(order)} vs {set(ids)}"

    max_volume = constraints["max_volume"]
    max_items = constraints["max_items"]

    cur_items = 0
    cur_vol = 0.0
    cur_tmax = 0
    recomputed_total = 0

    def flush():
        nonlocal cur_items, cur_vol, cur_tmax, recomputed_total
        if cur_items > 0:
            recomputed_total += cur_tmax
            cur_items = 0
            cur_vol = 0.0
            cur_tmax = 0

    prev_priority = None

    for mid in order:
        job = id_to_job[mid]

        # 🔧 нове: примусовий flush при зміні пріоритету, якщо мікс заборонено
        if forbid_mixing and prev_priority is not None and job["priority"] != prev_priority:
            flush()

        fits_items = (cur_items + 1) <= max_items
        fits_volume = (cur_vol + job["volume"]) <= max_volume
        if not (fits_items and fits_volume):
            flush()

        assert job["volume"] <= max_volume and max_items >= 1, "Окреме завдання не вміщується в принтер."

        cur_items += 1
        cur_vol += job["volume"]
        cur_tmax = max(cur_tmax, job["print_time"])
        prev_priority = job["priority"]

        if cur_items == max_items:
            flush()

    flush()

    assert recomputed_total == total_time, f"total_time неконсистентний: {recomputed_total} != {total_time}"

    if forbid_mixing:
        pr = [id_to_job[i]["priority"] for i in order]
        assert all(pr[i] <= pr[i+1] for i in range(len(pr)-1)), f"Порушено порядок пріоритетів: {pr}"

# ---------- Запуск прикладів і fuzz ----------

def run_edge_tests(optimize_printing: Callable, constraints: Dict):
    tests = build_edge_tests(constraints)
    for name, jobs in tests.items():
        print(f"\n=== {name} ===")
        try:
            res = optimize_printing(jobs, constraints)
            print("Порядок:", res["print_order"])
            print("Час   :", res["total_time"])
            # для наших демо — за замовчуванням пріоритети не змішуються
            if name not in ("single_over_capacity", "invalid_values"):
                assert_valid_schedule(jobs, constraints, res, forbid_mixing=True)
        except Exception as e:
            print("Виняток:", type(e).__name__, str(e))

def run_fuzz(optimize_printing: Callable, iterations: int = 200, seed: int = 123):
    rnd = random.Random(seed)
    for it in range(1, iterations + 1):
        constraints = {
            "max_volume": rnd.randint(80, 400),
            "max_items": rnd.choice([1, 2, 3, 4])
        }
        n = rnd.randint(1, 10)
        jobs = gen_random_jobs(
            n,
            vol_range=(1, max(5, constraints["max_volume"])),
            time_range=(5, 240),
            priorities=(1, 2, 3),
            seed=rnd.randint(0, 10**9),
        )
        try:
            res = optimize_printing(jobs, constraints)
            assert_valid_schedule(jobs, constraints, res, forbid_mixing=True)
        except AssertionError as ae:
            print("\n[FUZZ FAIL @ iter", it, "]")
            print("constraints:", constraints)
            print("jobs:", jobs)
            raise
        except ValueError:
            # ок: можливі кейси, коли окреме завдання > max_volume
            pass

if __name__ == "__main__":
    # Підстав тут свою реалізацію optimize_printing (імпорт або в тому ж файлі).
    # Для демо — скористайся constraints з умови:
    constraints = {"max_volume": 300, "max_items": 2}

    # Твої базові 3 тести (як у прикладі з умови):
    test1_jobs = [
        {"id": "M1", "volume": 100, "priority": 1, "print_time": 120},
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},
        {"id": "M3", "volume": 120, "priority": 1, "print_time": 150},
    ]
    test2_jobs = [
        {"id": "M1", "volume": 100, "priority": 2, "print_time": 120},
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},
        {"id": "M3", "volume": 120, "priority": 3, "print_time": 150},
    ]
    test3_jobs = [
        {"id": "M1", "volume": 250, "priority": 1, "print_time": 180},
        {"id": "M2", "volume": 200, "priority": 1, "print_time": 150},
        {"id": "M3", "volume": 180, "priority": 2, "print_time": 120},
    ]

    # Приклади запуску:
    res1 = optimize_printing(test1_jobs, constraints); print(res1)
    res2 = optimize_printing(test2_jobs, constraints); print(res2)
    res3 = optimize_printing(test3_jobs, constraints); print(res3)

    # Edge-тести:
    run_edge_tests(optimize_printing, constraints)

    # Fuzz:
    run_fuzz(optimize_printing, iterations=500)
