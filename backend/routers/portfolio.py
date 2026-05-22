"""
Portfólio — Gerenciamento de posições em paper trading local
Armazena posições em arquivo JSON (simples para começar)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json, os, logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger("quantbot.portfolio")

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")


def carregar() -> dict:
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    if not os.path.exists(PORTFOLIO_FILE):
        estado = {"capital": 100.0, "posicoes": [], "historico": [], "criado_em": datetime.now().isoformat()}
        salvar(estado)
        return estado
    with open(PORTFOLIO_FILE) as f:
        return json.load(f)


def salvar(estado: dict):
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)


class EntradaRequest(BaseModel):
    ticker: str
    preco: float
    qtd: int
    stop_loss: float
    take_profit: float
    score_ia: float
    razao: str = ""


class SaidaRequest(BaseModel):
    ticker: str
    preco: float
    motivo: str = "manual"


@router.get("/")
async def ver_portfolio():
    estado = carregar()
    total_posicoes = sum(p["preco_entrada"] * p["qtd"] for p in estado.get("posicoes", []))
    return {
        "capital_caixa": round(estado["capital"], 2),
        "valor_posicoes": round(total_posicoes, 2),
        "patrimonio_total": round(estado["capital"] + total_posicoes, 2),
        "posicoes": estado.get("posicoes", []),
        "n_trades": len(estado.get("historico", [])),
    }


@router.post("/entrar")
async def entrar_posicao(req: EntradaRequest):
    estado = carregar()
    custo = req.preco * req.qtd

    if custo > estado["capital"]:
        raise HTTPException(400, f"Capital insuficiente: R${estado['capital']:.2f} disponível, R${custo:.2f} necessário")

    ja_existe = any(p["ticker"] == req.ticker for p in estado.get("posicoes", []))
    if ja_existe:
        raise HTTPException(400, f"Já há posição aberta em {req.ticker}")

    estado["capital"] -= custo
    estado.setdefault("posicoes", []).append({
        "ticker": req.ticker,
        "preco_entrada": req.preco,
        "qtd": req.qtd,
        "stop_loss": req.stop_loss,
        "take_profit": req.take_profit,
        "score_ia": req.score_ia,
        "razao": req.razao,
        "data_entrada": datetime.now().isoformat(),
    })

    salvar(estado)
    logger.info(f"Entrada: {req.qtd}x {req.ticker} @ R${req.preco}")
    return {"status": "ok", "capital_restante": round(estado["capital"], 2)}


@router.post("/sair")
async def sair_posicao(req: SaidaRequest):
    estado = carregar()
    posicao = next((p for p in estado.get("posicoes", []) if p["ticker"] == req.ticker), None)

    if not posicao:
        raise HTTPException(404, f"Posição {req.ticker} não encontrada")

    pnl = (req.preco - posicao["preco_entrada"]) * posicao["qtd"]
    retorno = pnl / (posicao["preco_entrada"] * posicao["qtd"]) * 100

    estado["capital"] += req.preco * posicao["qtd"]
    estado["posicoes"] = [p for p in estado["posicoes"] if p["ticker"] != req.ticker]
    estado.setdefault("historico", []).append({
        "ticker": req.ticker,
        "preco_entrada": posicao["preco_entrada"],
        "preco_saida": req.preco,
        "qtd": posicao["qtd"],
        "pnl": round(pnl, 2),
        "retorno_pct": round(retorno, 2),
        "motivo": req.motivo,
        "data_saida": datetime.now().isoformat(),
    })

    salvar(estado)
    logger.info(f"Saída: {posicao['qtd']}x {req.ticker} @ R${req.preco} | PnL: R${pnl:.2f}")
    return {"status": "ok", "pnl": round(pnl, 2), "retorno_pct": round(retorno, 2)}


@router.get("/historico")
async def historico():
    estado = carregar()
    hist = estado.get("historico", [])
    if not hist:
        return {"historico": [], "resumo": {}}

    pnls = [t["pnl"] for t in hist]
    wins = [p for p in pnls if p > 0]
    return {
        "historico": hist[-50:],
        "resumo": {
            "total_trades": len(hist),
            "pnl_total": round(sum(pnls), 2),
            "win_rate": round(len(wins) / len(hist) * 100, 1),
            "ganho_medio": round(sum(wins) / len(wins), 2) if wins else 0,
            "perda_media": round(sum(p for p in pnls if p < 0) / max(1, len(pnls) - len(wins)), 2),
        }
    }


@router.post("/resetar")
async def resetar_portfolio(capital: float = 100.0):
    """Reinicia o portfolio (útil para começar um novo ciclo de paper trading)."""
    estado = {"capital": capital, "posicoes": [], "historico": [], "criado_em": datetime.now().isoformat()}
    salvar(estado)
    return {"status": "resetado", "capital": capital}
