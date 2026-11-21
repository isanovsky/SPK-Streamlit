"""Generator data simulasi ber-seed.

Setiap unit punya aliran acak sendiri (SeedSequence [seed, nomor_unit]) dan setiap hari
mengambil jumlah angka acak yang sama, apa pun status unitnya. Akibatnya, mengubah satu unit
(misalnya lewat skenario) tidak menggeser angka acak unit lain, dan hari-hari sebelum sebuah
event tetap identik dengan data aktual.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PARAM_PATH = Path(__file__).resolve().parent.parent / "data" / "parameter.json"


def muat_parameter(path: Path = PARAM_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rentang_tanggal(p: dict) -> list[date]:
    mulai = date.fromisoformat(p["periode"]["mulai"])
    selesai = date.fromisoformat(p["periode"]["selesai"])
    return [mulai + timedelta(days=i) for i in range((selesai - mulai).days + 1)]


def poisson_ppf(u: float, lam: float) -> int:
    """Invers CDF Poisson; monoton terhadap lam untuk u yang sama."""
    if lam <= 0:
        return 0
    k, p = 0, math.exp(-lam)
    c = p
    while u > c and k < 50:
        k += 1
        p *= lam / k
        c += p
    return k


def bangkitkan_armada(p: dict) -> pd.DataFrame:
    rng = np.random.default_rng(p["seed"])
    n = p["jumlah_armada"]
    kelas_nama = list(p["kelas"])
    proporsi = np.array([p["kelas"][k]["proporsi"] for k in kelas_nama])
    kelas = rng.choice(kelas_nama, size=n, p=proporsi / proporsi.sum())
    tahun = rng.integers(p["tahun_pembuatan"]["min"], p["tahun_pembuatan"]["maks"] + 1, size=n)
    trayek_ids = [t["id"] for t in p["trayek"]]
    trayek = [trayek_ids[i % len(trayek_ids)] for i in rng.permutation(n)]

    rng_merek = np.random.default_rng(p["seed"] + 1000)
    merek = rng_merek.choice(p["merek_sasis"], size=n)

    df = pd.DataFrame({
        "id": [f"B{i + 1:02d}" for i in range(n)],
        "kelas": kelas,
        "kapasitas": [p["kelas"][k]["kapasitas"] for k in kelas],
        "tahun": tahun,
        "merek_sasis": merek,
        "trayek_id": trayek,
        "faktor_kerusakan": 1.0,
        "faktor_biaya": 1.0,
        "anomali": "",
    })

    tahun_acuan = p["periode"]["tahun_acuan_umur"]
    an = p["anomali"]
    lewat = an["unit_lewat_batas"]
    idx_tua = df.sort_values("tahun").index[: lewat["jumlah"]]
    df.loc[idx_tua, "tahun"] = lewat["tahun_pembuatan"]
    df.loc[idx_tua, "anomali"] = "Melewati batas usia regulasi"

    df["umur"] = tahun_acuan - df["tahun"]

    muda = an["unit_muda_rawan"]
    calon = df[(df["umur"] <= muda["umur_maks"]) & (df["anomali"] == "")].index
    idx_muda = calon[: muda["jumlah"]]
    df.loc[idx_muda, "faktor_kerusakan"] = muda["pengali_kerusakan"]
    df.loc[idx_muda, "anomali"] = "Unit muda rawan rusak"

    ov = an["unit_tua_overhaul"]
    calon = df[(df["umur"] >= ov["umur_min"]) & (df["anomali"] == "")].index
    idx_ov = calon[: ov["jumlah"]]
    df.loc[idx_ov, "faktor_biaya"] = ov["pengali_biaya"]
    df.loc[idx_ov, "faktor_kerusakan"] = ov["pengali_kerusakan"]
    df.loc[idx_ov, "anomali"] = "Unit tua baru di-overhaul"
    return df


@dataclass
class Modifier:
    """Perubahan pada satu unit untuk rentang tanggal tertentu (hasil terjemahan event)."""
    mulai: date
    selesai: date | None = None
    pengali_kerusakan: float = 1.0
    pengali_biaya: float = 1.0
    nonaktif: bool = False
    overhaul_biaya: float = 0.0
    overhaul_hari: int = 0
    event_id: str = ""

    def aktif_pada(self, d: date) -> bool:
        return d >= self.mulai and (self.selesai is None or d <= self.selesai)


@dataclass
class _Status:
    henti: int = 0
    status_henti: str = "rusak"
    km_sejak_servis: float = 0.0


def simulasikan_unit(unit: pd.Series, nomor: int, p: dict, tanggal: list[date],
                     modifiers: list[Modifier] | None = None) -> pd.DataFrame:
    modifiers = modifiers or []
    rng = np.random.default_rng([p["seed"], nomor])
    tr = next(t for t in p["trayek"] if t["id"] == unit["trayek_id"])
    jarak = tr["jarak_km"]
    trip = 2 if jarak <= p["trip_per_hari"]["jarak_maks_dua_trip_km"] else 1
    musim = p["musiman_load_factor"]["nilai"]
    kr, pr, bb = p["kerusakan"], p["perawatan"], p["bbm"]
    umur = float(unit["umur"])
    laju_dasar = kr["lambda0_per_10rb_km"] * math.exp(kr["k_umur"] * umur) * unit["faktor_kerusakan"]
    biaya_dasar = pr["b0_rp_per_km"] * math.exp(pr["k_umur"] * umur) * unit["faktor_biaya"]
    kpl_dasar = bb["e0_km_per_liter"] - bb["penurunan_per_tahun"] * umur
    sigma = pr["sigma_lognormal"]
    st = _Status()
    baris = []

    for d in tanggal:
        u_rusak, u_henti = rng.random(), rng.random()
        z_biaya, z_bbm, z_lf = rng.standard_normal(3)

        aktif = [m for m in modifiers if m.aktif_pada(d)]
        if any(m.nonaktif for m in aktif):
            continue
        pk = math.prod(m.pengali_kerusakan for m in aktif)
        pb = math.prod(m.pengali_biaya for m in aktif)
        biaya_hari = 0.0
        for m in modifiers:
            if m.overhaul_hari and m.mulai == d:
                biaya_hari += m.overhaul_biaya
                st.henti, st.status_henti, st.km_sejak_servis = m.overhaul_hari, "overhaul", 0.0

        row = {"tanggal": d, "unit_id": unit["id"], "trip": 0, "km": 0.0, "penumpang": 0,
               "kursi": 0, "bbm_liter": 0.0, "kerusakan": 0}
        if st.henti > 0:
            st.henti -= 1
            row.update(status=st.status_henti, biaya_perawatan=biaya_hari)
            baris.append(row)
            continue
        if st.km_sejak_servis >= pr["servis_tiap_km"]:
            st.km_sejak_servis = 0.0
            row.update(status="servis", biaya_perawatan=biaya_hari + pr["biaya_servis"] * pb)
            baris.append(row)
            continue

        km = float(jarak * trip)
        lam = laju_dasar * pk * km / 10000
        kerusakan = poisson_ppf(u_rusak, lam)
        biaya = (km * biaya_dasar * pb * math.exp(sigma * z_biaya - sigma ** 2 / 2)
                 + kerusakan * kr["biaya_perbaikan_rata"] * pb + biaya_hari)
        kpl = min(max(kpl_dasar + bb["sigma"] * z_bbm, bb["min"]), bb["maks"])
        lf = min(max(tr["lf_dasar"] * musim[d.month - 1] * (1 + 0.08 * z_lf), 0.15), 1.0)
        kursi = int(unit["kapasitas"]) * trip
        row.update(status="operasi", trip=trip, km=km, kursi=kursi, penumpang=round(kursi * lf),
                   bbm_liter=km / kpl, kerusakan=kerusakan, biaya_perawatan=biaya)
        baris.append(row)
        st.km_sejak_servis += km
        if kerusakan > 0:
            rentang = kr["hari_henti_maks"] - kr["hari_henti_min"] + 1
            st.henti = kr["hari_henti_min"] + int(u_henti * rentang) + (kerusakan - 1)
            st.status_henti = "rusak"
    return pd.DataFrame(baris)


def bangkitkan_log(armada: pd.DataFrame, p: dict,
                   modifiers_per_unit: dict[str, list[Modifier]] | None = None) -> pd.DataFrame:
    tanggal = rentang_tanggal(p)
    modifiers_per_unit = modifiers_per_unit or {}
    frames = [simulasikan_unit(u, i, p, tanggal, modifiers_per_unit.get(u["id"]))
              for i, (_, u) in enumerate(armada.iterrows())]
    log = pd.concat(frames, ignore_index=True)
    log["tanggal"] = pd.to_datetime(log["tanggal"])
    return log


def bangkitkan_semua(p: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p = p or muat_parameter()
    armada = bangkitkan_armada(p)
    trayek = pd.DataFrame(p["trayek"])
    log = bangkitkan_log(armada, p)
    return armada, trayek, log
