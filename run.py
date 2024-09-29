import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# Set up Google Sheets API connection
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

CREDS = Credentials.from_service_account_file("creds.json")
SCOPED_CREDS = CREDS.with_scopes(SCOPE)
GSPREAD_CLIENT = gspread.authorize(SCOPED_CREDS)
SHEET = GSPREAD_CLIENT.open("holiday_book")

# Get the "holiday" worksheet
holiday = SHEET.worksheet("holiday")

# Define base dates for the start of the shift cycles
BASE_DATE_GREEN_RED = datetime.strptime("2024-01-04", "%Y-%m-%d")  # Day 1 for Green/Red shifts
BASE_DATE_BLUE_YELLOW = datetime.strptime("2023-01-31", "%Y-%m-%d")  # Day 1 for Blue/Yellow shifts

def find_date_column(sheet, date):
    """
    Finds the column number for a given date in the Google Sheet.
    """
    date_str = date.strftime("%d %b")  # Match the format used in your sheet (e.g., '01 Jan')
    try:
        date_cell = sheet.find(date_str)
        return date_cell.col
    except:
        return None

def cache_date_columns(sheet, start_date, end_date):
    """
    Caches date columns for all dates in the given range to minimize API calls.
    """
    date_columns = {}
    current_date = start_date
    while current_date <= end_date:
        date_col = find_date_column(sheet, current_date)
        if date_col:
            date_columns[current_date] = date_col
        current_date += timedelta(days=1)
    return date_columns

def is_employee_due_to_work(employee_shift, date):
    """
    Checks whether an employee is due to work on a given date based on the shift cycle.
    """
    if employee_shift in ["Red", "Green"]:
        days_since_base = (date - BASE_DATE_GREEN_RED).days
    elif employee_shift in ["Blue", "Yellow"]:
        days_since_base = (date - BASE_DATE_BLUE_YELLOW).days
    else:
        return False  # Invalid shift

    shift_cycle_day = days_since_base % 8  # 8-day shift cycle

    # Red/Green shifts work on days 0-3, Blue/Yellow shifts work on days 4-7
    if employee_shift in ["Red", "Green"]:
        return shift_cycle_day < 4  # Work on days 0-3
    elif employee_shift in ["Blue", "Yellow"]:
        return shift_cycle_day >= 4  # Work on days 4-7
    return False

def format_input(input_value):
    """
    Formats and standardizes user inputs for names and shifts.
    """
    return input_value.strip().title()  # Converts strings to Title Case and removes extra spaces

def validate_shift(sheet, employee_name, expected_shift):
    """
    Validates if the shift entered in the CLI matches the employee's actual shift in the Google Sheet.
    """
    employee_names = sheet.col_values(1)  # Employee names in column 1
    shifts = sheet.col_values(2)  # Shifts in column 2

    try:
        employee_row = employee_names.index(employee_name)  # Find the row for the employee
        actual_shift = shifts[employee_row]  # Get the actual shift from the sheet
        return actual_shift == expected_shift
    except ValueError:
        return False  # Employee not found

def validate_date(date_str):
    """
    Validates if the given date string is in the format 'YYYY-MM-DD' and within the year 2024.
    Returns a datetime object if valid, otherwise returns None.
    """
    try:
        # Attempt to parse the date string
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Check if the date is within the year 2024
        if date_obj.year != 2024:
            print(f"Error: The date must be in the year 2024. You entered {date_obj.year}.")
            return None
        return date_obj
    except ValueError:
        # Catch invalid date formats and non-existing dates
        print("Error: Invalid date format or non-existent date. Please enter the date in 'YYYY-MM-DD' format.")
        return None

def apply_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Applies leave for an employee, ensuring the employee is scheduled to work on the requested dates.
    If the employee is already marked as 'Off', notify the user and do not apply leave for those days.
    """
    employee_name = format_input(employee_name)  # Standardize employee name input
    shift = format_input(shift)  # Standardize shift input

    if not validate_shift(sheet, employee_name, shift):
        print(f"Leave request failed: {employee_name} does not belong to the {shift} shift.")
        return

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    # Fetch employee data once
    employee_names = sheet.col_values(1)  # Employee names in column 1
    total_leave_column = sheet.col_values(3)  # Total leave in column 3
    leave_taken_column = sheet.col_values(4)  # Leave taken in column 4 (auto-calculated)

    # Find the employee row
    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        print(f"Employee {employee_name} not found. Please ensure the name is correctly formatted.")
        return

    # Display leave statistics before applying leave
    total_leave = total_leave_column[employee_row - 1]  # Total leave allocated
    leave_taken = leave_taken_column[employee_row - 1]  # Current leave taken
    print(f"Employee: {employee_name}, Shift: {shift}")
    print(f"Total Leave: {total_leave}, Leave Taken: {leave_taken}")

    # Cache date columns to minimize API calls
    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)

    workdays_count = 0

    # Process each day in the requested range
    current_date = start_date_obj
    while current_date <= end_date_obj:
        date_col = date_columns.get(current_date)
        if date_col:
            leave_statuses = sheet.col_values(date_col)
            current_status = leave_statuses[employee_row - 1]

            # Check if the employee is already marked as "Off"
            if current_status == "Off":
                print(f"Employee is already planned to be off work on {current_date.strftime('%Y-%m-%d')}. Leave not needed.")
            elif current_status == "Leave":
                print(f"Leave already booked on {current_date.strftime('%Y-%m-%d')}")
            else:
                if is_employee_due_to_work(shift, current_date):
                    workdays_count += 1
                    if workdays_count > 8:
                        print(f"Leave denied for {employee_name}: Exceeds 8 workdays.")
                        return
                    sheet.update_cell(employee_row, date_col, "Leave")
                    print(f"Leave approved for {employee_name} on {current_date.strftime('%Y-%m-%d')}")

        current_date += timedelta(days=1)

    # Display updated leave taken count (which is automatically updated by the formula)
    leave_taken_column = sheet.col_values(4)  # Refresh the leave taken data
    updated_leave_taken = leave_taken_column[employee_row - 1]
    print(f"Updated Leave Taken: {updated_leave_taken} days.")

def cancel_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Cancels leave for an employee and validates the shift before processing.
    Ensures that leave has been booked on the requested dates.
    """
    employee_name = format_input(employee_name)  # Standardize employee name input
    shift = format_input(shift)  # Standardize shift input

    if not validate_shift(sheet, employee_name, shift):
        print(f"Leave cancellation failed: {employee_name} does not belong to the {shift} shift.")
        return

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    # Fetch employee data once
    employee_names = sheet.col_values(1)  # Employee names in column 1

    # Find the employee row
    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        print(f"Employee {employee_name} not found.")
        return

    # Cache date columns to minimize API calls
    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)

    # Process each day in the requested range
    current_date = start_date_obj
    while current_date <= end_date_obj:
        date_col = date_columns.get(current_date)
        if date_col:
            leave_statuses = sheet.col_values(date_col)
            # Check if leave was booked
            if leave_statuses[employee_row - 1] == "Leave":
                sheet.update_cell(employee_row, date_col, "")  # Remove the 'Leave' status
                print(f"Leave canceled for {employee_name} on {current_date.strftime('%Y-%m-%d')}.")
            else:
                print(f"No leave found for {employee_name} on {current_date.strftime('%Y-%m-%d')}.")

        current_date += timedelta(days=1)

def request_leave():
    """
    CLI function to request leave by taking inputs from the user and applying leave.
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    shift = input("Enter employee's shift (Green/Red/Blue/Yellow), e.g., 'Green': ")

    # Get a valid start date
    while True:
        start_date = input("Enter start date of leave (YYYY-MM-DD), e.g., '2024-01-01': ")
        start_date_obj = validate_date(start_date)
        if start_date_obj:
            break

    # Get a valid end date
    while True:
        end_date = input("Enter end date of leave (YYYY-MM-DD), e.g., '2024-01-08': ")
        end_date_obj = validate_date(end_date)
        if end_date_obj and end_date_obj >= start_date_obj:
            break
        else:
            print(f"Error: The end date must be on or after the start date ({start_date}).")

    apply_leave(holiday, employee_name, start_date, end_date, shift)

def request_leave_cancellation():
    """
    CLI function to cancel pre-booked leave by taking inputs from the user.
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    shift = input("Enter employee's shift (Green/Red/Blue/Yellow), e.g., 'Green': ")

    # Get a valid start date for cancellation
    while True:
        start_date = input("Enter start date of leave to cancel (YYYY-MM-DD), e.g., '2024-01-01': ")
        start_date_obj = validate_date(start_date)
        if start_date_obj:
            break

    # Get a valid end date for cancellation
    while True:
        end_date = input("Enter end date of leave to cancel (YYYY-MM-DD), e.g., '2024-01-08': ")
        end_date_obj = validate_date(end_date)
        if end_date_obj and end_date_obj >= start_date_obj:
            break
        else:
            print(f"Error: The end date must be on or after the start date ({start_date}).")

    cancel_leave(holiday, employee_name, start_date, end_date, shift)

def main():
    """
    Main function to run the CLI for the leave system.
    """
    while True:
        print("\nOptions:")
        print("1. Request leave")
        print("2. Cancel leave")
        print("3. Exit")

        choice = input("Enter your choice: ")
        if choice == '1':
            request_leave()
        elif choice == '2':
            request_leave_cancellation()
        elif choice == '3':
            print("Exiting system.")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()
