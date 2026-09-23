import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch, VerticalPitch
from statsbombpy import sb


def load_data():
    return sb.competitions()


def filter_competitions(df, gender=None, international=None):
    genero = {"👨 Masculino": "male", "👩 Feminino": "female"}
    tipo = {"🌎 Seleções": True, "🛡️ Clubes": False}

    if gender in genero:
        gender = genero[gender]
        df = df[df["competition_gender"] == gender]

    if international in tipo:
        international = tipo[international]
        df = df[df["competition_international"] == international]
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_competition(competition, season):
    with st.spinner("Carregando competição..."):
        return sb.matches(competition_id=competition, season_id=season)


def info_competition(df):
    n_partidas = df.shape[0]
    n_gols = df["home_score"].sum() + df["away_score"].sum()

    times_home = df["home_team"]
    times_away = df["away_team"]

    times = pd.concat([times_home, times_away]).unique()
    n_times = len(times)

    return n_partidas, n_gols, n_times


def make_match(df):
    with st.spinner("Carregando partidas..."):
        df_matches = pd.DataFrame(
            {
                "match_id": df["match_id"],
                "option": (
                    df["home_team"]
                    + " "
                    + df["home_score"].astype(str)
                    + " x "
                    + df["away_score"].astype(str)
                    + " "
                    + df["away_team"]
                ),
            }
        )

        if "competition_stage" in df.columns:
            df_matches["option"] += " - " + df["competition_stage"]
        df_matches = df_matches.sort_values("match_id")
        return df_matches


def create_table(df_matches, df_matches_filtered):
    if "competition_stage" in df_matches.columns:
        comp_stages = df_matches["competition_stage"].unique()
        select_competition_stage = st.multiselect(
            "",
            options=comp_stages,
            default=comp_stages,
            key="select_competition_stage",
        )

        if select_competition_stage == []:
            c1, c2, c3 = st.columns(3)
            c2.subheader("Sem dados para exibir")
        else:
            st.dataframe(df_matches_filtered, width="stretch", hide_index=True)
    else:
        st.dataframe(df_matches_filtered, width="stretch", hide_index=True)


@st.cache_data(ttl=3600, show_spinner=False)
def info_match(id):
    eventos = sb.events(match_id=id)
    lineups = sb.lineups(match_id=id)

    time1_nome = list(lineups.keys())[0]
    time1 = lineups[time1_nome]
    time1["team"] = time1_nome

    time2_nome = list(lineups.keys())[1]
    time2 = lineups[time2_nome]
    time2["team"] = time2_nome

    for time in [time1, time2]:
        time["player_nickname"] = time["player_nickname"].fillna(time["player_name"])
        time["saiu"] = pd.NA
        time["entrou"] = pd.NA
        time["cartao"] = pd.NA
        time["gols"] = pd.NA
        time["n_gols"] = 0

    for i in [time1, time2]:
        for indice, linha in i.iterrows():
            for position in linha["positions"]:
                if "Substitution - Off" in position["end_reason"]:
                    i.loc[indice, "saiu"] = "🔽"

                elif "Substitution - On" in position["start_reason"]:
                    i.loc[indice, "entrou"] = "🔼"

            for card in linha["cards"]:
                if card["card_type"] == "Yellow Card":
                    i.loc[indice, "cartao"] = "🟨"
                if (
                    card["card_type"] == "Second Yellow"
                    or card["card_type"] == "Red Card"
                ):
                    i.loc[indice, "cartao"] = "🟥"

    formacao1 = eventos.loc[
        (eventos["type"] == "Starting XI") & (eventos["team"] == time1_nome)
    ]["tactics"].item()
    formacao2 = eventos.loc[
        (eventos["type"] == "Starting XI") & (eventos["team"] == time2_nome)
    ]["tactics"].item()

    tatica_t1 = formacao1["formation"]
    tatica_t2 = formacao2["formation"]

    titulares1 = pd.DataFrame(formacao1["lineup"])
    titulares2 = pd.DataFrame(formacao2["lineup"])

    chutes = eventos[(eventos["type"] == "Shot") & (eventos["period"] <= 4)].copy()

    gols = eventos[
        (eventos["type"] == "Shot")
        & (eventos["shot_outcome"] == "Goal")
        & (eventos["period"] <= 4)
    ].copy()
    gols["player_id"] = gols["player_id"].astype("int")

    for i, linha in gols.iterrows():
        for time in [time1, time2]:
            if linha["player_id"] in list(time["player_id"]):
                indice = time[time["player_id"] == linha["player_id"]].index[0]
                time.loc[indice, "n_gols"] += 1
                if pd.isna(time.loc[indice, "gols"]):
                    time.loc[indice, "gols"] = "⚽"
                else:
                    time.loc[indice, "gols"] += "⚽"

    passes = eventos[
        (eventos["type"] == "Pass")
        & (eventos["period"] <= 4)
        & (eventos["pass_type"].isna())
    ].copy()

    escanteios = eventos[
        (eventos["pass_type"] == "Corner") & (eventos["period"] <= 4)
    ].copy()

    lineup1 = []
    lineup2 = []
    for time, lineup in [(titulares1, lineup1), (titulares2, lineup2)]:
        for indice, linha in time.iterrows():
            lineup.append(
                (
                    linha["player"]["id"],
                    linha["position"]["id"],
                    linha["position"]["name"],
                )
            )

    titulares_time1 = get_titulares(time1, lineup1)
    titulares_time2 = get_titulares(time2, lineup2)
    reservas_time1 = get_reservas(time1, lineup1)
    reservas_time2 = get_reservas(time2, lineup2)

    # titulares_time1 = build_team(titulares_time1)
    # titulares_time2 = build_team(titulares_time2)
    # reservas_time1 = build_team(reservas_time1)
    # reservas_time2 = build_team(reservas_time2)

    return (
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
    )


def get_titulares(time, lineup):
    display_titulares = []
    for i in lineup:
        linha = time[time["player_id"] == i[0]].iloc[0]
        display_titulares.append(
            [
                linha["team"],
                linha["player_id"],
                linha["jersey_number"],
                linha["player_nickname"],
                i[1],
                i[2],
                linha["saiu"],
                linha["entrou"],
                linha["cartao"],
                linha["gols"],
                linha["n_gols"],
            ]
        )

    display_titulares = pd.DataFrame(
        display_titulares,
        columns=[
            "team",
            "player_id",
            "numero",
            "nome",
            "id_posicao",
            "posicao",
            "saiu",
            "entrou",
            "cartao",
            "gols",
            "n_gols",
        ],
    )

    return display_titulares


def get_reservas(time, lineup):
    display_reservas = []
    for indice, linha in time.iterrows():
        if linha["player_id"] in [i[0] for i in lineup]:
            continue

        posicao = linha["positions"][0]["position"] if linha["positions"] else pd.NA

        display_reservas.append(
            [
                linha["team"],
                linha["player_id"],
                linha["jersey_number"],
                linha["player_nickname"],
                posicao,
                linha["saiu"],
                linha["entrou"],
                linha["cartao"],
                linha["gols"],
                linha["n_gols"],
            ]
        )
    display_reservas = pd.DataFrame(
        display_reservas,
        columns=[
            "team",
            "player_id",
            "numero",
            "nome",
            "posicao",
            "saiu",
            "entrou",
            "cartao",
            "gols",
            "n_gols",
        ],
    )
    return display_reservas


def build_team(time, tatica=None):
    if tatica is not None:
        tatica = "-".join(str(tatica))
        st.markdown(
            f"""
            <div>
                <span style="display: inline-block; width: 30px;"></span>
                <span style="font-size: 1.1em; font-weight: bold;">
                    {tatica}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for i, linha in time.iterrows():
        sub = (
            linha["entrou"]
            if pd.notna(linha["entrou"])
            else linha["saiu"] if pd.notna(linha["saiu"]) else ""
        )
        nome_jogador = "   ".join(
            str(x)
            for x in [
                linha["nome"],
                linha["cartao"],
                linha["gols"],
            ]
            if pd.notna(x)
        )
        posicao = linha["posicao"] if pd.notna(linha["posicao"]) else ""
        st.markdown(
            f"""
            <div>
                <span style="display: inline-block; width: 30px;">{sub}</span>
                <span>{nome_jogador}</span>
                <div style="font-size: 0.8em; color: gray;">
                    <span style="display: inline-block; width: 30px;"></span>
                    {linha['numero']}    {posicao}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_tab(
    tab, time_nome, titulares, reservas, tatica, gols, chutes, passes, escanteios
):
    with tab:
        c_chutes, c_passes, c_escanteios = st.columns(3)

        chutes_time = chutes.loc[chutes["team"] == time_nome].shape[0]
        chutes_outro = chutes.loc[chutes["team"] != time_nome].shape[0]

        passes_time = passes.loc[passes["team"] == time_nome].shape[0]
        passes_outro = passes.loc[passes["team"] != time_nome].shape[0]

        escanteios_time = escanteios.loc[escanteios["team"] == time_nome].shape[0]
        escanteios_outro = escanteios.loc[escanteios["team"] != time_nome].shape[0]

        c_chutes.metric("Chutes", chutes_time, delta=chutes_time - chutes_outro)
        c_passes.metric("Passes", passes_time, delta=passes_time - passes_outro)
        c_escanteios.metric(
            "Escanteios", escanteios_time, delta=escanteios_time - escanteios_outro
        )

        c1_tab, c2_tab = st.columns(2)

        with c1_tab:
            build_team(titulares, tatica)
            st.divider()
            build_team(reservas)

        with c2_tab:
            tab3, tab4 = st.tabs(["Campo de jogo", "Mapa de calor"])

            with tab3:
                fig = build_campo(titulares, tatica)
                st.pyplot(fig)

            with tab4:
                fig = build_heatmap(passes, time_nome)
                st.pyplot(fig)
        show_events(time_nome, gols, chutes, passes, escanteios)


def show_events(time_nome, gols, chutes, passes, escanteios):
    with st.expander("Eventos do time"):
        selected_stat = st.selectbox(
            "Estatística",
            options=["Gols", "Chutes", "Passes", "Escanteios"],
            index=None,
            key=f"select_stat_{time_nome}",
            label_visibility="collapsed",
        )

        if selected_stat is not None:
            if selected_stat == "Gols":
                stat = gols[gols["team"] == time_nome]
            elif selected_stat == "Chutes":
                stat = chutes[chutes["team"] == time_nome]
            elif selected_stat == "Passes":
                stat = passes[passes["team"] == time_nome]
            elif selected_stat == "Escanteios":
                stat = escanteios[escanteios["team"] == time_nome]
            st.dataframe(stat)


def build_campo(titulares, tatica):
    pitch = VerticalPitch(
        pitch_color="grass",
        line_color="white",
        stripe=True,
    )

    fig, ax = pitch.draw(figsize=(4, 8))

    positions = titulares["id_posicao"]
    numeros = titulares["numero"]

    pitch.formation(
        str(tatica),
        positions=positions,
        kind="scatter",
        ax=ax,
        s=500,
    )

    pitch.formation(
        str(tatica),
        positions=positions,
        kind="text",
        text=numeros,
        ax=ax,
        va="center",
        ha="center",
        fontsize=8,
        fontweight="bold",
        color="white",
    )

    return fig


def build_heatmap(eventos, time_nome):
    passes_time = eventos[
        (eventos["team"] == time_nome) & (eventos["period"] <= 4)
    ].copy()

    passes_time[["x", "y"]] = pd.DataFrame(
        passes_time["location"].tolist(),
        index=passes_time.index,
    )

    pitch = VerticalPitch(pitch_color="grass", line_color="white", stripe=True)

    fig, ax = pitch.draw(
        figsize=(4, 8),
    )

    cmap = LinearSegmentedColormap.from_list(
        "heatmap_fade",
        [
            (1, 1, 1, 0),  # transparente
            (1, 1, 0, 0.3),  # amarelo
            (1, 0.5, 0, 0.7),  # laranja
            (1, 0, 0, 1),  # vermelho
        ],
    )

    pitch.kdeplot(
        passes_time["x"],
        passes_time["y"],
        ax=ax,
        fill=True,
        levels=100,
        thresh=0.02,
        cmap=cmap,
        zorder=0,
    )

    return fig
