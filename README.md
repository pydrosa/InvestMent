# QuantBot — Plataforma de Trading Algorítmico

Plataforma completa de investimento automático com:
- **Dados reais** via Yahoo Finance (PETR4, VALE3, ITUB4, etc.)
- **Modelo de IA** (LightGBM + regras técnicas como fallback)
- **Sentimento de mercado** via RSS feeds de notícias
- **Paper trading real** via Alpaca Markets (gratuito)
- **Backtest** com dados históricos reais

---

## 📋 Pré-requisitos

- **Python 3.10+** → https://python.org
- **Node.js 18+** → https://nodejs.org

Verifique com:
```bash
python --version   # deve ser 3.10+
node --version     # deve ser 18+
```

---

## 🚀 Como rodar (passo a passo)

### 1. Baixe o projeto

Se recebeu como .zip, extraia. Se clonou do git, entre na pasta:
```bash
git clone https://github.com/pydrosa/InvestMent.git
cd InvestMent
```

### 2. Configure o Backend Python

```bash
# Entre na pasta do backend
cd backend

# Crie um ambiente virtual (boa prática)
python -m venv venv

# Ative o ambiente virtual:
# No Mac/Linux:
source venv/bin/activate
# No Windows:
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Opcional mas recomendado — instale o LightGBM para IA mais avançada:
pip install lightgbm
```

### 3. Configure as variáveis de ambiente

```bash
# Ainda na pasta backend/:
cp .env.example .env
```

Abra o arquivo `.env` num editor de texto e preencha (se quiser usar Alpaca):
```
ALPACA_API_KEY=sua_chave_aqui
ALPACA_SECRET_KEY=seu_secret_aqui
```

> **Para começar sem Alpaca:** deixe como está — o app funciona em modo paper trading local.

### 4. Inicie o Backend

```bash
# Ainda na pasta backend/, com o venv ativado:
uvicorn main:app --reload --port 8000
```

Você verá:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

✅ **Deixe esse terminal aberto.**

Teste abrindo no navegador: http://localhost:8000
Deve aparecer: `{"status":"online","version":"1.0.0",...}`

Documentação automática da API: http://localhost:8000/docs

### 5. Configure e inicie o Frontend

Abra **um novo terminal** (mantenha o backend rodando):

```bash
# Da raiz do projeto, entre na pasta frontend:
cd frontend

# Instale as dependências Node:
npm install

# Inicie o servidor de desenvolvimento:
npm run dev
```

Você verá:
```
  VITE v5.x  ready in 500ms
  ➜  Local:   http://localhost:3000/
```

### 6. Acesse o app

Abra no navegador: **http://localhost:3000**

---

## 🎯 Como usar com R$100

### Passo 1 — Dashboard
- Veja o Fear & Greed Index
- Verifique o regime do Ibovespa (bull/bear/lateral)

### Passo 2 — Sinais de IA
- Clique em "Atualizar Sinais" (aguarde ~15 segundos — busca dados reais)
- Cada ativo recebe um score de 0 a 100%
- Score > 62% = sinal de compra
- Clique em um ativo para ver o stop loss, take profit e explicação da IA

### Passo 3 — Backtest
- Antes de operar, teste a estratégia
- Use período "1 ano" com PETR4 ou VALE3
- Verifique: Sharpe > 1.0 e Win Rate > 55%
- Se não passar, ajuste stop loss / take profit

### Passo 4 — Portfólio (paper trading local)
- Use a API diretamente para registrar entradas/saídas
- Ou use o swagger em http://localhost:8000/docs → /api/portfolio/entrar

### Passo 5 — Corretora (Alpaca — quando pronto)
- Crie conta em https://alpaca.markets (gratuito)
- Adicione as chaves no .env
- Opere ações americanas (SPY, QQQ, AAPL) com os mesmos sinais

---

## 📡 Endpoints úteis da API

| Endpoint | Descrição |
|----------|----------|
| GET /api/market/cotacao/PETR4 | Cotação + indicadores em tempo real |
| GET /api/market/multiplos?mercado=BR | Todos os ativos BR |
| GET /api/signals/calcular?capital=100 | Sinais de IA para todos os ativos |
| POST /api/backtest/rodar | Backtest com dados reais |
| GET /api/sentiment/noticias | Sentimento do mercado |
| GET /api/sentiment/fear-greed | Índice Fear & Greed |
| GET /api/broker/status | Status da Alpaca |
| GET /api/portfolio/ | Portfólio local |

---

## 🤖 Ativar o LightGBM (IA avançada)

Para treinar o modelo com dados históricos reais:

1. Instale: `pip install lightgbm`
2. Acesse: http://localhost:8000/docs
3. Vá em `/api/signals/treinar/{ticker}`
4. Execute com ticker = "PETR4" e mercado = "BR"
5. O modelo é salvo em `models/lgbm_model.pkl` e usado automaticamente

---

## 🏦 Conectar a corretora Alpaca (paper trading real)

1. Acesse https://alpaca.markets → "Sign Up" (gratuito)
2. No painel: "Paper Trading" → "API Keys" → "Generate New Key"
3. Copie `API Key ID` e `Secret Key`
4. Cole no arquivo `.env`:
   ```
   ALPACA_API_KEY=PKxxxxxxxxxxxxxxxx
   ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. Reinicie o backend: Ctrl+C e `uvicorn main:app --reload`
6. Na aba "Corretora" do app, você verá saldo e poderá operar

> ⚠️ **NUNCA mude para `api.alpaca.markets`** (live) sem validar o sistema com paper trading por pelo menos 2-3 meses.

---

## 📈 Estratégia recomendada para R$100

```
Estratégia:   Momentum + IA Leve
Stop Loss:    3%
Take Profit:  6%
Risco/Op:     5% do capital = R$5 por trade
Ativos:       PETR4, VALE3, WEGE3 (maior liquidez)
Frequência:   Swing trade (2-5 dias por operação)
Meta mensal:  3-6% (R$3-R$6/mês)
```

**Progresso esperado:**
- Mês 1-2: paper trading, ajuste de parâmetros
- Mês 3: R$100 real se Sharpe > 1.0 e win rate > 55%
- Mês 6+: aportar mais capital conforme consistência

---

## 🛠️ Solução de problemas

**Backend não inicia:**
```bash
# Verifique se o venv está ativo (deve aparecer "(venv)" no terminal)
# Se não: source venv/bin/activate (Mac/Linux) ou venv\Scripts\activate (Windows)
```

**Erro "yfinance":**
```bash
pip install --upgrade yfinance
```

**Frontend não conecta ao backend:**
- Verifique se o backend está rodando na porta 8000
- No arquivo `frontend/vite.config.js` o proxy já aponta para localhost:8000

**Dados do Yahoo Finance lentos:**
- Normal! A primeira busca de múltiplos ativos leva 15-30 segundos
- Os dados são reais — vale a espera

---

## 📁 Estrutura do projeto

```
InvestMent/
├── backend/
│   ├── main.py              # FastAPI app principal
│   ├── requirements.txt     # Dependências Python
│   ├── .env.example         # Modelo de configuração
│   ├── data/
│   │   └── portfolio.json   # Portfolio local (gerado automaticamente)
│   ├── models/
│   │   └── lgbm_model.pkl   # Modelo IA treinado (gerado via API)
│   └── routers/
│       ├── market.py        # Dados Yahoo Finance + indicadores
│       ├── signals.py       # Sinais de IA (LightGBM + regras)
│       ├── sentiment.py     # Sentimento via RSS + Fear & Greed
│       ├── backtest.py      # Backtest com dados reais
│       ├── portfolio.py     # Gestão de portfólio local
│       └── broker.py        # Integração Alpaca
└── frontend/
    ├── src/
    │   ├── App.jsx          # Interface React completa
    │   └── main.jsx         # Entrada da aplicação
    ├── package.json
    └── vite.config.js
```

---

## 🌐 Deploy na Nuvem

Ver arquivo `DEPLOY.md` para instruções completas de deploy.

---

## 📄 Licença

MIT — Livre para usar e modificar.

**Aviso Legal:** Este é um sistema educacional de paper trading. Não realize operações com dinheiro real sem validar completamente o sistema e entender os riscos envolvidos.
