import secret_farmapp
CSV_DIR = './data_csv' # Relative location where the CSV files will be saved from GoogleDrive
DATABASE = './erdling.db' # SQLite Database relative location
#
## Google Sheet ID -- Get from GoogleDrive
# Example: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv
#
GOOGLESHEETID = secret_farmapp.GOOGLESHEETID
#
# The name and GID of each table as a dictionary.
# The GID are usually 9-10 digit 
# Sheet names are manually defined here.
# Be sure that the sheet names and columns match the values in schema.sql
#
GOOGLESHEETDICT = {
    # 'AnbauInfos': secret_farmapp.GOOGLESHEETDICT['AnbauInfos'],
    # 'SeedSaving': secret_farmapp.GOOGLESHEETDICT['SeedSaving'],
    'Beds': secret_farmapp.GOOGLESHEETDICT['Beds'],
    'Crops': secret_farmapp.GOOGLESHEETDICT['Crops'],
    'Plantings': secret_farmapp.GOOGLESHEETDICT['Plantings'],
    'SoilImprovements': secret_farmapp.GOOGLESHEETDICT['SoilImprovements']
    }