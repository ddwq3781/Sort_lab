# Простые сортировки, O(n^2)

def bubble_sort(data):
    """Сортировка пузырьком"""
    a = list(data)
    n = len(a)
    comparisons = moves = 0
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            comparisons += 1
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                moves += 1
                swapped = True
        if not swapped:
            break
    return a, comparisons, moves


def selection_sort(data):
    """Сортировка выбором"""
    a = list(data)
    n = len(a)
    comparisons = moves = 0
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            comparisons += 1
            if a[j] < a[min_idx]:
                min_idx = j
        if min_idx != i:
            a[i], a[min_idx] = a[min_idx], a[i]
            moves += 1
    return a, comparisons, moves


def insertion_sort(data):
    """Сортировка вставками"""
    a = list(data)
    comparisons = moves = 0
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0:
            comparisons += 1
            if a[j] > key:
                a[j + 1] = a[j]
                moves += 1
                j -= 1
            else:
                break
        if j + 1 != i:
            a[j + 1] = key
            moves += 1
    return a, comparisons, moves



# Эффективные сортировки, O(n log n)


def merge_sort(data):
    """Сортировка слиянием (нисходящая-восходящая, без рекурсии)"""
    a = list(data)
    n = len(a)
    comparisons = moves = 0
    buf = a[:]
    width = 1
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                comparisons += 1
                if a[i] <= a[j]:
                    buf[k] = a[i]
                    i += 1
                else:
                    buf[k] = a[j]
                    j += 1
                k += 1
                moves += 1
            while i < mid:
                buf[k] = a[i]
                i += 1
                k += 1
                moves += 1
            while j < hi:
                buf[k] = a[j]
                j += 1
                k += 1
                moves += 1
        a, buf = buf, a  # результат прохода теперь лежит в a
        width *= 2
    return a, comparisons, moves


def quick_sort(data):
    """
    Быстрая сортировка.
    """
    a = list(data)
    n = len(a)
    comparisons = moves = 0
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue

        #выбор опорного элемента: медиана из трёх 
        x, y, z = a[lo], a[(lo + hi) // 2], a[hi]
        comparisons += 3
        if x < y:
            if y < z:
                pivot = y
            elif x < z:
                pivot = z
            else:
                pivot = x
        else:
            if x < z:
                pivot = x
            elif y < z:
                pivot = z
            else:
                pivot = y

   
        lt, i, gt = lo, lo, hi
        while i <= gt:
            comparisons += 1
            if a[i] < pivot:
                a[lt], a[i] = a[i], a[lt]
                moves += 1
                lt += 1
                i += 1
            else:
                comparisons += 1
                if a[i] > pivot:
                    a[i], a[gt] = a[gt], a[i]
                    moves += 1
                    gt -= 1
                else:
                    i += 1

        stack.append((lo, lt - 1))
        stack.append((gt + 1, hi))
    return a, comparisons, moves


def _sift_down(a, root, end):
    """Вспомогательная функция пирамиды: просеивание элемента вниз"""
    comparisons = moves = 0
    while True:
        child = 2 * root + 1
        if child >= end:
            break
        if child + 1 < end:
            comparisons += 1
            if a[child] < a[child + 1]:
                child += 1
        comparisons += 1
        if a[root] < a[child]:
            a[root], a[child] = a[child], a[root]
            moves += 1
            root = child
        else:
            break
    return comparisons, moves


def heap_sort(data):
    """Пирамидальная сортировка"""
    a = list(data)
    n = len(a)
    comparisons = moves = 0
    for start in range(n // 2 - 1, -1, -1):
        c, m = _sift_down(a, start, n)
        comparisons += c
        moves += m
    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        moves += 1
        c, m = _sift_down(a, 0, end)
        comparisons += c
        moves += m
    return a, comparisons, moves



# Линейная сортировка


def counting_sort(data):
    """
    Сортировка подсчётом — O(n + k), k - размах значений.
    только с целыми числами (в том числе отрицательными).
    """
    a = list(data)
    if not a:
        return a, 0, 0
    lo, hi = min(a), max(a)
    counts = [0] * (hi - lo + 1)
    for v in a:
        counts[v - lo] += 1
    result = []
    moves = len(a)  # запись в массив counts
    for offset, c in enumerate(counts):
        if c:
            result.extend([offset + lo] * c)
            moves += c
    return result, 0, moves  # сравнений между элементами нет


# Реестр алгоритмов и их теоретическая сложность

NAME_BUBBLE = "Пузырьком"
NAME_SELECTION = "Выбором"
NAME_INSERTION = "Вставками"
NAME_MERGE = "Слиянием"
NAME_QUICK = "Быстрая"
NAME_HEAP = "Пирамидальная"
NAME_COUNTING = "Подсчётом"

ALGORITHMS = {
    NAME_BUBBLE: bubble_sort,
    NAME_SELECTION: selection_sort,
    NAME_INSERTION: insertion_sort,
    NAME_MERGE: merge_sort,
    NAME_QUICK: quick_sort,
    NAME_HEAP: heap_sort,
    NAME_COUNTING: counting_sort,
}

THEORY = {
    NAME_BUBBLE: "O(n²)",
    NAME_SELECTION: "O(n²)",
    NAME_INSERTION: "O(n²)",
    NAME_MERGE: "O(n log n)",
    NAME_QUICK: "O(n log n)",
    NAME_HEAP: "O(n log n)",
    NAME_COUNTING: "O(n + k)",
}
