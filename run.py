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


def log_to_audit_trail(employee_name, action, start_date, end_date,
                       status, remarks=""):
    """
    Logs the leave request status to the 'audit_trail' worksheet.
    Parameters:
    - employee_name (str): Name of the employee requesting leave.
    - action (str): Type of action performed
    (e.g., "Apply Leave", "Cancel Leave").
    - start_date (str): Start date of the leave request in 'YYYY-MM-DD' format.
    - end_date (str): End date of the leave request in 'YYYY-MM-DD' format.
    - status (str): Status of the request ("Approved", "Denied").
    - remarks (str): Additional remarks or comments
    for the log entry (default is an empty string).

    Returns:
    None
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = [timestamp, employee_name, action, start_date, end_date,
               status, remarks]
    audit_trail.append_row(new_row)
    print(f"Logged action to audit_trail: {new_row}")


def find_date_column(sheet, date):
    """
    Finds the column number for a given date in the Google Sheet.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet to search within.
    - date (datetime): The date for which the column number is to be found.

    Returns:
    - int: The column number if found, or
    None if the date is not present in the sheet.
    """
    date_str = date.strftime("%d %b")
    date_cell = sheet.find(date_str)

    if date_cell is not None:
        return date_cell.col
    else:
        print(f"[ERROR] Date {date_str} not found in the sheet.")
        return None

# Credit for helping me scope and write the code for cache data
# to Tomas Kubancik - alumni of CodeInstitute


def cache_date_columns(sheet, start_date, end_date):
    """
    Caches the column numbers for all dates in the
    given range to minimize API calls.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing the date columns.
    - start_date (datetime): The starting date of the range.
    - end_date (datetime): The ending date of the range.

    Returns:
    - dict: A dictionary mapping each date in the range to
    its corresponding column number.
    """
    date_columns = {}
    current_date = start_date
    while current_date <= end_date:
        date_col = find_date_column(sheet, current_date)
        if date_col:
            date_columns[current_date] = date_col
        else:
            print(
                f"[DEBUG] No date column found for "
                f"{current_date.strftime('%Y-%m-%d')}"
            )
        current_date += timedelta(days=1)
    return date_columns


def is_employee_due_to_work(employee_shift, date):
    """
    Checks whether an employee is due to work on a
    given date based on their shift type.

    Parameters:
    - employee_shift (str): Shift type of the employee (e.g., "Red", "Green").
    - date (datetime): The date to check.

    Returns:
    - bool: True if the employee is scheduled to work, False otherwise.
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
    Formats and standardizes user inputs by trimming
    whitespace and converting to title case.

    Parameters:
    - input_value (str): The raw input value provided by the user.

    Returns:
    - str: The formatted string.
    """
    return input_value.strip().title()  # Converts strings to Title Case


def validate_shift(sheet, employee_name, expected_shift):
    """
    Validates if the shift entered by the employee
    matches their actual shift in the system.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing employee shift data.
    - employee_name (str): Name of the employee.
    - expected_shift (str): The shift provided by the user for validation.

    Returns:
    - bool: True if the shift matches, False if it does not.
    """
    employee_names = sheet.col_values(1)  # Employee names in column 1
    shifts = sheet.col_values(2)  # Shifts in column 2

    try:
        employee_row = employee_names.index(employee_name)  # Find employee
        actual_shift = shifts[employee_row]  # Get the actual shift
        return actual_shift == expected_shift
    except ValueError:
        return False  # Employee not found


def validate_date(date_str):
    """
    Validates if the given date string is in the
    format 'YYYY-MM-DD' and within the year 2024.

    Parameters:
    - date_str (str): Date string to be validated.

    Returns:
    - datetime: A datetime object if the date is
    valid and within 2024, otherwise None.
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


def calculate_consecutive_leave(sheet, employee_name, start_date_obj, shift):
    """
    Calculates the number of consecutive leave days an
    employee has taken before the requested start date.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing leave data.
    - employee_name (str): Name of the employee.
    - start_date_obj (datetime): The start date of the new leave request.
    - shift (str): The shift type of the employee.

    Returns:
    - int: The number of consecutive leave days before the
    requested start date.
    """
    date_columns = cache_date_columns(
        sheet, start_date_obj - timedelta(days=8), start_date_obj
    )
    current_date = start_date_obj - timedelta(days=8)
    employee_names = sheet.col_values(1)
    shifts = sheet.col_values(2)

    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        return 0

    consecutive_days = 0
    while current_date < start_date_obj:
        if is_employee_due_to_work(shift, current_date):
            date_col = date_columns.get(current_date)
            if date_col:
                leave_statuses = sheet.col_values(date_col)
                if leave_statuses[employee_row - 1] == "Leave":
                    consecutive_days += 1
                else:
                    break
        current_date += timedelta(days=1)
    return consecutive_days


def apply_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Applies leave for an employee, ensuring no more than 2 employees
    are on leave within the same shift and that the cumulative
    workdays do not exceed 8 consecutive days.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing leave data.
    - employee_name (str): Name of the employee applying for leave.
    - start_date (str): The start date of the leave in 'YYYY-MM-DD' format.
    - end_date (str): The end date of the leave in 'YYYY-MM-DD' format.
    - shift (str): The shift type of the employee.

    Returns:
    None
    """
    employee_name, shift = format_input(employee_name), format_input(shift)

    if not validate_employee_and_shift(
            sheet, employee_name, shift, start_date, end_date):
        return

    start_date_obj, end_date_obj = get_date_objects(start_date, end_date)

    if not validate_workdays_limit(
            sheet, employee_name, shift, start_date_obj, end_date_obj,
            start_date, end_date):
        return

    if not validate_existing_leave_conflicts(
            sheet, employee_name, shift, start_date_obj, end_date_obj,
            start_date, end_date):
        return

    process_leave_application(
        sheet, employee_name, start_date_obj, end_date_obj,
        shift, start_date, end_date)


def validate_employee_and_shift(sheet, employee_name, shift, start_date,
                                end_date):
    """
    Validates if the employee and shift are correct before applying leave.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing employee shift data.
    - employee_name (str): Name of the employee.
    - shift (str): Employee's shift type.
    - start_date (str): Start date of the leave in 'YYYY-MM-DD' format.
    - end_date (str): End date of the leave in 'YYYY-MM-DD' format.

    Returns:
    - bool: True if the shift and employee are valid, False otherwise.
    """
    if not validate_shift(sheet, employee_name, shift):
        print(
            f"Leave request failed: {employee_name} "
            f"is not in {shift} shift."
        )
        log_to_audit_trail(
            employee_name, "Apply Leave", start_date, end_date,
            "Denied", "Invalid Shift"
        )
        return False
    return True


def get_date_objects(start_date, end_date):
    """
    Converts string dates to datetime objects.

    Parameters:
    - start_date (str): Start date in 'YYYY-MM-DD' format.
    - end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
    - tuple: A tuple containing datetime objects for start and end dates.
    """
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    return start_date_obj, end_date_obj


def validate_workdays_limit(sheet, employee_name, shift, start_date_obj,
                            end_date_obj, start_date, end_date):
    """
    Validates if the new leave days along with consecutive days
    exceed the limit.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing leave data.
    - employee_name (str): Name of the employee.
    - shift (str): Employee's shift type.
    - start_date_obj (datetime): Start date as a datetime object.
    - end_date_obj (datetime): End date as a datetime object.
    - start_date (str): Start date in 'YYYY-MM-DD' format.
    - end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
    - bool: True if the leave does not exceed the limit, False otherwise.
    """
    consecutive_leave_days = calculate_consecutive_leave(
        sheet, employee_name, start_date_obj, shift
    )
    new_workdays = sum(
        1 for d in (
            start_date_obj + timedelta(days=i)
            for i in range((end_date_obj - start_date_obj).days + 1)
        ) if is_employee_due_to_work(shift, d)
    )

    if new_workdays + consecutive_leave_days > 8:
        print(f"Leave request denied for {employee_name}: Exceeds "
              f"8 consecutive workdays.")
        log_to_audit_trail(
            employee_name, "Apply Leave", start_date, end_date,
            "Denied", "Exceeds Consecutive 8 Days"
        )
        return False
    return True


def validate_existing_leave_conflicts(sheet, employee_name, shift,
                                      start_date_obj, end_date_obj,
                                      start_date, end_date):
    """
    Checks if there are already 2 employees on leave within the same shift.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing leave data.
    - employee_name (str): Name of the employee.
    - shift (str): Employee's shift type.
    - start_date_obj (datetime): Start date as a datetime object.
    - end_date_obj (datetime): End date as a datetime object.
    - start_date (str): Start date in 'YYYY-MM-DD' format.
    - end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
    - bool: True if there is no conflict, False if conflict exists.
    """
    employee_names = sheet.col_values(1)
    shifts = sheet.col_values(2)
    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)
    current_date = start_date_obj

    while current_date <= end_date_obj:
        if is_employee_due_to_work(shift, current_date):
            date_col = date_columns.get(current_date)
            if date_col:
                leave_statuses = sheet.col_values(date_col)
                same_shift_leaves = [
                    i for i, name in enumerate(employee_names)
                    if leave_statuses[i] == "Leave" and shifts[i] == shift
                ]
                if len(same_shift_leaves) >= 2:
                    print(f"Leave request denied for {employee_name}: "
                          f"More than 2 employees already on leave on "
                          f"{current_date.strftime('%Y-%m-%d')} within "
                          f"the {shift} shift.")
                    log_to_audit_trail(
                        employee_name, "Apply Leave", start_date, end_date,
                        "Denied", "Exceeds 2 employees on leave"
                    )
                    return False
        current_date += timedelta(days=1)
    return True


def process_leave_application(sheet, employee_name, start_date_obj,
                              end_date_obj, shift, start_date, end_date):
    """
    Processes the leave application if all validations are passed.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing leave data.
    - employee_name (str): Name of the employee.
    - start_date_obj (datetime): Start date as a datetime object.
    - end_date_obj (datetime): End date as a datetime object.
    - shift (str): Employee's shift type.
    - start_date (str): Start date in 'YYYY-MM-DD' format.
    - end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
    None
    """
    employee_names = sheet.col_values(1)
    try:
        employee_row = employee_names.index(employee_name) + 1
    except ValueError:
        print(f"Employee {employee_name} not found.")
        log_to_audit_trail(employee_name, "Apply Leave", start_date,
                           end_date, "Denied", "Employee Not Found")
        return

    date_columns = cache_date_columns(sheet, start_date_obj, end_date_obj)
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

    # Update and log the total leave taken
    leave_taken_column = sheet.col_values(4)
    updated_leave_taken = leave_taken_column[employee_row - 1]
    print(f"Updated Leave Taken: {updated_leave_taken} days.")
    log_to_audit_trail(employee_name, "Apply Leave", start_date, end_date,
                       "Approved", f"Total Leave Taken: {updated_leave_taken}")


def cancel_leave(sheet, employee_name, start_date, end_date, shift):
    """
    Cancels leave for an employee if it is already marked as
    "Leave" in the system.

    Parameters:
    - sheet (gspread.Worksheet): The worksheet containing leave data.
    - employee_name (str): Name of the employee.
    - start_date (str): Start date of the leave to be canceled
    in 'YYYY-MM-DD' format.
    - end_date (str): End date of the leave to be canceled
    in 'YYYY-MM-DD' format.
    - shift (str): Employee's shift type.

    Returns:
    None
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
    CLI function to request leave by taking inputs from the user.

    Prompts the user to enter their employee name, shift,
    and the start and end dates of their leave.
    Calls the `apply_leave` function if the inputs are valid.

    Parameters:
    None

    Returns:
    None
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    shift = input("Enter employee's shift (Green/Red/Blue/Yellow), "
                  "e.g., 'Green': ")

    while True:
        start_date = input("Enter start date of leave (YYYY-MM-DD), "
                           "e.g., '2024-01-01': ")
        start_date_obj = validate_date(start_date)
        if start_date_obj:
            break

    while True:
        end_date = input("Enter end date of leave (YYYY-MM-DD), "
                         "e.g., '2024-01-08': ")
        end_date_obj = validate_date(end_date)
        if end_date_obj and end_date_obj >= start_date_obj:
            break
        else:
            print(f"Error: The end date must be on or after the start date "
                  f"({start_date}).")

    apply_leave(holiday, employee_name, start_date, end_date, shift)


def request_leave_cancellation():
    """
    CLI function to cancel a previously booked leave by
    taking inputs from the user.

    Prompts the user to enter their employee name, shift, and the
    start and end dates of the leave they wish to cancel.
    Calls the `cancel_leave` function if the inputs are valid.

    Parameters:
    None

    Returns:
    None
    """
    employee_name = input("Enter employee name (e.g., 'John Doe'): ")
    shift = input("Enter employee's shift (Green/Red/Blue/Yellow), "
                  "e.g., 'Green': ")

    while True:
        start_date = input("Enter start date of leave to cancel (YYYY-MM-DD), "
                           "e.g., '2024-01-01': ")
        start_date_obj = validate_date(start_date)
        if start_date_obj:
            break

    while True:
        end_date = input("Enter end date of leave to cancel (YYYY-MM-DD), "
                         "e.g., '2024-01-08': ")
        end_date_obj = validate_date(end_date)
        if end_date_obj and end_date_obj >= start_date_obj:
            break
        else:
            print(f"Error: The end date must be on or after the start date "
                  f"({start_date}).")

    cancel_leave(holiday, employee_name, start_date, end_date, shift)


def main():
    """
    Main function to run the Command Line Interface (CLI) for the leave system.

    Presents a menu to the user with options to request leave,
    cancel leave, or exit the system.
    Handles user input and calls the appropriate functions
    based on the user's choice.

    Parameters:
    None

    Returns:
    None
    """
    while True:
        print(
            "\n"
            "Welcome to the Holiday Booking Application\n"
            "\n"
            "Depending on what you want to do with your "
            "annual leave, select an option below. "
            "ie (1) to request leave and (2) to cancel leave.\n"
            "\n"
            "Bear in mind: only 2 employees can be on leave "
            "from the same shift on any given date, and if more than 8 days "
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
