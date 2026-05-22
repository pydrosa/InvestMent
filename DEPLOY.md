# Deploy na Nuvem — QuantBot

Guia completo para fazer deploy do QuantBot em serviços de nuvem gratuitos.

---

## 🚀 Opção 1: Backend no Render.com (Recomendado)

### Pré-requisitos
- Conta GitHub com repositório `pydrosa/InvestMent`
- Conta no [Render.com](https://render.com) (gratuito)

### Passo 1: Conectar GitHub ao Render

1. Acesse https://dashboard.render.com
2. Clique em "New +" → "Web Service"
3. Selecione "Connect a repository"
4. Procure por `InvestMent` e clique em "Connect"

### Passo 2: Configurar o Serviço

```
Name:              quantbot-backend
Environment:       Python 3
Region:            Ohio (US-EAST) ou Singapore (mais rápido para BR)
Branch:            main
Build Command:     pip install -r backend/requirements.txt
Start Command:     cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Passo 3: Adicionar Variáveis de Ambiente

Na aba "Environment", adicione:
```
ALPACA_API_KEY=sua_chave_aqui
ALPACA_SECRET_KEY=seu_secret_aqui
BACKEND_PORT=10000
```

### Passo 4: Deploy

Clique em "Deploy Service". Aguarde ~5 minutos.

Sua URL será: `https://quantbot-backend.onrender.com`

**Salve esta URL!** Você usará no frontend.

---

## 🎨 Opção 2: Frontend no Vercel (Grátis + Rápido)

### Pré-requisitos
- Conta no [Vercel](https://vercel.com) (gratuito)
- Conectar com GitHub

### Passo 1: Importar Repositório

1. Acesse https://vercel.com/new
2. Clique em "Import Git Repository"
3. Cole: `https://github.com/pydrosa/InvestMent`
4. Clique em "Import"

### Passo 2: Configurar Build

```
Framework:         Vite
Root Directory:    frontend
Build Command:     npm run build
Output Directory:  dist
```

### Passo 3: Adicionar Variáveis de Ambiente

Em "Environment Variables", adicione:
```
VITE_API_URL=https://quantbot-backend.onrender.com/api
```

### Passo 4: Deploy

Clique em "Deploy". Aguarde ~2 minutos.

Sua URL será: `https://investmentbot.vercel.app` (ou similar)

---

## 🔗 Conectar Frontend ao Backend

Depois que ambos estiverem deployed:

1. No **Vercel**, vá em "Settings" → "Environment Variables"
2. Mude `VITE_API_URL` para a URL do seu backend Render:
   ```
   VITE_API_URL=https://quantbot-backend.onrender.com/api
   ```
3. Clique em "Save" e o Vercel fará redeploy automático

---

## 📊 Monitorar Logs

### Backend (Render)
1. Dashboard → Select your service
2. Aba "Logs" mostra erros em tempo real

### Frontend (Vercel)
1. Dashboard → Select your project
2. Aba "Deployments" → "Logs"

---

## 🆓 Plano Gratuito - Limitações

| Serviço | Limite | Nota |
|---------|--------|------|
| **Render** | 750 h/mês | Suficiente para sempre ligado |
| **Vercel** | Unlimited | Sem limite de requisições |
| **Yahoo Finance** | ~2000 req/dia | Suficiente para sinais em tempo real |

⚠️ **Atenção**: Depois de 15 min sem requisições, o Render entra em "sleep" (free tier). A primeira requisição após isso leva ~30 segundos.

**Solução**: Use um serviço de "keep-alive" como [UptimeRobot](https://uptimerobot.com) (gratuito):
- Monitore: `https://quantbot-backend.onrender.com/api/health`
- Intervalo: 5 minutos

---

## 🔐 Segurança

### Checklist
- [ ] Nunca commite `.env` com chaves reais no repositório
- [ ] Use "Secrets" do Render/Vercel para chaves sensíveis
- [ ] Para Alpaca LIVE: use URL `https://api.alpaca.markets` (não `paper-api`)
- [ ] CORS está configurado para `localhost:3000` e `vercel.app` no `main.py`

---

## 📱 Usar em Produção

### Quando estiver pronto para operar com dinheiro real:

1. **Teste 2-3 meses com paper trading** (Alpaca gratuito)
2. **Valide Sharpe > 1.5 e Win Rate > 55%**
3. **Apenas aí mude para live**:
   - Em `.env` do Render: `ALPACA_BASE_URL=https://api.alpaca.markets`
   - Gere novas chaves em https://alpaca.markets/live-trading

⚠️ **Risco real**: A partir deste ponto, erros podem custar dinheiro. Backup seus dados antes.

---

## 🆘 Troubleshooting

**"Backend offline" no app**
→ Verifique se Render está rodando em Dashboard → Logs
→ Atualize `VITE_API_URL` no Vercel

**"Erro 429 Too Many Requests"**
→ Limite do Yahoo Finance atingido
→ Aguarde 1 hora ou use dados em cache

**"ModuleNotFoundError: No module named 'lightgbm'"**
→ Render não instalou LightGBM (arquivo grande)
→ Sistema continua em modo "Regras" - é ok para começar

---

## 📞 Suporte

- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **Alpaca API**: https://alpaca.markets/docs
- **Yahoo Finance**: https://finance.yahoo.com

---

**Parabéns!** Seu QuantBot está na nuvem e pronto para operar. 🚀
