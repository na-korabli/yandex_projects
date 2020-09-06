#!/usr/bin/python
# -*- coding: utf-8 -*-

from sqlalchemy import create_engine

import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go


db_config = {'user': 'my_user',
             'pwd': 'my_user_password',
             'host': 'localhost',
             'port': 5432,
             'db': 'zen'}

connection_string = 'postgresql://{}:{}@{}:{}/{}'\
                    .format(db_config['user'],
                     	     db_config['pwd'],
                     	     db_config['host'],
                     	     db_config['port'],
                     	     db_config['db'])

engine = create_engine(connection_string)

query = '''
           SELECT * FROM dash_visits
        '''
dash_visits = pd.io.sql.read_sql(query, con=engine)


query = '''
           SELECT * FROM dash_engagement
        '''
dash_engagement = pd.io.sql.read_sql(query, con=engine)


note = '''
       Этот дашборд отображает историю событий по темам карточек, 
       разбивку событий по темам источников и глубину взаимодействия пользователей с карточками.
       Для выбора интервала дат воспользуйтесь фильтром дат.
       Для выбора возростной категории и тем карточек воспользуйтесь выпадающим списком.
       '''

dash_visits['dt'] = pd.to_datetime(dash_visits['dt'])
dash_engagement['dt'] = pd.to_datetime(dash_engagement['dt'])


dash_visits['dt'] = pd.to_datetime(dash_visits['dt'], format = '%Y-%m-%d %h:%m:%s')
dash_engagement['dt'] = pd.to_datetime(dash_engagement['dt'], format = '%Y-%m-%d %h:%m:%s')

#задаем лэйаут
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(children=[

	#формируем html
	html.H1(children='Анализ взаимодействия пользователей с карточками Яндекс.Дзен'),
	html.Label(note),
	html.Br(),

	#Input
	html.Div([
		html.Div([
			html.Label('Дата и время'),
			dcc.DatePickerRange(
				start_date = dash_visits['dt'].min(),
				end_date = dash_visits['dt'].max(),
				display_format = 'YYYY-MM-DD HH:SS',
				id = 'dt_selector')],

			className = 'three columns'),
		
		html.Div([
			html.Label('Возрастные категории'),
			dcc.Dropdown(
	    		options = [{'label': x, 'value': x} for x in dash_visits['age_segment'].unique()],
	    		value = dash_visits['age_segment'].unique().tolist(),
	    		multi = True,
	    		id = 'age_dropdown')],

			className = 'three columns'),

	    html.Div([
	    	html.Label('Темы'),
	    	dcc.Dropdown(
	    		options = [{'label': x, 'value': x} for x in dash_visits['item_topic'].unique()],
	    		value =dash_visits['item_topic'].unique().tolist(),
	    		multi = True,
	    		id = 'item_topic_dropdown')],

	    	className = 'six columns')
		], className = 'row'),

	html.Br(),

	#Output
	html.Div([
		html.Div([
			dcc.Graph(
				id = 'history_absolute_visits',
				style = {'height': '50vw'})],

			className = 'six columns'),

		html.Div([
			dcc.Graph(
				id = 'pie_visits',
				style = {'height': '25vw'}),
		
			dcc.Graph(
				id = 'engagement_graph',
				style = {'height': '25vw'})], 

			className = 'six columns')
	], className = 'row')
])


@app.callback(
	[Output('history_absolute_visits', 'figure'),
	 Output('pie_visits', 'figure'),
	 Output('engagement_graph', 'figure')],

	[Input('item_topic_dropdown', 'value'),
	 Input('age_dropdown', 'value'),
	 Input('dt_selector', 'start_date'),
	 Input('dt_selector', 'end_date')]
	 )


def update_figures(selected_item_topic, selected_ages, start_date, end_date):
	
	filtred_visits = dash_visits.query('dt >= @start_date and \
		                                dt <= @end_date and \
		                                item_topic in @selected_item_topic and \
		                                age_segment in @selected_ages')


	filtred_engagement = dash_visits.query('dt >= @start_date and \
		                                    dt <= @end_date and \
		                                    item_topic in @selected_item_topic and \
		                                    age_segment in @selected_ages')


	visits_group_topic = filtred_visits.groupby(['item_topic', 'dt'])\
	                                   .agg({'visits': 'sum'})\
	                                   .reset_index()
	scatter_by_topic = []
	for item_topic in visits_group_topic['item_topic'].unique():
		scatter_by_topic += [go.Scatter(x = visits_group_topic.query('item_topic == @item_topic')['dt'],
			                            y = visits_group_topic.query('item_topic == @item_topic')['visits'],
			                            mode = 'lines',
			                            stackgroup = 'one',
	                                    name = item_topic)]




	visits_group_source = filtred_visits.groupby(['source_topic'])\
	                                    .agg({'visits': 'sum'})\
	                                    .reset_index()
	pie_by_source = [go.Pie(labels = visits_group_source['source_topic'],
		                    values = visits_group_source['visits'])]

	
	engagement_group_event = dash_engagement.groupby(['event'])\
                                            .agg({'unique_users': 'mean'})\
                                            .reset_index()\
                                            .rename(columns = {'unique_users':
                                            	               'avg_unique_users'})\
                                            .sort_values(by='avg_unique_users',
                                                        ascending=False)


	mean_show = engagement_group_event.query('event == "show"')['avg_unique_users'].tolist()
	engagement_group_event['funnel'] = (engagement_group_event['avg_unique_users'] /
	                                              mean_show * 100).round(0)


	bar_by_avg_unique_user = [go.Bar(x = engagement_group_event['event'],
                                     y = engagement_group_event['funnel'],
                                     text = engagement_group_event['funnel'],
                                     textposition = 'auto')]


	return({'data': scatter_by_topic,
		    'layout': go.Layout(title = 'События по темам карточек',
		     	                title_font_size = 23,
		                        xaxis_title = 'Дата и время',
		                        yaxis_title = 'Количество посещений',
		                        width = 750)},


		   {'data': pie_by_source,
		    'layout': go.Layout(title = 'События по темам источников',
		    	                title_font_size = 23,
		      	                height = 420)},


		    {'data': bar_by_avg_unique_user,
		    'layout': go.Layout(title = 'Средняя глубина взаимодействия',
		      	                title_font_size = 23,
		      	                xaxis_title = 'Событие',
		      	                yaxis_title = '% от среднего числа показов')}
		    )


#описываем логику дашборда
if __name__ == '__main__':
	app.run_server(debug=True, host='0.0.0.0')