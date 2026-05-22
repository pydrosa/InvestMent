"""
Market Data — Yahoo Finance (dados reais, gratuitos)
Ativos brasileiros: PETR4.SA, VALE3.SA, etc.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger("quantbot.market")

# Ativos padrão para começar com pouco capital
ATIVOS_BR = {
    "PETR4": "PETR4.SA",
    "VALE3": "VALE3.SA",
    "ITUB4": "ITUB4.SA",
    "BBDC4": "BBDC4.SA",
    "WEGE3": "WEGE3.SA",
    "MGLU3": "MGLU3.SA",
    "ABEV3": "ABEV3.SA",
    "B3SA3": "B3SA3.SA",
}

# ETFs americanos acessíveis (para Alpaca paper trading)
ATIVOS_US = {
    "SPY":  "SPY",    # S&P 500 ETF
    "QQQ":  "QQQ",    # Nasdaq ETF
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
}


def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores técnicos no DataFrame de preços."""
    df = df.copy()

    # RSI (14 períodos)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # Bollinger Bands (20 períodos)
    sma20 = df["Close"].rolling(20).mean()
    std20 = df["Close"].rolling(20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_lower"] = sma20 - 2 * std20
    df["bb_mid"]   = sma20
    df["bb_pct"]   = (df["Close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # ATR (14 períodos) — para stop loss dinâmico
    high_low   = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close  = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    # Momentum (10 e 20 dias)
    df["mom_10"] = df["Close"].pct_change(10)
    df["mom_20"] = df["Close"].pct_change(20)

    # Volume médio
    df["vol_ratio"] = df["Volume"] / df["Volume"].rolling(20).mean()

    # Z-Score (mean reversion)
    df["zscore"] = (df["Close"] - df["Close"].rolling(20).mean()) / df["Close"].rolling(20).std()

    # Volatilidade realizada (21 dias)
    df["volatility"] = df["Close"].pct_change().rolling(21).std() * np.sqrt(252)

    return df


@router.get("/cotacao/{ticker}")
async def cotacao(ticker: str, periodo: str = "3mo"):
    """Busca cotação histórica real do Yahoo Finance."""
    sufixo = ".SA" if ticker.upper() in ATIVOS_BR else ""
    symbol = f"{ticker.upper()}{sufixo}"

    try:
        df = yf.download(symbol, period=periodo, auto_adjust=True, progress=False)
        if df.empty:
            raise HTTPException(404, f"Ticker {symbol} não encontrado")

        df = calcular_indicadores(df)
        df = df.dropna(subset=["rsi"])

        # Retorna os últimos 120 dias
        df_tail = df.tail(120)

        return {
            "ticker": ticker,
            "symbol": symbol,
            "ultimo_preco": round(float(df["Close"].iloc[-1]), 2),
            "variacao_dia": round(float(df["Close"].pct_change().iloc[-1] * 100), 2),
            "volume": int(df["Volume"].iloc[-1]),
            "datas": df_tail.index.strftime("%Y-%m-%d").tolist(),
            "closes": [round(float(x), 2) for x in df_tail["Close"]],
            "volumes": [int(x) for x in df_tail["Volume"]],
            "rsi": round(float(df["rsi"].iloc[-1]), 1),
            "macd": round(float(df["macd"].iloc[-1]), 4),
            "macd_signal": round(float(df["macd_signal"].iloc[-1]), 4),
            "atr": round(float(df["atr"].iloc[-1]), 2),
            "bb_upper": round(float(df["bb_upper"].iloc[-1]), 2),
            "bb_lower": round(float(df["bb_lower"].iloc[-1]), 2),
            "bb_pct": round(float(df["bb_pct"].iloc[-1]), 3),
            "zscore": round(float(df["zscore"].iloc[-1]), 2),
            "mom_10": round(float(df["mom_10"].iloc[-1] * 100), 2),
            "mom_20": round(float(df["mom_20"].iloc[-1] * 100), 2),
            "volatility": round(float(df["volatility"].iloc[-1] * 100), 1),
            "vol_ratio": round(float(df["vol_ratio"].iloc[-1]), 2),
        }

    except Exception as e:
        logger.error(f"Erro ao buscar {symbol}: {e}")
        raise HTTPException(500, str(e))


@router.get("/multiplos")
async def multiplos_ativos(
    mercado: str = Query("BR", description="BR ou US"),
    periodo: str = "3mo"
):
    """Busca cotações e indicadores de múltiplos ativos."""
    ativos = ATIVOS_BR if mercado == "BR" else ATIVOS_US
    resultados = []

    for ticker in ativos:
        try:
            sufixo = ".SA" if mercado == "BR" else ""
            symbol = f"{ticker}{sufixo}"
            df = yf.download(symbol, period=periodo, auto_adjust=True, progress=False)
            if df.empty:
                continue
            df = calcular_indicadores(df)
            df = df.dropna(subset=["rsi"])
            ultimo = df.iloc[-1]

            resultados.append({
                "ticker": ticker,
                "preco": round(float(ultimo["Close"]), 2),
                "variacao": round(float(df["Close"].pct_change().iloc[-1] * 100), 2),
                "rsi": round(float(ultimo["rsi"]), 1),
                "zscore": round(float(ultimo["zscore"]), 2),
                "mom_10": round(float(ultimo["mom_10"] * 100), 2),
                "volatility": round(float(ultimo["volatility"] * 100), 1),
                "atr": round(float(ultimo["atr"]), 2),
                "vol_ratio": round(float(ultimo["vol_ratio"]), 2),
            })
        except Exception as e:
            logger.warning(f"Pulando {ticker}: {e}")

    return {"mercado": mercado, "ativos": resultados, "total": len(resultados)}


@router.get("/ibovespa")
async def ibovespa(periodo: str = "6mo"):
    """Busca o Ibovespa para detectar regime de mercado."""
    df = yf.download("^BVSP", period=periodo, auto_adjust=True, progress=False)
    df = calcular_indicadores(df)
    df = df.dropna(subset=["rsi"])

    retorno_30d = float(df["Close"].pct_change(21).iloc[-1] * 100)
    volatilidade = float(df["volatility"].iloc[-1] * 100)

    if retorno_30d > 3 and df["rsi"].iloc[-1] > 50:
        regime = "bull"
    elif retorno_30d < -3 and df["rsi"].iloc[-1] < 50:
        regime = "bear"
    elif volatilidade > 30:
        regime = "crise"
    else:
        regime = "lateral"

    return {
        "datas": df.tail(90).index.strftime("%Y-%m-%d").tolist(),
        "closes": [round(float(x), 0) for x in df.tail(90)["Close"]],
        "regime": regime,
        "retorno_30d": round(retorno_30d, 2),
        "volatilidade": round(volatilidade, 1),
        "rsi": round(float(df["rsi"].iloc[-1]), 1),
    }
