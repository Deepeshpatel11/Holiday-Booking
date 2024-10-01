# Testing

### Holiday Book System Testing

The following tests were carried out to ensure the Holiday Book system is functioning correctly and adheres to the expected behavior for both normal and edge cases.

| **Feature**                | **Action**                                                    | **Expected Result**                                                     | **Actual Result**                      |
| -------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------- | -------------------------------------- |
| **CLI - Main Menu**        | User is presented with options to request leave, cancel leave, or exit | Options "1. Request leave", "2. Cancel leave", "3. Exit" are displayed | Works as expected                      |
| **Request Leave - Name Input** | User enters a valid employee name                               | Name is accepted and user moves to the next step                        | Works as expected                      |
| Request Leave - Name Input  | User inputs a non-existent or incorrectly formatted name           | Error message: "Employee not found. Please enter a valid name." appears | Works as expected                      |
| Request Leave - Name Input  | User inputs special characters or numbers                          | Error message: "Please enter a valid name using only letters." appears  | Works as expected                      |
| **Request Leave - Shift Input** | User enters a valid shift (e.g., Green, Red, Blue, Yellow)            | Shift is accepted and user moves to the next step                        | Works as expected                      |
| Request Leave - Shift Input | User inputs an invalid shift (e.g., Pink)                               | Error message: "Invalid shift. Please enter a valid shift." appears     | Works as expected                      |
| Request Leave - Shift Input | User inputs lowercase or improperly capitalized shift                  | Input is converted to the correct format and accepted                   | Works as expected                      |
| **Request Leave - Date Input** | User enters a valid start and end date in the format YYYY-MM-DD         | Dates are accepted and validated                                        | Works as expected                      |
| Request Leave - Date Input  | User enters a date outside of 2024 or in an invalid format               | Error message: "The date must be in the year 2024." or "Invalid format." appears | Works as expected                      |
| Request Leave - Date Input  | User enters an end date that is earlier than the start date             | Error message: "The end date must be on or after the start date." appears | Works as expected                      |
| **Leave Application - Date Conflict Check** | User applies for leave on days already marked as "Off"                   | Message: "Employee is already planned to be off work on this date." appears | Works as expected                      |
| Leave Application - Date Conflict Check | User applies for leave on days where leave is already booked              | Message: "Leave already booked on this date." appears                    | Works as expected                      |
| **Leave Application - Exceeding Workdays Check** | User tries to apply for more than 8 working days                          | Leave request is denied, and a message "Exceeds 8 workdays." appears     | Works as expected                      |
| Leave Application - Exceeding Workdays Check | User applies for exactly 8 working days                                   | Leave is approved                                                        | Works as expected                      |
| **Leave Application - Quota Check** | User tries to apply for leave when 2 employees are already on leave         | Leave request is denied, and a message "More than 2 employees already on leave for this date." appears | Works as expected                      |
| Leave Application - Quota Check | User applies for leave when 0 or 1 employees are on leave                    | Leave request is accepted                                                | Works as expected                      |
| **Leave Application - Holiday Book Update** | Leave is successfully applied for the given date range                     | The respective dates in the holiday book are marked as "Leave"           | Works as expected                      |
| Leave Application - Holiday Book Update | Leave request fails due to quota or workdays check                         | No changes are made in the holiday book                                  | Works as expected                      |
| **Leave Application - Audit Trail Update** | Leave is successfully applied                                              | A single entry is made in the `audit_trail` tab with status "Approved"   | Works as expected                      |
| Leave Application - Audit Trail Update | Leave request is denied due to quota, shift, or workdays error              | A single entry is made in the `audit_trail` tab with status "Denied"     | Works as expected                      |
| **Cancel Leave - Name Input** | User enters a valid employee name                                             | Name is accepted and user moves to the next step                        | Works as expected                      |
| Cancel Leave - Name Input   | User inputs a non-existent or incorrectly formatted name                    | Error message: "Employee not found. Please enter a valid name." appears | Works as expected                      |
| **Cancel Leave - Shift Input** | User enters a valid shift (e.g., Green, Red, Blue, Yellow)                      | Shift is accepted and user moves to the next step                        | Works as expected                      |
| Cancel Leave - Shift Input  | User inputs an invalid shift                                                    | Error message: "Invalid shift. Please enter a valid shift." appears     | Works as expected                      |
| **Cancel Leave - Date Input** | User enters a valid start and end date in the format YYYY-MM-DD                 | Dates are accepted and validated                                        | Works as expected                      |
| Cancel Leave - Date Input   | User enters a date outside of 2024 or in an invalid format                       | Error message: "The date must be in the year 2024." or "Invalid format." appears | Works as expected                      |
| **Leave Cancellation - Date Conflict Check** | User tries to cancel leave for dates where no leave was booked             | Message: "No leave found for [employee] on [date]." appears              | Works as expected                      |
| Leave Cancellation - Date Conflict Check | User cancels leave on dates where leave was previously booked              | Leave is successfully removed from the holiday book                      | Works as expected                      |
| **Leave Cancellation - Holiday Book Update** | Leave is successfully canceled for the given date range                    | The respective dates in the holiday book are cleared                     | Works as expected                      |
| Leave Cancellation - Holiday Book Update | Leave cancellation fails due to shift, date, or employee name mismatch     | No changes are made in the holiday book                                  | Works as expected                      |
| **Leave Cancellation - Audit Trail Update** | Leave is successfully canceled                                             | A single entry is made in the `audit_trail` tab with status "Approved"   | Works as expected                      |
| Leave Cancellation - Audit Trail Update | Leave cancellation fails due to shift, date, or employee name mismatch      | A single entry is made in the `audit_trail` tab with status "Denied"     | Works as expected                      |
| **Exit Option**             | User selects "Exit" option from the menu                                    | Program terminates with a farewell message                               | Works as expected                      |
| Exit Option                 | User inputs an invalid menu choice                                           | Error message: "Invalid choice, try again." appears                      | Works as expected                      |


### Testing Browsers

I have tested the CLI portal deployed on Heroku on:
* Google Chrome
* Microsoft Edge