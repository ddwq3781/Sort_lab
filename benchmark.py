"""
Модуль замеров: запускает алгоритмы на данных разных типов и размеров,
собирает время, число сравнений и перестановок, проверяет корректность
"""

from __future__ import annotations

import csv
import math
import time
from dataclasses import dataclass

from algorithms import ALGORITHMS, THEORY
from data_generators import generate


@dataclass
class Result:
    algorithm: str
    kind: str                 # тип данных
    size: int                 # размер массива n
    time_s: float | None      # среднее время, секунды (None — пропущено)
    comparisons: int | None
    moves: int | None
    correct: bool = True
    skipped: bool = False     # пропущено из-за превышения лимита времени


def measure(func, data, repeats):
    """
    Замеряет среднее время работы func(data).
    Если один прогон длится дольше 0.5 с, повторные прогоны не делаются
    Возвращает (среднее время, сравнения, перестановки, корректно ли)
    """
    times = []
    result = None
    for _ in range(max(1, repeats)):
        start = time.perf_counter()
        result = func(data)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        if elapsed > 0.5:
            break
    sorted_list, comparisons, moves = result
    correct = sorted_list == sorted(data)
    return sum(times) / len(times), comparisons, moves, correct


def run_benchmark(algorithm_names, kinds, sizes, repeats=3, time_limit=10.0,
                  seed=42, progress=None, cancel=None):
    """
    Основной цикл эксперимента

    algorithm_names — список названий из ALGORITHMS
    kinds           — список типов данных
    sizes           — размеры массивов
    repeats         — сколько раз повторять замер (берётся среднее)
    time_limit      — если алгоритм на размере n работал дольше (сек),
                      на бо́льших размерах для этого типа данных он пропускается
    progress        — функция progress(сделано, всего, сообщение)
    cancel          — threading.Event; если установлен, эксперимент прерывается

    Возвращает список Result
    """
    sizes = sorted(set(sizes))
    total = len(kinds) * len(sizes) * len(algorithm_names)
    done = 0
    results = []
    too_slow = set()  # пары (алгоритм, тип данных), которые превысили лимит

    for kind in kinds:
        for n in sizes:
            data = generate(kind, n, seed=seed)
            for name in algorithm_names:
                if cancel is not None and cancel.is_set():
                    return results
                done += 1
                if progress:
                    progress(done, total, f"{kind}, n={n}: {name}")

                if (name, kind) in too_slow:
                    results.append(Result(name, kind, n, None, None, None,
                                          correct=True, skipped=True))
                    continue

                t, cmp_, mv, ok = measure(ALGORITHMS[name], data, repeats)
                results.append(Result(name, kind, n, t, cmp_, mv, correct=ok))
                if t > time_limit:
                    too_slow.add((name, kind))
    return results


def export_csv(results, path):
    """Сохраняет результаты в CSV"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Алгоритм", "Тип данных", "n", "Время, мс",
                    "Сравнения", "Перестановки/записи", "Корректно", "Пропущено"])
        for r in results:
            w.writerow([
                r.algorithm, r.kind, r.size,
                "" if r.time_s is None else f"{r.time_s * 1000:.4f}".replace(".", ","),
                "" if r.comparisons is None else r.comparisons,
                "" if r.moves is None else r.moves,
                "да" if r.correct else "НЕТ",
                "да" if r.skipped else "",
            ])



# Анализ результатов


def empirical_exponent(sizes, times, last_points=4):
    pts = [(math.log(n), math.log(t)) for n, t in zip(sizes, times)
           if n > 0 and t is not None and t > 0]
    pts = pts[-last_points:]
    if len(pts) < 3:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    den = sum((x - mx) ** 2 for x, _ in pts)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pts) / den


def series(results, algorithm, kind):
    """Возвращает (размеры, результаты) для одной линии графика, без пропущенных"""
    rows = sorted((r for r in results
                   if r.algorithm == algorithm and r.kind == kind and not r.skipped),
                  key=lambda r: r.size)
    return rows


def build_conclusions(results):
    """Формирует текстовые выводы по результатам эксперимента"""
    if not results:
        return 

    lines = []
    kinds = []
    for r in results:
        if r.kind not in kinds:
            kinds.append(r.kind)

    wrong = [r for r in results if not r.correct]
    if wrong:
        lines.append(" ВНИМАНИЕ: найдены некорректные результаты сортировки!")
        for r in wrong:
            lines.append(f"   {r.algorithm}, {r.kind}, n={r.size}")
        lines.append("")
    else:
        lines.append(" Все алгоритмы отсортировали все массивы корректно.")
        lines.append("")

    for kind in kinds:
        lines.append(f"━━━ {kind} ━━━")
        kind_res = [r for r in results if r.kind == kind and not r.skipped]
        if not kind_res:
            lines.append("  нет данных\n")
            continue

        # наибольший размер, на котором отработало хотя бы два алгоритма
        sizes = sorted({r.size for r in kind_res}, reverse=True)
        top_n = None
        for n in sizes:
            if sum(1 for r in kind_res if r.size == n) >= 2:
                top_n = n
                break
        if top_n is None:
            top_n = sizes[0]

        at_top = sorted((r for r in kind_res if r.size == top_n), key=lambda r: r.time_s)
        lines.append(f"Рейтинг по времени при n = {top_n}:")
        for place, r in enumerate(at_top, 1):
            lines.append(f"  {place}. {r.algorithm:<20} {r.time_s * 1000:>10.3f} мс")
        if len(at_top) >= 2 and at_top[0].time_s > 0:
            ratio = at_top[-1].time_s / at_top[0].time_s
            lines.append(f"  Разница между лучшим и худшим: в {ratio:,.1f} раз".replace(",", " "))

        lines.append("Эмпирический показатель k (время ≈ c·nᵏ) и теория:")
        for name in ALGORITHMS:
            rows = series(results, name, kind)
            k = empirical_exponent([r.size for r in rows], [r.time_s for r in rows])
            if k is not None:
                lines.append(f"  {name:<20} k = {k:4.2f}   (теория: {THEORY[name]})")
        lines.append("")

    skipped = sorted({(r.algorithm, r.kind) for r in results if r.skipped})
    if skipped:
        lines.append("Алгоритмы, остановленные по лимиту времени на больших n:")
        for name, kind in skipped:
            lines.append(f"  {name} — {kind}")
    return "\n".join(lines)
