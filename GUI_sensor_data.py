from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import csv
#import GUI_ecc from the main file and let it run

app = Dash(__name__)  
filename = "trying_thing.csv"  
list_sensor = ["Sensor 1", "Sensor 2", "Sensor 3","Sensor 4","Sensor 5"]
time = []
Temperature = []

#here insert the csv reader 
def updating_value(time,Temperature):
    with open(filename, "r") as f:
        line = f.readlines()[-1]
        line = line.split(';')[0:-1]
        line[-1] = line[-1].strip('\n')
        print(line)
    time.append(line[0])
    Temperature.append(line[1:])
    return time,Temperature

#layout of the GUI
app.layout = html.Div([
    html.H1('Sensor Data'),
    dcc.Dropdown(
        id="checklist",
        options=list_sensor,
        value=[],
        multi=True
    ),
    html.Div(children=html.Div(id='live-graph'), className='row'),
    dcc.Interval(
        id='refresh',
        interval=1*1000,
        n_intervals=0
        ),    
])

#callback and online updating
@app.callback(
    Output("live-graph", 'children'), 
    Input("checklist", "value"),
    [Input("refresh", "n_intervals")])

def update_line_chart(data_names,n_intervals): 
    graphs = []
    updating_value(time,Temperature)
    for data_name in data_names:
        data = {'time': time,
        'Temperature':Temperature}
        df = pd.DataFrame(data)
        fig = px.line(df, x="time", y="Temperature", title=data_name)
        graphs.append( html.Div(dcc.Graph(id=data_name, figure = fig
        )))
    return graphs


if __name__ == '__main__':
    app.run_server(debug=True)