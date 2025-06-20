#Write a Python program to count the frequency of each element in a list.
def count_frequency(lst):
    """Counts the frequency of each element in a list.

    Args:
        lst: The input list.

    Returns:
        A dictionary where keys are elements and values are their frequencies.
    """

    freq = {}
    for element in lst:
        if element in freq:
            freq[element] += 1
        else:
            freq[element] = 1
    return freq

# Example usage:
my_list = [1, 3, 2, 3, 3, 3, 4]
result = count_frequency(my_list)
print(result)  # Output: {1: 1, 2: 2, 3: 3, 4: 1}