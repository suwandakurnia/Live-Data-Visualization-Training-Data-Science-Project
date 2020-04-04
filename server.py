import credentials, preferences

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

import pandas as pd
import pytz
import sqlite3
import datetime

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Live Twitter Visualization'

server = app.server

app.layout = html.Div(children=[

    html.H2('Live Tweet Sentiment Dashboard', style={'textAlign': 'center'}),
    
    html.Div(id='live-update-graph'),

    dcc.Interval(
        id='interval-component-slow',
        interval=5*1000, # in milliseconds
        n_intervals=0
    )
    ], style={'padding': '20px'})



# Update graph everytime interval is fired
@app.callback(Output('live-update-graph', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_live(n):

    # 1. Create Database Connection
    db = sqlite3.connect('corona.db')

    # 2. Query the data 
    tz_gmt = pytz.timezone('GMT+0')
    time_diff = datetime.timedelta(minutes=15)
    now = pd.datetime.now(tz=tz_gmt)
    last_5min = now-time_diff
    last_10min = now-time_diff*2

    query = f"""SELECT id_str, created_at, polarity, user_location, text FROM {preferences.TABLE_NAME} WHERE created_at >= '{last_10min}' AND created_at <= '{now}';"""

    df10 = pd.read_sql(query, con=db, parse_dates='created_at')
    df10['created_at'] = df10['created_at'].dt.tz_localize('GMT+0')
    df = df10[df10['created_at'] > last_5min ]

    # 3. Apply Preprocessing for Area Plot
    result = df.copy()
    result['sentiment'] = df['polarity'].apply(to_sentiment)
    result = result.join(pd.get_dummies(result['sentiment']))
    result['total_tweets'] = result[['positive', 'negative', 'neutral']].sum(axis=1)
    result = result.set_index('created_at').resample('5S').agg({
        'positive':sum,
        'neutral':sum,
        'negative':sum,
        'total_tweets':sum,
    })


    # Create the graph html object
    children = [
                html.Div([
                    # Line Plot
                    html.Div([
                        dcc.Graph(
                            id='line-plot',
                            figure={
                                'data': [
                                    go.Scatter(
                                        x=result.index,
                                        y=result['neutral'] ,
                                        name='Neutrals',
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(shape='spline', smoothing=0.5, width=0.5, color='#323232'),
                                        stackgroup='one'
                                    ),
                                    go.Scatter(
                                        x=result.index,
                                        y=result['negative']*-1,
                                        name='Negatives',
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(shape='spline', smoothing=0.5, width=0.5, color='#891921'),
                                        stackgroup='two'
                                    ),
                                    go.Scatter(
                                        x=result.index,
                                        y=result['positive'] ,
                                        name='Positives',
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(shape='spline', smoothing=0.5, width=0.5, color='#119dff'),
                                        stackgroup='three'
                                    )
                                ],
                                'layout':{
                                    'showlegend':False,
                                    'title':'Number of Tweets in 15min',
                                }
                            }
                        )
                    ], style={'width': '73%', 'display': 'inline-block', 'padding': '0 0 0 20'}),
                    
                    # Pie Plot
                    html.Div([
                        dcc.Graph(
                            id='pie-chart',
                            figure={
                                'data': [
                                    go.Pie(
                                        labels=['Positives', 'Negatives', 'Neutrals'], 
                                        values=[result['positive'].sum(), result['negative'].sum(), result['neutral'].sum()],
                                        marker_colors=['#119dff','#891921','#323232'],
                                        opacity=0.8,
                                        textinfo='value',
                                        hole=.65)
                                ],
                                'layout':{
                                    'showlegend':True,
                                    'title':'Tweets Percentage',
                                    'annotations':[
                                        dict(
                                            text='{0:.1f}K'.format(result[['positive', 'negative', 'neutral']].sum().sum()/1000),
                                            font=dict(
                                                size=40
                                            ),
                                            showarrow=False
                                        )
                                    ]
                                }

                            }
                        )
                    ], style={'width': '27%', 'display': 'inline-block'})
                    
                ]),
                
            ]
    return children


# Helper Functions 
def to_sentiment(polarity):
    if polarity > 0.5:
        return 'positive'
    elif polarity > -0.5:
        return 'neutral'
    else:
        return 'negative'

if __name__ == '__main__':
    app.run_server(debug=True)