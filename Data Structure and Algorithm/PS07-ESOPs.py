import random

# Checks if a number is a palindrome.
def is_number_palindrome(number):
    number_str = str(number)
    return number_str == number_str[::-1]

# Calculates the sum of the digits of a number.
def calculate_sum_of_digits(number):
    return sum(int(digit) for digit in str(number))

# Determines the eligibility of an employee ID based on the given criteria.
def determine_employee_eligibility(employee_id):
    eligibility_groups = []
    
    is_palindrome = is_number_palindrome(employee_id)
    sum_digits = calculate_sum_of_digits(employee_id)
    
    if is_palindrome:
        eligibility_groups.append("Group 1 (Palindrome)")
    if employee_id % 25 == 0:
        eligibility_groups.append("Group 2 (Divisible by 25)")
    if sum_digits % 5 == 0:
        eligibility_groups.append("Group 3 (Sum divisible by 5)")
    if is_palindrome and sum_digits % 5 == 0:
        eligibility_groups.append("Eligible for extra 10% ESOPs")
    
    return eligibility_groups

# Uses Divide and Conquer to process a list of employee IDs and determine eligibility for each.
def process_employee_ids(employee_ids):
    if len(employee_ids) == 1:
        emp_id = employee_ids[0]
        return {emp_id: determine_employee_eligibility(emp_id)}
    
    mid = len(employee_ids) // 2
    left_part = process_employee_ids(employee_ids[:mid])
    right_part = process_employee_ids(employee_ids[mid:])
    
    return {**left_part, **right_part}

# Reads employee IDs from a file, processes them, and writes eligibility results to an output file.
def main(input_file, output_file):
    try:
        # Read employee IDs from the input file
        with open(input_file, 'r') as file:
            employee_ids = [int(line.strip()) for line in file if 10000 <= int(line.strip()) <= 99999]

        # Process eligibility for each employee ID using Divide and Conquer
        eligibility_dict = process_employee_ids(employee_ids)

        # Categorize employee IDs into different groups
        palindrome_group = [eid for eid, groups in eligibility_dict.items() if "Group 1 (Palindrome)" in groups]
        divisible_by_25_group = [eid for eid, groups in eligibility_dict.items() if "Group 2 (Divisible by 25)" in groups]
        sum_divisible_by_5_group = [eid for eid, groups in eligibility_dict.items() if "Group 3 (Sum divisible by 5)" in groups]
        extra_esop_group = [eid for eid, groups in eligibility_dict.items() if "Eligible for extra 10% ESOPs" in groups]
        
        total_eligible = len(set(palindrome_group + divisible_by_25_group + sum_divisible_by_5_group))
        sorted_eligible_ids = sorted(set(palindrome_group + divisible_by_25_group + sum_divisible_by_5_group), reverse=True)
        
        # Write results to the output file
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(f"1. Total eligible Employees count: {total_eligible}\n")
            file.write(f"Group 1: {len(palindrome_group)}\n")
            file.write(f"Group 2: {len(divisible_by_25_group)}\n")
            file.write(f"Group 3: {len(sum_divisible_by_5_group)}\n\n")
            
            file.write("2. Eligible employee IDs:\n")
            file.write(f"Group 1: Palindrome: {', '.join(map(str, random.sample(palindrome_group, min(5, len(palindrome_group)))))}\n")
            file.write(f"Group 2: Divisible by 25: {', '.join(map(str, random.sample(divisible_by_25_group, min(5, len(divisible_by_25_group)))))} \n")
            file.write(f"Group 3: Sum divisible by 5: {', '.join(map(str, random.sample(sum_divisible_by_5_group, min(5, len(sum_divisible_by_5_group)))))} \n\n")
            
            file.write(f"3. Eligible IDs in descending order: {', '.join(map(str, sorted_eligible_ids[:15]))}\n\n")
            
            file.write(f"4. Count eligible for extra ESOPs: {len(extra_esop_group)}\n")
            if extra_esop_group:
                file.write(f"Top Extra ESOP Eligible: {', '.join(map(str, sorted(extra_esop_group)[:3]))}\n\n")
            
            # Example check for an employee ID
            example_employee_id = 14258
            example_eligibility = determine_employee_eligibility(example_employee_id)
            file.write(f"5. {example_employee_id} – This employee ID is eligible for ESOPs and belongs to {', '.join(example_eligibility)}\n")
    
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except ValueError:
        print("Error: Invalid data in the input file. Ensure all lines contain valid integers.")

if __name__ == "__main__":
    input_file = "inputPS07.txt"
    output_file = "outputPS07.txt"
    main(input_file, output_file)