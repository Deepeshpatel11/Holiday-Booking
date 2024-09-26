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
    
    Args:
    sheet: The Google Sheet object (worksheet).
    date: The date object for which the column needs to be found.

    Returns:
    int: The column number where the date is located in the Google Sheet, or None if not found.
    """
    date_str = date.strftime("%d %b")  # Match the format used in your sheet (e.g., '01 Jan')
    try:
        date_cell = sheet.find(date_str)
        return date_cell.col
    except:
        print(f"Date {date_str} not found in the sheet.")
        return None

def count_employees_on_leave(sheet, shift, date_col):
    """
    Counts how many employees are already marked as 'Leave' for a given shift on a specific day.
    This version optimizes API usage by reading the entire shift column at once instead of cell-by-cell.
    
    Args:
    sheet: The Google Sheet object (worksheet).
    shift: The shift name ('Red', 'Green', 'Blue', 'Yellow').
    date_col: The column number corresponding to the requested date.

    Returns:
    int: The number of employees on leave for the given shift and date.
    """
    leave_count = 0

    # Read all the shift column and the date column in one API call to minimize read requests
    shift_data = sheet.col_values(2)  # Column B contains the shift
    leave_status_data = sheet.col_values(date_col)  # The date column that corresponds to the leave status

    # Loop through all the rows to count how many employees are marked "Leave"
    for i in range(1, len(shift_data)):  # Start from index 1 to skip the header
        if shift_data[i] == shift and leave_status_data[i] == "Leave":
            leave_count += 1

    return leave_count

def is_employee_due_to_work(employee_shift, date):
    """
    Checks whether an employee is due to work on a given date based on the shift cycle.
    
    Args:
    employee_shift: The employee's shift ('Red', 'Green', 'Blue', 'Yellow').
    date: The requested date to check.

    Returns:
    bool: True if the employee is due to work, False if they are off.
    """
    # Calculate how many days have passed since the base date for each shift
    if employee_shift in ["Red", "Green"]:
        days_since_base = (date - BASE_DATE_GREEN_RED).days
    elif employee_shift in ["Blue", "Yellow"]:
        days_since_base = (date - BASE_DATE_BLUE_YELLOW).days
    else:
        return False  # Invalid shift

    shift_cycle_day = days_since_base % 8  # Get the day in the current 8-day shift cycle

    # Red/Green shifts work on days 0-3, Blue/Yellow shifts work on days 4-7
    if employee_shift in ["Red", "Green"]:
        return shift_cycle_day < 4  # Work on days 0-3
    elif employee_shift in ["Blue", "Yellow"]:
        return shift_cycle_day >= 4  # Work on days 4-7
    return False

def apply_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Applies leave for an employee by checking if the leave request is valid (i.e., fewer than 2 people 
    are already on leave) and updating the Google Sheet if approved.
    
    Args:
    sheet: The Google Sheet object (worksheet).
    employee_name: The name of the employee requesting leave.
    start_date: The start date of the leave request (YYYY-MM-DD format).
    end_date: The end date of the leave request (YYYY-MM-DD format).
    shift: The shift name ('Red', 'Green', 'Blue', 'Yellow').

    Returns:
    None: The function updates the sheet if the leave is approved and prints the status of the request.
    """
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    # Find the employee's row
    try:
        employee_cell = sheet.find(employee_name)
        employee_row = employee_cell.row
    except gspread.exceptions.CellNotFound:
        print(f"Employee {employee_name} not found in the sheet.")
        return

    workdays_count = 0  # To keep track of how many workdays are counted

    # Check each day in the requested range
    current_date = start_date_obj
    while current_date <= end_date_obj:
        # Check if the employee is due to work on this date
        if is_employee_due_to_work(shift, current_date):
            workdays_count += 1

            # If the employee has already requested 8 workdays, stop the process
            if workdays_count > 8:
                print(f"Leave denied for {employee_name}: Exceeds 8 workdays.")
                return

            date_col = find_date_column(sheet, current_date)
            if date_col:
                leave_count = count_employees_on_leave(sheet, shift, date_col)
                if leave_count >= 2:
                    print(f"Leave denied for {employee_name}: More than 2 employees already on leave on {current_date.strftime('%Y-%m-%d')}.")
                    return  # Deny leave if 2 or more people are already on leave

        current_date += timedelta(days=1)

    # Approve leave and update the sheet
    current_date = start_date_obj
    while current_date <= end_date_obj:
        # Only mark leave for workdays
        if is_employee_due_to_work(shift, current_date):
            date_col = find_date_column(sheet, current_date)
            if date_col:
                sheet.update_cell(employee_row, date_col, "Leave")
        current_date += timedelta(days=1)

    print(f"Leave approved for {employee_name} covering {workdays_count} workdays.")

def request_leave():
    """
    CLI function to request leave by taking inputs from the user for the employee name, start date, end date, 
    and shift, and then calls the apply_leave function to process the request.
    
    Args:
    None: User inputs are taken interactively.

    Returns:
    None: The function calls apply_leave to handle the request and provides output to the user.
    """
    # Get all employee names from the Google Sheet to verify if the entered name exists
    employee_names = holiday.col_values(1)  # Assuming employee names are in the first column

    while True:
        employee_name = input("Enter employee name: ")

        # Check if the entered employee name exists in the holiday book
        if employee_name not in employee_names:
            print("Employee name not found. Please try again.")
            continue

        start_date = input("Enter start date of leave (YYYY-MM-DD): ")
        end_date = input("Enter end date of leave (YYYY-MM-DD): ")
        shift = input("Enter employee's shift (Green/Red/Blue/Yellow): ")

        # Apply the leave
        apply_leave(holiday, employee_name, start_date, end_date, shift)
        break

def main():
    """
    Main function to run the command-line interface (CLI) for the leave request system. 
    It displays options to request leave or exit the program.
    
    Args:
    None

    Returns:
    None: This function runs the CLI loop until the user chooses to exit.
    """
    while True:
        print("\nOptions:")
        print("1. Request leave")
        print("2. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            request_leave()
        elif choice == '2':
            print("Exiting system.")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()
