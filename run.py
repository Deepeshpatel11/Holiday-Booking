import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# Set up Google Sheets API connection
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

CREDS = Credentials.from_service_account_file("creds.json")
SCOPED_CREDS = CREDS.with_scopes(SCOPE)
GSPREAD_CLIENT = gspread.authorize(SCOPED_CREDS)
SHEET = GSPREAD_CLIENT.open("holiday_book")

# Get the "holiday" and "audit_trail" worksheets
holiday = SHEET.worksheet("holiday")
audit_trail = SHEET.worksheet("audit_trail")

# Define base dates for the start of the shift cycles (same for alignment)
BASE_DATE_GREEN_RED = datetime.strptime("2024-01-04", "%Y-%m-%d")
BASE_DATE_BLUE_YELLOW = BASE_DATE_GREEN_RED  # Consistent cycle alignment


def log_to_audit_trail(employee_name, action, start_date, end_date, status,
                       remarks=""):
    """
    Logs the leave request status to the
    'audit_trail' worksheet in Google Sheets.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = [timestamp, employee_name, action, start_date, end_date, status,
               remarks]
    audit_trail.append_row(new_row)
    print(f"Logged action to audit_trail: {new_row}")


def find_date_column(sheet, date):
    """
    Finds the column number for a given date in the Google Sheet.
    The date in the sheet is in 'DD MMM' format (e.g., '01 Jan').
    """
    date_str = date.strftime("%d %b")  # Format to match 'DD MMM'
    date_cell = sheet.find(date_str)

    if date_cell is not None:
        return date_cell.col
    else:
        print(f"[ERROR] Date {date_str} not found in the sheet.")
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
        else:
            print(f"[DEBUG] No date column found for "
                  f"{current_date.strftime('%Y-%m-%d')}")
        current_date += timedelta(days=1)
    return date_columns


def is_employee_due_to_work(employee_shift, date):
    """
    Checks whether an employee is due to
    work on a given date based on the shift.
    """
    if employee_shift in ["Red", "Green"]:
        days_since_base = (date - BASE_DATE_GREEN_RED).days
    elif employee_shift in ["Blue", "Yellow"]:
        days_since_base = (date - BASE_DATE_BLUE_YELLOW).days
    else:
        return False

    shift_cycle_day = days_since_base % 8  # 8-day shift cycle

    if employee_shift in ["Red", "Green"]:
        return shift_cycle_day < 4  # Work on days 0-3
    elif employee_shift in ["Blue", "Yellow"]:
        return shift_cycle_day >= 4  # Work on days 4-7
    return False


def format_input(input_value):
    """
    Formats and standardizes user inputs for names and shifts.
    """
    return input_value.strip().title()  # Converts strings to Title Case


def validate_shift(sheet, employee_name, expected_shift):
    """
    Validates if the shift entered matches the employee's actual shift.
    """
    employee_names = sheet.col_values(1)  # Employee names in column 1
    shifts = sheet.col_values(2)  # Shifts in column 2

    try:
        employee_row = employee_names.index(employee_name)  # Find employee row
        actual_shift = shifts[employee_row]  # Get the actual shift
        return actual_shift == expected_shift
    except ValueError:
        return False  # Employee not found


def validate_date(date_str):
    """
    Validates if the given date string is in the format 'YYYY-MM-DD' and
    within the year 2024.
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if date_obj.year != 2024:
            print(f"Error: The date must be in the year 2024. "
                  f"You entered {date_obj.year}.")
            return None
        return date_obj
    except ValueError:
        print("Error: Invalid date format or non-existent date. "
              "Please enter the date in 'YYYY-MM-DD' format.")
        return None


def apply_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Applies leave for an employee, ensuring no more than 2 employees are on
    leave within the same exact shift (e.g., Red, Green, Blue, or Yellow).
    """
    employee_name = format_input(employee_name)
    shift = format_input(shift)

    if not validate_shift(sheet, employee_name, shift):
        print(
            f"Leave request failed: {employee_name} is not in "
            f"{shift} shift."
        )
        log_to_audit_trail(employee_name, "Apply Leave", start_date, end_date,
                           "Denied", "Invalid Shift")
        return

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    employee_names = sheet.col_values(1)
    shifts = sheet.col_values(2)
    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        print(f"Employee {employee_name} not found.")
        log_to_audit_trail(employee_name, "Apply Leave", start_date, end_date,
                           "Denied", "Employee Not Found")
        return

    # Cache the date columns for quick lookups
    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)
    current_date = start_date_obj

    # Check for existing leave conflicts within the same individual shift
    while current_date <= end_date_obj:
        if is_employee_due_to_work(shift, current_date):
            date_col = date_columns.get(current_date)
            if date_col:
                leave_statuses = sheet.col_values(date_col)
                same_shift_leaves = [
                    i for i, name in enumerate(employee_names)
                    if leave_statuses[i] == "Leave" and shifts[i] == shift
                ]
                employees_on_leave = len(same_shift_leaves)

                if employees_on_leave >= 2:
                    print(f"Leave request denied for {employee_name}: More "
                          f"than 2 employees already on leave on "
                          f"{current_date.strftime('%Y-%m-%d')} within "
                          f"the {shift} shift.")
                    log_to_audit_trail(employee_name, "Apply Leave",
                                       start_date, end_date, "Denied",
                                       "Exceeds 2 employees on leave")
                    return
        current_date += timedelta(days=1)

    # If no conflicts, apply leave
    current_date = start_date_obj
    while current_date <= end_date_obj:
        date_col = date_columns.get(current_date)
        if date_col:
            leave_statuses = sheet.col_values(date_col)
            if len(leave_statuses) >= employee_row:
                if leave_statuses[employee_row - 1] not in ["Off", "Leave"]:
                    if is_employee_due_to_work(shift, current_date):
                        sheet.update_cell(employee_row, date_col, "Leave")
                        print(f"Leave applied for {employee_name} on "
                              f"{current_date.strftime('%Y-%m-%d')}")
        current_date += timedelta(days=1)

    leave_taken_column = sheet.col_values(4)
    updated_leave_taken = leave_taken_column[employee_row - 1]
    print(f"Updated Leave Taken: {updated_leave_taken} days.")
    log_to_audit_trail(employee_name, "Apply Leave", start_date, end_date,
                       "Approved", f"Total Leave Taken: {updated_leave_taken}")


def cancel_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Cancels leave for an employee and validates the shift before processing.
    """
    employee_name = format_input(employee_name)
    shift = format_input(shift)

    if not validate_shift(sheet, employee_name, shift):
        print(f"Leave cancellation failed: {employee_name} does not belong to "
              f"the {shift} shift.")
        log_to_audit_trail(employee_name, "Cancel Leave", start_date, end_date,
                           "Denied", "Invalid Shift")
        return

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    employee_names = sheet.col_values(1)

    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        print(f"Employee {employee_name} not found.")
        log_to_audit_trail(employee_name, "Cancel Leave", start_date, end_date,
                           "Denied", "Employee Not Found")
        return

    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)
    current_date = start_date_obj
    cancellation_made = False

    while current_date <= end_date_obj:
        date_col = date_columns.get(current_date)
        if date_col:
            leave_statuses = sheet.col_values(date_col)
            if (len(leave_statuses) >= employee_row and
                    leave_statuses[employee_row - 1] == "Leave"):
                sheet.update_cell(employee_row, date_col, "In")
                print(f"Leave canceled for {employee_name} on "
                      f"{current_date.strftime('%Y-%m-%d')}.")
                cancellation_made = True
        current_date += timedelta(days=1)

    if cancellation_made:
        log_to_audit_trail(employee_name, "Cancel Leave", start_date, end_date,
                           "Approved", "")


def request_leave():
    """
    CLI function to request leave by taking
    inputs from the user and applying leave.
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    shift = input(
        "Enter employee's shift (Green/Red/Blue/Yellow), e.g., 'Green': "
    )

    while True:
        start_date = input(
            "Enter start date of leave (YYYY-MM-DD), e.g., '2024-01-01': "
        )
        start_date_obj = validate_date(start_date)
        if start_date_obj:
            break

    while True:
        end_date = input(
            "Enter end date of leave (YYYY-MM-DD), e.g., '2024-01-08': "
        )
        end_date_obj = validate_date(end_date)
        if end_date_obj and end_date_obj >= start_date_obj:
            break
        else:
            print(
                f"Error: The end date must be on or after the start date "
                f"({start_date})."
            )

    apply_leave(holiday, employee_name, start_date, end_date, shift)


def request_leave_cancellation():
    """
    CLI function to cancel pre-booked leave by taking inputs from the user.
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    shift = input(
        "Enter employee's shift (Green/Red/Blue/Yellow), e.g., 'Green': "
    )

    while True:
        start_date = input(
            "Enter start date of leave to cancel (YYYY-MM-DD), e.g., "
            "'2024-01-01': "
        )
        start_date_obj = validate_date(start_date)
        if start_date_obj:
            break

    while True:
        end_date = input(
            "Enter end date of leave to cancel (YYYY-MM-DD), e.g., "
            "'2024-01-08': "
        )
        end_date_obj = validate_date(end_date)
        if end_date_obj and end_date_obj >= start_date_obj:
            break
        else:
            print(
                f"Error: The end date must be on or after the start date "
                f"({start_date})."
            )

    cancel_leave(holiday, employee_name, start_date, end_date, shift)


def main():
    """
    Main function to run the CLI for the leave system.
    """
    while True:
        print(
            "Welcome to the Holiday Booking Application\n"
            "Depending on what you want to do with your "
            "annual leave, select an option below.\n"
            "Bear in mind: only 2 employees can be on leave "
            "from the same shift on any given date,\nand if more than 8 days "
            "are requested, this will be denied.\n"
        )
        print("\nOptions:")
        print("1. Request leave")
        print("2. Cancel leave")
        print("3. Exit")

        choice = input("Enter your choice: ")
        if choice == "1":
            request_leave()
        elif choice == "2":
            request_leave_cancellation()
        elif choice == "3":
            print("Exiting system.")
            break
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()
