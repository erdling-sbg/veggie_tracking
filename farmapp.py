from flask import Flask, g, jsonify, request, render_template, redirect, url_for
import os, sqlite3
import numpy as np
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
    'Grünbrache': '#00cc99',
    'mit Laub gemulcht': "#c57c5c",
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
    #
    # Get planting information
    #
    crop_cols, crop_data = get_specific_crop(kultur_name)
    df_crop = pd.DataFrame(crop_data, columns=crop_cols)
    df_crop = df_crop.sort_values(by=['StartDate'], ascending=False)
    df_result = df_crop.where(df_crop.notnull(), '')
    #
    # Generate figure -- allow modifications for figure visualisation by creating copy.
    #
    df_fig = df_result.copy(deep=True)
    # Change to give enddate to everything for the figure (otherwise timeline bars don't display)
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
    # Points for each starting date
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
    h1_str="Kultur: {}".format(kultur_name)
    anbau_cols, anbau_data = get_anbau_info(kultur_name)
    df_anbau = pd.DataFrame(anbau_data, columns=anbau_cols)
    df_anbau = df_anbau.where(df_anbau.notnull(), '')
    anbau_fig = make_anbau_figure(df_anbau, 400)
    anbau_fig.add_vline(x=today, line_width=3, line_color="black")
    h1_anbau_str = f"Wann bauen die Erdlinge {kultur_name} an?"
    h1_woanbau_str = f"Wo hat man {kultur_name} angebaut?"
    #
    # Harvest information.
    #
    harvest_table = get_crop_from_harvest_table(generate_harvest_table(), kultur_name)
    h1_harvest_str = f"Gibt es {kultur_name} zum Ernten?"
    #
    # Get bed with longest history, or none.
    #
    priority_info = str()
    if harvest_table.shape[0] == 0:
        priority_info = 'Nein.'
    else:
        harvest_table_filtered = harvest_table.loc[(harvest_table['ErnteStatus'] == "1: Zum Ernten")]
        if harvest_table_filtered.shape[0] == 0:
            priority_info = 'Vielleicht? Ernteinfos fehlen.'
        else:
            most_days = harvest_table_filtered['TageNachReife'].max()
            harvest_prio = harvest_table_filtered[harvest_table_filtered['TageNachReife'] == most_days]
            harvest_rest = harvest_table_filtered[harvest_table_filtered['TageNachReife'] != most_days]
            harvest_rest_list = list(dict.fromkeys((harvest_rest['BedID'].tolist())))
            prio_beds_list = list(dict.fromkeys((harvest_prio['BedID'].tolist())))
            for prio_bed in prio_beds_list:
                if prio_bed in harvest_rest_list:
                    harvest_rest_list.remove(prio_bed)
            prio_beds_list = [str(int(x)) for x in prio_beds_list]
            prio_bit = str(prio_beds_list).replace("[", '').replace("]", '').replace("'", '')
            priority_info = f"Ja! Hier zuerst ernten: <mark>{prio_bit}</mark>"
            if len(harvest_rest_list) >= 1:
                harvest_rest_list = [str(int(x)) for x in harvest_rest_list]
                add_str_bit = str(harvest_rest_list).replace("[", '').replace("]", '').replace("'", '')
                add_str = f"</br> und dann in dieser Reihenfolge weiterschauen: <mark>{add_str_bit}</mark>"
                priority_info += add_str

    return render_template(
        'crop_location.html', tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")],
        fig=new_fig.to_html(full_html=False),
        anbau_fig=anbau_fig.to_html(full_html=False),
        h1_string=h1_str,
        h1_anbau_str=h1_anbau_str,
        h1_harvest_str=h1_harvest_str,
        h1_woanbau_str=h1_woanbau_str,
        priority_info=priority_info,
        #harvest_tables=[harvest_table.to_html(classes=['tablestyle', 'sortable'], header="true")],
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
        # Remove Improvement categories as bars from graphic
        df_fig.loc[((df_fig['ImprovementName'] != 'Kompost') & (df_fig['ImprovementName'] != '') & (df_fig['ImprovementName'] != 'mit Laub gemulcht'))],
        x_start="StartDate",
        x_end="EndDate",
        y="ImprovementName",
        color="ImprovementName",
        color_discrete_map = soil_improvement_colors
    )
    soil_event = px.scatter(
        df_fig.loc[((df_fig['ImprovementName'] == 'Kompost') | (df_fig['ImprovementName'] == 'mit Laub gemulcht'))],
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
    # Walkthrough buttons
    # Decided not to use the function due to possible skipping of "empty" beds...
    #list_of_active_beds = get_all_active_beds()
    before_bed = None
    after_bed = None
    if int(ID) == 0:
        before_bed = 51
    elif int(ID) == 51:
        before_bed = 0
    else:
        before_bed = int(ID) - 1
    if int(ID) == 82:
        after_bed = 41
    elif int(ID) == 41:
        after_bed = 82
    else:
        after_bed = int(ID) + 1
    h1_wasanbau_str = f"Was wurde in Beet #{ID} überhaupt angebaut?"
    #
    # Generate harvest table.
    #
    harvest_table = get_bed_from_harvest_table(generate_harvest_table(), int(ID))
    harvest_str = f'Gibt es in diesem Beet etwas zum Ernten?'
    #
    # Get crops to harvest, or none.
    #
    priority_info = str()
    if harvest_table.shape[0] == 0:
        priority_info = 'Nein.'
    else:
        harvest_table_filtered = harvest_table.loc[(harvest_table['ErnteStatus'] == "1: Zum Ernten")]
        harvest_table_filtered = harvest_table_filtered.sort_values(by=['TageNachReife'], ascending=[False])
        if harvest_table_filtered.shape[0] == 0:
            priority_info = 'Vielleicht? Ernteinfos fehlen.'
        else:
            harvest_set = str(list(dict.fromkeys((harvest_table_filtered['CropName'].tolist())))).replace("[", '').replace("]", '').replace("'", '')
            priority_info = f"Ja! Es gibt: <mark>{harvest_set}</mark>"

    return render_template(
        'bed_history.html',
        tables=[df_result.to_html(classes=['tablestyle', 'sortable'], header="true")],
        fig=new_fig.to_html(full_html=False),
        h1_string=h1_str,
        priority_info=priority_info,
        #harvest_tables=[harvest_table.to_html(classes=['tablestyle', 'sortable'], header="true")],
        harvest_str=harvest_str,
        h1_wasanbau_str=h1_wasanbau_str,
        after_bed = str(after_bed),
        before_bed = str(before_bed),
        update_date = str(get_most_recent_update_date())
    )

@app.route('/ernteliste', methods=("POST", "GET"))
def ernteliste_table():
    df_harvest = generate_harvest_table()
    # Filter just for erntable or unknowns...
    df_harvest = df_harvest.loc[
        ((df_harvest['ErnteStatus'] == "1: Zum Ernten") | (df_harvest['ErnteStatus'] == "2: Keine Ahnung"))
    ]
    df_harvest = df_harvest.reset_index(drop=True)
    df_harvest = df_harvest.sort_values(by=['CropName', 'ErnteStatus', 'TageNachReife'], ascending=[True, True, False])
    df_harvest = df_harvest.reset_index(drop=True)

    df_harvest_text = df_harvest.loc[
        (df_harvest['ErnteStatus'] == "1: Zum Ernten")
    ]
    harvestable_dict = dict.fromkeys((df_harvest_text['CropName'].tolist()))
    harvest_text = str()
    for veggie in harvestable_dict.keys():
        # Get subseet for veggie
        df_harvest_text_veg = get_crop_from_harvest_table(df_harvest_text, veggie)
        df_harvest_text_veg = df_harvest_text_veg.sort_values(by=['TageNachReife'], ascending=[False])
        most_days = df_harvest_text_veg['TageNachReife'].max()
        harvest_veg_prio = df_harvest_text_veg[df_harvest_text_veg['TageNachReife'] == most_days]
        harvest_veg_rest = df_harvest_text_veg[df_harvest_text_veg['TageNachReife'] != most_days]
        harvest_rest_list = harvest_veg_rest['BedID'].tolist()
        prio_beds_list = harvest_veg_prio['BedID'].tolist()
        prio_beds_list = [str(int(x)) for x in prio_beds_list]
        harvest_rest_list = [str(int(x)) for x in harvest_rest_list]
        harvest_rest_list = list(dict.fromkeys(harvest_rest_list))
        prio_beds_list = list(dict.fromkeys(prio_beds_list))
        for prio_bed in prio_beds_list:
            if prio_bed in harvest_rest_list:
                harvest_rest_list.remove(prio_bed)
        priority_info = str()
        prio_bit = str(prio_beds_list).replace("[", '').replace("]", '').replace("'", '')
        priority_info = f"<mark>{prio_bit}</mark>"
        if len(harvest_rest_list) >= 1:
            add_str_bit = str(harvest_rest_list).replace("[", '').replace("]", '').replace("'", '')
            add_str = f", <i><small>aber auch: <mark>{add_str_bit}</mark></small></i>"
            priority_info += add_str
        harvestable_dict[veggie] = priority_info
        harvest_text += f"</br>{veggie}: {priority_info}"

    return render_template(
        'ernteliste.html',
        harvest_text=harvest_text,
        harvest_tables=[df_harvest.to_html(classes=['tablestyle', 'sortable'], header="true")],
        update_date = str(get_most_recent_update_date())
    )

@app.route('/anbau', methods=("POST", "GET"))
def anbau_view():
    today = datetime.today().strftime('%Y-%m-%d')
    anbau_cols, anbau_data = get_all_anbau_info()
    df_anbau = pd.DataFrame(anbau_data, columns=anbau_cols)
    df_anbau = df_anbau.where(df_anbau.notnull(), '')
    anbau_fig = make_anbau_figure_overview(df_anbau, 3000, grouped=False)
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
    # make index match count
    df_folien= df_folien.reset_index(drop=True)
    # Get number of rows/tarps
    num_tarps = df_folien.shape[0]
    return render_template(
        'folien_history.html',
        tables=[df_folien.to_html(classes=['tablestyle', 'sortable'], header="true")],
        h1_string="Seit wann liegen schwarze Folien?",
        num_tarps = num_tarps,
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
    for x in range(min_left, max_left_plus_one):
        empty_year_list.append(str(x))
    return empty_year_list

def days_from_start(planting_date):
    days = (datetime.strptime(planting_date, '%Y-%m-%d') - datetime.today()).days
    days = abs(days)
    return days

def generate_harvest_table():
    # Get planting info.
    crop_cols, crop_data = get_all_unharvested_crops()
    df_harvest = pd.DataFrame(crop_data, columns=crop_cols)
    df_harvest = df_harvest.where(df_harvest.notnull(), '')
    # Get harvestable plantings by having no EndDate
    df_harvest = df_harvest.loc[df_harvest['EndDate'] == '']
    df_harvest = df_harvest.copy(deep=True)

    # Get Anbau Info
    anbau_cols, anbau_data = get_all_anbau_info()
    df_anbau = pd.DataFrame(anbau_data, columns=anbau_cols)
    df_anbau = df_anbau.where(df_anbau.notnull(), '')
    df_anbau = df_anbau.copy(deep=True)

    # Merge
    df_harvest = df_harvest.merge(df_anbau, how="inner", on="CropName")
    desired_columns = [
            "BedID",
            "StartDate",
            "CropName",
            "CropSorte",
            "PlantingMethod",
            "TagezurReifeGesäet",
            "TagezurReifeGesetzt",
            "TagezurReifeGesteckt"    ]
    df_harvest = df_harvest.get(desired_columns)

    # Calculate days from start
    df_harvest["TageNachStart"] = df_harvest.loc[:, "StartDate"].map(days_from_start)
    # Fill nodata to 0.0 numeric typed
    df_harvest['TagezurReifeGesäet'] = df_harvest['TagezurReifeGesäet'].apply(pd.to_numeric, errors='coerce', downcast='integer').fillna(0)
    df_harvest['TagezurReifeGesetzt'] = df_harvest['TagezurReifeGesetzt'].apply(pd.to_numeric, errors='coerce', downcast='integer').fillna(0)
    df_harvest['TagezurReifeGesteckt'] = df_harvest['TagezurReifeGesteckt'].apply(pd.to_numeric, errors='coerce', downcast='integer').fillna(0)
    
    # Get days to harvest depending on planting method
    conditions = [
        df_harvest['PlantingMethod'].eq('gesät'),
        df_harvest['PlantingMethod'].eq('gesetzt'),
        df_harvest['PlantingMethod'].eq('gesteckt')
    ]
    choices = [
        df_harvest['TagezurReifeGesäet'],
        df_harvest['TagezurReifeGesetzt'],
        df_harvest['TagezurReifeGesteckt'],
    ]
    df_harvest['TagezurReife'] = np.select(conditions, choices, default=0)
    df_harvest = df_harvest.drop(columns=["TagezurReifeGesäet", "TagezurReifeGesetzt", "TagezurReifeGesteckt"])
    df_harvest['TageNachReife'] = df_harvest['TageNachStart'] - df_harvest['TagezurReife']

    # Calculate whether harvestable
    conditions = [
        (df_harvest['TagezurReife'] < 1),
        (df_harvest['TageNachStart']>= df_harvest['TagezurReife']),
        (df_harvest['TageNachStart'] < df_harvest['TagezurReife']) & (df_harvest['TagezurReife'] >= 1),
    ]
    choices = [
        "2: Keine Ahnung",
        "1: Zum Ernten",
        "3: Reift noch"
    ]
    df_harvest['ErnteStatus'] = np.select(conditions, choices, default="2: Keine Ahnung")
    df_harvest = df_harvest.sort_values(by=['ErnteStatus', "TageNachReife", 'CropName'], ascending=[True, False, True])

    df_harvest = df_harvest.astype({
    'TageNachStart': 'int',
    'TagezurReife': 'int',
    'TageNachReife': 'int',
    })
    return df_harvest

def get_crop_from_harvest_table(df_harvest, kultur_name):
    df_harvest = df_harvest.loc[df_harvest['CropName'] == kultur_name]
    # Filter just for erntable or unknowns...
    df_harvest = df_harvest.loc[
        ((df_harvest['ErnteStatus'] == "1: Zum Ernten") | (df_harvest['ErnteStatus'] == "2: Keine Ahnung"))
    ]
    df_harvest = df_harvest.reset_index(drop=True)
    # TODO: add logic depending on number of rows to prioritise what to harvest.
    return df_harvest

def get_bed_from_harvest_table(df_harvest, ID):
    df_harvest = df_harvest.loc[df_harvest['BedID'] == ID]
    # Filter just for erntable or unknowns...
    df_harvest = df_harvest.loc[
        ((df_harvest['ErnteStatus'] == "1: Zum Ernten") | (df_harvest['ErnteStatus'] == "2: Keine Ahnung"))
    ]
    df_harvest = df_harvest.reset_index(drop=True)
    return df_harvest

def get_family_anbau_overview(family_list):
    family_overview = {}
    for family in family_list:
        # Get data per family.
        crop_cols, crop_data = get_planting_history_per_family(family)
        df_crop = pd.DataFrame(crop_data, columns=crop_cols)
        df_crop = df_crop.sort_values(by=['BedID'], ascending=True)
        df_result = df_crop.where(df_crop.notnull(), '')
        # Create family dictionary if first round
        if family not in family_overview:
            family_overview[family] = {}
        # Sort data from database into dictionary
        for index, row in df_result.iterrows():
            # Get information per row
            bedid = str(row["BedID"])
            family = row["CropFamilie"]
            yyyy, mm, dd = row["StartDate"].split("-")
            # Create year dictionary if first time
            if yyyy not in family_overview[family]:
                family_overview[family][yyyy] = []
            # Get list of beds in that year
            bed_list = family_overview[family][yyyy]
            # Add each bed used per year based on existing database
            if bedid not in bed_list:
                bed_list.append(bedid)
                family_overview[family][yyyy] = bed_list
        for year in list(family_overview[family]):
            anzahl_str = "{} Anzahl".format(year)
            family_overview[family][anzahl_str] = [len(family_overview[family][year]),]
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

def get_all_unharvested_crops():
    sql_query = ('''SELECT BedID, StartDate, EndDate, Crops.CropName, CropSorte, CropFamilie, PlantingMethod, Plantings.Notizen
                    FROM Plantings
                    INNER JOIN Crops
                    on Plantings.CropID = Crops.CropID
                    WHERE Plantings.EndDate IS NULL
                    ORDER BY StartDate DESC;''')
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

def get_all_active_beds():
    sql_query = ('''SELECT DISTINCT BedID
                        FROM (
                            SELECT BedID, EndDate
                            FROM Plantings
                        UNION ALL
                            SELECT BedID, EndDate
                            FROM SoilImprovements)
                    WHERE EndDate is NULL AND BedID is NOT NULL
                    ORDER BY BedID ASC;
                    ''')
    cols, history = connect_execute_query(sql_query)
    tracked_beds = list(history)
    tracked_beds = [bed[0] for bed in tracked_beds]
    return tracked_beds

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
    combined_figure.update_xaxes(range=['2025-01-01', '2025-12-31'], fixedrange=True)
    combined_figure.update_yaxes(autorange="reversed", fixedrange=True)
    if grouped == True:
        combined_figure.update_layout({'barmode':'group'})
    return combined_figure

def make_anbau_figure_overview(df, height, grouped=True):
    fig0 = create_anbau_partial_figure_width(df, "SäenVorziehenStart", "SäenVorziehenEnde", solarised_colors['violet'], 1)
    fig1 = create_anbau_partial_figure_width(df, "SäenDirektStart1", "SäenDirektEnde1", solarised_colors['red'], 0.8)
    fig2 = create_anbau_partial_figure_width(df, "SäenDirektStart2", "SäenDirektEnde2", solarised_colors['red'], 0.8)
    fig3 = create_anbau_partial_figure_width(df, "SetzenStart1", "SetzenEnde1", solarised_colors['yellow'], 0.5)
    fig4 = create_anbau_partial_figure_width(df, "SetzenStart2", "SetzenEnde2", solarised_colors['yellow'], 0.5)
    fig5 = create_anbau_partial_figure_width(df, "SteckenStart1", "SteckenEnde1", solarised_colors['blue'], 0.4)
    fig6 = create_anbau_partial_figure_width(df, "ErntefensterStart1", "ErntefensterEnde1", solarised_colors['green'], 0.3)
    fig7 = create_anbau_partial_figure_width(df, "ErntefensterStart2", "ErntefensterEnde2", solarised_colors['green'], 0.3)
    combined_figure = go.Figure(data=fig0.data + fig1.data + fig2.data + fig3.data + fig4.data + fig5.data + fig6.data+ fig7.data, layout=fig0.layout)
    combined_figure.update_layout({
        'plot_bgcolor': 'rgb(234,216,192)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'height': height
        })
    combined_figure.update_xaxes(range=['2025-01-01', '2025-12-31'], fixedrange=True)
    combined_figure.update_yaxes(autorange="reversed", fixedrange=True)
    if grouped == True:
        combined_figure.update_layout({'barmode':'group'})
    return combined_figure

def create_anbau_partial_figure_width(df, start, end, marker_clr, bar_width=1):
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
    for i, d in enumerate(fig.data):
        d.width = bar_width
    return fig

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
