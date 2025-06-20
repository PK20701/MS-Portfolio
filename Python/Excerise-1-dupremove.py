# Write a Python program to remove duplicates from a list while preserving the original order.

def remove_duplicates(lst):
  """Removes duplicates from a list while preserving order.

  Args:
    lst: The input list.

  Returns:
    A new list with duplicates removed.
  """

  seen = set()
  result = []
  for item in lst:
    if item not in seen:
      seen.add(item)
      result.append(item)
  return result


# Example usage:
my_list = [1, 2, 2, 3, 4, 3]
result = remove_duplicates(my_list)
print(result)  # Output: [1, 2, 3, 4]