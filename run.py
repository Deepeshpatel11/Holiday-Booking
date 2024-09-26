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

print("Google Sheets connection established and 'Holiday Book' worksheet accessed successfully.")


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

# Testing the function (for demonstration purposes)
test_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
print(f"Column for 01 Jan 2024: {find_date_column(holiday, test_date)}")