from flask import Flask, g, jsonify, request, render_template, redirect, url_for
import os, sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

app = Flask(__name__)
DATABASE = 'erdling.db'
VIZ_START_DATE = '2024-01-01'
#
# Chart Color Dictionaries
#
crop_family_colors = {
    'Brassicaceae':'#8dd3c7',
    'Cucurbitaceae':'#fdb462',
    'Fabaceae':'#bebada',
    'Solanaceae':'#fb8072',
    'Asteraceae':'#b3de69',
    'Apiaceae':'#fccde5',
    'Allioideae':'#80b1d3',
    'Poaceae':'#ffffb3',
    'Amaranthaceae':'#bc80bd',
}
soil_improvement_colors = {
    'Kompost': '#996600',
    'Schwarze Folie': '#000000',
    'Gründüngung': '#99ff66',
    'Grünbrache': '#00cc99'
}
solarised_colors = {
    'base03':    '#002b36',
    'base02':    '#073642',
    'base01':    '#586e75',
    'base00':    '#657b83',
    'base0':     '#839496',
    'base1':     '#93a1a1',
    'base2':     '#eee8d5',
    'base3':     '#fdf6e3',
    'yellow':    '#b58900',
    'orange':    '#cb4b16',
    'red':       '#dc322f',
    'magenta':   '#d33682',
    'violet':    '#6c71c4',
    'blue':      '#268bd2',
    'cyan':      '#2aa198',
    'green':     '#859900',
}
#
# Routing
#
# Receive and check input for bedID number (0-90).
@app.route('/',methods = ['POST', 'GET'])
def my_form_post():
    kultur_namen_list = get_all_planted_crops()
    update_date = str(get_most_recent_update_date())
    if request.method == 'POST' and 'bid' in request.form:
        # Validate number as input.
        while True:
            try:
                bedid = int(request.form['bid'])
            except ValueError:
                return render_template('abfrage.html', name=kultur_namen_list, update_date=update_date)
            if bedid < 0:
                return render_template('abfrage.html', name=kultur_namen_list, update_date=update_date)
            elif bedid > 90:
                return render_template('abfrage.html', name=kultur_namen_list, update_date=update_date)
            else:
                break
        return redirect(url_for('beetID', ID = str(bedid)))
    elif request.method == 'POST' and 'kulturname' in request.form:
        # Validate number as input.
        while True:
            try:
                kultur_name = str(request.form.get('kulturname'))
            except ValueError:
                return render_template('abfrage.html', name=kultur_namen_list, update_date=update_date)
            else:
                break
        return redirect(url_for('kulturname', kultur_name = kultur_name))
    else:
        return render_template('abfrage.html', name=kultur_namen_list, update_date=update_date)

# Go to kulturname URL to retrieve info.
@app.route('/kulturname/<kultur_name>', methods=("POST", "GET"))
def kulturname(kultur_name):
    crop_cols, crop_data = get_specific_crop(kultur_name)
    df_crop = pd.DataFrame(crop_data, columns=crop_cols)
    df_crop = df_crop.sort_values(by=['StartDate'], ascending=False)
    df_result = df_crop.where(df_crop.notnull(), '')
    # Generate figure -- allow modifications for figure visualisation by creating copy.
    df_fig = df_result.copy(deep=True)
    # Change to give enddate to everything, now that database is more consistent.
    today = datetime.today().strftime('%Y-%m-%d')
    df_fig.loc[
            (df_fig['EndDate'] == '')
            , 'EndDate'
        ] = today
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
    fig.update_xaxes(range=[VIZ_START_DATE, f'{today}'], fixedrange=True)
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
    # Move legend to top.
    new_fig.update_layout(legend=dict(
    orientation="h",
    yanchor="bottom",
    y=1.05,
    xanchor="right",
    x=1
    ))
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
        intensity=str(df_anbau['Intensität'][0]),
        update_date = str(get_most_recent_update_date())
        )

# Go to bedID URL to retrieve info.
@app.route('/beetID/<ID>', methods=("POST", "GET"))
def beetID(ID):
    planting_cols, planting_data = get_planting_history_per_bed(ID)
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
    # Set end date to today for anything that doesn't have one
    today = datetime.today().strftime('%Y-%m-%d')
    df_fig.loc[
            (df_fig['EndDate'] == '')
            , 'EndDate'
        ] = today
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
    fig.update_xaxes(range=[VIZ_START_DATE, f'{today}'], fixedrange=True)
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
    # Move legend to top.
    new_fig.update_layout(legend=dict(
    orientation="h",
    yanchor="bottom",
    y=1.05,
    xanchor="right",
    x=1
    ))
    pd.set_option('colheader_justify', 'center')
    h1_str="Beet #{}".format(ID)
    return render_template(
        'bed_history.html',
        tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")],
        fig=new_fig.to_html(full_html=False),
        h1_string=h1_str,
        update_date = str(get_most_recent_update_date())
    )

# Go to kulturname URL to retrieve info.
@app.route('/anbau', methods=("POST", "GET"))
def anbau_view():
    today = datetime.today().strftime('%Y-%m-%d')
    anbau_cols, anbau_data = get_all_anbau_info()
    df_anbau = pd.DataFrame(anbau_data, columns=anbau_cols)
    df_anbau = df_anbau.where(df_anbau.notnull(), '')
    anbau_fig = make_anbau_figure(df_anbau, 3000, grouped=False)
    anbau_fig.add_vline(x=today, line_width=3, line_color="black")
    family_overview = get_family_anbau_overview(list(crop_family_colors.keys()))
    families = family_overview.keys()
    return render_template(
        'anbau_view.html',
        fig=anbau_fig.to_html(full_html=False),
        h1_string="Wann wird alles bei den Erdlingen angebaut?",
        update_date = str(get_most_recent_update_date()),
        families = families,
        family_overview = family_overview
    )

# Go to kulturname URL to retrieve info.
@app.route('/folien', methods=("POST", "GET"))
def folien_view():
    today = datetime.today().strftime('%Y-%m-%d')
    folien_cols, folien_data = get_all_folien()
    df_folien = pd.DataFrame(folien_data, columns=folien_cols)
    df_folien = df_folien.where(df_folien.notnull(), '')
    df_folien = df_folien.loc[df_folien['EndDate'] == '']
    df_folien["Tage drauf"] = ((datetime.today() - pd.to_datetime(df_folien['StartDate'], format='%Y-%m-%d')).dt.days)
    df_folien = df_folien.drop(['EndDate'], axis=1)
    return render_template(
        'folien_history.html',
        tables=[df_folien.to_html(classes=['tablestyle', 'sortable'], header="true")],
        h1_string="Seit wann liegen schwarze Folien?",
        update_date = str(get_most_recent_update_date())
    )

def get_planting_history_per_bed(ID):
    sql_query = ('''SELECT Plantings.StartDate, Plantings.EndDate, Crops.CropName, Crops.AlternativeNamen, Crops.CropSorte, Crops.CropFamilie, Plantings.PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE Plantings.BedID = {}
                    ORDER BY StartDate DESC;''').format(ID)
    cols, history = connect_execute_query(sql_query)
    return cols, history

def get_planting_history_per_family(family):
    sql_query = ('''SELECT Plantings.BedID, Plantings.StartDate, Plantings.EndDate, Crops.CropName, Crops.AlternativeNamen, Crops.CropSorte, Crops.CropFamilie, Plantings.PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE Crops.CropFamilie = "{}"
                    ORDER BY Plantings.BedID ASC;''').format(family)
    cols, history = connect_execute_query(sql_query)
    return cols, history

def empty_year_list_gen(min_right=0, max_right_plus_one=43, min_left=51, max_left_plus_one=83):
    empty_year_list = []
    for x in range(min_right, max_right_plus_one):
        empty_year_list.append(str(x))
    for x in range (min_left, max_left_plus_one):
        empty_year_list.append(str(x))
    return empty_year_list

def get_family_anbau_overview(family_list):
    family_overview = {}
    for family in family_list:
        # Get data per family.
        crop_cols, crop_data = get_planting_history_per_family(family)
        df_crop = pd.DataFrame(crop_data, columns=crop_cols)
        df_crop = df_crop.sort_values(by=['BedID'], ascending=True)
        df_result = df_crop.where(df_crop.notnull(), '')
        # Create list of all beds for future planning calculation
        empty_year_list = empty_year_list_gen()
        # Sort data from database into dictionary
        for index, row in df_result.iterrows():
            bedid = str(row["BedID"])
            family = row["CropFamilie"]
            yyyy, mm, dd = row["StartDate"].split("-")
            if family not in family_overview:
                family_overview[family] = {}
            if "Beete für 2025" not in family_overview[family]:
                family_overview[family]["Beete für 2025"] = empty_year_list
            if yyyy not in family_overview[family]:
                family_overview[family][yyyy] = []
            bed_list = family_overview[family][yyyy]
            possible_2025 = family_overview[family]["Beete für 2025"]
            if bedid not in bed_list:
                bed_list.append(bedid)
                family_overview[family][yyyy] = bed_list
            if (bedid in bed_list) and (bedid in possible_2025):
                possible_2025.remove(bedid)
                family_overview[family]["Beete für 2025"] = possible_2025
        family_overview[family]["2023 Anzahl"] = [len(family_overview[family]["2023"]),]
        family_overview[family]["2024 Anzahl"] = [len(family_overview[family]["2024"]),]
        family_overview[family]["Beete für 2025 Anzahl"] = [len(family_overview[family]["Beete für 2025"]),]
        family_overview[family] = dict(sorted(family_overview[family].items()))
    family_overview = dict(sorted(family_overview.items()))
    return family_overview

def get_soil_history(ID):
    sql_query = ('''SELECT StartDate, EndDate, ImprovementName, Notizen
                    FROM SoilImprovements
                    WHERE BedID = {};''').format(ID)
    cols, history = connect_execute_query(sql_query)
    return cols, history

def get_anbau_info(crop_str):
    crop_str = str(crop_str)
    crop_str = crop_str.lower()
    sql_query = ('''SELECT *
                    FROM AnbauInfos
                    WHERE LOWER(CropName) LIKE "{}";''').format(crop_str)
    cols, history = connect_execute_query(sql_query)
    return cols, history

def get_all_anbau_info():
    sql_query = ('''SELECT *
                    FROM AnbauInfos;''')
    cols, history = connect_execute_query(sql_query)
    return cols, history

def get_specific_crop(crop_str):
    crop_str = str(crop_str)
    crop_str = crop_str.lower()
    sql_query = ('''SELECT BedID, StartDate, EndDate, Crops.CropName, CropSorte, CropFamilie, PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE LOWER(Crops.CropName) LIKE "{}"
                    ORDER BY StartDate DESC;''').format(crop_str)
    cols, history = connect_execute_query(sql_query)
    return cols, history

def get_all_planted_crops():
    sql_query = ('''SELECT DISTINCT Crops.CropName
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    ORDER BY Crops.CropName ASC;''')
    cols, history = connect_execute_query(sql_query)
    planted_crops = list(history)
    planted_crops = [crop[0] for crop in planted_crops]
    return planted_crops

def get_most_recent_update_date():
    sql_query = ('''SELECT Plantings.StartDate, Plantings.EndDate, SoilImprovements.StartDate as StartDate2, SoilImprovements.EndDate as Enddate2
                    FROM Plantings
                    INNER JOIN SoilImprovements
                    on Plantings.BedID = SoilImprovements.BedID;''')
    cols, history = connect_execute_query(sql_query)
    df_dates = pd.DataFrame(history, columns=cols)
    df_dates = df_dates.where(df_dates.notnull(), '')
    df_dates = df_dates.apply(pd.to_datetime)
    most_recent_date = pd.to_datetime(df_dates.stack()).max()
    most_recent_date = most_recent_date.strftime('%Y-%m-%d')
    return most_recent_date

def get_all_folien():
    sql_query = ('''SELECT BedID, StartDate, EndDate, Notizen
                    FROM SoilImprovements
                    WHERE ImprovementName = "Schwarze Folie"
                    ORDER BY StartDate DESC;''')
    cols, history = connect_execute_query(sql_query)
    return cols, history

def connect_execute_query(sql_query):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    cur = c.execute(sql_query)
    cols = list(map(lambda x: x[0], cur.description))
    history = c.fetchall()
    conn.close()
    return cols, history

def make_anbau_figure(df, height, grouped=True):
    fig0 = create_anbau_partial_figure(df, "SäenVorziehenStart", "SäenVorziehenEnde", solarised_colors['violet'])
    fig1 = create_anbau_partial_figure(df, "SäenDirektStart1", "SäenDirektEnde1", solarised_colors['red'])
    fig2 = create_anbau_partial_figure(df, "SäenDirektStart2", "SäenDirektEnde2", solarised_colors['red'])
    fig3 = create_anbau_partial_figure(df, "SetzenStart1", "SetzenEnde1", solarised_colors['yellow'])
    fig4 = create_anbau_partial_figure(df, "SetzenStart2", "SetzenEnde2", solarised_colors['yellow'])
    fig5 = create_anbau_partial_figure(df, "SteckenStart1", "SteckenEnde1", solarised_colors['blue'])
    fig6 = create_anbau_partial_figure(df, "ErntefensterStart1", "ErntefensterEnde1", solarised_colors['green'])
    fig7 = create_anbau_partial_figure(df, "ErntefensterStart2", "ErntefensterEnde2", solarised_colors['green'])
    combined_figure = go.Figure(data=fig0.data + fig1.data + fig2.data + fig3.data + fig4.data + fig5.data + fig6.data+ fig7.data, layout=fig0.layout)
    combined_figure.update_layout({
        'plot_bgcolor': 'rgb(234,216,192)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'height': height
        })
    combined_figure.update_xaxes(range=['2024-01-01', '2024-12-31'], fixedrange=True)
    combined_figure.update_yaxes(autorange="reversed", fixedrange=True)
    if grouped == True:
        combined_figure.update_layout({'barmode':'group'})
    return combined_figure

def create_anbau_partial_figure(df, start, end, marker_clr):
    fig = px.timeline(
        df,
        x_start=start,
        x_end=end,
        y="CropName",
        labels={
            "CropName": "Kulturnamen"
        }
    )
    fig.update_traces(marker_color=marker_clr)
    return fig

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)