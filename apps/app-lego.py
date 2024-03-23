import dash
import numpy as np
import pandas as pd
from dash import Dash
from dash import dash_table
from dash import dcc
from dash import html
from dash import Input
from dash import Output
from dash.dash_table.Format import Format


# From https://stackoverflow.com/questions/52213738/html-dash-table
def generate_table(df, max_rows=26):
    return [html.Tr([html.Th(col) for col in df.columns])] + [
        html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
        for i in range(min(len(df), max_rows))
    ]


def markdown_link(link, name=None):
    #name = link if name is None else name
    #print(link)
    return "" if pd.isnull(link) else f"[{name}]({link})" 


inventories = pd.read_csv(
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2022/2022-09-06/inventories.csv.gz"
)
inventory_sets = pd.read_csv(
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2022/2022-09-06/inventory_sets.csv.gz"
)

sets = pd.read_csv(
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2022/2022-09-06/sets.csv.gz"
)

combined = pd.merge(
    pd.merge(inventories, inventory_sets, on="set_num", how="left"),
    sets,
    on="set_num",
    how="left",
)
combined["img_url"] = combined["img_url"].map(lambda x: markdown_link(x, name="image"))
combined["quantity"] = combined["quantity"].fillna(0)

renames = {
    "set_num": "Set Number",
    "inventory_id": "Inventory ID",
    "quantity": "Quantity",
    "name": "Set Name",
    "year": "Year",
    "theme_id": "Theme ID",
    "num_parts": "Number of Parts",
    "img_url": "Image Link",
}
combined = combined.rename(columns=renames)
choices = [
    col
    for col in renames.values()
    if col not in ("Inventory ID", "Theme ID", "Image Link")
]


# See https://stackoverflow.com/questions/70205486/clickable-hyperlinks-in-plotly-dash-datatable

for col in combined.columns:
    if combined[col].dtype == "object":
        combined[col] = combined[col].map(
            lambda x: "Unknown" if x is None or x == "" else x
        )


def col_dict(col):
    if col == "Image Link":
        return {"id": col, "name": col, "presentation": "markdown"}

    elif combined[col].dtype == "float64":
        return {
            "name": col,
            "id": col,
            "type": "numeric",
            "format": Format(nully="Unknown"),
        }
    else:
        return {"name": col, "id": col}


columns = [col_dict(col) for col in combined.columns]

app = Dash(__name__)
style_cell_conditional = [
    {
        "if": {"column_id": c},
        "textAlign": "left",
    }
    for c in ("Set Name", "Set ID")
]

app.layout = html.Div(
    [
        html.H2("LEGO Sets Data"),
        html.Div(
            [
                html.H4("Sort column: "),
                dcc.Dropdown(
                    choices, choices[0], id="sort-column", className="sort-col"
                ),
            ],
            style={
                "width": "30%",
                "verticalAlign": "top",
                "display": "inline-block",
            },
        ),
        html.Div(
            [
                html.H4("Sort: "),
                dcc.RadioItems(
                    ("Ascending", "Descending", "Random"),
                    "Ascending",
                    id="sort-type",
                    className="sort-type",
                ),
            ],
            style={
                "width": "30%",
                "verticalAlign": "top",
                "display": "inline-block",
            },
        ),
        html.Div(
            [
                dash_table.DataTable(
                    columns=columns,
                    id="table-display",
                    style_table={
                        "position": "relative",
                        "top": "5vh",
                        "left": "5vw",
                        "width": "60vw",
                    },
                    style_cell={"padding": "5px"},
                    style_data={"border": "1px solid black"},
                    style_data_conditional=[
                        {
                            "if": {"row_index": "odd"},
                            "backgroundColor": "rgb(220, 220, 220)",
                        }
                    ],
                    style_header={
                        "backgroundColor": "gold",
                        "fontWeight": "bold",
                        "border": "1px solid black",
                        "textAlign": "center",
                    },
                    style_cell_conditional=style_cell_conditional,
                    style_as_list_view=True,
                ),
            ],
            style={"text-align": "center", "width": "80%"},
        ),
    ],
    style={"text-align": "center"},
)


@app.callback(
    Output("table-display", "data"),
    Input("sort-column", "value"),
    Input("sort-type", "value"),
)
def arrange_table(sort_column, sort_type):
    if sort_type != "Random":
        result = combined.sort_values(
            by=sort_column, ascending=(sort_type == "Ascending"), inplace=False
        )
    else:
        result = combined.sample(frac=1)
    return result.to_dict("records")


if __name__ == "__main__":
    app.run_server(debug=True)
