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
    df_crop = df_crop.sort_values(by=['StartDate'], ascending=False)
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
        color_discrete_map = crop_family_colors,
        labels={
            "BedID": "Beet #",
            "CropFamilie": "Pflanzenfamilien"
        }
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
    anbau_cols, anbau_data = get_anbau_info(kultur_name)
    df_anbau = pd.DataFrame(anbau_data, columns=anbau_cols)
    df_anbau = df_anbau.where(df_anbau.notnull(), '')
    anbau_fig = make_anbau_figure(df_anbau, 400)
    anbau_fig.add_vline(x=today, line_width=3, line_color="black")
    h1_anbau_str = f"Wann bauen die Erdlinge {kultur_name} an?"
    return render_template(
        'crop_location.html', tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")],
        fig=new_fig.to_html(full_html=False),
        anbau_fig=anbau_fig.to_html(full_html=False),
        h1_string=h1_str,
        h1_anbau_str=h1_anbau_str,
        good_neighbors=str(df_anbau['NachbarnGut'][0]),
        bad_neighbors=str(df_anbau['NachbarnSchlecht'][0]),
        intensity=str(df_anbau['Intensität'][0])
        )

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
        color_discrete_map = crop_family_colors,
        labels={
            "CropName": "Kulturnamen",
            "CropFamilie": "In dem Beet..."
        }
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

# Go to kulturname URL to retrieve info.
@app.route('/anbau', methods=("POST", "GET"))
def anbau_view():
    today = datetime.today().strftime('%Y-%m-%d')
    anbau_cols, anbau_data = get_all_anbau_info()
    df_anbau = pd.DataFrame(anbau_data, columns=anbau_cols)
    df_anbau = df_anbau.where(df_anbau.notnull(), '')
    anbau_fig = make_anbau_figure(df_anbau, 3000, grouped=False)
    anbau_fig.add_vline(x=today, line_width=3, line_color="black")
    return render_template(
        'anbau_view.html',
        fig=anbau_fig.to_html(full_html=False),
        h1_string="Überblick"
    )

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

def get_anbau_info(crop_str):
    crop_str = str(crop_str)
    crop_str = crop_str.lower()
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT *
                    FROM AnbauInfos
                    WHERE LOWER(CropName) LIKE "{}";''').format(crop_str)
    cur = c.execute(sql_query)
    cols = list(map(lambda x: x[0], cur.description))
    history = c.fetchall()
    conn.close()
    return cols, history

def get_all_anbau_info():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = ('''SELECT *
                    FROM AnbauInfos;''')
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

def make_anbau_figure(df, height, grouped=True):
    fig0 = px.timeline(
        df,
        x_start="SäenVorziehenStart",
        x_end="SäenVorziehenEnde",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
    )
    fig0.update_yaxes(autorange="reversed")
    fig0.update_traces(marker_color="#6c71c4")
    fig1 = px.timeline(
        df,
        x_start="SäenDirektStart1",
        x_end="SäenDirektEnde1",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
    )
    fig1.update_yaxes(autorange="reversed")
    fig1.update_traces(marker_color="#dc322f")
    fig2 = px.timeline(
        df,
        x_start="SäenDirektStart2",
        x_end="SäenDirektEnde2",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
        )
    fig2.update_yaxes(autorange="reversed")
    fig2.update_traces(marker_color="#dc322f")
    fig3 = px.timeline(
        df,
        x_start="SetzenStart1",
        x_end="SetzenEnde1",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
        )
    fig3.update_yaxes(autorange="reversed")
    fig3.update_traces(marker_color="#b58900")
    fig4 = px.timeline(
        df,
        x_start="SetzenStart2",
        x_end="SetzenEnde2",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
    )
    fig4.update_yaxes(autorange="reversed")
    fig4.update_traces(marker_color="#b58900")
    fig5 = px.timeline(
        df,
        x_start="SteckenStart1",
        x_end="SteckenEnde1",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
    )
    fig5.update_yaxes(autorange="reversed")
    fig5.update_traces(marker_color="#268bd2")
    fig6 = px.timeline(
        df,
        x_start="ErntefensterStart1",
        x_end="ErntefensterEnde1",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
    )
    fig6.update_yaxes(autorange="reversed")
    fig6.update_traces(marker_color="#859900")
    fig7 = px.timeline(
        df,
        x_start="ErntefensterStart2",
        x_end="ErntefensterEnde2",
        y="CropName",
        labels={
            "CropName": "Kulturnamen",
        },
        height=1500,
    )
    fig7.update_yaxes(autorange="reversed")
    fig7.update_traces(marker_color="#859900")
    if grouped == True:
        new_fig_grouped = go.Figure(data=fig0.data + fig1.data + fig2.data + fig3.data + fig4.data + fig5.data + fig6.data+ fig7.data, layout=fig0.layout)
        new_fig_grouped.update_layout({
        'plot_bgcolor': 'rgb(234,216,192)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'barmode':'group',
        'height': height
        })
        new_fig_grouped.update_xaxes(range=['2024-01-01', '2024-12-31'], fixedrange=True)
        new_fig_grouped.update_yaxes(fixedrange=True)
        return new_fig_grouped
    else:
        new_fig_all = go.Figure(data=fig0.data + fig1.data + fig2.data + fig3.data + fig4.data + fig5.data + fig6.data+ fig7.data, layout=fig0.layout)
        new_fig_all.update_layout({
        'plot_bgcolor': 'rgb(234,216,192)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'height': height
        })
        new_fig_all.update_xaxes(range=['2024-01-01', '2024-12-31'], fixedrange=True)
        new_fig_all.update_yaxes(fixedrange=True)
        return new_fig_all

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)