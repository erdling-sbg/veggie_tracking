import os # Standard
import config_farmapp, db_stuff # Internal

if __name__ == "__main__":
    # Get sheets from GoogleDrive as CSV files.
    # Check config_farmapp for more info.
    os.makedirs(config_farmapp.CSV_DIR, exist_ok = True)
    db_stuff.getGoogleSheet(config_farmapp.GOOGLESHEETID, config_farmapp.CSV_DIR, config_farmapp.GOOGLESHEETDICT)
    # Initialise the database based on the CSV files.
    # Delete any existing database file first.
    # The deletion is manual (for now) to avoid unintentional overwriting.
    db_stuff.init_db()
    db_stuff.insert_data(config_farmapp.CSV_DIR, config_farmapp.GOOGLESHEETDICT.keys())