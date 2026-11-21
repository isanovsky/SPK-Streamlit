"""Agregasi log harian menjadi kriteria C1–C5, KPI, dan data bulanan."""
from __future__ import annotations

import numpy as np
import pandas as pd

KRITERIA = [
    {"kode": "C1", "nama": "Umur kendaraan", "kolom": "umur", "satuan": "tahun", "benefit": True},
    {"kode": "C2", "nama": "Biaya perawatan", "kolom": "biaya_per_km", "satuan": "Rp/km", "benefit": True},
    {"kode": "C3", "nama": "Tingkat kerusakan", "kolom": "kerusakan_per_10rb", "satuan": "per 10.000 km", "benefit": True},
    {"kode": "C4", "nama": "Efisiensi BBM", "kolom": "km_per_liter", "satuan": "km/liter", "benefit": False},
    {"kode": "C5", "nama": "Ketersediaan", "kolom": "ketersediaan", "satuan": "%", "benefit": False},
]
KOLOM_KRITERIA = [k["kolom"] for k in KRITERIA]
BENEFIT = np.array([k["benefit"] for k in KRITERIA])


def ringkasan_armada(armada: pd.DataFrame, log: pd.DataFrame, keluar: set[str] | None = None) -> pd.DataFrame:
    keluar = keluar or set()
    g = log.groupby("unit_id")
    agg = pd.DataFrame({
        "km": g["km"].sum(),
        "biaya": g["biaya_perawatan"].sum(),
        "kerusakan": g["kerusakan"].sum(),
        "bbm": g["bbm_liter"].sum(),
        "hari_operasi": g["status"].apply(lambda s: (s == "operasi").sum()),
        "hari_tercatat": g.size(),
        "penumpang": g["penumpang"].sum(),
        "kursi": g["kursi"].sum(),
    })
    df = armada.set_index("id").join(agg, how="left")
    df["biaya_per_km"] = df["biaya"] / df["km"]
    df["kerusakan_per_10rb"] = df["kerusakan"] / df["km"] * 10000
    df["km_per_liter"] = df["km"] / df["bbm"]
    df["ketersediaan"] = df["hari_operasi"] / df["hari_tercatat"] * 100
    df["load_factor"] = df["penumpang"] / df["kursi"] * 100
    df["status_unit"] = np.where(df.index.isin(keluar), "Keluar", "Aktif")
    return df.reset_index().rename(columns={"index": "id"})


def kpi(ringkasan: pd.DataFrame, batas_usia: int) -> dict:
    aktif = ringkasan[ringkasan["status_unit"] == "Aktif"]
    return {
        "armada_aktif": int(len(aktif)),
        "rata_umur": float(aktif["umur"].mean()),
        "ketersediaan": float(aktif["hari_operasi"].sum() / aktif["hari_tercatat"].sum() * 100),
        "biaya_per_km": float(aktif["biaya"].sum() / aktif["km"].sum()),
        "mendekati_batas": int(((aktif["umur"] >= batas_usia - 5) & (aktif["umur"] <= batas_usia)).sum()),
        "lewat_batas": int((aktif["umur"] > batas_usia).sum()),
    }


def bulanan(log: pd.DataFrame) -> pd.DataFrame:
    m = log.assign(bulan=log["tanggal"].dt.to_period("M").dt.to_timestamp())
    g = m.groupby("bulan")
    out = pd.DataFrame({
        "km": g["km"].sum(),
        "biaya": g["biaya_perawatan"].sum(),
        "kerusakan": g["kerusakan"].sum(),
        "penumpang": g["penumpang"].sum(),
        "kursi": g["kursi"].sum(),
    })
    out["biaya_per_km"] = out["biaya"] / out["km"]
    out["load_factor"] = out["penumpang"] / out["kursi"] * 100
    return out.reset_index()


def bulanan_unit(log: pd.DataFrame, unit_id: str) -> pd.DataFrame:
    return bulanan(log[log["unit_id"] == unit_id])


def matriks_keputusan(ringkasan: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    aktif = ringkasan[ringkasan["status_unit"] == "Aktif"].reset_index(drop=True)
    return aktif, aktif[KOLOM_KRITERIA].to_numpy(dtype=float)
