import pandas as pd
import streamlit as st
from statsbombpy import sb


def load_data():
    return sb.competitions()


@st.cache_data(ttl=3600, show_spinner=False)
def load_eventos(match_id):
    return sb.events(match_id=match_id)


@st.cache_data(ttl=3600, show_spinner=False)
def load_lineup(match_id):
    return sb.lineups(match_id=match_id)


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
    eventos = load_eventos(id)
    lineups = load_lineup(id)

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

                if "Substitution - On" in position["start_reason"]:
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

    return (
        eventos,
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
