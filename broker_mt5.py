import MetaTrader5 as mt5

# Configurações de conexão (edite para seus dados)
MT5_LOGIN = 1234567                   # <==== Seu login na corretora
MT5_PASSWORD = "SUA_SENHA"            # <==== Sua senha MT5
MT5_SERVER = "NomeDoServidor"         # <==== Exemplo: "ClearInvestimentos-Demo"

def connect():
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        raise Exception(f"Erro para conectar ao MetaTrader 5: {mt5.last_error()}")

def close():
    mt5.shutdown()

def get_open_positions(symbols=None):
    positions = mt5.positions_get()
    if symbols is None:
        return positions or []
    return [p for p in (positions or []) if p.symbol in symbols]

def close_position(ticket):
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "type": mt5.ORDER_TYPE_SELL,
        "volume": 1.0,  # volume padrão, ajuste conforme necessidade
        "deviation": 20,
        "magic": 234000,
        "comment": "Fechamento automático por bot"
    }
    result = mt5.order_send(request)
    return result

def get_symbol_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    return tick.last if tick else None
