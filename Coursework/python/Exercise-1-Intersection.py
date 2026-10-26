#Given two lists, write a Python function to find the intersection (common elements) of the lists.

def find_intersection(list1, list2):
    """Finds the intersection of two lists.

    Args:
        list1: The first list.
        list2: The second list.

    Returns:
        A list containing the   
 common elements of both lists.
    """

    intersection = []
    for element in list1:
        if element in list2:
            intersection.append(element)
    return intersection

# Example usage:
list1 = [1, 2, 3, 4]
list2 = [3, 4, 5, 6]
result = find_intersection(list1, list2)
print(result)  # Output: [3, 4]