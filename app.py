from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="OIL SYNT", layout="wide")
st.title("🛢️ OIL SYNT - Analisi WTI")

if "df_raw" not in st.session_state:
    st.session_state.df_raw = None

@st.cache_data(ttl=3600, show_spinner=False)
def load_wti_data(start_date, end_date):
    ticker = "CL=F"  # WTI Crude Oil
    df = yf.download(ticker, start=start_date, end=end_date, interval="1d")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

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

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    calc_btn_1 = st.button("Calcola Dati e Grafico SYNT1")
with col_btn2:
    if st.button("Svuota cache"):
        st.cache_data.clear()
        st.success("Cache svuotata.")

if calc_btn_1:
    if start_date >= end_date:
        st.error("La data di inizio deve essere precedente alla data di fine.")
    else:
        with st.spinner("Download dati da Yahoo Finance (con cache)..."):
            df_downloaded = load_wti_data(start_date, end_date)

        if df_downloaded.empty:
            st.error("Nessun dato trovato per il periodo selezionato.")
            st.session_state.df_raw = None
        else:
            st.session_state.df_raw = df_downloaded
            df_view = df_downloaded.copy()

            if data_freq != "Giornaliero":
                agg_dict = {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
                df_view = (
                    df_downloaded.resample(resample_map[data_freq])
                    .agg(agg_dict)
                    .dropna()
                )

            min_price = df_view["Close"].min()
            max_price = df_view["Close"].max()
            avg_price = df_view["Close"].mean()

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

st.divider()
st.header("Sezione SYNT2: Analisi Movimenti Progressivi")

if st.session_state.df_raw is not None:
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
        n_sedute = st.selectbox(
            "Numero Sedute", options=[3, 5, 7, 10], index=1, key="nsedute"
        )

    with col_c:
        st.subheader("Azione")
        calc_btn_2 = st.button("Esegui Analisi SYNT2", key="calc2")

    df_analysis = st.session_state.df_raw

    if calc_btn_2:
        results = []
        total_intervals = 0
        data_len = len(df_analysis)

        if data_len < n_sedute + 1:
            st.warning(
                "Il periodo selezionato è troppo corto per il numero di sedute richiesto."
            )
        else:
            current_idx = 0
            movm_values = {
                "MOVM1": movm1,
                "MOVM2": movm2,
                "MOVM3": movm3,
                "MOVM4": movm4,
            }

            while current_idx + n_sedute < data_len:
                total_intervals += 1
                next_idx = current_idx + n_sedute

                row_curr = df_analysis.iloc[current_idx]
                row_next = df_analysis.iloc[next_idx]

                price_curr_close = row_curr["Close"]
                price_next_close = row_next["Close"]

                if price_next_close >= price_curr_close:
                    direction = "Salito"
                    price_effective = row_next["High"]
                else:
                    direction = "Sceso"
                    price_effective = row_next["Low"]

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
            st.write(
                f"**Totale Rilevazioni Utili Eseguite (Intervalli):** {total_intervals}"
            )

            if results:
                df_results = pd.DataFrame(results)

                stats_list = []
                thresholds_map = {
                    "MOVM1": movm1,
                    "MOVM2": movm2,
                    "MOVM3": movm3,
                    "MOVM4": movm4,
                }

                for name in ["MOVM1", "MOVM2", "MOVM3", "MOVM4"]:
                    threshold_val = thresholds_map[name]
                    if threshold_val <= 0:
                        continue

                    subset = df_results[df_results["MOVM Rilevato"] == name]
                    count = len(subset)
                    percentage = (count / total_intervals) * 100 if total_intervals > 0 else 0

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
                    st.dataframe(
                        df_results.sort_values(by="Giorno", ascending=False),
                        use_container_width=True,
                    )
            else:
                st.info(
                    "Nessun movimento rilevato ha superato le soglie MOVM inserite nel periodo selezionato."
                )
else:
    st.info(
        "Premi 'Calcola Dati e Grafico SYNT1' per caricare i dati necessari a questa sezione."
    )
