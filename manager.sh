#!/bin/bash

# Переходим в директорию проекта
cd ~/projects/Spending-Statistics || exit

# Функция для запуска бота
start_bot() {
    if pgrep -f "python3 main.py --bot spending" > /dev/null; then
        echo "Spending-бот уже запущен."
    else
        nohup python3 main.py --bot spending > spending_bot.log 2>&1 &
        echo "Spending-бот запущен."
    fi
}

# Функция для запуска дашборда
start_dashboard() {
    if pgrep -f "python3 dashboard.py --bot spending" > /dev/null; then
        echo "Spending-дашборд уже запущен."
    else
        nohup python3 dashboard.py --bot spending > spending_dashboard.log 2>&1 &
        echo "Spending-дашборд запущен."
    fi
}

# Функция для авто-коммитов
start_autocommit() {
    if pgrep -f "spending_autocommit.sh" > /dev/null; then
        echo "Spending-автокоммиты уже запущены."
    else
        cat > spending_autocommit.sh << 'EOL'
#!/bin/bash
while true; do
    datetime=$(date '+%Y-%m-%d %H:%M:%S %Z')
    git pull
    git add -A
    git commit -m "SPENDING AUTOCOMMIT $datetime" --allow-empty
    git push
    sleep 3600
done
EOL
        chmod +x spending_autocommit.sh
        nohup ./spending_autocommit.sh > spending_autocommit.log 2>&1 &
        echo "Spending-автокоммиты запущены."
    fi
}

# Останавливаем все процессы Spending-бота
stop_all() {
    pkill -f "python3 main.py --bot spending"
    pkill -f "python3 dashboard.py --bot spending"
    pkill -f "spending_autocommit.sh"
    echo "Все процессы Spending-бота остановлены."
}

# Проверяем аргументы командной строки
case "$1" in
    start)
        start_bot
        start_dashboard
        start_autocommit
        ;;
    stop)
        stop_all
        ;;
    *)
        echo "Использование: $0 {start|stop}"
        exit 1
        ;;
esac

exit 0
