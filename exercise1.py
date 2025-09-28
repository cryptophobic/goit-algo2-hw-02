import random


def find_min_max(arr, left, right):
    # Якщо в підмасиві лише один елемент
    if left == right:
        return arr[left], arr[left]

    # Якщо два елементи — порівняти напряму
    if right == left + 1:
        if arr[left] < arr[right]:
            return arr[left], arr[right]
        else:
            return arr[right], arr[left]

    # Інакше розділити масив на дві частини
    mid = (left + right) // 2
    min1, max1 = find_min_max(arr, left, mid)
    min2, max2 = find_min_max(arr, mid + 1, right)

    # Об’єднати результати
    return min(min1, min2), max(max1, max2)


# Обгортка для зручності
def min_max(arr):
    if not arr:
        raise ValueError("Масив не може бути порожнім")
    return find_min_max(arr, 0, len(arr) - 1)

low, high = -100000, 100000
n = 1000

for _ in range(10):
    rand_list = [random.randint(low, high) for _ in range(n)]
    print(min_max(rand_list))
