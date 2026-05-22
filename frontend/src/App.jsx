import { useState, useEffect, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

const API = "http://localhost:8000/api";

const TABS = ["Dashboard", "Sinais", "Backtest", "Portfólio", "Sentimento", "Corretora"];

function Badge({ text, type }) {
  const colors = {
    COMPRAR: "bg-emerald-100 text-emerald-800",
    VENDER:  "bg-red-100 text-red-800",
    AGUARDAR:"bg-gray-100 text-gray-700",
    positivo:"bg-emerald-100 text-emerald-800",
    negativo:"bg-red-100 text-red-800",
    neutro:  "bg-gray-100 text-gray-700",
    bull:    "bg-emerald-100 text-emerald-800",
    bear:    "bg-red-100 text-red-800",
    lateral: "bg-amber-100 text-amber-800",
    crise:   "bg-red-200 text-red-900",
  };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${colors[text] || "bg-gray-100 text-gray-600"}`}>
      {text}
    </span>
  );
}

function Metric({ label, value, sub, subColor }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      {sub && <p className={`text-xs mt-1 ${subColor || "text-gray-400"}`}>{sub}</p>}
    </div>
  );
}

function useFetch(url, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch_ = useCallback(async () => {
    if (!url) return;
    setLoading(true);
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => { fetch_(); }, deps);
  return { data, loading, error, refetch: fetch_ };
}

// ── Tab: Dashboard ────────────────────────────────────────────────
function DashTab() {
  const { data: ibov }  = useFetch(`${API}/market/ibovespa`, []);
  const { data: portf } = useFetch(`${API}/portfolio/`, []);
  const { data: fg }    = useFetch(`${API}/sentiment/fear-greed`, []);

  const equityData = ibov?.datas?.slice(-30).map((d, i) => ({
    data: d.slice(5),
    valor: ibov.closes[ibov.closes.length - 30 + i],
  })) || [];

  const pat = portf?.patrimonio_total || 100;
  const pnl = portf ? (pat - 100) / 100 * 100 : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Patrimônio" value={`R$ ${pat.toFixed(2)}`} sub={`${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}%`} subColor={pnl >= 0 ? "text-emerald-600" : "text-red-500"} />
        <Metric label="Em Caixa" value={`R$ ${portf?.capital_caixa?.toFixed(2) || "100.00"}`} />
        <Metric label="Posições" value={portf?.posicoes?.length || 0} sub="abertas" />
        <Metric label="Trades Totais" value={portf?.n_trades || 0} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-100 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Ibovespa — 30 dias</h3>
            {ibov && <Badge text={ibov.regime} />}
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={equityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="data" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
              <Tooltip formatter={(v) => v.toLocaleString("pt-BR")} />
              <Line type="monotone" dataKey="valor" stroke="#10b981" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-5">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Fear & Greed Index</h3>
          {fg && (
            <>
              <div className="flex items-center gap-4 mb-3">
                <div className="text-5xl font-bold" style={{ color: fg.score > 60 ? "#10b981" : fg.score < 40 ? "#ef4444" : "#f59e0b" }}>
                  {fg.score}
                </div>
                <div>
                  <p className="font-semibold text-gray-800">{fg.classificacao}</p>
                  <p className="text-xs text-gray-400">Índice de mercado</p>
                </div>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 mb-3">
                <div className="h-3 rounded-full transition-all" style={{ width: `${fg.score}%`, background: "linear-gradient(90deg, #ef4444, #f59e0b, #10b981)" }} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
                <div><span className="font-medium text-gray-700">{fg.componentes?.momentum_20d}%</span><br />Momentum 20d</div>
                <div><span className="font-medium text-gray-700">{fg.componentes?.volatilidade_21d}%</span><br />Volatilidade</div>
                <div><span className="font-medium text-gray-700">{fg.componentes?.volume_ratio}x</span><br />Volume ratio</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Tab: Sinais ───────────────────────────────────────────────────
function SinaisTab() {
  const [mercado, setMercado] = useState("BR");
  const [capital, setCapital] = useState(100);
  const { data, loading, error, refetch } = useFetch(`${API}/signals/calcular?mercado=${mercado}&capital=${capital}`, [mercado]);
  const [selecionado, setSelecionado] = useState(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <select className="border border-gray-200 rounded-lg px-3 py-2 text-sm" value={mercado} onChange={e => setMercado(e.target.value)}>
          <option value="BR">Brasil (B3)</option>
          <option value="US">EUA (Alpaca)</option>
        </select>
        <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-32" value={capital} onChange={e => setCapital(Number(e.target.value))} placeholder="Capital R$" />
        <button onClick={refetch} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          {loading ? "Calculando..." : "↺ Atualizar Sinais"}
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">Erro: {error}. Verifique se o backend está rodando.</div>}

      <div className="space-y-2">
        {(data?.sinais || []).map(s => (
          <div key={s.ticker} className="bg-white border border-gray-100 rounded-xl p-4 cursor-pointer hover:border-emerald-200 transition-colors" onClick={() => setSelecionado(selecionado?.ticker === s.ticker ? null : s)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-bold text-gray-900 w-14">{s.ticker}</span>
                <Badge text={s.direcao} />
                <span className="text-xs text-gray-400">{s.modelo}</span>
              </div>
              <div className="flex items-center gap-4 text-right">
                <div>
                  <p className="text-xs text-gray-400">Score IA</p>
                  <p className="font-semibold text-gray-900">{(s.score * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Preço</p>
                  <p className="font-semibold">R$ {s.preco}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">RSI</p>
                  <p className={`font-semibold ${s.rsi > 70 ? "text-red-500" : s.rsi < 30 ? "text-emerald-600" : "text-gray-700"}`}>{s.rsi}</p>
                </div>
                <div className="hidden md:block">
                  <p className="text-xs text-gray-400">Posição</p>
                  <p className="font-semibold text-emerald-700">R$ {s.posicao_reais}</p>
                </div>
              </div>
            </div>

            {selecionado?.ticker === s.ticker && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="grid grid-cols-3 gap-3 mb-3 text-sm">
                  <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-400">Stop Loss</p><p className="font-semibold text-red-500">R$ {s.stop_loss}</p></div>
                  <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-400">Take Profit</p><p className="font-semibold text-emerald-600">R$ {s.take_profit}</p></div>
                  <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-400">Risco/Op</p><p className="font-semibold">{s.risco_pct}%</p></div>
                </div>
                <div className="space-y-1">
                  {(s.razoes || []).map((r, i) => (
                    <p key={i} className="text-xs text-gray-600 flex items-start gap-1">
                      <span className="text-emerald-500 mt-0.5">•</span>{r}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Tab: Backtest ─────────────────────────────────────────────────
function BacktestTab() {
  const [form, setForm] = useState({ ticker: "PETR4", capital_inicial: 100, periodo: "1y", stop_loss_pct: 3, take_profit_pct: 6, risco_por_op: 5, mercado: "BR", estrategia: "momentum" });
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  async function rodar() {
    setLoading(true); setErro("");
    try {
      const r = await fetch(`${API}/backtest/rodar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await r.json();
      if (data.erro) setErro(data.erro);
      else setResultado(data);
    } catch (e) { setErro(e.message); }
    setLoading(false);
  }

  const eqData = resultado?.datas?.map((d, i) => ({ data: d.slice(5), capital: resultado.equity[i] })) || [];

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-100 rounded-2xl p-5">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Configurar Backtest</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Ticker</label>
            <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.ticker} onChange={e => setForm({ ...form, ticker: e.target.value.toUpperCase() })} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Mercado</label>
            <select className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.mercado} onChange={e => setForm({ ...form, mercado: e.target.value })}>
              <option value="BR">Brasil</option><option value="US">EUA</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Período</label>
            <select className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.periodo} onChange={e => setForm({ ...form, periodo: e.target.value })}>
              <option value="6mo">6 meses</option><option value="1y">1 ano</option><option value="2y">2 anos</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Estratégia</label>
            <select className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.estrategia} onChange={e => setForm({ ...form, estrategia: e.target.value })}>
              <option value="momentum">Momentum</option>
              <option value="mean_reversion">Mean Reversion</option>
              <option value="hibrida">Híbrida</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Capital (R$)</label>
            <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.capital_inicial} onChange={e => setForm({ ...form, capital_inicial: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Stop Loss %</label>
            <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.stop_loss_pct} onChange={e => setForm({ ...form, stop_loss_pct: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Take Profit %</label>
            <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.take_profit_pct} onChange={e => setForm({ ...form, take_profit_pct: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Risco/Op %</label>
            <input type="number" className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-full" value={form.risco_por_op} onChange={e => setForm({ ...form, risco_por_op: Number(e.target.value) })} />
          </div>
        </div>
        <button onClick={rodar} disabled={loading} className="mt-4 w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white py-2.5 rounded-xl text-sm font-semibold transition-colors">
          {loading ? "Rodando backtest com dados reais..." : "▶ Rodar Backtest"}
        </button>
        {erro && <p className="text-red-500 text-sm mt-2">{erro}</p>}
      </div>

      {resultado && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Retorno Total" value={`+${resultado.retorno_total}%`} subColor="text-emerald-600" />
            <Metric label="Sharpe Ratio" value={resultado.sharpe} sub={resultado.sharpe > 1.5 ? "✓ Excelente" : resultado.sharpe > 1 ? "Bom" : "Melhorar"} />
            <Metric label="Max Drawdown" value={`${resultado.max_drawdown}%`} subColor="text-red-500" />
            <Metric label="Win Rate" value={`${resultado.win_rate}%`} sub={`${resultado.wins}W / ${resultado.losses}L`} />
            <Metric label="Profit Factor" value={resultado.profit_factor} sub={resultado.profit_factor > 1.5 ? "✓ Positivo" : "Ajustar"} />
            <Metric label="Calmar Ratio" value={resultado.calmar} />
            <Metric label="Capital Final" value={`R$ ${resultado.capital_final}`} />
            <Metric label="Total Trades" value={resultado.total_trades} />
          </div>

          <div className="bg-white border border-gray-100 rounded-2xl p-5">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Curva de Capital — Dados Reais {resultado.ticker}</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={eqData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="data" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
                <Tooltip formatter={(v) => `R$ ${v.toFixed(2)}`} />
                <Line type="monotone" dataKey="capital" stroke="#3b82f6" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

// ── Tab: Portfólio ────────────────────────────────────────────────
function PortfolioTab() {
  const { data, refetch } = useFetch(`${API}/portfolio/`, []);
  const { data: hist }    = useFetch(`${API}/portfolio/historico`, []);
  const [resetando, setResetando] = useState(false);

  async function resetar() {
    if (!confirm("Zerar o portfolio e voltar para R$100?")) return;
    setResetando(true);
    await fetch(`${API}/portfolio/resetar?capital=100`, { method: "POST" });
    setResetando(false);
    refetch();
  }

  const resumo = hist?.resumo || {};

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Patrimônio" value={`R$ ${data?.patrimonio_total?.toFixed(2) || "100.00"}`} />
        <Metric label="Em Caixa" value={`R$ ${data?.capital_caixa?.toFixed(2) || "100.00"}`} />
        <Metric label="PnL Total" value={resumo.pnl_total != null ? `R$ ${resumo.pnl_total?.toFixed(2)}` : "—"} subColor={resumo.pnl_total >= 0 ? "text-emerald-600" : "text-red-500"} />
        <Metric label="Win Rate" value={resumo.win_rate != null ? `${resumo.win_rate}%` : "—"} />
      </div>

      <div className="bg-white border border-gray-100 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Posições Abertas</h3>
          <button onClick={resetar} disabled={resetando} className="text-xs text-red-400 hover:text-red-600 transition-colors">
            {resetando ? "Resetando..." : "Resetar Portfolio"}
          </button>
        </div>
        {!data?.posicoes?.length ? (
          <p className="text-gray-400 text-sm py-4 text-center">Nenhuma posição aberta. Use a aba Sinais para entrar em operações.</p>
        ) : (
          <div className="space-y-2">
            {data.posicoes.map(p => (
              <div key={p.ticker} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <span className="font-semibold w-16">{p.ticker}</span>
                <span className="text-sm text-gray-500">{p.qtd}x @ R${p.preco_entrada}</span>
                <span className="text-xs text-gray-400">SL: {p.stop_loss} · TP: {p.take_profit}</span>
                <span className={`text-xs font-medium ${p.score_ia > 0.6 ? "text-emerald-600" : "text-amber-600"}`}>IA: {(p.score_ia * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {hist?.historico?.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-2xl p-5">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Histórico de Trades</h3>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {[...hist.historico].reverse().map((t, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
                <span className="font-medium w-14">{t.ticker}</span>
                <span className="text-gray-400 text-xs">{t.data_saida?.slice(0, 10)}</span>
                <span className="text-gray-500 text-xs">{t.motivo}</span>
                <span className={`font-semibold ${t.pnl >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                  {t.pnl >= 0 ? "+" : ""}R$ {t.pnl}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab: Sentimento ───────────────────────────────────────────────
function SentimentoTab() {
  const { data, loading } = useFetch(`${API}/sentiment/noticias`, []);

  return (
    <div className="space-y-4">
      {data && (
        <div className="grid grid-cols-3 gap-3">
          <Metric label="Sentimento Geral" value={data.sentimento_geral} />
          <Metric label="Score Médio" value={data.score_medio?.toFixed(2)} sub={data.score_medio > 0 ? "Ligeiramente positivo" : "Ligeiramente negativo"} />
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-2">Distribuição</p>
            <div className="flex gap-3 text-sm">
              <span className="text-emerald-600 font-semibold">{data.positivas}↑</span>
              <span className="text-gray-400">{data.neutras}—</span>
              <span className="text-red-500 font-semibold">{data.negativas}↓</span>
            </div>
          </div>
        </div>
      )}

      {data?.aviso && <div className="bg-amber-50 text-amber-700 p-3 rounded-lg text-sm">{data.aviso}</div>}

      <div className="bg-white border border-gray-100 rounded-2xl p-5">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Notícias Analisadas</h3>
        {loading && <p className="text-gray-400 text-sm">Buscando feeds de notícias...</p>}
        <div className="space-y-2">
          {(data?.noticias || []).map((n, i) => (
            <div key={i} className="flex items-start justify-between gap-3 py-2 border-b border-gray-50 last:border-0">
              <div className="flex-1">
                <a href={n.link} target="_blank" rel="noreferrer" className="text-sm text-gray-800 hover:text-emerald-700 line-clamp-2">{n.titulo}</a>
                <p className="text-xs text-gray-400 mt-0.5">{n.fonte}</p>
              </div>
              <Badge text={n.sentimento} type={n.sentimento} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Tab: Corretora ────────────────────────────────────────────────
function CorretoraTab() {
  const { data: status } = useFetch(`${API}/broker/status`, []);
  const { data: posicoes, refetch: refetchPos } = useFetch(`${API}/broker/posicoes`, []);

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-100 rounded-2xl p-5">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Status Alpaca</h3>
        {status?.configurada ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <Metric label="Modo" value={status.modo?.toUpperCase()} />
            <Metric label="Saldo" value={`$ ${Number(status.cash).toFixed(2)}`} />
            <Metric label="Portfolio" value={`$ ${Number(status.portfolio_value).toFixed(2)}`} />
          </div>
        ) : (
          <div className="bg-amber-50 rounded-xl p-5">
            <p className="font-semibold text-amber-900 mb-2">Alpaca não configurada</p>
            <p className="text-sm text-amber-800 mb-3">{status?.instrucoes}</p>
            <ol className="text-sm text-amber-800 space-y-1 list-decimal list-inside">
              <li>Acesse <a href="https://alpaca.markets" target="_blank" className="underline font-medium">alpaca.markets</a> e crie conta gratuita</li>
              <li>Vá em "Paper Trading" → "API Keys"</li>
              <li>Copie as chaves para o arquivo <code className="bg-amber-100 px-1 rounded">.env</code></li>
              <li>Reinicie o backend</li>
            </ol>
            <p className="text-xs text-amber-700 mt-3">✓ Paper trading é 100% gratuito — sem risco de dinheiro real</p>
          </div>
        )}
      </div>

      {posicoes?.posicoes?.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-2xl p-5">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Posições Alpaca</h3>
          {posicoes.posicoes.map(p => (
            <div key={p.symbol} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0 text-sm">
              <span className="font-semibold">{p.symbol}</span>
              <span className="text-gray-500">{p.qty}x @ ${p.preco_entrada}</span>
              <span className={p.pnl >= 0 ? "text-emerald-600 font-semibold" : "text-red-500 font-semibold"}>
                {p.pnl >= 0 ? "+" : ""}${p.pnl.toFixed(2)} ({p.pnl_pct.toFixed(1)}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── App Principal ─────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState(0);
  const { data: health } = useFetch(`${API}/health`, []);

  const tabComponents = [DashTab, SinaisTab, BacktestTab, PortfolioTab, SentimentoTab, CorretoraTab];
  const TabComponent = tabComponents[tab];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-white">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <span className="font-semibold text-gray-900">QuantBot</span>
            <span className="text-xs text-gray-400 ml-1">v1.0</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full ${health ? "bg-emerald-400" : "bg-red-400"}`}></span>
            <span className="text-gray-500">{health ? "Backend online" : "Backend offline"}</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex bg-white border-b border-gray-100 px-4 overflow-x-auto">
          {TABS.map((t, i) => (
            <button key={t} onClick={() => setTab(i)} className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${tab === i ? "border-emerald-500 text-emerald-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}>
              {t}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-5">
          {!health && (
            <div className="bg-red-50 border border-red-100 rounded-xl p-4 mb-4 text-sm text-red-700">
              Backend não encontrado em localhost:8000. Execute: <code className="bg-red-100 px-1 rounded">cd backend && uvicorn main:app --reload</code>
            </div>
          )}
          <TabComponent />
        </div>
      </div>
    </div>
  );
}
