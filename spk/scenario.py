"""Skenario: daftar event bertanggal yang diterjemahkan menjadi Modifier per unit,
lalu unit terdampak disimulasikan ulang. Data aktual tidak pernah diubah."""
from __future__ import annotations

from datetime import date

import pandas as pd

from .generator import Modifier, rentang_tanggal, simulasikan_unit

JENIS_EVENT = {
    "lonjakan_kerusakan": "Lonjakan kerusakan unit",
    "gangguan_trayek": "Gangguan trayek",
    "kenaikan_suku_cadang": "Kenaikan harga suku cadang (per merek sasis)",
    "overhaul": "Overhaul unit",
    "unit_keluar": "Unit keluar (dijual/dipensiunkan)",
    "kenaikan_merata": "Kenaikan biaya perawatan merata",
}


def _tgl(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def unit_terdampak(event: dict, armada: pd.DataFrame) -> list[str]:
    j, t = event["jenis"], event.get("target", [])
    if j in ("lonjakan_kerusakan", "overhaul", "unit_keluar"):
        return [u for u in t if u in set(armada["id"])]
    if j == "gangguan_trayek":
        return armada.loc[armada["trayek_id"].isin(t), "id"].tolist()
    if j == "kenaikan_suku_cadang":
        return armada.loc[armada["merek_sasis"].isin(t), "id"].tolist()
    if j == "kenaikan_merata":
        return armada["id"].tolist()
    raise ValueError(f"Jenis event tidak dikenal: {j}")


def ke_modifier(event: dict) -> Modifier:
    j, prm = event["jenis"], event.get("parameter", {})
    m = Modifier(mulai=_tgl(event["mulai"]), selesai=_tgl(event.get("selesai")), event_id=event["id"])
    if j in ("lonjakan_kerusakan", "gangguan_trayek"):
        m.pengali_kerusakan = float(prm.get("pengali", 2.0))
    elif j in ("kenaikan_suku_cadang", "kenaikan_merata"):
        m.pengali_biaya = 1 + float(prm.get("persen", 10)) / 100
    elif j == "overhaul":
        m.selesai = None
        m.overhaul_biaya = float(prm.get("biaya", 350_000_000))
        m.overhaul_hari = int(prm.get("hari_henti", 14))
        m.pengali_biaya = float(prm.get("pengali", 0.5))
        m.pengali_kerusakan = float(prm.get("pengali", 0.5))
    elif j == "unit_keluar":
        m.selesai = None
        m.nonaktif = True
    return m


def urutkan(events: list[dict]) -> list[dict]:
    return [e for _, e in sorted(enumerate(events), key=lambda x: (x[1]["mulai"], x[0]))]


def terapkan(events: list[dict], armada: pd.DataFrame, log_aktual: pd.DataFrame,
             p: dict) -> pd.DataFrame:
    """Kembalikan log baru. Input tidak dimutasi; unit tanpa event memakai log aktual."""
    if not events:
        return log_aktual
    per_unit: dict[str, list[Modifier]] = {}
    for ev in urutkan(events):
        m = ke_modifier(ev)
        for u in unit_terdampak(ev, armada):
            per_unit.setdefault(u, []).append(m)
    tanggal = rentang_tanggal(p)
    nomor = {uid: i for i, uid in enumerate(armada["id"])}
    baru = []
    for uid, mods in per_unit.items():
        unit = armada.loc[armada["id"] == uid].iloc[0]
        baru.append(simulasikan_unit(unit, nomor[uid], p, tanggal, mods))
    tetap = log_aktual[~log_aktual["unit_id"].isin(per_unit)]
    hasil = pd.concat([tetap, *[b for b in baru if not b.empty]], ignore_index=True)
    hasil["tanggal"] = pd.to_datetime(hasil["tanggal"])
    return hasil.sort_values(["unit_id", "tanggal"], ignore_index=True)


def unit_keluar(events: list[dict]) -> set[str]:
    return {u for e in events if e["jenis"] == "unit_keluar" for u in e.get("target", [])}


def hari_terdampak(event: dict, p: dict) -> int:
    awal = date.fromisoformat(p["periode"]["mulai"])
    akhir = date.fromisoformat(p["periode"]["selesai"])
    mulai = max(_tgl(event["mulai"]), awal)
    selesai = akhir if event["jenis"] in ("overhaul", "unit_keluar") or not event.get("selesai") \
        else min(_tgl(event["selesai"]), akhir)
    return max((selesai - mulai).days + 1, 0)
