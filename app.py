import pandas as pd
import streamlit as st
from mplsoccer import Pitch, VerticalPitch
from statsbombpy import sb

from src.loader import (
    build_tab,
    build_team,
    filter_competitions,
    info_competition,
    info_match,
    load_competition,
    load_data,
    make_match,
)

st.set_page_config(
    page_title="AT - Desenvolvimento Front-End com Python (com Streamlit) [26E3_1]",
    page_icon="📚",
    layout="wide",
)


@st.cache_data(ttl=3600, show_spinner=False)
def get_competitions():
    df = load_data()
    return df


with st.spinner("Coletando dados de competições…"):
    df = get_competitions()

with st.sidebar:

    if "selected_gender" not in st.session_state:
        gender = None
    else:
        gender = st.session_state.selected_gender

    if "selected_type" not in st.session_state:
        international = None
    else:
        international = st.session_state.selected_type

    if "selected_competition" not in st.session_state:
        st.session_state.selected_competition = None

    if "selected_season" not in st.session_state:
        st.session_state.selected_season = None

    df_filtrado = filter_competitions(df, gender, international)

    options_competition = sorted(df_filtrado["competition_name"].unique())

    if st.session_state.selected_competition is not None:
        if st.session_state.selected_competition not in options_competition:
            st.session_state.selected_competition = None
            st.session_state.selected_season = None

    selected_competition = st.selectbox(
        "🏆 Selecione a competição: ",
        options_competition,
        index=None,
        key="selected_competition",
    )

    if selected_competition is not None:

        filtro = (
            df_filtrado["competition_name"] == st.session_state.selected_competition
        )
        options_season = sorted(
            df_filtrado[filtro]["season_name"].unique(), reverse=True
        )

        if st.session_state.selected_season is not None:
            if st.session_state.selected_season not in options_season:
                st.session_state.selected_season = None

        selected_season = st.selectbox(
            "📆 Selecione a temporada: ",
            options_season,
            index=None,
            key="selected_season",
        )

    selected_type = st.radio(
        "Selecione o tipo: ",
        ["🌎🛡️ Todos", "🌎 Seleções", "🛡️ Clubes"],
        key="selected_type",
    )

    selected_gender = st.radio(
        "Selecione o gênero: ",
        ["👨👩 Todos", "👨 Masculino", "👩 Feminino"],
        key="selected_gender",
    )


if (
    st.session_state.selected_competition is not None
    and st.session_state.selected_season is not None
):

    filtro = (df_filtrado["competition_name"] == selected_competition) & (
        df_filtrado["season_name"] == st.session_state.selected_season
    )

    id_comp = df_filtrado.loc[filtro, "competition_id"].iloc[0]
    id_season = df_filtrado.loc[filtro, "season_id"].iloc[0]

    df_matches = load_competition(id_comp, id_season)

    st.title(f"🏆 {selected_competition}")
    st.caption(f"Dados referentes à temporada `{selected_season}`.")

    # metricas
    n_partidas, n_gols, n_times = info_competition(df_matches)
    m1, m2, m3 = st.columns(3)

    if "select_competition_stage" in st.session_state:
        if st.session_state.select_competition_stage is not None:
            df_matches_filtered = df_matches[
                df_matches["competition_stage"].isin(
                    st.session_state.select_competition_stage
                )
            ]
        else:
            df_matches_filtered = df_matches

    else:
        df_matches_filtered = df_matches

    option_matches = make_match(df_matches_filtered)

    selected_match = st.selectbox(
        "Selecione uma partida: ",
        option_matches["option"].to_list(),
        index=None,
        key="selected_match",
    )

    if selected_match is None:

        m1.metric("Times", n_times)
        m2.metric("Partidas", n_partidas)
        m3.metric("Gols", n_gols)

        if "competition_stage" in df_matches.columns:

            comp_stages = df_matches["competition_stage"].unique()
            select_competition_stage = st.multiselect(
                "Fase da competição",
                options=comp_stages,
                default=comp_stages,
                key="select_competition_stage",
                label_visibility="collapsed",
            )

            if select_competition_stage == []:
                c1, c2, c3 = st.columns(3)
                c2.subheader("Sem dados para exibir")
            else:
                st.dataframe(df_matches_filtered, width="stretch", hide_index=True)
        else:
            st.dataframe(df_matches_filtered, width="stretch", hide_index=True)
    else:

        id_match = option_matches.loc[option_matches["option"] == selected_match][
            "match_id"
        ]
        # m1.metric("Times", n_times)
        # m2.metric("Partidas", n_partidas)
        # m3.metric("Gols", n_gols)
        if not id_match.empty:
            id_match = id_match.item()
            with st.spinner("Carregando partida..."):
                (
                    tatica_t1,
                    tatica_t2,
                    gols,
                    chutes,
                    passes,
                    escanteios,
                    titulares_time1,
                    titulares_time2,
                    reservas_time1,
                    reservas_time2,
                ) = info_match(id_match)

            # titulo do jogo
            gols_time1 = (
                titulares_time1["n_gols"].sum() + reservas_time1["n_gols"].sum()
            )
            gols_time2 = (
                titulares_time2["n_gols"].sum() + reservas_time2["n_gols"].sum()
            )
            time1_nome = titulares_time1["team"].loc[0]
            time2_nome = titulares_time2["team"].loc[0]

            st.subheader(f"{time1_nome} {gols_time1} vs " f"{gols_time2} {time2_nome}")

            # metricas
            c_null, c_chutes, c_passes, c_escanteios, c_null2 = st.columns(5)

            # tabs
            tab1, tab2 = st.tabs([time1_nome, time2_nome])

            # tab time1
            build_tab(
                tab1,
                time1_nome,
                titulares_time1,
                reservas_time1,
                tatica_t1,
                gols,
                chutes,
                passes,
                escanteios,
            )

            # tab time2
            build_tab(
                tab2,
                time2_nome,
                titulares_time2,
                reservas_time2,
                tatica_t2,
                gols,
                chutes,
                passes,
                escanteios,
            )


else:
    st.title("AT - Sport Analytics ⚽📊📈")
    st.info("Selecione uma competição no menu da esquerda para começar.")
