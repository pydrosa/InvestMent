"""
QuantBot — Backend Principal
FastAPI + Yahoo Finance + IA com Sentimento + Alpaca (paper trading real)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
import os

from routers import market, signals, portfolio, backtest, broker, sentiment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("quantbot")

app = FastAPI(
    title="QuantBot API",
    description="Plataforma de trading algorítmico com IA",
    version="1.0.0"
)

# CORS para aceitar requisições do frontend (localhost:3000 e vercel/netlify)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://investmentbot.vercel.app",
        "https://investment-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router,    prefix="/api/market",    tags=["Market Data"])
app.include_router(signals.router,   prefix="/api/signals",   tags=["Sinais de IA"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfólio"])
app.include_router(backtest.router,  prefix="/api/backtest",  tags=["Backtest"])
app.include_router(broker.router,    prefix="/api/broker",    tags=["Corretora"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["Sentimento"])

@app.get("/")
async def root():
    return {"status": "online", "version": "1.0.0", "message": "QuantBot rodando!"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
