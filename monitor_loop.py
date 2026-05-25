import time
import schedule
from datetime import datetime
from broker_mt5 import connect, close, get_open_positions, close_position, get_symbol_price

# Configura as variáveis dos papéis monitorados
ATIVOS = ["PETR4", "VALE3", "WINJ24", "WDOK24"]

# Parametrização de stops/take (exemplo simples)
STOPS = {
    "PETR4": {"stop": 3.0, "take": 10.0},   # valores em reais
    "VALE3": {"stop": 4.0, "take": 12.0},
    "WINJ24": {"stop": 400.0, "take": 800.0}, # pontos
    "WDOK24": {"stop": 20.0, "take": 50.0}
}

def monitorar():
    connect()
    try:
        log = []
        positions = get_open_positions(ATIVOS)
        for pos in positions:
            symbol = pos.symbol
            price = get_symbol_price(symbol)
            if price is None:
                continue
            entrada = pos.price_open
            stop = entrada - STOPS[symbol]["stop"]
            take = entrada + STOPS[symbol]["take"]
            # Simples: se comprou, monitora para baixo (stop) e cima (take). Inverter para vendidos.
            if pos.type == 0: # compra
                if price <= stop:
                    close_position(pos.ticket)
                    log.append(f"{datetime.now()} - STOP atingido em {symbol}. Fechado em {price}")
                elif price >= take:
                    close_position(pos.ticket)
                    log.append(f"{datetime.now()} - TAKE atingido em {symbol}. Fechado em {price}")
            else: # venda
                if price >= entrada + STOPS[symbol]["stop"]:
                    close_position(pos.ticket)
                    log.append(f"{datetime.now()} - STOP atingido (vendido) {symbol}. Fechado em {price}")
                elif price <= entrada - STOPS[symbol]["take"]:
                    close_position(pos.ticket)
                    log.append(f"{datetime.now()} - TAKE atingido (vendido) {symbol}. Fechado em {price}")
        # Salva registros
        with open("monitor_log.txt", "a") as f:
            for linha in log:
                f.write(linha+"\n")
        print("Monitoramento executado:", datetime.now())
    finally:
        close()

# Agenda para executar a cada hora
schedule.every().hour.do(monitorar)

if __name__ == "__main__":
    print("Iniciando o monitoramento automático cada 1h... (Ctrl+C para parar)")
    while True:
        schedule.run_pending()
        time.sleep(60)
