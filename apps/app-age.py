import re
from collections import defaultdict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from dash import Dash
from dash import dcc
from dash import html
from dash.dependencies import Input
from dash.dependencies import Output


def format_dates(dates):
    return dates.dt.strftime("%B %e, %Y")


def split_row(row):

    temp = {
        col: [row[col], row[col]]
        for col in ["movie_name", "release_year", "director", "age_difference"]
    }
    combined = pd.DataFrame(temp)
    combined["actor_name"] = [row["actor_1_name"], row["actor_2_name"]]
    combined["actor_gender"] = [row["actor_1_gender"], row["actor_2_gender"]]
    combined["actor_birthdate"] = [row["actor_1_birthdate"], row["actor_2_birthdate"]]
    combined["actor_name"] = [row["actor_1_name"], row["actor_2_name"]]
    return combined


def unpivot(data):
    group = data["variable"].unique()[0]
    data[group] = data["value"]
    data.pop("value")
    return data


# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
def conditional_swap(row):
    # Age before beauty
    if (
        row["actor_1_age"] < row["actor_2_age"]
        or row["actor_1_birthdate"] > row["actor_2_birthdate"]
    ):
        for col in ("name", "gender", "birthdate", "age"):
            first = f"actor_1_{col}"
            second = f"actor_2_{col}"
            row[first], row[second] = row[second], row[first]
    return row


def summarize_year(data):
    avg_gap = np.mean(data["age_difference"])
    # breakpoint()
    pct_male = 100 * np.mean(
        (data["actor_1_gender"] == "male") & (data["actor_2_gender"] == "female")
    )
    return pd.DataFrame(
        {"avg_gap": [avg_gap], "pct_male": [pct_male], "count": [data.shape[0]]}
    )


colorscales = px.colors.named_colorscales()
app = Dash(__name__)

colors = {"background": "#111111", "text": "#7FDBFF"}

# see https://plotly.com/python/px-arguments/ for more options
age_raw = pd.read_csv("http://hollywoodagegap.com/movies.csv")

# Average gap by year
# Actor's gaps
# Distribution by gender
genders = {"man": "male", "woman": "female"}

age = age_raw.copy()
age = age.rename(columns={col: re.sub(r" ", "_", col) for col in age.columns})
age.columns = map(str.lower, age.columns)

age["actor_1_birthdate"] = age["actor_1_birthdate"].map(pd.to_datetime)
age["actor_2_birthdate"] = age["actor_2_birthdate"].map(pd.to_datetime)
age = age.apply(conditional_swap, axis=1)


# "man/woman" aren't genders, technically
age["actor_1_gender"] = age["actor_1_gender"].map(genders)
age["actor_2_gender"] = age["actor_2_gender"].map(genders)
oldest = max(age["actor_1_age"].max(), age["actor_2_age"].max())

rows = []
for i in age.index:
    rows.append(split_row(age.loc[i, :]))
age_long = pd.concat(rows)
# age_long = age_long.loc[age_long["actor_1_age"] != age_long["actor_2_age"]]


movies = list(age["movie_name"].unique())

gaps_by_year = age.groupby(age["release_year"]).apply(summarize_year).reset_index()
years_plot = px.bar(
    gaps_by_year,
    x="release_year",
    y="count",
    color="avg_gap",
    color_continuous_scale="tropic",
    custom_data=["release_year", "avg_gap", "pct_male", "count"],
    labels={"avg_gap": "Average Age Gap"},
    # labels={
    #     "release_year": "Release Year",
    #     "avg_gap": "Average Age Gap",
    #     "pct_male": "Percentage with Male Older",
    #     "count": "Count",
    # },
    # hover_data={
    #     "release_year": ":.0f",
    #     "avg_gap": ":.2f",
    #     "pct_male": ":.2f",
    # },
)
years_plot.update_traces(
    hovertemplate="<br>".join(
        (
            "Release year: %{customdata[0]}",
            "Average age gap: %{customdata[1]:.2f} year(s)",
            "Percentage with male older: %{customdata[2]:.2f}",
            "Count: %{customdata[3]}",
        )
    )
)


line = {"color": "blue", "width": 2}
lines = [
    {
        "type": "line",
        "x0": age["actor_1_age"][i],
        "y0": i,
        "x1": age["actor_2_age"][i],
        "y1": i,
        "line": line,
    }
    for i in age.index
]
data = go.Scatter()

layout = go.Layout(
    shapes=lines,
    title=f"Age Gaps",
    plot_bgcolor="rgba(255,255,255,0.8)",
)
all_plot = go.Figure(
    layout=layout,
)
all_plot.update_xaxes(title="Actor Age", range=[15, round(oldest + 10, -1) + 10])
all_plot.update_yaxes(visible=False)


app.layout = html.Div(
    style={"backgroundColor": colors["background"]},
    children=[
        html.H1(
            children="Age Gaps",
            style={"textAlign": "center", "color": colors["text"]},
        ),
        html.Div(
            children="A visualization of age gaps in a sample of movies",
            style={"textAlign": "center", "color": colors["text"]},
        ),
        dcc.Graph(id="gaps-year", figure=years_plot),
        html.Div(
            children="Select a movie to see gaps:",
            style={"textAlign": "left", "color": colors["text"]},
        ),
        html.Div(children=[dcc.Dropdown(movies, movies[0], id="movie")]),
        dcc.Graph(id="movie-plot"),
        # dcc.Graph(id="all-plot", figure=all_plot),
        dcc.Link(
            children="Source: Tidy Tuesday 2023-02-14",
            href="https://github.com/rfordatascience/tidytuesday/blob/master/data/2023/2023-02-14/readme.md",
        ),
    ],
)


# https://stackoverflow.com/questions/55939775/succint-way-to-add-line-segments-to-plotly-graph-with-python-jupyter-notebook
@app.callback(Output("movie-plot", "figure"), Input("movie", "value"))
def plot_movie_gaps(movie):

    data = age.loc[(age["movie_name"] == movie), :]
    n = data.shape[0]
    data.index = tuple(range(n))
    gaps = (data["actor_2_birthdate"] - data["actor_1_birthdate"]).sort_values()[-1::-1]
    data.index = gaps.index

    # customdata hacks
    # https://stackoverflow.com/questions/59057881/python-plotly-how-to-customize-hover-template-on-with-what-information-to-show

    print(data)
    data["actor_1_birthdate"] = format_dates(data["actor_1_birthdate"])
    data["actor_2_birthdate"] = format_dates(data["actor_2_birthdate"])
    data["lower_cutoff"] = data["actor_1_age"] // 2 + 7
    template = (
        "%{customdata[0]} (age %{customdata[1]}, born %{customdata[2]}) <extra></extra>"
    )
    colors = defaultdict(lambda: "grey")
    colors.update({"male": "blue", "female": "red"})

    left = go.Scatter(
        x=data["actor_1_age"],
        y=data.index,
        mode="markers",
        marker={"color": colors[data["actor_1_gender"].unique()[0]], "size": 15},
        customdata=[
            [
                [data.loc[i, col]]
                for col in ("actor_1_name", "actor_1_age", "actor_1_birthdate")
            ]
            for i in data.index
        ],
        hovertemplate=template,
        showlegend=False,
    )
    minima = go.Scatter(
        x=data["lower_cutoff"],
        y=data.index,
        mode="markers",
        marker={"color": "black", "symbol": "x", "size": 12},
        customdata=[
            [[data.loc[i, col]] for col in ("actor_1_name", "lower_cutoff")]
            for i in data.index
        ],
        hovertemplate="Minimum recommended age for %{customdata[0]}: %{customdata[1]} <extra></extra>",
        showlegend=False,
    )

    right = go.Scatter(
        x=data["actor_2_age"],
        y=data.index,
        mode="markers",
        marker={"color": colors[data["actor_2_gender"].unique()[0]], "size": 15},
        customdata=[
            [
                data.loc[i, col]
                for col in ("actor_2_name", "actor_2_age", "actor_2_birthdate")
            ]
            for i in data.index
        ],
        hovertemplate=template,
        showlegend=False,
    )
    line = {"color": "grey", "width": 2}
    lines = [
        {
            "type": "line",
            "x0": data["actor_1_age"][i],
            "y0": i,
            "x1": data["actor_2_age"][i],
            "y1": i,
            "line": line,
        }
        for i in data.index
    ]

    year = data["release_year"].unique()[0]
    layout = go.Layout(
        shapes=lines,
        title=f"Age Gaps for {movie} ({year})",
        plot_bgcolor="rgba(255,255,255,0.8)",
    )
    fig = go.Figure(
        [left, right, minima],
        layout,
    )
    fig.update_xaxes(title="Actor Age", range=[15, round(oldest + 10, -1) + 10])
    fig.update_yaxes(visible=False)
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
