import os, sqlite3
import pandas as pd

DATABASE = 'erdling.db'
CSV_DIR = 'data_csv'
CSV_NAMES = ['Beds.csv', 'Crops.csv', 'Plantings.csv', 'SoilImprovements.csv']

#
# Database stuff
#
# Initialise schema
def init_db():
    db = get_db()
    with open('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()

def get_db():
    db = sqlite3.connect(DATABASE)
    return db

def insert_data():
    # creating a connection to the database
    db = get_db()
    for csv_fn in CSV_NAMES:
        # reading data from the CSV file
        path_to_csv = os.path.join(CSV_DIR, csv_fn)
        table_name = str.split(csv_fn, '.')[0]
        df = pd.read_csv(path_to_csv)
        # data cleanup
        df.columns = df.columns.str.strip()
        # Get the column names from the DataFrame
        columns = df.columns.tolist()
        id_col = columns[0]
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        # Load data file to SQLite as tmp table -- skip for now. Keep for reference.
        # df.to_sql('tmp', db, if_exists='replace', index=False)
        # insert non duplicates to existing table
        insert_sql = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT({id_col}) DO NOTHING'
        for _, row in df.iterrows():
            db.cursor().execute(insert_sql, tuple(row))
        db.commit()
    db.close()