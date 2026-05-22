"""
Backtest — Simulação de estratégia com dados históricos reais
Calcula métricas: Sharpe, Drawdown, Win Rate, Profit Factor
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
import numpy as np
import logging
from typing import List, Dict

router = APIRouter()
logger = logging.getLogger("quantbot.backtest")


class BacktestRequest(BaseModel):
    ticker: str
    mercado: str = "BR"
    capital_inicial: float = 100.0
    periodo: str = "1y"
    estrategia: str = "momentum"
    stop_loss_pct: float = 3.0
    take_profit_pct: float = 6.0
    risco_por_op: float = 5.0


def criar_sinais_backtest(df: pd.DataFrame, estrategia: str = "momentum") -> pd.Series:
    """
    Gera sinais de compra/venda baseado na estratégia selecionada.
    1 = comprar, -1 = vender, 0 = aguardar
    """
    df = df.copy()
    
    if estrategia == "momentum":
        # Momentum simples: compra se preço está acima da média móvel
        df["sma20"] = df["Close"].rolling(20).mean()
        df["sma50"] = df["Close"].rolling(50).mean()
        df["signal"] = np.where(df["Close"] > df["sma20"], 1, -1)
        df["signal"] = np.where(df["sma20"] > df["sma50"], df["signal"], -1)
        
    elif estrategia == "mean_reversion":
        # Mean reversion: compra se preço está abaixo da banda inferior
        df["sma20"] = df["Close"].rolling(20).mean()
        df["std20"] = df["Close"].rolling(20).std()
        df["bb_lower"] = df["sma20"] - 2 * df["std20"]
        df["signal"] = np.where(df["Close"] < df["bb_lower"], 1, -1)
        
    elif estrategia == "hibrida":
        # Híbrid: combina momentum + mean reversion
        df["sma20"] = df["Close"].rolling(20).mean()
        df["sma50"] = df["Close"].rolling(50).mean()
        df["std20"] = df["Close"].rolling(20).std()
        df["bb_lower"] = df["sma20"] - 2 * df["std20"]
        
        momentum = np.where(df["sma20"] > df["sma50"], 1, -1)
        reversion = np.where(df["Close"] < df["bb_lower"], 1, -1)
        df["signal"] = np.where((momentum == 1) & (reversion == 1), 1, -1)
    else:
        df["signal"] = 0
    
    return df["signal"]


def simular_trades(df: pd.DataFrame, capital: float, stop_loss_pct: float, 
                   take_profit_pct: float, risco_por_op: float) -> Dict:
    """
    Simula execução de trades com stops e targets.
    Retorna histórico de trades e métricas.
    """
    trades = []
    equity = [capital]
    posicao_ativa = None
    saldo = capital
    
    for i in range(1, len(df)):
        preco_atual = df["Close"].iloc[i]
        signal = df["signal"].iloc[i]
        
        # Verifica se está em posição aberta
        if posicao_ativa:
            preco_entrada = posicao_ativa["preco"]
            retorno = (preco_atual - preco_entrada) / preco_entrada * 100
            
            # Stop loss ou take profit atingido?
            if preco_atual <= preco_entrada * (1 - stop_loss_pct / 100):
                # Stop loss
                pnl = posicao_ativa["valor"] * (1 - stop_loss_pct / 100) - posicao_ativa["valor"]
                saldo += posicao_ativa["valor"] + pnl
                trades.append({
                    "entrada": df.index[posicao_ativa["idx"]],
                    "saida": df.index[i],
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_atual,
                    "pnl": round(pnl, 2),
                    "retorno": round(retorno, 2),
                    "motivo": "stop_loss"
                })
                posicao_ativa = None
                
            elif preco_atual >= preco_entrada * (1 + take_profit_pct / 100):
                # Take profit
                pnl = posicao_ativa["valor"] * (take_profit_pct / 100)
                saldo += posicao_ativa["valor"] + pnl
                trades.append({
                    "entrada": df.index[posicao_ativa["idx"]],
                    "saida": df.index[i],
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_atual,
                    "pnl": round(pnl, 2),
                    "retorno": round(retorno, 2),
                    "motivo": "take_profit"
                })
                posicao_ativa = None
        
        # Abre nova posição se sinal
        if signal == 1 and not posicao_ativa:
            posicao_valor = saldo * (risco_por_op / 100)
            posicao_ativa = {
                "preco": preco_atual,
                "valor": posicao_valor,
                "idx": i
            }
        
        equity.append(saldo)
    
    return {"trades": trades, "equity": equity}


@router.post("/rodar")
async def rodar_backtest(req: BacktestRequest):
    """
    Executa backtest com dados reais do Yahoo Finance.
    Retorna Sharpe, Drawdown, Win Rate e outros métricas.
    """
    sufixo = ".SA" if req.mercado == "BR" else ""
    symbol = f"{req.ticker.upper()}{sufixo}"
    
    try:
        # Busca dados históricos
        df = yf.download(symbol, period=req.periodo, auto_adjust=True, progress=False)
        if df.empty or len(df) < 50:
            raise HTTPException(400, f"Dados insuficientes para {symbol}")
        
        # Cria sinais
        df["signal"] = criar_sinais_backtest(df, req.estrategia)
        
        # Simula trades
        resultado = simular_trades(
            df, 
            req.capital_inicial, 
            req.stop_loss_pct,
            req.take_profit_pct,
            req.risco_por_op
        )
        
        trades = resultado["trades"]
        equity = resultado["equity"]
        
        if not trades:
            return {
                "erro": "Nenhum trade executado. Ajuste os parâmetros.",
                "ticker": req.ticker,
                "capital_inicial": req.capital_inicial,
                "capital_final": equity[-1],
                "retorno_total": 0,
                "total_trades": 0
            }
        
        # Calcula métricas
        capital_final = equity[-1]
        retorno_total = (capital_final - req.capital_inicial) / req.capital_inicial * 100
        
        # Sharpe Ratio
        retornos_diarios = np.diff(equity) / np.array(equity[:-1])
        sharpe = (np.mean(retornos_diarios) / np.std(retornos_diarios) * np.sqrt(252)) if np.std(retornos_diarios) > 0 else 0
        
        # Max Drawdown
        cummax = np.maximum.accumulate(equity)
        drawdown = (np.array(equity) - cummax) / cummax * 100
        max_drawdown = np.min(drawdown)
        
        # Win Rate
        pnls = [t["pnl"] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        win_rate = (wins / len(trades) * 100) if trades else 0
        
        # Profit Factor
        ganhos = sum(p for p in pnls if p > 0)
        perdas = abs(sum(p for p in pnls if p < 0))
        profit_factor = (ganhos / perdas) if perdas > 0 else 0
        
        # Calmar Ratio
        retorno_anual = retorno_total / (len(df) / 252)  # aproximado
        calmar = (retorno_anual / abs(max_drawdown)) if abs(max_drawdown) > 0 else 0
        
        return {
            "ticker": req.ticker,
            "estrategia": req.estrategia,
            "capital_inicial": req.capital_inicial,
            "capital_final": round(capital_final, 2),
            "retorno_total": round(retorno_total, 2),
            "sharpe": round(sharpe, 2),
            "max_drawdown": round(max_drawdown, 2),
            "win_rate": round(win_rate, 1),
            "wins": wins,
            "losses": len(trades) - wins,
            "total_trades": len(trades),
            "profit_factor": round(profit_factor, 2),
            "calmar": round(calmar, 2),
            "datas": df.index.strftime("%Y-%m-%d").tolist(),
            "equity": [round(e, 2) for e in equity],
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(500, str(e))
