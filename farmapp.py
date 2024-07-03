from flask import Flask, g, jsonify, request, render_template, redirect, url_for
import os, sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

app = Flask(__name__)
DATABASE = 'erdling.db'
#
# Chart Color Dictionaries
#
crop_family_colors = {
    'Brassiacaecaea':'#8dd3c7',
    'Cucurbitaceae':'#fdb462',
    'Fabaceae':'#bebada',
    'Solanaceae':'#fb8072',
    'Asteraceae':'#b3de69',
    'Apiaceae':'#fccde5',
    'Liliaceae':'#80b1d3',
    'Poaceae':'#ffffb3',
    'Amaranthaceae':'#bc80bd',
}

soil_improvement_colors = {
    'Kompost': '#996600',
    'Schwarze Folie': '#000000',
    'Gründüngung': '#99ff66',
    'Grünbrache': '#00cc99'
}

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
    df_crop = df_crop.sort_values(by=['CropName', 'StartDate'], ascending=True)
    df_result = df_crop.where(df_crop.notnull(), '')
    # Generate figure -- allow modifications for figure visualisation by creating copy.
    df_fig = df_result.copy(deep=True)
    today = datetime.today().strftime('%Y-%m-%d')
    year_start = datetime.today().strftime('%Y-01-01')
    df_fig.loc[((df_fig['StartDate'] >= year_start) & (df_fig['EndDate'] == '')), 'EndDate'] = today
    fig = px.timeline(
        df_fig,
        x_start="StartDate",
        x_end="EndDate",
        y="BedID",
        color="CropFamilie",
        color_discrete_map = crop_family_colors
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout({
        'plot_bgcolor': 'rgb(234,216,192)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)'
    })
    fig.update_xaxes(range=['2024-01-01', f'{today}'], fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    # Points for starting dates
    dia = px.scatter(
        df_fig,
        x="StartDate",
        y="BedID",
        color="CropFamilie",
        color_discrete_map = crop_family_colors,
        symbol_sequence=['diamond']
        )
    dia.update_traces(marker=dict(size=12, line=dict(width=2)))
    new_fig = go.Figure(data=fig.data + dia.data, layout=fig.layout)
    pd.set_option('colheader_justify', 'center')
    h1_str="Crop: {}".format(kultur_name)
    return render_template('crop_location.html', tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")], fig=new_fig.to_html(full_html=False), h1_string=h1_str)

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
    # Figure stuff
    df_fig = df_result.copy(deep=True)
    #df_fig = df_fig.drop(df_fig[df_fig['ImprovementName'] != ''].index)
    today = datetime.today().strftime('%Y-%m-%d')
    year_start = datetime.today().strftime('%Y-01-01')
    df_fig.loc[((df_fig['StartDate'] >= year_start) & (df_fig['EndDate'] == '')), 'EndDate'] = today
    fig = px.timeline(
        df_fig.loc[df_fig['ImprovementName'] == ''],
        x_start="StartDate",
        x_end="EndDate",
        y="CropName",
        color="CropFamilie",
        color_discrete_map = crop_family_colors
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout({
        'plot_bgcolor': 'rgb(234,216,192)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)'
    })
    fig.update_xaxes(range=['2024-01-01', f'{today}'], fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    dia = px.scatter(
        df_fig.loc[df_fig['ImprovementName'] == ''],
        x="StartDate",
        y="CropName",
        color="CropFamilie",
        color_discrete_map = crop_family_colors,
        symbol_sequence=['diamond']
    )
    dia.update_traces(marker=dict(size=12, line=dict(width=2)))
    soil_process = px.timeline(
        df_fig.loc[((df_fig['ImprovementName'] != 'Kompost') & (df_fig['ImprovementName'] != ''))],
        x_start="StartDate",
        x_end="EndDate",
        y="ImprovementName",
        color="ImprovementName",
        color_discrete_map = soil_improvement_colors
    )
    soil_event = px.scatter(
        df_fig.loc[df_fig['ImprovementName'] == 'Kompost'],
        x="StartDate",
        y="ImprovementName",
        color="ImprovementName",
        color_discrete_map = soil_improvement_colors,
        symbol_sequence=['line-ns-open'])
    soil_event.update_traces(marker=dict(size=12, line=dict(width=10))) 
    # Put it all together!
    new_fig = go.Figure(data=fig.data + dia.data + soil_process.data + soil_event.data, layout=fig.layout)
    pd.set_option('colheader_justify', 'center')
    h1_str="Beet #{}".format(ID)
    return render_template('bed_history.html', tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")], fig=new_fig.to_html(full_html=False), h1_string=h1_str)

def get_planting_history(ID):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT StartDate, EndDate, Crops.CropName, AlternativeNamen, CropSorte, CropFamilie, PlantingMethod, Plantings.Notizen
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
    sql_query = ('''SELECT BedID, StartDate, EndDate, Crops.CropName, CropSorte, CropFamilie, PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE LOWER(Crops.CropName) LIKE "{}"
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