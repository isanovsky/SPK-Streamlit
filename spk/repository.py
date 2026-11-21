"""Satu-satunya pintu akses data untuk halaman Streamlit.

Data dasar dibangkitkan dari parameter.json (seed 42) dan tidak pernah ditulis.
State pengguna (penilaian AHP, skenario, riwayat) disimpan di data/state.json.
"""
from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from . import metrics, scenario
from .generator import bangkitkan_semua, muat_parameter

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"

MATRIKS_AWAL = [[1, 1/2, 1/3, 2, 1], [2, 1, 1/2, 3, 2], [3, 2, 1, 4, 3],
                [1/2, 1/3, 1/4, 1, 1/2], [1, 1/2, 1/3, 2, 1]]

STATE_AWAL = {
    "penilaian": {"penilai_id": "P01", "nama": "Manajer Armada", "matriks": MATRIKS_AWAL,
                  "diperbarui": None},
    "skenario": [],
    "skenario_aktif": None,
    "riwayat": [],
}


@st.cache_data(show_spinner="Membangkitkan data simulasi...")
def _data_dasar():
    p = muat_parameter()
    armada, trayek, log = bangkitkan_semua(p)
    return p, armada, trayek, log


@st.cache_data(show_spinner="Menghitung skenario...")
def _log_skenario(events_json: str) -> pd.DataFrame:
    p, armada, _, log = _data_dasar()
    return scenario.terapkan(json.loads(events_json), armada, log, p)


def parameter() -> dict:
    return _data_dasar()[0]


def armada() -> pd.DataFrame:
    return _data_dasar()[1]


def trayek() -> pd.DataFrame:
    return _data_dasar()[2]


def batas_usia() -> int:
    return int(parameter()["batas_usia_regulasi"]["nilai"])


# ---------- state ----------
def _baca_state() -> dict:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return {**copy.deepcopy(STATE_AWAL), **data}
        except (json.JSONDecodeError, OSError):
            pass
    return copy.deepcopy(STATE_AWAL)


def state() -> dict:
    if "_state" not in st.session_state:
        st.session_state["_state"] = _baca_state()
    return st.session_state["_state"]


def _simpan():
    STATE_PATH.write_text(json.dumps(state(), ensure_ascii=False, indent=2), encoding="utf-8")


def ekspor_state() -> str:
    return json.dumps(state(), ensure_ascii=False, indent=2)


def impor_state(teks: str) -> None:
    data = json.loads(teks)
    if not isinstance(data, dict) or "penilaian" not in data:
        raise ValueError("Berkas bukan ekspor dari aplikasi ini.")
    st.session_state["_state"] = {**copy.deepcopy(STATE_AWAL), **data}
    _simpan()


def reset_state() -> None:
    st.session_state["_state"] = copy.deepcopy(STATE_AWAL)
    _simpan()


# ---------- penilaian AHP ----------
def matriks_ahp() -> np.ndarray:
    return np.array(state()["penilaian"]["matriks"], dtype=float)


def simpan_matriks_ahp(m: np.ndarray) -> None:
    state()["penilaian"]["matriks"] = m.tolist()
    state()["penilaian"]["diperbarui"] = datetime.now().isoformat(timespec="seconds")
    _simpan()


# ---------- skenario ----------
def daftar_skenario() -> list[dict]:
    return state()["skenario"]


def skenario(sid: str) -> dict | None:
    return next((s for s in daftar_skenario() if s["id"] == sid), None)


def simpan_skenario(s: dict) -> str:
    s = copy.deepcopy(s)
    s.setdefault("id", uuid.uuid4().hex[:8])
    s["diperbarui"] = datetime.now().isoformat(timespec="seconds")
    lst = daftar_skenario()
    idx = next((i for i, x in enumerate(lst) if x["id"] == s["id"]), None)
    if idx is None:
        lst.append(s)
    else:
        lst[idx] = s
    _simpan()
    return s["id"]


def hapus_skenario(sid: str) -> None:
    state()["skenario"] = [s for s in daftar_skenario() if s["id"] != sid]
    if state()["skenario_aktif"] == sid:
        state()["skenario_aktif"] = None
    _simpan()


def set_skenario_aktif(sid: str | None) -> None:
    state()["skenario_aktif"] = sid
    _simpan()


def skenario_aktif() -> dict | None:
    sid = state()["skenario_aktif"]
    return skenario(sid) if sid else None


def events_aktif() -> list[dict]:
    s = skenario_aktif()
    return s["events"] if s else []


# ---------- data turunan (otomatis mengikuti skenario aktif) ----------
def log_untuk(events: list[dict]) -> pd.DataFrame:
    if not events:
        return _data_dasar()[3]
    return _log_skenario(json.dumps(events, sort_keys=True))


def ringkasan_untuk(events: list[dict]) -> pd.DataFrame:
    return metrics.ringkasan_armada(armada(), log_untuk(events), scenario.unit_keluar(events))


def log() -> pd.DataFrame:
    return log_untuk(events_aktif())


def log_aktual() -> pd.DataFrame:
    return log_untuk([])


def ringkasan() -> pd.DataFrame:
    return ringkasan_untuk(events_aktif())


def ringkasan_aktual() -> pd.DataFrame:
    return ringkasan_untuk([])


# ---------- riwayat ----------
def riwayat() -> list[dict]:
    return state()["riwayat"]


def simpan_keputusan(k: dict) -> None:
    k = {**k, "id": uuid.uuid4().hex[:8], "waktu": datetime.now().isoformat(timespec="seconds")}
    state()["riwayat"].insert(0, k)
    _simpan()


def hapus_keputusan(kid: str) -> None:
    state()["riwayat"] = [k for k in riwayat() if k["id"] != kid]
    _simpan()
