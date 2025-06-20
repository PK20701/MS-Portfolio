#Write a Python function to find the factorial of a number using recursion.

def factorial(n):
    """Calculates the factorial of a non-negative integer using recursion.

    Args:
        n (int): The non-negative integer to calculate the factorial of.

    Returns:
        int: The factorial of n.
    """

    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)

# Example usage:
number = 5
result = factorial(number)
print(f"The factorial of {number} is {result}") 
