import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import numpy as np

# ======================
# STREAMLIT CONFIG
# ======================
st.set_page_config(page_title="OIL SYNT", layout="wide")
st.title("🛢️ OIL SYNT - Dashboard Analisi WTI")

# ======================
# SESSION STATE
# ======================
if "df_raw" not in st.session_state:
    st.session_state.df_raw = None

# ======================
# CACHING (cloud-friendly)
# ======================
@st.cache_data(ttl=60 * 30, show_spinner=False)  # 30 min
def load_yf_data(ticker: str, start: date, end: date) -> pd.DataFrame:
    # yfinance scarica end come esclusivo: va bene così, ma teniamolo esplicito
    df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=False, progress=False)

    if df is None or df.empty:
        return pd.DataFrame()

    # Gestione MultiIndex eventuale
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Assicuriamoci che l'indice sia DatetimeIndex e ordinato
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Manteniamo solo colonne attese (se presenti)
    expected = ["Open", "High", "Low", "Close", "Volume"]
    cols = [c for c in expected if c in df.columns]
    return df[cols].dropna(how="all")

def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    # df deve avere DatetimeIndex
    agg_dict = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    # Alcuni ticker possono non avere Volume: gestiamolo
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}

    out = df.resample(rule).agg(agg_dict).dropna()
    return out

# ---------------------------------------------------------
# SEZIONE SYNT1
# ---------------------------------------------------------
st.header("Sezione SYNT1: Rilevazione Dati di Mercato")
st.subheader("Impostazioni Parametri")

col1, col2, col3 = st.columns(3)
with col1:
    start_date = st.date_input("Data di Inizio", datetime(2025, 8, 1))
with col2:
    end_date = st.date_input("Data di Fine", datetime(2026, 2, 26))
with col3:
    data_freq = st.selectbox("Tipologia Dati", ("Giornaliero", "Settimanale", "Mensile"))

resample_map = {"Giornaliero": None, "Settimanale": "W", "Mensile": "M"}

calc_btn_1 = st.button("Calcola Dati e Grafico SYNT1")

if calc_btn_1:
    if start_date >= end_date:
        st.error("La data di inizio deve essere precedente alla data di fine.")
    else:
        with st.spinner("Download dati da Yahoo Finance..."):
            ticker = "CL=F"
            df_downloaded = load_yf_data(ticker, start_date, end_date)

        if df_downloaded.empty:
            st.error("Nessun dato trovato per il periodo selezionato.")
            st.session_state.df_raw = None
        else:
            st.session_state.df_raw = df_downloaded

            df_view = df_downloaded.copy()
            if data_freq != "Giornaliero":
                rule = resample_map[data_freq]
                df_view = resample_ohlcv(df_view, rule)

            # Statistiche
            if "Close" not in df_view.columns or df_view["Close"].dropna().empty:
                st.error("Colonna 'Close' non disponibile o vuota.")
            else:
                min_price = float(df_view["Close"].min())
                max_price = float(df_view["Close"].max())
                avg_price = float(df_view["Close"].mean())

                st.subheader("Statistiche Rilevazione")
                m1, m2, m3 = st.columns(3)
                m1.metric("Prezzo Minimo", f"{min_price:.2f} $")
                m2.metric("Prezzo Medio", f"{avg_price:.2f} $")
                m3.metric("Prezzo Massimo", f"{max_price:.2f} $")

                st.subheader("Andamento WTI")
                fig = px.line(
                    df_view,
                    x=df_view.index,
                    y="Close",
                    title=f"Andamento WTI ({data_freq})",
                    labels={"Close": "Prezzo ($)", "index": "Data"},
                )
                st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# SEZIONE SYNT2
# ---------------------------------------------------------
st.divider()
st.header("Sezione SYNT2: Analisi Movimenti Progressivi")

if st.session_state.df_raw is not None and not st.session_state.df_raw.empty:
    st.info("Utilizzando il periodo di rilevazione dati della Sezione SYNT1.")

    col_a, col_b, col_c = st.columns([3, 1, 1])

    with col_a:
        st.subheader("Inserimento Valori di Movimento (MOVM)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            movm1 = st.number_input("MOVM1", value=3.00, step=0.01, key="m1")
        with col_m2:
            movm2 = st.number_input("MOVM2", value=4.00, step=0.01, key="m2")
        with col_m3:
            movm3 = st.number_input("MOVM3", value=5.00, step=0.01, key="m3")
        with col_m4:
            movm4 = st.number_input("MOVM4", value=6.00, step=0.01, key="m4")

    with col_b:
        st.subheader("Sedute")
        n_sedute = st.selectbox("Numero Sedute", options=[3, 5, 7, 10], index=1, key="nsedute")

    with col_c:
        st.subheader("Azione")
        calc_btn_2 = st.button("Esegui Analisi SYNT2", key="calc2")

    df_analysis = st.session_state.df_raw.copy()

    if calc_btn_2:
        required_cols = {"Open", "High", "Low", "Close"}
        if not required_cols.issubset(set(df_analysis.columns)):
            st.error(f"Mancano colonne necessarie: {sorted(list(required_cols - set(df_analysis.columns)))}")
        else:
            results = []
            total_intervals = 0

            data_len = len(df_analysis)
            if data_len < n_sedute + 1:
                st.warning("Il periodo selezionato è troppo corto per il numero di sedute richiesto.")
            else:
                current_idx = 0
                movm_values = {"MOVM1": movm1, "MOVM2": movm2, "MOVM3": movm3, "MOVM4": movm4}

                while current_idx + n_sedute < data_len:
                    total_intervals += 1
                    next_idx = current_idx + n_sedute

                    row_curr = df_analysis.iloc[current_idx]
                    row_next = df_analysis.iloc[next_idx]

                    price_curr_close = float(row_curr["Close"])
                    price_next_close = float(row_next["Close"])

                    if price_next_close >= price_curr_close:
                        direction = "Salito"
                        price_effective = float(row_next["High"])
                    else:
                        direction = "Sceso"
                        price_effective = float(row_next["Low"])

                    movement = abs(price_effective - price_curr_close)

                    date_val = df_analysis.index[next_idx].date()
                    month_val = df_analysis.index[next_idx].strftime("%B")

                    for name, threshold in movm_values.items():
                        if threshold > 0 and movement >= threshold:
                            results.append(
                                {
                                    "Mese": month_val,
                                    "Giorno": date_val,
                                    "Direzione": direction,
                                    "Rilevazione Precedente": price_curr_close,
                                    "MOVM Rilevato": name,
                                    "Soglia MOVM": threshold,
                                    "Valore Effettivo": price_effective,
                                }
                            )

                    current_idx = next_idx

                st.subheader("Risultati Analisi SYNT2")
                st.write(f"**Totale Rilevazioni Utili Eseguite (Intervalli):** {total_intervals}")

                if results:
                    df_results = pd.DataFrame(results)

                    stats_list = []
                    for name in ["MOVM1", "MOVM2", "MOVM3", "MOVM4"]:
                        subset = df_results[df_results["MOVM Rilevato"] == name]
                        count = len(subset)
                        percentage = (count / total_intervals) * 100 if total_intervals > 0 else 0

                        threshold_val = {"MOVM1": movm1, "MOVM2": movm2, "MOVM3": movm3, "MOVM4": movm4}[name]
                        if threshold_val > 0:
                            stats_list.append(
                                {
                                    "Parametro": name,
                                    "Soglia Input": threshold_val,
                                    "Volte Rilevato": count,
                                    "% Rilevazione": f"{percentage:.2f}%",
                                }
                            )

                    df_stats = pd.DataFrame(stats_list)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### Statistiche Rilevazioni")
                        st.dataframe(df_stats, use_container_width=True)
                    with c2:
                        st.markdown("### Dettaglio Singole Rilevazioni")
                        st.dataframe(df_results.sort_values(by="Giorno", ascending=False), use_container_width=True)
                else:
                    st.info("Nessun movimento rilevato ha superato le soglie MOVM inserite nel periodo selezionato.")
else:
    st.info("Premi 'Calcola Dati e Grafico SYNT1' per caricare i dati necessari a questa sezione.")

# ---------------------------------------------------------
# SEZIONE SYNT3
# ---------------------------------------------------------
st.divider()
st.header("Sezione SYNT3: Simulazione Monte Carlo")

if st.session_state.df_raw is not None and not st.session_state.df_raw.empty:
    st.info("Simulazione basata sullo storico SYNT1 e le soglie SYNT2.")

    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.subheader("Parametri Simulazione")
        m1_val = float(st.session_state.get("m1", 3.00))
        m2_val = float(st.session_state.get("m2", 4.00))
        m3_val = float(st.session_state.get("m3", 5.00))
        m4_val = float(st.session_state.get("m4", 6.00))

        st.write(f"**Soglie MOVM:** {m1_val}, {m2_val}, {m3_val}, {m4_val}")
        st.write(f"**Data Riferimento:** {end_date}")

    with col_d2:
        st.subheader("Avvio")
        calc_btn_3 = st.button("Esegui Simulazione SYNT3 (1000 iterazioni)", key="calc3")

    if calc_btn_3:
        with st.spinner("Esecuzione Simulazione Monte Carlo in corso..."):
            df_sim = st.session_state.df_raw.copy()

            required_cols = {"Open", "High", "Low", "Close"}
            if not required_cols.issubset(set(df_sim.columns)):
                st.error(f"Mancano colonne necessarie: {sorted(list(required_cols - set(df_sim.columns)))}")
            else:
                df_target = df_sim[df_sim.index <= pd.Timestamp(end_date)]
                if df_target.empty:
                    st.error("La data di fine selezionata è anteriore alla data di inizio dati.")
                else:
                    last_row = df_target.iloc[-1]
                    sim_start_date = last_row.name

                    if float(last_row["Close"]) >= float(last_row["Open"]):
                        start_price = float(last_row["High"])
                        candle_color = "Verde"
                    else:
                        start_price = float(last_row["Low"])
                        candle_color = "Rossa"

                    log_returns = np.log(df_sim["Close"] / df_sim["Close"].shift(1)).dropna()
                    mu = float(log_returns.mean())
                    sigma = float(log_returns.std())

                    num_simulations = 1000
                    max_horizon_days = 252
                    thresholds = [m1_val, m2_val, m3_val, m4_val]
                    threshold_names = ["MOVM1", "MOVM2", "MOVM3", "MOVM4"]

                    results_stats = {t: {"hits": 0, "days_sum": 0} for t in threshold_names}

                    for _ in range(num_simulations):
                        current_price = start_price
                        hit_status = [False] * 4

                        for day in range(1, max_horizon_days + 1):
                            shock = np.random.normal(mu, sigma)
                            current_price = current_price * np.exp(shock)

                            movement = abs(current_price - start_price)

                            for idx, thresh in enumerate(thresholds):
                                if (not hit_status[idx]) and movement >= thresh:
                                    hit_status[idx] = True
                                    results_stats[threshold_names[idx]]["hits"] += 1
                                    results_stats[threshold_names[idx]]["days_sum"] += day

                            if all(hit_status):
                                break

                    final_output = []
                    for idx, name in enumerate(threshold_names):
                        stats = results_stats[name]
                        hits = stats["hits"]
                        total_days = stats["days_sum"]

                        prob_percent = (hits / num_simulations) * 100
                        avg_days = (total_days / hits) if hits > 0 else 0

                        final_output.append(
                            {
                                "Soglia (MOVM)": name,
                                "Valore Soglia": thresholds[idx],
                                "Probabilità Raggiungimento (%)": f"{prob_percent:.2f}%",
                                "Sedute Medie (se raggiunto)": f"{avg_days:.1f}",
                            }
                        )

                    df_synt3_results = pd.DataFrame(final_output)

                    st.subheader("Risultati Simulazione Monte Carlo")

                    col_r1, col_r2 = st.columns([2, 1])
                    with col_r1:
                        st.markdown("**Dettaglio Simulazione**")
                        st.markdown(
                            f"- **Prezzo di Partenza:** {start_price:.2f} $ "
                            f"(Candela {candle_color} del {sim_start_date.date()})"
                        )
                        st.markdown(f"- **Numero Simulazioni:** {num_simulations}")
                        st.markdown(f"- **Orizzonte Temporale Massimo:** {max_horizon_days} sedute")
                        st.dataframe(df_synt3_results, use_container_width=True)

                    with col_r2:
                        df_plot = df_synt3_results.copy()
                        df_plot["Probabilità Numerica"] = (
                            df_plot["Probabilità Raggiungimento (%)"].str.replace("%", "", regex=False).astype(float)
                        )

                        fig_p = px.bar(
                            df_plot,
                            x="Soglia (MOVM)",
                            y="Probabilità Numerica",
                            title="Probabilità di Raggiungimento",
                            text_auto=True,
                            labels={"Probabilità Numerica": "Probabilità (%)"},
                        )
                        st.plotly_chart(fig_p, use_container_width=True)
else:
    st.info("Dati non disponibili. Esegui prima il calcolo nella Sezione SYNT1.")
