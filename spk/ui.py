"""Format angka Indonesia dan kerangka halaman (banner, banner skenario, footer)."""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from . import repository as repo

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BANNER_NAMA = ("banner.png", "banner.jpg", "banner.jpeg", "banner.webp")
BANNER_TINGGI_PX = 150


def _ribuan(s: str) -> str:
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def angka(x: float, desimal: int = 0) -> str:
    return _ribuan(f"{x:,.{desimal}f}")


def rp(x: float, desimal: int = 0) -> str:
    return f"Rp {angka(x, desimal)}"


def rp_singkat(x: float) -> str:
    for batas, akhiran in ((1e12, "T"), (1e9, "M"), (1e6, "jt")):
        if abs(x) >= batas:
            return f"Rp {angka(x / batas, 1)} {akhiran}"
    return rp(x)


def persen(x: float, desimal: int = 1) -> str:
    return f"{angka(x, desimal)}%"


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def tanggal(d) -> str:
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def bulan_tahun(d) -> str:
    return f"{BULAN[d.month - 1]} {d.year}"


CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1280px;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
[data-testid="stMetric"] {background:#FFFFFF; border:1px solid #D9DEE5; border-radius:6px; padding:0.8rem 1rem;}
[data-testid="stMetricLabel"] p {font-size:0.82rem; color:#4A5563;}
img.spk-banner {width:100% !important; max-width:none !important; height:%TINGGI%px !important;
  object-fit:cover !important; object-position:left center !important; border-radius:6px; display:block;}
@media (max-width: 640px) { img.spk-banner {height:auto !important; object-fit:contain !important;}
  .block-container {padding-top: 3.75rem;} }
[data-testid="stPlotlyChart"] {border:1px solid #D9DEE5; border-radius:6px; overflow:hidden; background:#FFFFFF;}
.spk-skenario {background:#FFF6E8; border:1px solid #E8C48F; color:#5E3B0A; border-radius:6px;
  padding:0.55rem 0.9rem; margin-bottom:0.9rem; font-size:0.92rem;}
.spk-footer {color:#6B7684; font-size:0.78rem; border-top:1px solid #D9DEE5; margin-top:2.5rem; padding-top:0.6rem;}
.spk-sub {color:#4A5563; margin-top:-0.6rem; margin-bottom:1rem;}
@media (prefers-reduced-motion: reduce) { * {transition:none !important; animation:none !important;} }
</style>
"""


def _banner():
    for nama in BANNER_NAMA:
        path = ASSETS / nama
        if path.exists():
            mime = "image/jpeg" if path.suffix in (".jpg", ".jpeg") else f"image/{path.suffix[1:]}"
            data = base64.b64encode(path.read_bytes()).decode()
            st.markdown(f'<img class="spk-banner" src="data:{mime};base64,{data}" alt="Banner">',
                        unsafe_allow_html=True)
            return


def kepala(judul: str, sub: str | None = None):
    st.markdown(CSS.replace("%TINGGI%", str(BANNER_TINGGI_PX)), unsafe_allow_html=True)
    _banner()
    s = repo.skenario_aktif()
    if s:
        kiri, kanan = st.columns([5, 1.4], vertical_alignment="center")
        kiri.markdown(f'<div class="spk-skenario"><b>Mode skenario:</b> {s["nama"]} · '
                      f'{len(s["events"])} event. Semua angka di halaman ini memakai data skenario.</div>',
                      unsafe_allow_html=True)
        if kanan.button("Kembali ke data aktual", key="keluar_skenario", width="stretch"):
            repo.set_skenario_aktif(None)
            st.rerun()
    st.title(judul)
    if sub:
        st.markdown(f'<div class="spk-sub">{sub}</div>', unsafe_allow_html=True)


def kaki():
    p = repo.parameter()
    s = repo.skenario_aktif()
    teks = f'Data simulasi · seed {p["seed"]} · periode {p["periode"]["mulai"]} s.d. {p["periode"]["selesai"]}'
    if s:
        teks += f' · skenario: {s["nama"]}'
    st.markdown(f'<div class="spk-footer">{teks}</div>', unsafe_allow_html=True)


def fmt(desimal: int = 0, awalan: str = "", akhiran: str = ""):
    """Formatter Styler: angka gaya Indonesia, nilai kosong tampil sebagai tanda pisah."""
    def f(x):
        if x is None or (isinstance(x, float) and x != x):
            return "–"
        return f"{awalan}{angka(x, desimal)}{akhiran}"
    return f


def fmt_gerak(x):
    if x is None or (isinstance(x, float) and x != x):
        return "–"
    return f"+{int(x)}" if x > 0 else str(int(x))


def tabel(df, format_kolom: dict, **kwargs):
    """st.dataframe dengan tampilan angka Indonesia; pengurutan tetap memakai nilai numerik."""
    gaya = kwargs.pop("gaya", None)
    sty = df.style.format(format_kolom, na_rep="–")
    if gaya:
        sty = sty.apply(gaya, axis=1)
    return st.dataframe(sty, **kwargs)
