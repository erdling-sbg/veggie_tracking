from flask import Flask, g, jsonify, request, render_template, redirect, url_for
import os, sqlite3
import pandas as pd

app = Flask(__name__)
DATABASE = 'erdling.db'
#
# Routing
#
# Receive and check input for bedID number (0-90).
@app.route('/',methods = ['POST', 'GET'])
def my_form_post():
    kultur_namen_list = get_all_planted_crops()
    if request.method == 'POST' and 'bid' in request.form:
        # Validate number as input.
        while True:
            try:
                bedid = int(request.form['bid'])
            except ValueError:
                return render_template('abfrage.html', name=kultur_namen_list)
            if bedid < 0:
                return render_template('abfrage.html', name=kultur_namen_list)
            elif bedid > 90:
                return render_template('abfrage.html', name=kultur_namen_list)
            else:
                break
        return redirect(url_for('beetID', ID = str(bedid)))
    elif request.method == 'POST' and 'kulturname' in request.form:
        # Validate number as input.
        while True:
            try:
                kultur_name = str(request.form.get('kulturname'))
            except ValueError:
                return render_template('abfrage.html', name=kultur_namen_list)
            else:
                break
        return redirect(url_for('kulturname', kultur_name = kultur_name))
    else:
        return render_template('abfrage.html', name=kultur_namen_list)

# Go to kulturname URL to retrieve info.
@app.route('/kulturname/<kultur_name>', methods=("POST", "GET"))
def kulturname(kultur_name):
    crop_cols, crop_data = get_specific_crop(kultur_name)
    df_crop = pd.DataFrame(crop_data, columns=crop_cols)
    df_crop = df_crop.sort_values(by=['BedID', 'StartDate'], ascending=True)
    df_result = df_crop.where(df_crop.notnull(), '')
    pd.set_option('colheader_justify', 'center')
    h1_str="Crop: {}".format(kultur_name)
    return render_template('crop_location.html', tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")], h1_string=h1_str)

# Go to bedID URL to retrieve info.
@app.route('/beetID/<ID>', methods=("POST", "GET"))
def beetID(ID):
    planting_cols, planting_data = get_planting_history(ID)
    soil_cols, soil_data = get_soil_history(ID)
    # create DataFrame using data and concatonate plantings and soil improvements
    df_planting = pd.DataFrame(planting_data, columns=planting_cols)
    df_soil = pd.DataFrame(soil_data, columns=soil_cols)
    df_result = pd.concat([df_planting, df_soil], ignore_index=True)
    # Move Notizen column to the end
    df_result = df_result[[col for col in df_result.columns if col != 'Notizen'] + ['Notizen']]
    # Sort concatonated dataframe by startdate and CropFamilie
    df_result = df_result.sort_values(by=['StartDate', 'CropFamilie', 'CropName'], ascending=False)
    # Fix NaN values to None
    df_result = df_result.where(df_result.notnull(), '')
    pd.set_option('colheader_justify', 'center')
    h1_str="Beet #{}".format(ID)
    return render_template('bed_history.html', tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")], h1_string=h1_str)

def get_planting_history(ID):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT StartDate, EndDate, CropName, AlternativeNamen, CropSorte, CropFamilie, PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE Plantings.BedID = {}
                    ORDER BY StartDate DESC;''').format(ID)
    cur = c.execute(sql_query)
    cols = list(map(lambda x: x[0], cur.description))
    history = c.fetchall()
    conn.close()
    return cols, history

def get_soil_history(ID):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT StartDate, EndDate, ImprovementName, Notizen
                    FROM SoilImprovements
                    WHERE BedID = {};''').format(ID)
    cur = c.execute(sql_query)
    cols = list(map(lambda x: x[0], cur.description))
    history = c.fetchall()
    conn.close()
    return cols, history

def get_specific_crop(crop_str):
    crop_str = str(crop_str)
    crop_str = crop_str.lower()
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT BedID, StartDate, EndDate, CropName, CropSorte, CropFamilie, PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE LOWER(CropName) LIKE "%{}%"
                    ORDER BY StartDate DESC;''').format(crop_str)
    cur = c.execute(sql_query)
    cols = list(map(lambda x: x[0], cur.description))
    history = c.fetchall()
    conn.close()
    return cols, history

def get_all_planted_crops():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT DISTINCT Crops.CropName
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    ORDER BY Crops.CropName ASC;''')
    cur = c.execute(sql_query)
    cols = list(map(lambda x: x[0], cur.description))
    history = c.fetchall()
    planted_crops = list(history)
    conn.close()
    planted_crops = [crop[0] for crop in planted_crops]
    return planted_crops

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)