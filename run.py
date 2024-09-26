import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

# Testing the functions (for demonstration purposes)
test_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
test_date_col = find_date_column(holiday, test_date)
print(f"Employees on leave for shift Red on 01 Jan 2024: {count_employees_on_leave(holiday, 'Red', test_date_col)}")
