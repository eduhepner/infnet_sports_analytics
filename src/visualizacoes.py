import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import VerticalPitch
from statsbombpy import sb


def make_pitch():
    return VerticalPitch(pitch_color="grass", line_color="white", stripe=True)


def build_campo(titulares, tatica):
    pitch = make_pitch()

    fig, ax = pitch.draw(figsize=(4, 8))

    positions = titulares["id_posicao"]
    numeros = titulares["numero"]
    nomes = titulares["nome"]

    pitch.formation(
        str(tatica),
        positions=positions,
        kind="scatter",
        ax=ax,
        s=400,
        xoffset=-8,
        edgecolors="black",
        linewidths=1,
    )

    pitch.formation(
        str(tatica),
        positions=positions,
        kind="text",
        text=numeros,
        va="center",
        ha="center",
        fontsize=8,
        fontweight="bold",
        color="white",
        xoffset=-8,
        ax=ax,
    )

    pitch.formation(
        str(tatica),
        positions=positions,
        kind="text",
        text=nomes.str.replace(" ", "\n"),
        va="center",
        ha="center",
        fontsize=8,
        fontweight="bold",
        color="white",
        ax=ax,
        path_effects=[
            path_effects.withStroke(
                linewidth=1,
                foreground="black",
            )
        ],
    )

    return fig


@st.cache_data(ttl=3600, show_spinner=False)
def build_heatmap(id, time_nome):
    eventos = sb.events(match_id=id)
    filtro = (eventos["team"] == time_nome) & (eventos["type"] == "Pressure")

    pressao = eventos.loc[filtro, ["location"]].copy()

    pressao[["x", "y"]] = pd.DataFrame(
        pressao["location"].tolist(),
        index=pressao.index,
    )

    pitch = make_pitch()

    fig, ax = pitch.draw(figsize=(4, 8))

    cmap = LinearSegmentedColormap.from_list(
        "heatmap_fade",
        [
            (1, 1, 1, 0),
            (1, 1, 0, 0.3),
            (1, 0.5, 0, 0.7),
            (1, 0, 0, 1),
        ],
    )

    pitch.kdeplot(
        pressao["x"],
        pressao["y"],
        ax=ax,
        fill=True,
        levels=100,
        thresh=0.02,
        cmap=cmap,
        zorder=0,
    )

    return fig


def build_passes(time_nome, passes):

    passes[["inicio_x", "inicio_y"]] = pd.DataFrame(
        passes["location"].tolist(),
        index=passes.index,
    )

    passes[["fim_x", "fim_y"]] = pd.DataFrame(
        passes["pass_end_location"].tolist(),
        index=passes.index,
    )

    passes = passes.loc[(passes["team"] == time_nome) & (passes["pass_outcome"].isna())]

    df_passes_plot = passes[["inicio_x", "inicio_y", "fim_x", "fim_y"]]

    pitch = make_pitch()

    fig, ax = pitch.draw(figsize=(4, 8))

    pitch.arrows(
        df_passes_plot["inicio_x"],
        df_passes_plot["inicio_y"],
        df_passes_plot["fim_x"],
        df_passes_plot["fim_y"],
        width=2,
        headwidth=5,
        headlength=5,
        edgecolor="black",
        linewidth=0.5,
        color="#ad993c",
        ax=ax,
        label="completed passes",
    )

    ax.legend(
        facecolor="#000000",
        handlelength=3,
        edgecolor="None",
        fontsize=6,
        loc="upper right",
        labelcolor="white",
    )

    return fig


def build_chutes(titulares_time, reservas_time, chutes):
    # conforme https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_shot_freeze_frame.html
    time_nome = titulares_time["team"].iloc[0]
    time = pd.concat([titulares_time, reservas_time]).reset_index()
    chutes_time = chutes[chutes["team"] == time_nome]
    chutes_time = (
        chutes_time[chutes_time["shot_freeze_frame"].notna()]
        .dropna(axis=1, how="all")
        .copy()
    )
    if chutes_time.empty:
        st.info("Sem chutes disponíveis.")
        return None
    pitch = VerticalPitch(
        half=True,
        pitch_color="grass",
        line_color="white",
        stripe=True,
        goal_type="box",
        pad_bottom=-20,
    )

    fig, axs = pitch.grid(
        figheight=8,
        endnote_height=0,
        title_height=0.1,
        title_space=0.02,
        axis=False,
        grid_height=0.83,
    )

    for i, df_shot_event in chutes_time.iterrows():

        chute_x = df_shot_event["location"][0]
        chute_y = df_shot_event["location"][1]

        final_chute_x = df_shot_event["shot_end_location"][0]
        final_chute_y = df_shot_event["shot_end_location"][1]

        chutador_id = df_shot_event["player_id"]

        nome_chutador = time.loc[
            time["player_id"] == chutador_id,
            "nome",
        ].iloc[0]

        # Chutador
        if df_shot_event["shot_outcome"] == "Goal":
            pitch.scatter(
                chute_x,
                chute_y,
                marker="football",
                s=600,
                ax=axs["pitch"],
                label="Gol",
                zorder=2,
            )
        else:
            pitch.scatter(
                chute_x,
                chute_y,
                s=300,
                ax=axs["pitch"],
                label="Chute",
                zorder=2,
            )

        pitch.annotate(
            str(nome_chutador),
            xy=(chute_x, chute_y),
            xytext=(-20, 0),
            textcoords="offset points",
            ax=axs["pitch"],
            ha="center",
            va="center",
            fontsize=12,
            color="white",
            fontweight="bold",
            zorder=3,
            path_effects=[
                path_effects.withStroke(
                    linewidth=2,
                    foreground="black",
                )
            ],
        )

        # Linha do chute
        pitch.lines(
            chute_x,
            chute_y,
            final_chute_x,
            final_chute_y,
            comet=True,
            label="Chute",
            color="#cb5a4c",
            ax=axs["pitch"],
        )
    return fig


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
    tab,
    eventos,
    time_nome,
    titulares,
    reservas,
    adv_titulares,
    adv_reservas,
    tatica,
    gols,
    chutes,
    passes,
    escanteios,
    match_id,
):
    with tab:
        c_chutes, c_passes, c_escanteios = st.columns(3)

        chutes_time = chutes.loc[chutes["team"] == time_nome].shape[0]
        chutes_outro = chutes.loc[chutes["team"] != time_nome].shape[0]

        passes_time = passes.loc[passes["team"] == time_nome].shape[0]
        passes_outro = passes.loc[passes["team"] != time_nome].shape[0]

        escanteios_time = escanteios.loc[escanteios["team"] == time_nome].shape[0]
        escanteios_outro = escanteios.loc[escanteios["team"] != time_nome].shape[0]

        c_chutes.metric(
            "Chutes",
            chutes_time,
            delta=chutes_time - chutes_outro,
        )
        c_passes.metric(
            "Passes",
            passes_time,
            delta=passes_time - passes_outro,
        )
        c_escanteios.metric(
            "Escanteios",
            escanteios_time,
            delta=escanteios_time - escanteios_outro,
        )

        c1_tab, c2_tab = st.columns(2)

        with c1_tab:
            build_team(titulares, tatica)
            st.divider()
            build_team(reservas)

        with c2_tab:
            tab3, tab4, tab5, tab6 = st.tabs(
                ["Campo de jogo", "Mapa de calor", "Mapa de passes", "Mapa de chutes"]
            )

            with tab3:
                fig = build_campo(titulares, tatica)
                st.pyplot(fig)

            with tab4:
                fig = build_heatmap(match_id, time_nome)
                st.pyplot(fig)

            with tab5:
                fig = build_passes(time_nome, passes)
                st.pyplot(fig)
            with tab6:
                fig = build_chutes(titulares, reservas, chutes)
                if fig is not None:
                    st.pyplot(fig)

        st.divider()
        with st.expander("Gols"):

            gols_freeze = (
                gols[gols["shot_freeze_frame"].notna()].sort_values("timestamp").copy()
            )
            gols_freeze = gols_freeze[gols_freeze["team"] == time_nome]

            if gols_freeze.empty:
                st.info("Nenhum gol disponível.")

            else:

                opcoes_gol = [
                    f"Gol - {linha['team']} - {linha['timestamp']}"
                    for i, linha in gols_freeze.iterrows()
                ]

                select_gol = st.selectbox(
                    "Selecione o gol", opcoes_gol, index=None, key=f"gols_{time_nome}"
                )
                if select_gol is not None:
                    gol_id = gols_freeze.iloc[opcoes_gol.index(select_gol)]["id"]

                    fig = show_gol(
                        titulares,
                        reservas,
                        adv_titulares,
                        adv_reservas,
                        gols,
                        gol_id,
                    )

                    st.pyplot(fig)
        st.divider()
        show_events(time_nome, eventos, titulares, reservas)
        st.divider()
        show_analises(time_nome, passes, gols, chutes, titulares, reservas)


def show_events(time_nome, eventos, titulares, reservas):
    with st.expander("Eventos do time"):

        jogadores = pd.concat([titulares, reservas])

        with st.form(key=f"form_eventos_{time_nome}"):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                nome_jogador = st.selectbox(
                    "Jogador",
                    jogadores["nome"],
                    index=None,
                )
            with f2:
                chutes = st.checkbox("Chutes")
            with f3:
                passes = st.checkbox("Passes")
            with f4:
                desarmes = st.checkbox("Desarmes")

            aplicar = st.form_submit_button("Aplicar")

        if aplicar:
            tipos = []

            if chutes:
                tipos.append("Shot")
            if passes:
                tipos.append("Pass")
            if desarmes:
                tipos.append("Duel")

            stat = eventos[
                (eventos["team"] == time_nome) & (eventos["type"].isin(tipos))
            ]

            if nome_jogador is not None:
                player_id = jogadores.loc[
                    jogadores["nome"] == nome_jogador, "player_id"
                ].iloc[0]

                stat = stat[stat["player_id"] == player_id]
            st.session_state[f"stat_{time_nome}"] = stat

        if f"stat_{time_nome}" in st.session_state:
            stat = st.session_state[f"stat_{time_nome}"]

            if not stat.empty:
                linhas = st.slider(
                    "Linhas",
                    min_value=1,
                    max_value=len(stat),
                    value=len(stat),
                    key=f"linhas_{time_nome}",
                )

                st.dataframe(stat.head(linhas))

                st.download_button(
                    "Baixar CSV do que está na tela",
                    data=stat.head(linhas).to_csv(),
                    file_name=f"stats_{time_nome}.csv",
                    key=f"download_eventos_{time_nome}",
                )
            else:
                st.info("Nenhum evento encontrado.")


def show_gol(titulares_time, reservas_time, titulares_adv, reservas_adv, gols, gol_id):
    # conforme https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_shot_freeze_frame.html
    time_nome = titulares_time["team"].iloc[0]
    time = pd.concat([titulares_time, reservas_time]).reset_index()
    adversario = pd.concat([titulares_adv, reservas_adv]).reset_index()

    dois_times = pd.concat(
        [
            time[["player_id", "numero", "nome", "posicao", "team"]],
            adversario[["player_id", "numero", "nome", "posicao", "team"]],
        ]
    ).reset_index(drop=True)

    df_shot_event = gols[gols["id"] == gol_id].dropna(axis=1, how="all").copy()

    df_freeze_frame = df_shot_event["shot_freeze_frame"].iloc[0]
    df_freeze_frame = pd.DataFrame(df_freeze_frame)

    # só quem ta no frame
    for i, linha in df_freeze_frame.iterrows():
        df_freeze_frame.loc[i, "player_id"] = linha["player"]["id"]
    df_freeze_frame["player_id"] = df_freeze_frame["player_id"].astype("int")

    df_freeze_frame = df_freeze_frame.merge(
        dois_times[["player_id", "numero", "nome", "posicao", "team"]],
        how="left",
        on="player_id",
    )
    df_freeze_frame[["x", "y"]] = pd.DataFrame(
        df_freeze_frame["location"].tolist(), index=df_freeze_frame.index
    )

    # separando os jogadores
    df_teammate = df_freeze_frame[df_freeze_frame["teammate"] == True]
    df_adversario = df_freeze_frame[df_freeze_frame["teammate"] == False]
    df_adversario_goleiro = df_adversario[(df_adversario.posicao == "Goalkeeper")]
    chutador_id = df_shot_event["player_id"].iloc[0]
    nome_chutador = dois_times.loc[dois_times["player_id"] == chutador_id, "nome"].iloc[
        0
    ]

    pitch = VerticalPitch(
        half=True,
        pitch_color="grass",
        line_color="white",
        stripe=True,
        goal_type="box",
        pad_bottom=0,
    )

    fig, axs = pitch.grid(
        figheight=8,
        endnote_height=0,  # no endnote
        title_height=0.0001,
        title_space=0.0001,
        axis=False,
        grid_height=0.83,
    )
    # jogadores
    if not df_teammate.empty:
        sc1 = pitch.scatter(
            df_teammate.x,
            df_teammate.y,
            s=600,
            c="#727cce",
            label=f"Ataque - {time_nome}",
            ax=axs["pitch"],
        )
    if not df_adversario.empty:
        sc2 = pitch.scatter(
            df_adversario.x,
            df_adversario.y,
            s=600,
            c="#5ba965",
            label=f"Defesa - {df_adversario['team'].iloc[0]}",
            ax=axs["pitch"],
        )
    if not df_adversario.empty:
        sc4 = pitch.scatter(
            df_adversario_goleiro.x,
            df_adversario_goleiro.y,
            s=600,
            ax=axs["pitch"],
            c="#c15ca5",
            label="Goleiro",
        )

    chute_x = df_shot_event["location"].iloc[0][0]
    chute_y = df_shot_event["location"].iloc[0][1]

    final_chute_x = df_shot_event["shot_end_location"].iloc[0][0]
    final_chute_y = df_shot_event["shot_end_location"].iloc[0][1]

    for i, jogador in df_freeze_frame.iterrows():
        pitch.annotate(
            str(jogador["nome"]),
            xy=(jogador["x"], jogador["y"]),
            xytext=(-20, 0),
            textcoords="offset points",
            ax=axs["pitch"],
            ha="center",
            va="center",
            fontsize=10,
            color="white",
            fontweight="bold",
            path_effects=[path_effects.withStroke(linewidth=2, foreground="black")],
            zorder=20,
        )

    # plot the shot
    sc3 = pitch.scatter(
        chute_x,
        chute_y,
        marker="football",
        s=600,
        ax=axs["pitch"],
        label=f"Autor do gol:\n - {nome_chutador}",
        zorder=20,
    )

    pitch.annotate(
        str(nome_chutador),
        xy=(chute_x, chute_y),
        xytext=(-20, 0),
        textcoords="offset points",
        ax=axs["pitch"],
        ha="center",
        va="center",
        fontsize=10,
        color="white",
        fontweight="bold",
        zorder=30,
        path_effects=[path_effects.withStroke(linewidth=2, foreground="black")],
    )

    line = pitch.lines(
        chute_x,
        chute_y,
        final_chute_x,
        final_chute_y,
        comet=True,
        label="Chute",
        color="#cb5a4c",
        ax=axs["pitch"],
    )

    # plot the angle to the goal
    pitch.goal_angle(
        chute_x,
        chute_y,
        ax=axs["pitch"],
        alpha=0.5,
        zorder=1.1,
        color="#cb5a4c",
        goal="right",
    )

    legend = axs["pitch"].legend(loc="center left", labelspacing=1.5)
    for text in legend.get_texts():

        text.set_fontsize(10)
        text.set_va("bottom")

    return fig


def show_analises(time_nome, passes, gols, chutes, titulares, reservas):
    with st.expander("Análises"):
        show_relacao_chutes_gols(time_nome, passes, gols, chutes, titulares, reservas)
        # show_analise2(time_nome, passes, gols, chutes, titulares, reservas):


def show_relacao_chutes_gols(time_nome, passes, gols, chutes, titulares, reservas):
    estatisticas = pd.DataFrame(
        {
            "nome": titulares["nome"].tolist() + reservas["nome"].tolist(),
            "player_id": titulares["player_id"].tolist()
            + reservas["player_id"].tolist(),
        }
    )

    estatisticas["chutes"] = 0
    estatisticas["gols"] = 0

    for indice, jogador in estatisticas.iterrows():
        player_id = jogador["player_id"]

        estatisticas.loc[indice, "chutes"] = len(
            chutes[chutes["player_id"] == player_id]
        )

        estatisticas.loc[indice, "gols"] = len(gols[gols["player_id"] == player_id])

    fig, ax = plt.subplots(figsize=(10, 6))

    sns.scatterplot(
        data=estatisticas,
        x="chutes",
        y="gols",
        s=100,
        ax=ax,
    )

    for i, jogador in estatisticas.iterrows():
        ax.annotate(
            jogador["nome"],
            (jogador["chutes"], jogador["gols"]),
            xytext=(5, 5),
            textcoords="offset points",
        )

    ax.set_title(f"Relação entre chutes e gols — {time_nome}")
    ax.set_xlabel("chutes")
    ax.set_ylabel("Gols")

    st.pyplot(fig)
