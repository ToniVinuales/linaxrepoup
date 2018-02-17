import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, Event
import plotly.plotly as py
from plotly.graph_objs import *
from scipy.stats import rayleigh
from flask import Flask
import numpy as np
import pandas as pd
import os
import sqlite3
import datetime as dt
import pickle
from dotenv import find_dotenv, load_dotenv
from toolz import groupby, compose, pluck
from csv import DictReader

#server = Flask('my app')
#server.secret_key = os.environ.get('secret_key', 'secret')
#
#MAPS
#
file = open('data/IRB7600FX_locations.csv', encoding="utf8")
reader = DictReader(file)
BFRO_LOCATION_DATA = [
    line for line in reader
]
file.close()
MAPBOX_KEY = "pk.eyJ1IjoidG9uaXZpbnVhbGVzIiwiYSI6ImNqZHBvcHIxcjB3ZzEyd29jaTZsNG1rMGsifQ.mCOBAWOe2teqCop5WUXKrw"
# Setup the app
server = Flask('my app')
#server.secret_key = os.environ.get('secret_key', 'secret')
app = dash.Dash('my app', server=server, csrf_protect=False) 
#app = dash.Dash() 
# Title the app.
app.title = "ABB LInax Torque"
app.config['suppress_callback_exceptions']=True 
# Boostrap CSS.
app.css.append_css({
    "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"
})

# Extra Dash styling.
app.css.append_css({
    "external_url": 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})

# JQuery is required for Bootstrap.
app.scripts.append_script({
    "external_url": "https://code.jquery.com/jquery-3.2.1.min.js"
})
# Bootstrap Javascript.
app.scripts.append_script({
    "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"
}) 
#MAPS
listpluck = compose(list, pluck)
def linax(sightings):
    # groupby returns a dictionary mapping the values of the first field 
    # 'classification' onto a list of record dictionaries with that 
    # classification value.
    classifications = groupby('classification', sightings)
    return {
        "data": [
                {
                    "type": "scattermapbox",
                    "lat": listpluck("latitude", class_sightings),
                    "lon": listpluck("longitude", class_sightings),
                    "text": listpluck("title", class_sightings),
                    "mode": "markers",
                    "name": classification,
                    "marker": {
                        "size": 3,
                        "opacity": 1.0
                    }
                }
                for classification, class_sightings in classifications.items()
            ],
        "layout": {
            "autosize": True,
            "hovermode": "closest",
            "mapbox": {
                "accesstoken": MAPBOX_KEY,
                "bearing": 0,
                "center": {
                    "lat": 40,
                    "lon": -98.5
                },
                "pitch": 0,
                "zoom": 3,
                "style": 'light'		
            }
        }
    }
app.layout = html.Div([
    html.Div([
	    html.Img(src="https://sypro.co.uk/assets/uploads/abb-logo-white.png",
					style={
                        'height': '37',
                        'width': '82',
                        'float': 'left',
                        'position': 'relative',
						'margin-left': '50',
						'margin-top': '15'
                    },),
        html.H2("IRB 7600FX_Analytics", style={'color': 'white', 'fontSize': 36,'float': 'right','position': 'relative','margin-right': '20'}),
		],className='banner',style={'backgroundColor': 'black','marginBottom': 20, 'marginTop': 50}), 
    html.Div([
        html.Div([
            html.Div([
                html.H3("TORQUE REALTIME")
            ], className='Title'),
			html.P('IRB7600FX Torque-Current,Torque Linax,Speed,Mobile Wagon Position-Speed,Tilting Current-Angle Data', id='bin-size', className='bin-size'),
            dcc.Graph(id='wind-speed'),
			dcc.Interval(id='wind-speed-update', interval=5000),
        ], className='four columns wind-speed'),
        html.Div([
            html.Div([
                html.H3("TORQUE HISTOGRAM")
            ], className='Title'),
            html.Div([
                dcc.Slider(
                    id='bin-slider',
                    min=1,
                    max=60,
                    step=1,
                    value=20,
                    updatemode='drag'
                ),
            ], className='histogram-slider'),
            html.P('# of Bins: Auto', id='bin-size', className='bin-size'),
            html.Div([
                dcc.Checklist(
                    id='bin-auto',
                    options=[
                        {'label': 'Auto', 'value': 'Auto'}
                    ],
                    values=['Auto']
                ),
            ], className='bin-auto'),
            dcc.Graph(id='wind-histogram'),
        ], className='four columns wind-speed'),
        html.Div([
            html.Div([
                html.H3("PREDICTIVE TORQUE FAILURE")
            ], className='Title'),
			html.P('Use variables 3D-Map to detect root-cause of Torque Failure'),
			html.Div([
                dcc.Slider(
                    min=0,
                    max=0,
                    value=0,
                    marks={i: ''.format(i + 1) for i in range(6)},
                    id='slider'
                ),
            ], className='four columns wind-speed',style={'color': 'white','margin-bottom': '10px'}),
			html.Div([
				dcc.Graph(id='graph'),
			], className='twelve columns wind-speed'),
        ], className='four columns wind-speed')
    ], className='row wind-speed-row'),
    html.Div([
        html.Div([
            html.Div([
                html.H3("IRB-7600FX PERFORMANCE MAP")
            ], className='Title'),
			html.P('Filter by OEE performance (Overall Equipment Efectiveness): Select IRB7600FX in the map and compare between all equipment'),
			html.Div([
				 dcc.Graph(
                id="bigfoot-map",
                ############### NEW CODE #############
                figure=linax(BFRO_LOCATION_DATA)
                ######################################
				)				
            ], ),
        ], className='twelve columns wind-speed-row')
    ], className='row wind-histo-polar')
], style={'padding': '0px 10px 15px 10px',
          'marginLeft': 'auto', 'marginRight': 'auto', "width": "900px",
          'boxShadow': '0px 0px 5px 5px rgba(204,204,204,0.4)'})
#GRAPH3D
# Internal logic
last_back = 0
last_next = 0
df = pd.read_csv("data/yield_curve.csv")
xlist = list(df["x"].dropna())
ylist = list(df["y"].dropna())
del df["x"]
del df["y"]
zlist = []
for row in df.iterrows():
    index, data = row
    zlist.append(data.tolist())
UPS = {
    0: dict(x=0, y=0, z=1),
    1: dict(x=0, y=0, z=1),
    2: dict(x=0, y=0, z=1),
    3: dict(x=0, y=0, z=1),
    4: dict(x=0, y=0, z=1),
    5: dict(x=0, y=0, z=1),
}
CENTERS = {
    0: dict(x=0.3, y=0.8, z=-0.5),
    1: dict(x=0, y=0, z=-0.37),
    2: dict(x=0, y=1.1, z=-1.3),
    3: dict(x=0, y=-0.7, z=0),
    4: dict(x=0, y=-0.2, z=0),
    5: dict(x=-0.11, y=-0.5, z=0),
}
EYES = {
    0: dict(x=2.7, y=2.7, z=0.3),
    1: dict(x=0.01, y=3.8, z=-0.37),
    2: dict(x=1.3, y=3, z=0),
    3: dict(x=2.6, y=-1.6, z=0),
    4: dict(x=3, y=-0.2, z=0),
    5: dict(x=-0.1, y=-0.5, z=2.66)
}
# Make 3d graph
@app.callback(Output('graph', 'figure'), [Input('slider', 'value')])
def make_graph(value):

    if value is None:
        value = 0

    if value in [0, 2, 3]:
        z_secondary_beginning = [z[1] for z in zlist if z[0] == 'None']
        z_secondary_end = [z[0] for z in zlist if z[0] != 'None']
        z_secondary = z_secondary_beginning + z_secondary_end
        x_secondary = [
            '3-month'] * len(z_secondary_beginning) + ['1-month'] * len(z_secondary_end)
        y_secondary = ylist
        opacity = 0.7

    elif value == 1:
        x_secondary = xlist
        y_secondary = [ylist[-1] for i in xlist]
        z_secondary = zlist[-1]
        opacity = 0.7

    elif value == 4:
        z_secondary = [z[8] for z in zlist]
        x_secondary = ['10-year' for i in z_secondary]
        y_secondary = ylist
        opacity = 0.25

    if value in range(0, 5):

        trace1 = dict(
            type="surface",
            x=xlist,
            y=ylist,
            z=zlist,
            hoverinfo='x+y+z',
            lighting={
                "ambient": 0.95,
                "diffuse": 0.99,
                "fresnel": 0.01,
                "roughness": 0.01,
                "specular": 0.01,
            },
            colorscale=[[0, "rgb(230,245,254)"], [0.4, "rgb(123,171,203)"], [
                0.8, "rgb(40,119,174)"], [1, "rgb(37,61,81)"]],
            opacity=opacity,
            showscale=False,
            zmax=9.18,
            zmin=0,
            scene="scene",
        )

        trace2 = dict(
            type='scatter3d',
            mode='lines',
            x=x_secondary,
            y=y_secondary,
            z=z_secondary,
            hoverinfo='x+y+z',
            line=dict(color='#444444')
        )

        data = [trace1, trace2]

    else:

        trace1 = dict(
            type="contour",
            x=ylist,
            y=xlist,
            z=np.array(zlist).T,
            colorscale=[[0, "rgb(230,245,254)"], [0.4, "rgb(123,171,203)"], [
                0.8, "rgb(40,119,174)"], [1, "rgb(37,61,81)"]],
            showscale=False,
            zmax=9.18,
            zmin=0,
            line=dict(smoothing=1, color='rgba(40,40,40,0.15)'),
            contours=dict(coloring='heatmap')
        )

        data = [trace1]

        # margin = dict(
        #     t=5,
        #     l=50,
        #     b=50,
        #     r=5,
        # ),

    layout = dict(
        autosize=True,
        font=dict(
            size=12,
            color="#CCCCCC",
        ),
        margin=dict(
            t=5,
            l=5,
            b=5,
            r=5,
        ),
        showlegend=False,
        hovermode='closest',
        scene=dict(
            aspectmode="manual",
            aspectratio=dict(x=2, y=5, z=1.5),
            camera=dict(
                up=UPS[value],
                center=CENTERS[value],
                eye=EYES[value]
            ),
            annotations=[dict(
                showarrow=False,
                y="2015-03-18",
                x="1-month",
                z=0.046,
                text="Point 1",
                xanchor="left",
                xshift=10,
                opacity=0.7
            ), dict(
                y="2015-03-18",
                x="3-month",
                z=0.048,
                text="Point 2",
                textangle=0,
                ax=0,
                ay=-75,
                font=dict(
                    color="black",
                    size=12
                ),
                arrowcolor="black",
                arrowsize=3,
                arrowwidth=1,
                arrowhead=1
            )],
            xaxis={
                "showgrid": True,
                "title": "",
                "type": "category",
                "zeroline": False,
                "categoryorder": 'array',
                "categoryarray": list(reversed(xlist))
            },
            yaxis={
                "showgrid": True,
                "title": "",
                "type": "date",
                "zeroline": False,
            },
        )
    )

    figure = dict(data=data, layout=layout)
    # py.iplot(figure)
    return figure	
#WIND 
@app.callback(Output('wind-speed', 'figure'), [],[],[Event('wind-speed-update', 'interval')])
def gen_wind_speed():
    now = dt.datetime.now()
    sec = now.second
    minute = now.minute
    hour = now.hour

    total_time = (hour * 3600) + (minute * 60) + (sec)

    con = sqlite3.connect("./Data/wind-data.db")
    df = pd.read_sql_query('SELECT Speed, SpeedError, Direction from Wind where\
                            rowid > "{}" AND rowid <= "{}";'
                            .format(total_time-200, total_time), con)

    trace = Scatter(
        y=df['Speed'],
        line=Line(
            color='##b3b3b3'
			#color='grey'
        ),
        hoverinfo='skip',
        error_y=ErrorY(
            type='data',
            array=df['SpeedError'],
            thickness=0.5,
            width=1,
            color='#B4E8FC'
        ),
        mode='lines'
    )

    layout = Layout(
        height=450,
        xaxis=dict(
            range=[0, 200],
            showgrid=False,
            showline=False,
            zeroline=False,
            fixedrange=True,
            tickvals=[0, 50, 100, 150, 200],
            ticktext=['200', '150', '100', '50', '0'],
            title='Time Elapsed (sec)'
        ),
        yaxis=dict(
            range=[min(0, min(df['Speed'])),
                   max(45, max(df['Speed'])+max(df['SpeedError']))],
            showline=False,
            fixedrange=True,
            zeroline=False,
            nticks=max(6, round(df['Speed'].iloc[-1]/10))
        ),
        margin=Margin(
            t=5,
            l=20,
            r=5
        )
    )
    return Figure(data=[trace], layout=layout)
@app.callback(Output('wind-direction', 'figure'), [],
              [],
              [Event('wind-speed-update', 'interval')])
def gen_wind_direction():
    now = dt.datetime.now()
    sec = now.second
    minute = now.minute
    hour = now.hour
    total_time = (hour * 3600) + (minute * 60) + (sec)
    con = sqlite3.connect("./Data/wind-data.db")
    df = pd.read_sql_query("SELECT * from Wind where rowid = " +
                                         str(total_time) + ";", con)

    val = df['Speed'].iloc[-1]
    trace = Area(
        r=np.full(5, val),
        t=np.full(5, df['Direction']),
        marker=Marker(
            color='rgb(242, 196, 247)'
        )
    )
    trace1 = Area(
        r=np.full(5, val*0.65),
        t=np.full(5, df['Direction']),
        marker=Marker(
            color='#F6D7F9'
        )
    )
    trace2 = Area(
        r=np.full(5, val*0.30),
        t=np.full(5, df['Direction']),
        marker=Marker(
            color='#FAEBFC'
        )
    )
    layout = Layout(
        autosize=True,
        width=275,
        plot_bgcolor='#F2F2F2',
        margin=Margin(
            t=10,
            b=10,
            r=30,
            l=40
        ),
        showlegend=False,
        radialaxis=dict(
            range=[0, max(max(df['Speed']), 40)]
        ),
        angularaxis=dict(
            showline=False,
            tickcolor='white'
        ),
        orientation=270,
    )
    return Figure(data=[trace, trace1, trace2], layout=layout)
@app.callback(Output('wind-histogram', 'figure'),
              [],
              [State('wind-speed', 'figure'),
               State('bin-slider', 'value'),
               State('bin-auto', 'values')],
              [Event('wind-speed-update', 'interval')])
def gen_wind_histogram(wind_speed_figure, sliderValue, auto_state):
#def gen_wind_histogram(wind_speed_figure, sliderValue):
    wind_val = []
    # Check to see whether wind-speed has been plotted yet
    if wind_speed_figure is not None:
        wind_val = wind_speed_figure['data'][0]['y']
    if 'Auto' in auto_state:
        bin_val = np.histogram(wind_val, bins=range(int(round(min(wind_val))),
                               int(round(max(wind_val)))))
    else:
        bin_val = np.histogram(wind_val, bins=sliderValue)

    avg_val = float(sum(wind_val))/len(wind_val)
    median_val = np.median(wind_val)

    pdf_fitted = rayleigh.pdf(bin_val[1], loc=(avg_val)*0.55,
                              scale=(bin_val[1][-1] - bin_val[1][0])/3)

    y_val = pdf_fitted * max(bin_val[0]) * 20,
    y_val_max = max(y_val[0])
    bin_val_max = max(bin_val[0])

    trace = Bar(
        x=bin_val[1],
        y=bin_val[0],
        marker=Marker(
            color='#7F7F7F'
        ),
        showlegend=False,
        hoverinfo='x+y'
    )
    trace1 = Scatter(
        x=[bin_val[int(len(bin_val)/2)]],
        y=[0],
        mode='lines',
        line=Line(
            dash='dash',
            color='#2E5266'
        ),
        marker=Marker(
            opacity=0,
        ),
        visible=False,
        name='Average'
    )
    trace2 = Scatter(
        x=[bin_val[int(len(bin_val)/2)]],
        y=[0],
        line=Line(
            dash='dot',
            color='#BD9391'
        ),
        mode='lines',
        marker=Marker(
            opacity=0,
        ),
        visible=False,
        name='Median'
    )
    trace3 = Scatter(
        mode='lines',
        line=Line(
            color='#42C4F7'
        ),
        y=y_val[0],
        x=bin_val[1][:len(bin_val[1])],
        name='Rayleigh Fit'
    )
    layout = Layout(
        xaxis=dict(
            title='Torque (Nm)',
            showgrid=False,
            showline=False,
            fixedrange=True
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            title='Number of Samples',
            fixedrange=True
        ),
        margin=Margin(
            t=0,
            b=10,
            r=10
        ),
        autosize=True,
        bargap=0.01,
        bargroupgap=0,
        hovermode='closest',
        legend=Legend(
            x=0.175,
            y=-0.01,
            orientation='h'
        ),
        shapes=[
            dict(
                xref='x',
                yref='y',
                y1=int(max(bin_val_max, y_val_max))+0.5,
                y0=0,
                x0=avg_val,
                x1=avg_val,
                type='line',
                line=Line(
                    dash='dash',
                    color='#2E5266',
                    width=5
                )
            ),
            dict(
                xref='x',
                yref='y',
                y1=int(max(bin_val_max, y_val_max))+0.5,
                y0=0,
                x0=median_val,
                x1=median_val,
                type='line',
                line=Line(
                    dash='dot',
                    color='#BD9391',
                    width=5
                )
            )
        ]
    )
    return Figure(data=[trace, trace1, trace2, trace3], layout=layout)
@app.callback(Output('bin-auto', 'values'), [Input('bin-slider', 'value')],
              [State('wind-speed', 'figure')],
              [Event('bin-slider', 'change')])
def deselect_auto(sliderValue, wind_speed_figure):
    if (wind_speed_figure is not None and
       len(wind_speed_figure['data'][0]['y']) > 5):
        return ['']
    else:
        return ['Auto']
@app.callback(Output('bin-size', 'children'), [Input('bin-auto', 'values')],
              [State('bin-slider', 'value')],
              [])
def deselect_auto(autoValue, sliderValue):
    if 'Auto' in autoValue:
        return '# of Bins: Auto'
    else:
        return '# of Bins: ' + str(int(sliderValue))
external_css = ["https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
                "https://cdn.rawgit.com/plotly/dash-app-stylesheets/737dc4ab11f7a1a8d6b5645d26f69133d97062ae/dash-wind-streaming.css",
                "https://fonts.googleapis.com/css?family=Raleway:400,400i,700,700i",
                "https://fonts.googleapis.com/css?family=Product+Sans:400,400i,700,700i"]
for css in external_css:
    app.css.append_css({"external_url": css})
if 'DYNO' in os.environ:
    app.scripts.append_script({
        'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'
    })
if __name__ == '__main__':
    app.run_server(debug=True)
