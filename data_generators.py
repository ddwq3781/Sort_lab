"""
Генераторы тестовых данных.
"""

import random

KIND_RANDOM = "Случайные"
KIND_SORTED = "Отсортированные"
KIND_REVERSED = "В обратном порядке"
KIND_NEARLY = "Почти отсортированные"
KIND_FEW_UNIQUE = "Много повторов"

KINDS = [KIND_RANDOM, KIND_SORTED, KIND_REVERSED, KIND_NEARLY, KIND_FEW_UNIQUE]

DESCRIPTIONS = {
    KIND_RANDOM: "целые числа от 0 до 10·n, порядок случайный",
    KIND_SORTED: "уже отсортированы по возрастанию",
    KIND_REVERSED: "отсортированы по убыванию (худший случай для многих алгоритмов)",
    KIND_NEARLY: "отсортированы, но ~5% элементов переставлены случайно",
    KIND_FEW_UNIQUE: "только 10 различных значений, много дубликатов",
}


def generate(kind, n, seed=None):
    """Возвращает список из n целых чисел заданного типа."""
    rng = random.Random(seed)
    if n <= 0:
        return []

    if kind == KIND_RANDOM:
        return [rng.randint(0, 10 * n) for _ in range(n)]

    if kind == KIND_SORTED:
        return sorted(rng.randint(0, 10 * n) for _ in range(n))

    if kind == KIND_REVERSED:
        return sorted((rng.randint(0, 10 * n) for _ in range(n)), reverse=True)

    if kind == KIND_NEARLY:
        a = sorted(rng.randint(0, 10 * n) for _ in range(n))
        swaps = max(1, n // 20) if n > 1 else 0
        for _ in range(swaps):
            i, j = rng.randrange(n), rng.randrange(n)
            a[i], a[j] = a[j], a[i]
        return a

    if kind == KIND_FEW_UNIQUE:
        return [rng.randint(0, 9) for _ in range(n)]

    raise ValueError(f"Неизвестный тип данных: {kind!r}")
