"""
Sinais de IA — Modelo LightGBM + Ensemble com features técnicas e sentimento
Score 0-1: probabilidade de alta nos próximos 3 dias
"""

from fastapi import APIRouter, HTTPException
import numpy as np
import pandas as pd
import yfinance as yf
import logging
from typing import List, Dict, Any
import os
import joblib

router = APIRouter()
logger = logging.getLogger("quantbot.signals")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "lgbm_model.pkl")


def criar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cria todas as features para o modelo de IA."""
    df = df.copy()

    # ── Indicadores técnicos ────────────────────
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["macd"]  = ema12 - ema26
    df["macd_s"] = df["macd"].ewm(span=9).mean()
    df["macd_h"] = df["macd"] - df["macd_s"]

    sma20 = df["Close"].rolling(20).mean()
    std20 = df["Close"].rolling(20).std()
    df["bb_pct"] = (df["Close"] - (sma20 - 2*std20)) / (4*std20 + 1e-9)

    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["atr"]  = tr.rolling(14).mean()
    df["atr_n"] = df["atr"] / df["Close"]   # normalizado

    # ── Momentum ──────────────────────────
    for n in [3, 5, 10, 20]:
        df[f"mom_{n}"] = df["Close"].pct_change(n)

    # ── Volatilidade ─────────────────────────
    df["vol_5"]  = df["Close"].pct_change().rolling(5).std()
    df["vol_21"] = df["Close"].pct_change().rolling(21).std() * np.sqrt(252)

    # ── Z-Score (mean reversion) ────────────────────
    df["zscore"] = (df["Close"] - sma20) / (std20 + 1e-9)

    # ── Volume ─────────────────────────────
    df["vol_ratio"] = df["Volume"] / (df["Volume"].rolling(20).mean() + 1)

    # ── Padrões de candle ───────────────────────
    df["body"]   = (df["Close"] - df["Open"]).abs() / (df["High"] - df["Low"] + 1e-9)
    df["upper_w"] = (df["High"] - df[["Close","Open"]].max(axis=1)) / (df["High"] - df["Low"] + 1e-9)
    df["lower_w"] = (df[["Close","Open"]].min(axis=1) - df["Low"]) / (df["High"] - df["Low"] + 1e-9)

    # ── Target: retorno 3 dias à frente ─────────────────
    df["target"] = (df["Close"].shift(-3) > df["Close"]).astype(int)

    return df


FEATURES = [
    "rsi","macd","macd_s","macd_h","bb_pct",
    "atr_n","mom_3","mom_5","mom_10","mom_20",
    "vol_5","vol_21","zscore","vol_ratio",
    "body","upper_w","lower_w"
]


def treinar_modelo_simples(df: pd.DataFrame):
    """
    Treina LightGBM se disponível, senão usa modelo baseado em regras.
    Salva o modelo para reutilização.
    """
    try:
        import lightgbm as lgb
        X = df[FEATURES].dropna()
        y = df["target"].loc[X.index]

        # Remove últimas 3 linhas (target ainda não conhecido)
        X = X.iloc[:-3]
        y = y.iloc[:-3]

        model = lgb.LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=20,
            min_child_samples=10,
            colsample_bytree=0.8,
            subsample=0.8,
            random_state=42,
            verbose=-1
        )
        model.fit(X, y)

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        return model, "lightgbm"

    except ImportError:
        logger.warning("LightGBM não instalado — usando modelo baseado em regras")
        return None, "rules"


def score_por_regras(row: dict) -> float:
    """
    Modelo de pontuação baseado em regras técnicas.
    Usado como fallback quando LightGBM não está disponível.
    Retorna score de 0.0 a 1.0.
    """
    score = 0.5

    rsi = row.get("rsi", 50)
    if 40 < rsi < 65:   score += 0.10
    elif rsi < 30:       score += 0.08   # sobrevenda — possível reversão
    elif rsi > 70:       score -= 0.12   # sobrecompra

    if row.get("macd_h", 0) > 0:         score += 0.08
    if row.get("macd_h", 0) > row.get("macd_h", 0) * 0.9:  # crescendo
        score += 0.04

    zscore = row.get("zscore", 0)
    if -1.5 < zscore < 0:   score += 0.06   # levemente abaixo da média
    elif zscore < -2.0:      score += 0.04   # reversão
    elif zscore > 1.5:       score -= 0.08

    mom_10 = row.get("mom_10", 0)
    if mom_10 > 0.03:    score += 0.08
    elif mom_10 < -0.05: score -= 0.10

    vol_ratio = row.get("vol_ratio", 1)
    if vol_ratio > 1.3:  score += 0.05   # volume alto confirma sinal

    bb_pct = row.get("bb_pct", 0.5)
    if 0.2 < bb_pct < 0.8:  score += 0.04
    elif bb_pct < 0.1:       score += 0.06  # próximo banda inferior

    vol_21 = row.get("vol_21", 0.2)
    if vol_21 > 0.4:  score -= 0.06   # alta volatilidade = risco

    return max(0.05, min(0.95, score))


def calcular_stop_take(preco: float, atr: float, score: float, risco_pct: float = 0.03) -> dict:
    """Calcula stop loss e take profit baseados no ATR."""
    multiplicador_stop = 1.5
    rr_ratio = 2.0  # risco:retorno 1:2

    stop  = round(preco - atr * multiplicador_stop, 2)
    take  = round(preco + atr * multiplicador_stop * rr_ratio, 2)
    risco = round((preco - stop) / preco * 100, 2)

    return {"stop_loss": stop, "take_profit": take, "risco_pct": risco, "rr_ratio": rr_ratio}


def gerar_razoes(row: dict, score: float) -> List[str]:
    """Gera explicações em linguagem natural para o sinal."""
    razoes = []

    if row.get("rsi", 50) < 40:
        razoes.append(f"RSI {row['rsi']:.0f} — zona de sobrevenda, possível reversão")
    elif row.get("rsi", 50) > 70:
        razoes.append(f"RSI {row['rsi']:.0f} — sobrecomprado, cuidado")
    else:
        razoes.append(f"RSI {row['rsi']:.0f} — zona saudável")

    if row.get("macd_h", 0) > 0:
        razoes.append("MACD histograma positivo — momentum de alta")
    else:
        razoes.append("MACD histograma negativo — pressão vendedora")

    mom = row.get("mom_10", 0)
    razoes.append(f"Momentum 10d: {mom*100:.1f}% {'\u2191' if mom > 0 else '\u2193'}")

    vol = row.get("vol_ratio", 1)
    if vol > 1.3:
        razoes.append(f"Volume {vol:.1f}x acima da média — confirma sinal")

    z = row.get("zscore", 0)
    razoes.append(f"Z-Score: {z:.2f} ({'acima' if z > 0 else 'abaixo'} da média 20d)")

    return razoes


@router.get("/calcular")
async def calcular_sinais(mercado: str = "BR", capital: float = 100.0):
    """
    Calcula sinais de IA para todos os ativos do mercado selecionado.
    Retorna score, direção, stops e explicação para cada ativo.
    """
    from routers.market import ATIVOS_BR, ATIVOS_US
    ativos = ATIVOS_BR if mercado == "BR" else ATIVOS_US
    sinais = []

    for ticker, symbol in ativos.items():
        try:
            df = yf.download(symbol, period="6mo", auto_adjust=True, progress=False)
            if len(df) < 50:
                continue

            df = criar_features(df)
            df = df.dropna(subset=FEATURES)

            ultima = df[FEATURES].iloc[-1].to_dict()
            preco  = float(df["Close"].iloc[-1])
            atr    = float(df["atr"].iloc[-1]) if "atr" in df else preco * 0.02

            # Tenta usar LightGBM; fallback para regras
            if os.path.exists(MODEL_PATH):
                try:
                    model = joblib.load(MODEL_PATH)
                    X = pd.DataFrame([ultima])[FEATURES]
                    score = float(model.predict_proba(X)[0][1])
                    tipo_modelo = "LightGBM"
                except Exception:
                    score = score_por_regras(ultima)
                    tipo_modelo = "Regras"
            else:
                score = score_por_regras(ultima)
                tipo_modelo = "Regras"

            # Direção
            if score >= 0.62:
                direcao = "COMPRAR"
            elif score <= 0.38:
                direcao = "VENDER"
            else:
                direcao = "AGUARDAR"

            # Tamanho da posição (Kelly simplificado)
            win_prob  = score
            loss_prob = 1 - score
            kelly = (win_prob * 2 - loss_prob) / 2  # RR = 2
            kelly = max(0.02, min(kelly, 0.25))      # limite 2–25% do capital
            posicao_reais = round(capital * kelly, 2)
            qtd_acoes     = max(1, int(posicao_reais / preco)) if preco > 0 else 0

            stops = calcular_stop_take(preco, atr, score)
            razoes = gerar_razoes(ultima, score)

            sinais.append({
                "ticker": ticker,
                "symbol": symbol,
                "preco": round(preco, 2),
                "score": round(score, 3),
                "direcao": direcao,
                "modelo": tipo_modelo,
                "posicao_reais": posicao_reais,
                "qtd_acoes": qtd_acoes,
                "stop_loss": stops["stop_loss"],
                "take_profit": stops["take_profit"],
                "risco_pct": stops["risco_pct"],
                "razoes": razoes,
                "rsi": round(ultima.get("rsi", 0), 1),
                "zscore": round(ultima.get("zscore", 0), 2),
                "mom_10": round(ultima.get("mom_10", 0) * 100, 2),
                "volatility": round(ultima.get("vol_21", 0) * 100, 1),
            })

        except Exception as e:
            logger.warning(f"Erro em {ticker}: {e}")

    sinais.sort(key=lambda x: x["score"], reverse=True)
    return {"mercado": mercado, "capital": capital, "sinais": sinais, "total": len(sinais)}


@router.post("/treinar/{ticker}")
async def treinar_modelo(ticker: str, mercado: str = "BR"):
    """
    Treina/retreina o modelo LightGBM com dados históricos do ticker.
    Útel para calibrar o modelo periodicamente.
    """
    sufixo = ".SA" if mercado == "BR" else ""
    symbol = f"{ticker.upper()}{sufixo}"

    df = yf.download(symbol, period="2y", auto_adjust=True, progress=False)
    if len(df) < 100:
        raise HTTPException(400, "Dados insuficientes para treino")

    df = criar_features(df)
    df = df.dropna(subset=FEATURES + ["target"])

    _, tipo = treinar_modelo_simples(df)
    return {"status": "ok", "modelo": tipo, "amostras": len(df), "symbol": symbol}
