CSV_DIR = './data_csv' # Relative location where the CSV files will be saved from GoogleDrive
DATABASE = './erdling.db' # SQLite Database relative location
#
## Google Sheet ID -- Get from GoogleDrive
# Example: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv
#
GOOGLESHEETID = ''
#
# The name and GID of each table as a dictionary
# Sheet names are manually defined here.
# Be sure that the sheet names and columns match the values in schema.sql
#
GOOGLESHEETDICT = {
    # 'AnbauInfos': ##########,
    # 'SeedSaving': ##########,,
    'Beds': ##########,,
    'Crops': ##########,,
    'Plantings': ##########,,
    'SoilImprovements': ##########,
    }