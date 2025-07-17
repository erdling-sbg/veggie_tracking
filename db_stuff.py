import os, requests, sqlite3, sys
import pandas as pd
import config_farmapp # Internal

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
    db = sqlite3.connect(config_farmapp.DATABASE)
    return db

def insert_data(csv_dir, sheet_names):
    # creating a connection to the database
    db = get_db()
    for sheetname in sheet_names:
        # reading data from the CSV file
        path_to_csv = os.path.join(csv_dir, f'{sheetname}.csv')
        df = pd.read_csv(path_to_csv)
        # data cleanup
        df.columns = df.columns.str.strip()
        # Get the column names from the DataFrame
        columns = df.columns.tolist()
        id_col = columns[0]
        #
        # Check ID column for errors
        #
        exit_check = False
        id_list = df[id_col].values.tolist() # get as list
        id_list = [x for x in id_list if x != 'NaN'] # filter NaN
        try:
            id_list = [int(i) for i in id_list] # convert to int
        except ValueError:
            print("There is an invalid ID number in col {} in sheet {}, likely NaN".format(id_col, sheetname))
            exit_check = True
        id_list.sort() # sort ascending
        maybe_missing = missing_number(id_list)
        if len(maybe_missing) != 0:
            print('Sheet {} is missing an expected ID in col {}: {}'.format(sheetname, id_col, str(maybe_missing)))
            exit_check = True
        # A set to keep track of elements that have been seen
        seen = set()
        # A list to store duplicates found in the input list
        duplicates = []
        # Iterate over each element in the list
        for i in id_list:
            if i in seen:
                duplicates.append(i)
            else:
                seen.add(i)
        if len(duplicates) != 0:
            print('Sheet {} has ID duplicates in col {}: {}'.format(sheetname, id_col, str(duplicates)))
            exit_check = True
        if exit_check == True:
            sys.exit()
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        # Load data file to SQLite as tmp table -- skip for now. Keep for reference.
        # df.to_sql('tmp', db, if_exists='replace', index=False)
        # insert non duplicates to existing table
        insert_sql = f'INSERT INTO {sheetname} ({columns_str}) VALUES ({placeholders}) ON CONFLICT({id_col}) DO NOTHING'
        for _, row in df.iterrows():
            db.cursor().execute(insert_sql, tuple(row))
        db.commit()
    db.close()
    print('SQLite Database saved to: {}'.format(config_farmapp.DATABASE))  
#
# Google Sheet Stuff
#
def getGoogleSheet(spreadsheet_id, outDir, dict_of_sheets):
    for sheetname, sheet_number in dict_of_sheets.items():
        url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_number}'
        response = requests.get(url)
        if response.status_code == 200:
            filepath = os.path.join(outDir, f'{sheetname}.csv')
            with open(filepath, 'wb') as f:
                f.write(response.content)
                print('CSV file saved to: {}'.format(filepath))    
        else:
            print(f'Error downloading Google Sheet: {response.status_code}')
            sys.exit(1)

def missing_number(myList): # myList is assumed to be sorted ascending
    return sorted(set(myList).symmetric_difference(range((myList[0]), myList[-1]+1)))