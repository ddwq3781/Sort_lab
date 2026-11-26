"""
Пошаговые версии алгоритмов для анимации.

Каждая функция — генератор: после каждого значимого действия (сравнение,
обмен, запись) она делает yield a, active, где
    a - текущее состояние массива,
    active - кортеж индексов, которые сейчас обрабатываются (подсвечиваются).

Массив изменяется на месте 
"""

from algorithms import (NAME_BUBBLE, NAME_SELECTION, NAME_INSERTION,
                        NAME_MERGE, NAME_QUICK, NAME_HEAP)


def bubble(a):
    n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            yield a, (j, j + 1)
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
                yield a, (j, j + 1)
        if not swapped:
            break


def selection(a):
    n = len(a)
    for i in range(n - 1):
        m = i
        for j in range(i + 1, n):
            yield a, (m, j)
            if a[j] < a[m]:
                m = j
        if m != i:
            a[i], a[m] = a[m], a[i]
            yield a, (i, m)


def insertion(a):
    for i in range(1, len(a)):
        j = i
        while j > 0:
            yield a, (j - 1, j)
            if a[j - 1] > a[j]:
                a[j - 1], a[j] = a[j], a[j - 1]
                yield a, (j - 1, j)
                j -= 1
            else:
                break


def merge(a):
    n = len(a)
    width = 1
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            left, right = a[lo:mid], a[mid:hi]
            i = j = 0
            k = lo
            while i < len(left) and j < len(right):
                if left[i] <= right[j]:
                    a[k] = left[i]
                    i += 1
                else:
                    a[k] = right[j]
                    j += 1
                yield a, (k,)
                k += 1
            while i < len(left):
                a[k] = left[i]
                i += 1
                yield a, (k,)
                k += 1
            while j < len(right):
                a[k] = right[j]
                j += 1
                yield a, (k,)
                k += 1
        width *= 2


def quick(a):
    stack = [(0, len(a) - 1)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        x, y, z = a[lo], a[(lo + hi) // 2], a[hi]
        pivot = sorted((x, y, z))[1]  # медиана из трёх
        lt, i, gt = lo, lo, hi
        while i <= gt:
            yield a, (i, lt, gt)
            if a[i] < pivot:
                a[lt], a[i] = a[i], a[lt]
                lt += 1
                i += 1
                yield a, (i - 1, lt - 1)
            elif a[i] > pivot:
                a[i], a[gt] = a[gt], a[i]
                gt -= 1
                yield a, (i, gt + 1)
            else:
                i += 1
        stack.append((lo, lt - 1))
        stack.append((gt + 1, hi))


def _sift_down(a, root, end):
    while True:
        child = 2 * root + 1
        if child >= end:
            return
        if child + 1 < end and a[child] < a[child + 1]:
            child += 1
        yield a, (root, child)
        if a[root] < a[child]:
            a[root], a[child] = a[child], a[root]
            yield a, (root, child)
            root = child
        else:
            return


def heap(a):
    n = len(a)
    for start in range(n // 2 - 1, -1, -1):
        yield from _sift_down(a, start, n)
    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        yield a, (0, end)
        yield from _sift_down(a, 0, end)


# Какие алгоритмы анимируем
VISUAL_SORTS = {
    NAME_BUBBLE: bubble,
    NAME_SELECTION: selection,
    NAME_INSERTION: insertion,
    NAME_MERGE: merge,
    NAME_QUICK: quick,
    NAME_HEAP: heap,
}
