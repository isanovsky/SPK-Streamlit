"""Grafik Plotly dengan gaya yang seragam."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

UTAMA = "#0E5A6B"
AKSEN = "#C2703D"
NETRAL = "#9AA5B1"
GRID = "#E3E7EC"
TEKS = "#18212B"
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _label_bulan(seri) -> list[str]:
    return [f"{BULAN[d.month - 1]} {d.year}" for d in pd.to_datetime(seri)]


def _gaya(fig: go.Figure, judul: str, tinggi: int = 320, y_judul: str = "", x_judul: str = "") -> go.Figure:
    fig.update_layout(
        title={"text": judul, "x": 0, "xanchor": "left", "font": {"size": 15, "color": TEKS}},
        height=tinggi, margin={"l": 8, "r": 8, "t": 48, "b": 8},
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font={"family": "Source Sans Pro, sans-serif", "size": 12, "color": "#3B4654"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "right", "x": 1, "title": None},
        hoverlabel={"bgcolor": "#FFFFFF", "font_size": 12},
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, title=x_judul or None)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y_judul or None)
    return fig


def tren_biaya(aktual: pd.DataFrame, skenario: pd.DataFrame | None = None,
               tanggal_event: list[tuple[str, str]] | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=_label_bulan(aktual["bulan"]), y=aktual["biaya_per_km"], name="Aktual",
                    mode="lines+markers", line={"color": NETRAL if skenario is not None else UTAMA, "width": 2},
                    hovertemplate="%{x}<br>Rp %{y:,.0f}/km<extra></extra>")
    if skenario is not None:
        fig.add_scatter(x=_label_bulan(skenario["bulan"]), y=skenario["biaya_per_km"], name="Skenario",
                        mode="lines+markers", line={"color": AKSEN, "width": 2.5},
                        hovertemplate="%{x}<br>Rp %{y:,.0f}/km<extra></extra>")
    sudah = set()
    for tgl, label in tanggal_event or []:
        x = _label_bulan([tgl])[0]
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper",
                      line={"color": AKSEN, "dash": "dot", "width": 1})
        if x not in sudah:
            fig.add_annotation(x=x, y=1, yref="paper", text=label, showarrow=False,
                               font={"size": 10, "color": AKSEN}, xanchor="left", yanchor="top")
            sudah.add(x)
    fig = _gaya(fig, "Biaya perawatan per km, per bulan", y_judul="Rp/km")
    fig.update_yaxes(tickformat=",.0f")
    return fig


def sebaran_umur(ringkasan: pd.DataFrame, batas: int) -> go.Figure:
    hitung = ringkasan["umur"].value_counts().sort_index()
    warna = [AKSEN if u > batas else (UTAMA if u < batas - 5 else "#5E8C99") for u in hitung.index]
    fig = go.Figure(go.Bar(x=hitung.index, y=hitung.values, marker_color=warna,
                           hovertemplate="Umur %{x} tahun<br>%{y} unit<extra></extra>"))
    fig.add_vline(x=batas + 0.5, line={"color": AKSEN, "dash": "dash", "width": 1})
    fig.add_annotation(x=batas + 0.5, y=1, yref="paper", text=f"Batas {batas} th", showarrow=False,
                       font={"size": 10, "color": AKSEN}, xanchor="right", yanchor="top")
    return _gaya(fig, "Sebaran umur armada", y_judul="Unit", x_judul="Umur (tahun)")


def umur_vs_kerusakan(ringkasan: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    normal = ringkasan[ringkasan["anomali"] == ""]
    khusus = ringkasan[ringkasan["anomali"] != ""]
    fig.add_scatter(x=normal["umur"], y=normal["kerusakan_per_10rb"], mode="markers", name="Unit",
                    marker={"color": UTAMA, "size": 9, "opacity": 0.75}, text=normal["id"],
                    hovertemplate="%{text}<br>Umur %{x} th<br>%{y:.2f} kerusakan/10.000 km<extra></extra>")
    fig.add_scatter(x=khusus["umur"], y=khusus["kerusakan_per_10rb"], mode="markers+text", name="Anomali simulasi",
                    marker={"color": AKSEN, "size": 11, "symbol": "diamond"}, text=khusus["id"],
                    textposition="top center", textfont={"size": 10, "color": AKSEN},
                    customdata=khusus["anomali"],
                    hovertemplate="%{text}<br>%{customdata}<br>Umur %{x} th<br>%{y:.2f}/10.000 km<extra></extra>")
    return _gaya(fig, "Umur vs tingkat kerusakan", y_judul="Kerusakan per 10.000 km", x_judul="Umur (tahun)")


def bulanan_unit(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    x = _label_bulan(df["bulan"])
    fig.add_bar(x=x, y=df["kerusakan"], name="Kerusakan", marker_color=AKSEN, yaxis="y2", opacity=0.55,
                hovertemplate="%{x}<br>%{y} kerusakan<extra></extra>")
    fig.add_scatter(x=x, y=df["biaya_per_km"], name="Biaya per km", mode="lines+markers",
                    line={"color": UTAMA, "width": 2}, hovertemplate="%{x}<br>Rp %{y:,.0f}/km<extra></extra>")
    fig.update_layout(yaxis2={"overlaying": "y", "side": "right", "showgrid": False, "title": "Kerusakan",
                              "rangemode": "tozero"})
    return _gaya(fig, "Biaya per km dan kerusakan per bulan", y_judul="Rp/km")


def bobot(nama: list[str], w, w_banding=None, label_banding: str = "AHP") -> go.Figure:
    fig = go.Figure()
    if w_banding is not None:
        fig.add_bar(y=nama, x=w_banding, orientation="h", name=label_banding, marker_color=NETRAL,
                    hovertemplate="%{y}: %{x:.4f}<extra></extra>")
    fig.add_bar(y=nama, x=w, orientation="h", name="Bobot" if w_banding is None else "What-if",
                marker_color=UTAMA, text=[f"{v:.3f}".replace(".", ",") for v in w], textposition="outside",
                hovertemplate="%{y}: %{x:.4f}<extra></extra>")
    maks = max(max(w), max(w_banding) if w_banding is not None else 0)
    fig.update_layout(barmode="group", yaxis={"autorange": "reversed"}, showlegend=w_banding is not None,
                      xaxis={"range": [0, maks * 1.22]}, uniformtext={"mode": "show", "minsize": 10})
    return _gaya(fig, "Bobot kriteria", tinggi=260)
