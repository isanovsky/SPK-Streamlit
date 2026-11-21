"""Ranking TOPSIS, alasan per unit, dan pemilihan unit berdasarkan anggaran."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import metrics
from .engine import HasilTOPSIS, topsis

LABEL_ALASAN = {
    "umur": "umur tinggi",
    "biaya_per_km": "biaya perawatan tinggi",
    "kerusakan_per_10rb": "sering rusak",
    "km_per_liter": "konsumsi BBM boros",
    "ketersediaan": "ketersediaan rendah",
}


def ranking(ringkasan: pd.DataFrame, bobot: np.ndarray) -> tuple[pd.DataFrame, HasilTOPSIS]:
    alt, x = metrics.matriks_keputusan(ringkasan)
    h = topsis(x, bobot, metrics.BENEFIT)
    # Porsi tiap kriteria dalam D⁻² (jarak kuadrat ke solusi ideal negatif): kriteria yang paling
    # menjauhkan unit dari kondisi "paling tidak mendesak".
    kuadrat = (h.terbobot - h.ideal_neg) ** 2
    total = kuadrat.sum(axis=1, keepdims=True)
    porsi = np.divide(kuadrat, total, out=np.zeros_like(kuadrat), where=total > 0)
    df = alt.copy()
    df["skor"] = h.skor
    df["peringkat"] = h.peringkat
    alasan = []
    for i in range(len(df)):
        urut = [j for j in np.argsort(-porsi[i])[:2] if porsi[i, j] >= 0.10]
        alasan.append(", ".join(f"{LABEL_ALASAN[metrics.KOLOM_KRITERIA[j]]} ({porsi[i, j] * 100:.0f}%)"
                                for j in urut))
    df["alasan"] = alasan
    return df.sort_values("peringkat").reset_index(drop=True), h


def pilih_berdasarkan_anggaran(rank: pd.DataFrame, anggaran: float, biaya_kelas: dict[str, float],
                               batas_usia: int) -> pd.DataFrame:
    df = rank.copy()
    df["biaya_peremajaan"] = df["kelas"].map(biaya_kelas).astype(float)
    df["wajib"] = df["umur"] > batas_usia
    df = df.sort_values(["wajib", "peringkat"], ascending=[False, True]).reset_index(drop=True)
    sisa, pilih = anggaran, []
    for _, r in df.iterrows():
        ok = r["biaya_peremajaan"] <= sisa
        pilih.append(ok)
        if ok:
            sisa -= r["biaya_peremajaan"]
    df["terpilih"] = pilih
    return df


def bandingkan(rank_aktual: pd.DataFrame, rank_skenario: pd.DataFrame) -> pd.DataFrame:
    a = rank_aktual[["id", "skor", "peringkat"]].rename(columns={"skor": "skor_aktual", "peringkat": "peringkat_aktual"})
    s = rank_skenario[["id", "skor", "peringkat"]].rename(columns={"skor": "skor_skenario", "peringkat": "peringkat_skenario"})
    df = a.merge(s, on="id", how="outer")
    df["selisih_skor"] = df["skor_skenario"] - df["skor_aktual"]
    df["gerak"] = df["peringkat_aktual"] - df["peringkat_skenario"]
    return df.sort_values(["peringkat_skenario", "peringkat_aktual"], na_position="last").reset_index(drop=True)
