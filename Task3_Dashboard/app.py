"""
Task 3: Dashboard Development - Superstore Sales Dashboard
EliteTech Intern - Data Analytics Internship

An interactive dashboard built with Plotly Dash on the Superstore Sales dataset
(8,399 orders from a Canadian office-supplies retailer, 2009-2012).

Run it with:
    python app.py
then open http://127.0.0.1:8050 in a browser.

Every chart, KPI card and insight responds to the filters at the top.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html, dash_table

# ---------------------------------------------------------------------------
# 1. Load and prepare the data
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "superstore_sales.csv")

df = pd.read_csv(DATA_PATH, encoding="latin1")
df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y")
df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%m/%d/%Y")
df["Year"] = df["Order Date"].dt.year
df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
df["Days to Ship"] = (df["Ship Date"] - df["Order Date"]).dt.days
# Fix a spelling mistake in the source data
df["Region"] = df["Region"].replace({"Prarie": "Prairie"})
df["Province"] = df["Province"].replace({"Saskachewan": "Saskatchewan"})
# Group discounts into readable bands
df["Discount Band"] = pd.cut(df["Discount"], bins=[-0.001, 0.02, 0.05, 0.08, 1.0],
                             labels=["0-2%", "3-5%", "6-8%", "9%+"])

YEARS = sorted(df["Year"].unique())
REGIONS = sorted(df["Region"].unique())
CATEGORIES = sorted(df["Product Category"].unique())
SEGMENTS = sorted(df["Customer Segment"].unique())

# Colour palette used across the dashboard
BLUE, RED, GREEN, GREY = "#2E5EAA", "#D1495B", "#2A9D8F", "#6C757D"
CAT_COLORS = {"Furniture": "#E9C46A", "Office Supplies": "#2A9D8F", "Technology": "#2E5EAA"}
TEMPLATE = "plotly_white"


# ---------------------------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------------------------
def money(x):
    """Format a number as compact currency, e.g. 1.2M or 35.4K."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e6:
        return f"{sign}${x / 1e6:.2f}M"
    if x >= 1e3:
        return f"{sign}${x / 1e3:.1f}K"
    return f"{sign}${x:.0f}"


def filter_data(years, regions, categories, segments):
    """Return the rows matching the current filter selections."""
    d = df[(df["Year"] >= years[0]) & (df["Year"] <= years[1])]
    if regions:
        d = d[d["Region"].isin(regions)]
    if categories:
        d = d[d["Product Category"].isin(categories)]
    if segments:
        d = d[d["Customer Segment"].isin(segments)]
    return d


def kpi_card(title, value, color):
    return html.Div(className="kpi", style={"borderTop": f"4px solid {color}"}, children=[
        html.Div(title, className="kpi-title"),
        html.Div(value, className="kpi-value"),
    ])


def empty_figure(message="No data for this selection"):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"size": 16, "color": GREY})
    fig.update_layout(template=TEMPLATE, xaxis={"visible": False}, yaxis={"visible": False})
    return fig


def style(fig, title):
    fig.update_layout(template=TEMPLATE, title={"text": title, "x": 0.01, "font": {"size": 16}},
                      margin={"l": 10, "r": 10, "t": 50, "b": 10}, legend_title_text="")
    return fig


# ---------------------------------------------------------------------------
# 3. Layout
# ---------------------------------------------------------------------------
app = Dash(__name__, title="Superstore Sales Dashboard")
server = app.server  # exposed for deployment (e.g. gunicorn app:server)

app.index_string = """<!DOCTYPE html>
<html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
  body { font-family: "Segoe UI", Roboto, Arial, sans-serif; background:#F4F6F9; margin:0; color:#212529; }
  .header { background:#1F3A5F; color:white; padding:18px 28px; }
  .header h1 { margin:0; font-size:26px; } .header p { margin:4px 0 0; opacity:.8; }
  .container { padding:18px 28px; }
  .filters { display:grid; grid-template-columns: 1.4fr 1fr 1fr 1fr; gap:16px; background:white;
             padding:16px; border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .filters label { font-weight:600; font-size:13px; display:block; margin-bottom:6px; }
  .kpis { display:grid; grid-template-columns: repeat(5, 1fr); gap:16px; margin:16px 0; }
  .kpi { background:white; border-radius:10px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .kpi-title { font-size:13px; color:#6C757D; text-transform:uppercase; letter-spacing:.5px; }
  .kpi-value { font-size:26px; font-weight:700; margin-top:4px; }
  .grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:16px; }
  .card { background:white; border-radius:10px; padding:8px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .insights { background:white; border-left:5px solid #2A9D8F; border-radius:10px; padding:12px 20px;
              box-shadow:0 1px 3px rgba(0,0,0,.08); margin-bottom:16px; }
  .insights h3 { margin:6px 0; } .insights li { margin:6px 0; line-height:1.4; }
  @media (max-width: 1000px) { .filters, .kpis, .grid2 { grid-template-columns: 1fr; } }
</style></head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""

app.layout = html.Div([
    html.Div(className="header", children=[
        html.H1("Superstore Sales Dashboard"),
        html.P("Sales and profitability of a Canadian office-supplies retailer, 2009-2012. "
               "Use the filters to explore."),
    ]),
    html.Div(className="container", children=[
        # ---- Filters ----
        html.Div(className="filters", children=[
            html.Div([html.Label("Order year"),
                      dcc.RangeSlider(id="f-years", min=YEARS[0], max=YEARS[-1], step=1,
                                      value=[YEARS[0], YEARS[-1]],
                                      marks={int(y): str(y) for y in YEARS})]),
            html.Div([html.Label("Region"),
                      dcc.Dropdown(id="f-region", options=REGIONS, multi=True, placeholder="All regions")]),
            html.Div([html.Label("Product category"),
                      dcc.Dropdown(id="f-category", options=CATEGORIES, multi=True, placeholder="All categories")]),
            html.Div([html.Label("Customer segment"),
                      dcc.Dropdown(id="f-segment", options=SEGMENTS, multi=True, placeholder="All segments")]),
        ]),
        # ---- KPI cards ----
        html.Div(id="kpis", className="kpis"),
        # ---- Actionable insights (generated from the filtered data) ----
        html.Div(className="insights", children=[html.H3("Key insights for this selection"),
                                                 html.Ul(id="insights")]),
        # ---- Charts ----
        html.Div(className="grid2", children=[
            html.Div(className="card", children=dcc.Graph(id="g-trend")),
            html.Div(className="card", children=dcc.Graph(id="g-category")),
        ]),
        html.Div(className="grid2", children=[
            html.Div(className="card", children=dcc.Graph(id="g-subcat", style={"height": "520px"})),
            html.Div(className="card", children=dcc.Graph(id="g-region", style={"height": "520px"})),
        ]),
        html.Div(className="grid2", children=[
            html.Div(className="card", children=dcc.Graph(id="g-discount")),
            html.Div(className="card", children=dcc.Graph(id="g-segment")),
        ]),
        html.Div(className="grid2", children=[
            html.Div(className="card", children=dcc.Graph(id="g-shipping")),
            html.Div(className="card", style={"padding": "14px"}, children=[
                html.H4("Top 10 loss-making products", style={"margin": "4px 0 10px"}),
                dash_table.DataTable(
                    id="t-losses",
                    columns=[{"name": c, "id": c} for c in ["Product", "Sub-Category", "Sales", "Profit"]],
                    style_cell={"fontFamily": "Segoe UI, Roboto, Arial, sans-serif", "fontSize": 13, "padding": "6px",
                                "textAlign": "left", "maxWidth": 280, "overflow": "hidden",
                                "textOverflow": "ellipsis"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#F1F3F5"},
                    style_data_conditional=[{"if": {"column_id": "Profit"}, "color": RED, "fontWeight": "600"}],
                ),
            ]),
        ]),
        html.P("Data source: Superstore Sales sample dataset (Tableau). Built with Plotly Dash.",
               style={"color": GREY, "fontSize": 12, "textAlign": "center"}),
    ]),
])


# ---------------------------------------------------------------------------
# 4. Callback: update everything whenever a filter changes
# ---------------------------------------------------------------------------
@app.callback(
    Output("kpis", "children"), Output("insights", "children"),
    Output("g-trend", "figure"), Output("g-category", "figure"),
    Output("g-subcat", "figure"), Output("g-region", "figure"),
    Output("g-discount", "figure"), Output("g-segment", "figure"),
    Output("g-shipping", "figure"), Output("t-losses", "data"),
    Input("f-years", "value"), Input("f-region", "value"),
    Input("f-category", "value"), Input("f-segment", "value"),
)
def update_dashboard(years, regions, categories, segments):
    d = filter_data(years, regions, categories, segments)

    if d.empty:
        blank = empty_figure()
        kpis = [kpi_card(t, "-", GREY) for t in ["Total sales", "Total profit", "Profit margin",
                                                 "Orders", "Avg discount"]]
        return kpis, [html.Li("No orders match the selected filters.")], *([blank] * 7), []

    # ---------------- KPIs ----------------
    sales, profit = d["Sales"].sum(), d["Profit"].sum()
    margin = profit / sales * 100 if sales else 0
    kpis = [
        kpi_card("Total sales", money(sales), BLUE),
        kpi_card("Total profit", money(profit), GREEN if profit >= 0 else RED),
        kpi_card("Profit margin", f"{margin:.1f}%", GREEN if margin >= 0 else RED),
        kpi_card("Orders", f"{d['Order ID'].nunique():,}", GREY),
        kpi_card("Avg discount", f"{d['Discount'].mean() * 100:.1f}%", "#E9C46A"),
    ]

    # ---------------- Monthly trend ----------------
    monthly = d.groupby("Month")[["Sales", "Profit"]].sum().reset_index()
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Sales"], name="Sales",
                                   line={"color": BLUE, "width": 2}))
    fig_trend.add_trace(go.Bar(x=monthly["Month"], y=monthly["Profit"], name="Profit",
                               marker_color=[GREEN if p >= 0 else RED for p in monthly["Profit"]],
                               opacity=0.7))
    style(fig_trend, "Monthly sales and profit")
    fig_trend.update_layout(legend={"orientation": "h", "y": 1.1, "x": 1, "xanchor": "right"},
                            yaxis_tickprefix="$")

    # ---------------- Category ----------------
    cat = d.groupby("Product Category")[["Sales", "Profit"]].sum().reset_index()
    cat_long = cat.melt(id_vars="Product Category", var_name="Measure", value_name="Amount")
    fig_cat = px.bar(cat_long, x="Product Category", y="Amount", color="Measure", barmode="group",
                     color_discrete_map={"Sales": BLUE, "Profit": GREEN}, text_auto=".3s")
    style(fig_cat, "Sales vs profit by category")
    fig_cat.update_layout(xaxis_title="", yaxis_title="", yaxis_tickprefix="$")

    # ---------------- Sub-category profit ----------------
    sub = (d.groupby(["Product Sub-Category", "Product Category"])[["Sales", "Profit"]]
           .sum().reset_index().sort_values("Profit"))
    sub["Margin %"] = (sub["Profit"] / sub["Sales"] * 100).round(1)
    fig_sub = px.bar(sub, x="Profit", y="Product Sub-Category", orientation="h",
                     color=sub["Profit"].apply(lambda p: "Loss" if p < 0 else "Profit"),
                     color_discrete_map={"Loss": RED, "Profit": GREEN},
                     hover_data={"Sales": ":$,.0f", "Margin %": True, "Product Category": True})
    style(fig_sub, "Profit by sub-category (red = losing money)")
    fig_sub.update_layout(yaxis_title="", xaxis_title="Profit", xaxis_tickprefix="$", showlegend=False)

    # ---------------- Region ----------------
    reg = d.groupby("Region")[["Sales", "Profit"]].sum().reset_index()
    reg["Margin %"] = (reg["Profit"] / reg["Sales"] * 100).round(1)
    reg = reg.sort_values("Sales")
    fig_reg = px.bar(reg, x="Sales", y="Region", orientation="h", color="Margin %",
                     color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                     hover_data={"Profit": ":$,.0f"}, text=reg["Sales"].apply(money))
    style(fig_reg, "Sales by region (colour = profit margin %)")
    fig_reg.update_layout(yaxis_title="", xaxis_tickprefix="$")

    # ---------------- Discount impact ----------------
    disc = d.groupby("Discount Band", observed=True)[["Sales", "Profit"]].sum().reset_index()
    disc["Margin %"] = disc["Profit"] / disc["Sales"] * 100
    fig_disc = px.bar(disc, x="Discount Band", y="Margin %", text=disc["Margin %"].round(1).astype(str) + "%",
                      color="Margin %", color_continuous_scale="RdYlGn", color_continuous_midpoint=0)
    style(fig_disc, "Profit margin by discount level")
    fig_disc.update_layout(coloraxis_showscale=False, xaxis_title="Discount given")

    # ---------------- Segment ----------------
    seg = d.groupby("Customer Segment")[["Sales", "Profit"]].sum().reset_index()
    fig_seg = px.pie(seg, names="Customer Segment", values="Sales", hole=0.5,
                     color_discrete_sequence=[BLUE, GREEN, "#E9C46A", RED])
    style(fig_seg, "Share of sales by customer segment")

    # ---------------- Shipping ----------------
    ship = (d.groupby(["Ship Mode", "Order Priority"])
            .agg(Orders=("Order ID", "nunique"), AvgShipCost=("Shipping Cost", "mean"))
            .reset_index())
    priority_order = ["Critical", "High", "Medium", "Low", "Not Specified"]
    fig_ship = px.bar(ship, x="Order Priority", y="Orders", color="Ship Mode", barmode="stack",
                      category_orders={"Order Priority": priority_order},
                      hover_data={"AvgShipCost": ":$.2f"},
                      color_discrete_sequence=[BLUE, "#E9C46A", GREEN])
    style(fig_ship, "Orders by priority and ship mode")
    fig_ship.update_layout(xaxis_title="")

    # ---------------- Loss-making products table ----------------
    prod = (d.groupby(["Product Name", "Product Sub-Category"])[["Sales", "Profit"]].sum()
            .reset_index().nsmallest(10, "Profit"))
    prod = prod[prod["Profit"] < 0]
    table = [{"Product": r["Product Name"], "Sub-Category": r["Product Sub-Category"],
              "Sales": f"${r['Sales']:,.0f}", "Profit": f"-${abs(r['Profit']):,.0f}"} for _, r in prod.iterrows()]

    # ---------------- Actionable insights ----------------
    insights = []
    best_cat = cat.loc[cat["Profit"].idxmax()]
    insights.append(html.Li([html.B(best_cat["Product Category"]),
                             f" is the most profitable category ({money(best_cat['Profit'])} profit, "
                             f"{best_cat['Profit'] / best_cat['Sales'] * 100:.1f}% margin)."]))
    losers = sub[sub["Profit"] < 0]
    if not losers.empty:
        names = ", ".join(losers["Product Sub-Category"].head(3))
        insights.append(html.Li([html.B(f"{len(losers)} sub-categories lose money"),
                                 f" (worst: {names}), with a combined loss of {money(abs(losers['Profit'].sum()))}. "
                                 "Review their pricing, discounts and shipping costs, or reduce the range."]))
    weak_cat = cat.loc[(cat["Profit"] / cat["Sales"]).idxmin()]
    if len(cat) > 1:
        insights.append(html.Li([html.B(weak_cat["Product Category"]),
                                 f" has the thinnest margin ({weak_cat['Profit'] / weak_cat['Sales'] * 100:.1f}%) "
                                 f"despite {money(weak_cat['Sales'])} in sales, so selling more of it adds little profit."]))
    if len(disc) >= 2:
        lo, hi = disc.iloc[0], disc.iloc[-1]
        trend = "fall" if hi["Margin %"] < lo["Margin %"] else "rise"
        advice = " Cap discounts, especially on low-margin items." if trend == "fall" else ""
        insights.append(html.Li([f"Margins {trend} from ", html.B(f"{lo['Margin %']:.1f}%"),
                                 f" at {lo['Discount Band']} discount to ", html.B(f"{hi['Margin %']:.1f}%"),
                                 f" at {hi['Discount Band']}.{advice}"]))
    top_reg = reg.iloc[-1]
    low_reg = reg.loc[reg["Margin %"].idxmin()]
    if len(reg) > 1:
        insights.append(html.Li([html.B(top_reg["Region"]), f" brings in the most sales ({money(top_reg['Sales'])}), while ",
                                 html.B(low_reg["Region"]), f" has the lowest margin ({low_reg['Margin %']:.1f}%)."]))
    if d["Year"].nunique() > 1:
        yearly = d.groupby("Year")[["Sales", "Profit"]].sum()
        first, last = yearly.index.min(), yearly.index.max()
        change = (yearly.loc[last, "Sales"] / yearly.loc[first, "Sales"] - 1) * 100
        insights.append(html.Li([f"Sales changed by ", html.B(f"{change:+.1f}%"),
                                 f" from {first} to {last}."]))

    return (kpis, insights, fig_trend, fig_cat, fig_sub, fig_reg, fig_disc, fig_seg, fig_ship, table)


# ---------------------------------------------------------------------------
# 5. Run the app
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
