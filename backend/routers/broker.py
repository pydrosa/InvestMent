"""
Corretora — Alpaca Markets (paper trading gratuito)
Para começar: https://alpaca.markets → cadastro gratuito → Paper Trading
Suporta ações americanas (SPY, AAPL, MSFT, etc.)

Para ações brasileiras (PETR4, VALE3):
Use a API da Clear Corretora ou XP (via BTG Pactual API)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import logging

router = APIRouter()
logger = logging.getLogger("quantbot.broker")

# Carrega credenciais do .env (nunca hardcode as chaves!)
ALPACA_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_URL    = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")


class OrdemRequest(BaseModel):
    symbol: str
    qty: float
    side: str           # "buy" ou "sell"
    type: str = "market"
    time_in_force: str = "day"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None


def headers_alpaca():
    return {
        "APCA-API-KEY-ID":     ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
        "Content-Type": "application/json",
    }


def alpaca_configurado():
    return bool(ALPACA_KEY and ALPACA_SECRET)


@router.get("/status")
async def status_corretora():
    """Verifica se a corretora está configurada e acessível."""
    if not alpaca_configurado():
        return {
            "configurada": False,
            "corretora": "Alpaca",
            "modo": "paper",
            "instrucoes": "Adicione ALPACA_API_KEY e ALPACA_SECRET_KEY no arquivo .env",
            "link_cadastro": "https://alpaca.markets/",
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ALPACA_URL}/v2/account", headers=headers_alpaca())
            if r.status_code == 200:
                data = r.json()
                return {
                    "configurada": True,
                    "corretora": "Alpaca",
                    "modo": "paper" if "paper" in ALPACA_URL else "live",
                    "conta": data.get("account_number", ""),
                    "cash": float(data.get("cash", 0)),
                    "portfolio_value": float(data.get("portfolio_value", 0)),
                    "buying_power": float(data.get("buying_power", 0)),
                    "status": data.get("status", ""),
                }
            return {"configurada": False, "erro": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"configurada": False, "erro": str(e)}


@router.get("/conta")
async def conta():
    """Retorna saldo e posições da conta Alpaca."""
    if not alpaca_configurado():
        raise HTTPException(400, "Alpaca não configurada. Veja .env.example")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{ALPACA_URL}/v2/account", headers=headers_alpaca())
        r.raise_for_status()
        return r.json()


@router.get("/posicoes")
async def posicoes():
    """Lista todas as posições abertas."""
    if not alpaca_configurado():
        return {"posicoes": [], "aviso": "Configure Alpaca no .env"}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{ALPACA_URL}/v2/positions", headers=headers_alpaca())
        r.raise_for_status()
        data = r.json()

    return {
        "posicoes": [
            {
                "symbol": p["symbol"],
                "qty": float(p["qty"]),
                "preco_entrada": float(p["avg_entry_price"]),
                "preco_atual": float(p["current_price"]),
                "pnl": float(p["unrealized_pl"]),
                "pnl_pct": float(p["unrealized_plpc"]) * 100,
                "valor": float(p["market_value"]),
            }
            for p in data
        ]
    }


@router.post("/ordem")
async def enviar_ordem(ordem: OrdemRequest):
    """
    Envia ordem para Alpaca (paper trading).
    CUIDADO: Em modo live, executa ordens reais!
    """
    if not alpaca_configurado():
        raise HTTPException(400, "Configure ALPACA_API_KEY e ALPACA_SECRET_KEY no .env")

    payload = {
        "symbol":        ordem.symbol.upper(),
        "qty":           str(ordem.qty),
        "side":          ordem.side,
        "type":          ordem.type,
        "time_in_force": ordem.time_in_force,
    }

    if ordem.type == "limit" and ordem.limit_price:
        payload["limit_price"] = str(ordem.limit_price)
    if ordem.type in ("stop", "stop_limit") and ordem.stop_price:
        payload["stop_price"] = str(ordem.stop_price)

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{ALPACA_URL}/v2/orders",
            json=payload,
            headers=headers_alpaca()
        )

    if r.status_code not in (200, 201):
        raise HTTPException(r.status_code, r.text)

    data = r.json()
    logger.info(f"Ordem enviada: {ordem.side} {ordem.qty}x {ordem.symbol} → {data.get('id')}")

    return {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "qty": data.get("qty"),
        "side": data.get("side"),
        "type": data.get("type"),
        "status": data.get("status"),
        "submitted_at": data.get("submitted_at"),
    }


@router.delete("/ordem/{order_id}")
async def cancelar_ordem(order_id: str):
    """Cancela uma ordem pendente."""
    if not alpaca_configurado():
        raise HTTPException(400, "Alpaca não configurada")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.delete(
            f"{ALPACA_URL}/v2/orders/{order_id}",
            headers=headers_alpaca()
        )

    if r.status_code == 204:
        return {"status": "cancelada", "id": order_id}
    raise HTTPException(r.status_code, r.text)


@router.get("/ordens")
async def listar_ordens(status: str = "all", limit: int = 20):
    """Lista ordens recentes."""
    if not alpaca_configurado():
        return {"ordens": [], "aviso": "Configure Alpaca no .env"}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{ALPACA_URL}/v2/orders",
            params={"status": status, "limit": limit},
            headers=headers_alpaca()
        )
        r.raise_for_status()

    return {"ordens": r.json()}


@router.get("/historico")
async def historico_portfolio():
    """Histórico de patrimônio da conta (curva de equity real)."""
    if not alpaca_configurado():
        return {"historico": [], "aviso": "Configure Alpaca no .env"}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{ALPACA_URL}/v2/account/portfolio/history",
            params={"period": "1M", "timeframe": "1D"},
            headers=headers_alpaca()
        )
        if r.status_code != 200:
            return {"historico": []}

    data = r.json()
    timestamps = data.get("timestamp", [])
    equity     = data.get("equity", [])

    return {
        "historico": [
            {"data": str(t), "patrimonio": round(float(e), 2)}
            for t, e in zip(timestamps, equity)
        ]
    }
