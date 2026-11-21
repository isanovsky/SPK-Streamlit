import numpy as np
import pandas as pd
import streamlit as st

from spk import keputusan, metrics
from spk import repository as repo
from spk import ui
from spk.engine import ahp

ui.kepala("Hasil TOPSIS", "Ranking prioritas peremajaan. Skor Cᵢ mendekati 1 berarti unit makin "
          "mendesak diremajakan.")

w = ahp(repo.matriks_ahp()).bobot
rank, h = keputusan.ranking(repo.ringkasan(), w)
aktif = repo.skenario_aktif()
if aktif:
    banding = keputusan.bandingkan(keputusan.ranking(repo.ringkasan_aktual(), w)[0], rank)
    rank = rank.merge(banding[["id", "peringkat_aktual", "gerak"]], on="id", how="left")

st.caption("Bobot dari halaman Pembobotan AHP: " + " · ".join(
    f'{k["kode"]} {ui.angka(v, 4)}' for k, v in zip(metrics.KRITERIA, w)))

kolom = ["peringkat", "id", "kelas", "umur", "skor", "alasan"]
cfg = {
    "peringkat": st.column_config.NumberColumn("Peringkat", format="%d", width="small"),
    "id": st.column_config.TextColumn("Unit", width="small"),
    "kelas": st.column_config.TextColumn("Kelas"),
    "umur": st.column_config.NumberColumn("Umur (th)", format="%d"),
    "skor": st.column_config.TextColumn("Skor Cᵢ"),
    "alasan": st.column_config.TextColumn("Faktor dominan", width="large",
                                          help="Kriteria dengan porsi terbesar dalam jarak ke solusi ideal negatif (D⁻²)"),
}
if aktif:
    kolom[1:1] = ["peringkat_aktual", "gerak"]
    cfg["peringkat_aktual"] = st.column_config.TextColumn("Peringkat aktual", width="small")
    cfg["gerak"] = st.column_config.TextColumn("Gerak", width="small",
                                               help="Positif: naik peringkat dibanding data aktual")
ui.tabel(rank[kolom], {"skor": ui.fmt(4), "gerak": ui.fmt_gerak, "peringkat_aktual": ui.fmt(0)},
         hide_index=True, width="stretch", height=460, column_config=cfg)

kode = [k["kode"] for k in metrics.KRITERIA]
idx = rank.sort_values("id")["id"].tolist()
urut = metrics.matriks_keputusan(repo.ringkasan())[0]["id"].tolist()


def tabel(arr, desimal=4):
    df = pd.DataFrame(arr, index=urut, columns=kode).loc[idx]
    return df.style.format(ui.fmt(desimal))


st.subheader("Langkah perhitungan")
t1, t2, t3, t4 = st.tabs(["1 · Matriks keputusan", "2 · Normalisasi", "3 · Terbobot & solusi ideal",
                          "4 · Jarak & skor"])
with t1:
    st.markdown("Nilai asli C1–C5 per unit. Tipe: C1–C3 *benefit* (makin besar makin mendesak), "
                "C4–C5 *cost* (makin kecil makin mendesak).")
    m1 = pd.DataFrame(metrics.matriks_keputusan(repo.ringkasan())[1], index=urut, columns=kode).loc[idx]
    st.dataframe(m1.style.format({"C1": ui.fmt(0), "C2": ui.fmt(0), "C3": ui.fmt(3), "C4": ui.fmt(2),
                                  "C5": ui.fmt(1)}), width="stretch")
with t2:
    st.markdown("rᵢⱼ = xᵢⱼ / √(Σᵢ xᵢⱼ²)")
    st.dataframe(tabel(h.normal), width="stretch")
with t3:
    st.markdown("vᵢⱼ = wⱼ · rᵢⱼ. A⁺ = maks untuk benefit dan min untuk cost; A⁻ sebaliknya.")
    st.dataframe(tabel(h.terbobot), width="stretch")
    st.dataframe(pd.DataFrame([h.ideal_pos, h.ideal_neg], index=["A⁺", "A⁻"], columns=kode)
                 .style.format(ui.fmt(4)), width="stretch")
with t4:
    st.markdown("Dᵢ⁺ = √Σⱼ(vᵢⱼ − Aⱼ⁺)², Dᵢ⁻ = √Σⱼ(vᵢⱼ − Aⱼ⁻)², Cᵢ = Dᵢ⁻ / (Dᵢ⁺ + Dᵢ⁻)")
    df = pd.DataFrame({"D⁺": h.d_pos, "D⁻": h.d_neg, "Cᵢ": h.skor, "Peringkat": h.peringkat}, index=urut)
    st.dataframe(df.sort_values("Peringkat").style.format(
        {"D⁺": ui.fmt(4), "D⁻": ui.fmt(4), "Cᵢ": ui.fmt(4), "Peringkat": ui.fmt(0)}), width="stretch")

ui.kaki()
