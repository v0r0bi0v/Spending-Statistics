import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import calendar

# Загрузка данных (замените на ваш CSV)
df = pd.read_csv('expenses.csv')

# Преобразование даты в datetime
df['date'] = pd.to_datetime(df['date'])

# Извлекаем месяц и год из даты
df['month'] = df['date'].dt.month
df['year'] = df['date'].dt.year

# Создаем список уникальных пользователей
users = df['user_id'].unique()

# Создаем список месяцев для выпадающего списка
months = [{'label': calendar.month_name[i], 'value': i} for i in range(1, 13)]

# Инициализация Dash приложения
app = dash.Dash(__name__)

# Layout приложения
app.layout = html.Div([
    html.H1("Анализ расходов пользователя"),
    
    html.Div([
        html.Label("Выберите пользователя:"),
        dcc.Dropdown(
            id='user-dropdown',
            options=[{'label': user, 'value': user} for user in users],
            value=users[0]
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    
    html.Div([
        html.Label("Выберите месяц:"),
        dcc.Dropdown(
            id='month-dropdown',
            options=months,
            value=1
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    
    dcc.Graph(id='pie-chart')
])

# Callback для обновления диаграммы
@app.callback(
    Output('pie-chart', 'figure'),
    [Input('user-dropdown', 'value'),
     Input('month-dropdown', 'value')]
)
def update_pie_chart(selected_user, selected_month):
    # Фильтруем данные по пользователю и месяцу
    filtered_df = df[(df['user_id'] == selected_user) & (df['month'] == selected_month)]
    
    if filtered_df.empty:
        return px.pie(title="Нет данных для выбранных параметров")
    
    # Группируем по категориям и суммируем amount
    grouped_df = filtered_df.groupby('label')['amount'].sum().reset_index()
    
    # Создаем круговую диаграмму с абсолютными и относительными значениями
    fig = px.pie(
        grouped_df,
        values='amount',
        names='label',
        title=f'Расходы пользователя {selected_user} за {calendar.month_name[selected_month]}',
        hover_data=['amount'],
        labels={'amount': 'Сумма', 'label': 'Категория'}
    )
    
    # Добавляем подписи с абсолютными и относительными значениями
    fig.update_traces(
        textinfo='label+percent+value',
        texttemplate='%{label}<br>%{percent:.1%}<br>%{value:.2f}',
        hovertemplate='<b>%{label}</b><br>' +
                      'Сумма: %{value:.2f}<br>' +
                      'Доля: %{percent:.1%}<extra></extra>'
    )
    
    return fig

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="8081")
