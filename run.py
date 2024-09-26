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

def apply_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Optimized leave application logic by caching date columns and minimizing API calls.
    """
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    # Fetch employee data once
    employee_names = sheet.col_values(1)  # Employee names in column 1
    shifts = sheet.col_values(2)  # Shifts in column 2
    
    # Find the employee row
    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        print(f"Employee {employee_name} not found.")
        return

    # Cache date columns to minimize API calls
    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)

    workdays_count = 0

    # Process each day in the requested range
    current_date = start_date_obj
    while current_date <= end_date_obj:
        if is_employee_due_to_work(shift, current_date):
            workdays_count += 1
            if workdays_count > 8:
                print(f"Leave denied for {employee_name}: Exceeds 8 workdays.")
                return

            # Get the date column and leave status in batches
            date_col = date_columns.get(current_date)
            if date_col:
                leave_statuses = sheet.col_values(date_col)
                if leave_statuses[employee_row - 1] == "Leave":
                    print(f"Leave already booked on {current_date.strftime('%Y-%m-%d')}")
                else:
                    sheet.update_cell(employee_row, date_col, "Leave")
                    print(f"Leave approved for {employee_name} on {current_date.strftime('%Y-%m-%d')}")

        current_date += timedelta(days=1)

def request_leave():
    """
    CLI function to request leave by taking inputs from the user and applying leave.
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    start_date = input("Enter start date of leave (YYYY-MM-DD), e.g., '2024-01-01': ")
    end_date = input("Enter end date of leave (YYYY-MM-DD), e.g., '2024-01-08': ")
    shift = input("Enter employee's shift (Green/Red/Blue/Yellow), e.g., 'Green': ")

    apply_leave(holiday, employee_name, start_date, end_date, shift)

def main():
    """
    Main function to run the CLI for the leave system.
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
