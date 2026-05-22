"""
Sentimento de Mercado — RSS feeds de notícias financeiras
Análise com palavras-chave ponderadas (sem custo de API)
Opcional: integração com NewsAPI se tiver chave
"""

from fastapi import APIRouter
import httpx
import xml.etree.ElementTree as ET
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict

router = APIRouter()
logger = logging.getLogger("quantbot.sentiment")

# ── Feeds RSS gratuitos de finanças ──────────────────
RSS_FEEDS = [
    {"nome": "Infomoney",   "url": "https://www.infomoney.com.br/feed/"},
    {"nome": "Valor Econômico", "url": "https://valor.globo.com/rss/home/"},
    {"nome": "Reuters Brasil",  "url": "https://feeds.reuters.com/reuters/BRbusinessNews"},
    {"nome": "Yahoo Finance BR", "url": "https://br.financas.yahoo.com/rss/"},
]

# ── Dicionário de sentimento financeiro (PT-BR) ─────────────
POSITIVO = {
    "alta": 1.0, "sobe": 1.0, "subiu": 1.0, "valoriza": 1.0,
    "crescimento": 0.8, "lucro": 1.0, "resultado positivo": 1.2,
    "recorde": 1.2, "máxima": 0.9, "compra": 0.8, "recomenda": 0.9,
    "otimismo": 1.0, "expansão": 0.8, "dividend": 0.7, "ganho": 0.9,
    "supera": 1.1, "forte": 0.8, "rally": 1.2, "bull": 1.0,
    "recover": 0.9, "upside": 1.0, "buy": 0.9, "outperform": 1.0,
}

NEGATIVO = {
    "queda": -1.0, "cai": -1.0, "caiu": -1.0, "desvaloriza": -1.0,
    "prejuízo": -1.2, "resultado negativo": -1.2, "mínima": -0.9,
    "venda": -0.8, "rebaixa": -1.0, "pessimismo": -1.0,
    "recessão": -1.2, "crise": -1.2, "bear": -1.0, "sell": -0.9,
    "underperform": -1.0, "risco": -0.6, "incerteza": -0.7,
    "inflação": -0.5, "juros alta": -0.8, "inadimplência": -0.9,
    "fraude": -1.5, "investigação": -0.8, "processo": -0.7,
}


def analisar_texto(texto: str) -> Dict:
    """Analisa sentimento de um texto financeiro."""
    texto_lower = texto.lower()
    score = 0.0
    termos = []

    for palavra, peso in POSITIVO.items():
        if palavra in texto_lower:
            score += peso
            termos.append({"termo": palavra, "peso": peso})

    for palavra, peso in NEGATIVO.items():
        if palavra in texto_lower:
            score += peso
            termos.append({"termo": palavra, "peso": peso})

    if score > 0.5:   sentimento = "positivo"
    elif score < -0.5: sentimento = "negativo"
    else:              sentimento = "neutro"

    return {
        "score": round(score, 2),
        "sentimento": sentimento,
        "termos": termos[:5],
    }


def extrair_ticker_mencionado(texto: str, tickers: List[str]) -> List[str]:
    """Detecta quais tickers são mencionados no texto."""
    mencionados = []
    texto_upper = texto.upper()
    for t in tickers:
        if t in texto_upper:
            mencionados.append(t)
    return mencionados


async def buscar_rss(feed_url: str, timeout: int = 5) -> List[Dict]:
    """Busca e parseia um feed RSS."""
    noticias = []
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(feed_url, headers={"User-Agent": "QuantBot/1.0"})
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.text)
            channel = root.find("channel")
            if channel is None:
                channel = root

            for item in channel.findall("item")[:10]:
                titulo = item.findtext("title", "")
                descr  = item.findtext("description", "")
                link   = item.findtext("link", "")
                pubdate = item.findtext("pubDate", "")

                texto = f"{titulo} {descr}"
                sent  = analisar_texto(texto)

                noticias.append({
                    "titulo": titulo[:120],
                    "link": link,
                    "data": pubdate[:30] if pubdate else "",
                    "score": sent["score"],
                    "sentimento": sent["sentimento"],
                })

    except Exception as e:
        logger.debug(f"Feed {feed_url} falhou: {e}")

    return noticias


@router.get("/noticias")
async def noticias(mercado: str = "BR"):
    """Agrega notícias de feeds RSS e calcula sentimento do mercado."""
    todas = []

    for feed in RSS_FEEDS:
        itens = await buscar_rss(feed["url"])
        for item in itens:
            item["fonte"] = feed["nome"]
            todas.append(item)

    if not todas:
        # Fallback: retorna sentimento neutro quando feeds falham
        return {
            "sentimento_geral": "neutro",
            "score_medio": 0.0,
            "noticias": [],
            "positivas": 0,
            "negativas": 0,
            "neutras": 0,
            "aviso": "Feeds RSS temporariamente indisponíveis"
        }

    scores = [n["score"] for n in todas]
    score_medio = sum(scores) / len(scores) if scores else 0

    positivas = sum(1 for s in scores if s > 0.5)
    negativas = sum(1 for s in scores if s < -0.5)
    neutras   = len(scores) - positivas - negativas

    if score_medio > 0.3:   sentimento_geral = "positivo"
    elif score_medio < -0.3: sentimento_geral = "negativo"
    else:                    sentimento_geral = "neutro"

    return {
        "sentimento_geral": sentimento_geral,
        "score_medio": round(score_medio, 2),
        "noticias": sorted(todas, key=lambda x: abs(x["score"]), reverse=True)[:15],
        "positivas": positivas,
        "negativas": negativas,
        "neutras": neutras,
    }


@router.get("/fear-greed")
async def fear_greed():
    """
    Índice Fear & Greed simplificado baseado em:
    - Volatilidade do Ibovespa (VIX-like)
    - Momentum do mercado
    - Volume relativo
    """
    import yfinance as yf
    import numpy as np

    try:
        df = yf.download("^BVSP", period="60d", auto_adjust=True, progress=False)
        if len(df) < 20:
            return {"score": 50, "classificacao": "Neutro", "componentes": {}}

        retornos = df["Close"].pct_change().dropna()
        vol_21   = float(retornos.rolling(21).std().iloc[-1]) * np.sqrt(252) * 100
        mom_20   = float(df["Close"].pct_change(20).iloc[-1]) * 100
        vol_ratio = float(df["Volume"].iloc[-5:].mean() / df["Volume"].iloc[-20:].mean())

        # Score 0–100 (50 = neutro)
        score = 50
        if mom_20 > 5:   score += 20
        elif mom_20 > 2: score += 10
        elif mom_20 < -5: score -= 20
        elif mom_20 < -2: score -= 10

        if vol_21 < 15:  score += 10   # baixa vol = ganância
        elif vol_21 > 30: score -= 15  # alta vol = medo

        if vol_ratio > 1.3: score += 5  # volume alto = confiança

        score = max(0, min(100, score))

        if score >= 75:    classificacao = "Ganância Extrema"
        elif score >= 55:  classificacao = "Ganância"
        elif score >= 45:  classificacao = "Neutro"
        elif score >= 25:  classificacao = "Medo"
        else:              classificacao = "Medo Extremo"

        return {
            "score": round(score),
            "classificacao": classificacao,
            "componentes": {
                "momentum_20d": round(mom_20, 1),
                "volatilidade_21d": round(vol_21, 1),
                "volume_ratio": round(vol_ratio, 2),
            }
        }

    except Exception as e:
        logger.error(f"Fear & Greed error: {e}")
        return {"score": 50, "classificacao": "Neutro", "componentes": {}}
