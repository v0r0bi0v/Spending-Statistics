import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import pytz
import calendar

timezone = pytz.timezone('Europe/Moscow')

# Функция для загрузки данных
def load_data():
    global last_modified_time, df
    current_modified_time = os.path.getmtime('expenses.csv')  # Измените на ваш файл
    
    if 'last_modified_time' not in globals() or current_modified_time != last_modified_time:
        last_modified_time = current_modified_time
        df = pd.read_csv("expenses.csv")  # Измените на ваш файл
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        df['month_name'] = df['month'].apply(lambda x: calendar.month_name[x])
        print(f"Данные обновлены в {datetime.now(timezone).strftime('%H:%M:%S')}")
    
    return df

# Инициализация приложения Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Создание layout дэшборда
app.layout = dbc.Container([
    html.H1("Анализ расходов", className="mb-4"),
    
    dbc.Button("Обновить данные", id="refresh-button", n_clicks=0, className="mb-3"),
    html.Div(id="last-updated", className="mb-2"),
    html.Div(id="total-month-sum", className="mb-2", style={'fontSize': 18, 'fontWeight': 'bold'}),
    
    dbc.Row([
        dbc.Col([
            html.Label("Выберите пользователя:"),
            dcc.Dropdown(
                id='user-dropdown',
                options=[],
                value=None,
                clearable=False
            )
        ], width=4),
        
        dbc.Col([
            html.Label("Выберите месяц:"),
            dcc.Dropdown(
                id='month-dropdown',
                options=[],
                value=None,
                clearable=False
            )
        ], width=4),
        
        dbc.Col([
            html.Label("Выберите год:"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[],
                value=None,
                clearable=False
            )
        ], width=4)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='spending-pie-chart')
        ], width=12)
    ]),
    
    # Закомментирован автоматический интервал обновления
    # dcc.Interval(
    #     id='interval-component',
    #     interval=120*1000,  # 120 секунд
    #     n_intervals=0
    # )
], fluid=True)

# Callback для обновления данных и dropdown пользователей
@callback(
    Output('user-dropdown', 'options'),
    Output('user-dropdown', 'value'),
    Output('last-updated', 'children'),
    Input('refresh-button', 'n_clicks'),
    # Input('interval-component', 'n_intervals')  # Закомментировано
)
def update_data(n_clicks, n_intervals=None):  # Убрал n_intervals из обязательных аргументов
    df = load_data()
    user_options = [{'label': user, 'value': user} for user in df['user_id'].unique()]
    default_user = user_options[0]['value'] if user_options else None
    last_update = f"Последнее обновление: {datetime.now(timezone).strftime('%H:%M:%S')}"
    return user_options, default_user, last_update

# Callback для обновления dropdown месяцев
@callback(
    Output('month-dropdown', 'options'),
    Output('month-dropdown', 'value'),
    Input('user-dropdown', 'value')
)
def update_month_dropdown(selected_user):
    df = load_data()
    if selected_user is None:
        return [], None
        
    filtered_df = df[df['user_id'] == selected_user]
    month_options = [{'label': calendar.month_name[m], 'value': m} 
                    for m in sorted(filtered_df['month'].unique())]
    default_value = month_options[0]['value'] if month_options else None
    return month_options, default_value

# Callback для обновления dropdown годов
@callback(
    Output('year-dropdown', 'options'),
    Output('year-dropdown', 'value'),
    Input('user-dropdown', 'value')
)
def update_year_dropdown(selected_user):
    df = load_data()
    if selected_user is None:
        return [], None
        
    filtered_df = df[df['user_id'] == selected_user]
    year_options = [{'label': str(y), 'value': y} 
                   for y in sorted(filtered_df['date'].dt.year.unique(), reverse=True)]
    default_value = year_options[0]['value'] if year_options else None
    return year_options, default_value

# Callback для обновления круговой диаграммы и общей суммы
@callback(
    Output('spending-pie-chart', 'figure'),
    Output('total-month-sum', 'children'),
    Input('user-dropdown', 'value'),
    Input('month-dropdown', 'value'),
    Input('year-dropdown', 'value')
)
def update_pie_chart(selected_user, selected_month, selected_year):
    df = load_data()
    
    if None in [selected_user, selected_month, selected_year]:
        return px.pie(title="Выберите параметры для отображения данных"), ""
    
    filtered_df = df[(df['user_id'] == selected_user) & 
                    (df['month'] == selected_month) & 
                    (df['date'].dt.year == selected_year)]
    
    if filtered_df.empty:
        return px.pie(title="Нет данных для выбранных параметров"), ""
    
    grouped_df = filtered_df.groupby('label')['amount'].sum().reset_index()
    total_sum = filtered_df['amount'].sum()
    
    month_name = calendar.month_name[selected_month]
    sum_text = f"Общая сумма расходов за {month_name} {selected_year}: {total_sum:.2f}"
    
    fig = px.pie(
        grouped_df,
        values='amount',
        names='label',
        title=f'Расходы пользователя {selected_user} за {month_name} {selected_year}',
        hover_data=['amount'],
        labels={'amount': 'Сумма', 'label': 'Категория'}
    )
    
    fig.update_traces(
        textinfo='label+percent+value',
        texttemplate='%{label}<br>%{percent:.1%}<br>%{value:.2f}',
        hovertemplate='<b>%{label}</b><br>Сумма: %{value:.2f}<br>Доля: %{percent:.1%}<extra></extra>',
        marker=dict(line=dict(color='#ffffff', width=1))
    )
    
    fig.update_layout(
        uniformtext_minsize=12,
        uniformtext_mode='hide',
        plot_bgcolor='rgba(240, 240, 240, 0.8)',
        paper_bgcolor='rgba(240, 240, 240, 0.1)'
    )
    
    return fig, sum_text

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8081)
