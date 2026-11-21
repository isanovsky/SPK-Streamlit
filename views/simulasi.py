import copy
import uuid
from datetime import date

import numpy as np
import streamlit as st

from spk import keputusan, scenario
from spk import repository as repo
from spk import ui
from spk.engine import ahp

ui.kepala("Simulasi Skenario", "Tambahkan event bertanggal untuk melihat dampaknya pada data dan ranking. "
          "Data aktual tidak pernah diubah.")

p = repo.parameter()
armada = repo.armada()
awal = date.fromisoformat(p["periode"]["mulai"])
akhir = date.fromisoformat(p["periode"]["selesai"])
unit_ids = armada.id.tolist()
trayek = repo.trayek()
nama_trayek = dict(zip(trayek.id, trayek.nama))

PENGALI = [round(1 + i / 10, 1) for i in range(41)]
PENGALI_TURUN = [round(i / 20, 2) for i in range(2, 21)]


def kali(x):
    return f"{ui.angka(x, 2 if x * 10 % 1 else 1)}×"


def teks_parameter(k, v):
    if k == "pengali":
        return f"pengali {kali(v)}"
    if k == "persen":
        return f"+{ui.angka(v)}%"
    if k == "biaya":
        return f"biaya {ui.rp_singkat(v)}"
    if k == "hari_henti":
        return f"henti {v} hari"
    return f"{k} {v}"


if "sk_kerja" not in st.session_state:
    aktif = repo.skenario_aktif()
    st.session_state["sk_kerja"] = copy.deepcopy(aktif) if aktif else {"nama": "Skenario baru", "events": []}
kerja = st.session_state["sk_kerja"]

# ---------- daftar skenario ----------
daftar = repo.daftar_skenario()
with st.container(border=True):
    a, b, c, d = st.columns([2.4, 1, 1, 1], vertical_alignment="bottom")
    pilihan = {s["id"]: s["nama"] for s in daftar}
    sid = a.selectbox("Skenario tersimpan", [None, *pilihan], index=0 if kerja.get("id") not in pilihan
                      else [None, *pilihan].index(kerja["id"]),
                      format_func=lambda x: "Pilih skenario..." if x is None else pilihan[x])
    if b.button("Buka", width="stretch", disabled=sid is None):
        st.session_state["sk_kerja"] = copy.deepcopy(repo.skenario(sid))
        st.rerun()
    if c.button("Skenario baru", width="stretch"):
        st.session_state["sk_kerja"] = {"nama": "Skenario baru", "events": []}
        st.rerun()
    if d.button("Hapus", width="stretch", disabled=sid is None):
        repo.hapus_skenario(sid)
        if kerja.get("id") == sid:
            st.session_state["sk_kerja"] = {"nama": "Skenario baru", "events": []}
        st.rerun()

kiri, kanan = st.columns([1, 1.25], gap="large")

# ---------- editor ----------
with kiri:
    kerja["nama"] = st.text_input("Nama skenario", value=kerja["nama"], max_chars=60)
    st.markdown("**Tambah event**")
    jenis = st.selectbox("Jenis event", list(scenario.JENIS_EVENT), format_func=scenario.JENIS_EVENT.get)
    with st.form("form_event", clear_on_submit=False, border=True):
        prm, target, selesai = {}, [], None
        if jenis == "lonjakan_kerusakan":
            target = st.multiselect("Unit", unit_ids, default=["B05"])
            prm["pengali"] = st.select_slider("Pengali laju kerusakan", PENGALI, 2.0, format_func=kali)
        elif jenis == "gangguan_trayek":
            target = st.multiselect("Trayek", trayek.id.tolist(), default=[trayek.id.iloc[4]],
                                    format_func=lambda t: f"{t} · {nama_trayek[t]}")
            prm["pengali"] = st.select_slider("Pengali laju kerusakan unit di trayek ini", PENGALI, 1.8,
                                              format_func=kali)
        elif jenis == "kenaikan_suku_cadang":
            target = st.multiselect("Merek sasis", p["merek_sasis"], default=[p["merek_sasis"][0]])
            prm["persen"] = st.slider("Kenaikan biaya perawatan (%)", 1, 100, 25)
        elif jenis == "overhaul":
            target = [st.selectbox("Unit", unit_ids, index=unit_ids.index("B04"))]
            prm["biaya"] = st.number_input("Biaya overhaul (Rp)", 0, value=350_000_000, step=10_000_000, format="%d")
            prm["hari_henti"] = st.number_input("Lama tidak beroperasi (hari)", 1, 90, 14)
            prm["pengali"] = st.select_slider("Pengali biaya & kerusakan setelah overhaul", PENGALI_TURUN, 0.5,
                                              format_func=kali)
        elif jenis == "unit_keluar":
            target = st.multiselect("Unit", unit_ids, default=["B34"])
        elif jenis == "kenaikan_merata":
            prm["persen"] = st.slider("Kenaikan biaya perawatan semua unit (%)", 1, 100, 20)
        mulai = st.date_input("Tanggal mulai", value=date(2026, 8, 1), min_value=awal, max_value=akhir,
                              format="DD/MM/YYYY")
        if jenis not in ("overhaul", "unit_keluar"):
            pakai_selesai = st.checkbox("Ada tanggal selesai")
            selesai = st.date_input("Tanggal selesai", value=akhir, min_value=awal, max_value=akhir,
                                    format="DD/MM/YYYY", disabled=False) if pakai_selesai else None
        kirim = st.form_submit_button("Tambah event", type="primary")
    if kirim:
        if jenis != "kenaikan_merata" and not target:
            st.error("Pilih minimal satu target.")
        elif selesai and selesai < mulai:
            st.error("Tanggal selesai harus setelah tanggal mulai.")
        else:
            kerja["events"].append({"id": uuid.uuid4().hex[:8], "jenis": jenis, "target": list(target),
                                    "parameter": prm, "mulai": mulai.isoformat(),
                                    "selesai": selesai.isoformat() if selesai else None})
            st.rerun()

    st.markdown(f"**Event dalam skenario** ({len(kerja['events'])})")
    if not kerja["events"]:
        st.caption("Belum ada event.")
    for i, e in enumerate(scenario.urutkan(kerja["events"])):
        with st.container(border=True):
            x, y = st.columns([5, 1], vertical_alignment="center")
            tgt = "semua unit" if e["jenis"] == "kenaikan_merata" else ", ".join(
                nama_trayek.get(t, t) for t in e["target"])
            prm_txt = ", ".join(teks_parameter(k, v) for k, v in e.get("parameter", {}).items())
            rentang = ui.tanggal(date.fromisoformat(e["mulai"])) + (
                f" – {ui.tanggal(date.fromisoformat(e['selesai']))}" if e.get("selesai") else " dst.")
            x.markdown(f"**{scenario.JENIS_EVENT[e['jenis']]}**  \n{tgt} · {prm_txt}  \n"
                       f":gray[{rentang} · {scenario.hari_terdampak(e, p)} hari terdampak dari 365]")
            if y.button("", icon=":material/delete:", key=f"hapus_{e['id']}", help="Hapus event ini"):
                kerja["events"] = [z for z in kerja["events"] if z["id"] != e["id"]]
                st.rerun()

    s1, s2 = st.columns(2)
    if s1.button("Simpan skenario", width="stretch", disabled=not kerja["events"]):
        kerja["id"] = repo.simpan_skenario(kerja)
        st.toast("Skenario disimpan.")
        st.rerun()
    sedang_aktif = repo.skenario_aktif() is not None and repo.skenario_aktif().get("id") == kerja.get("id")
    if s2.button("Simpan & aktifkan" if not sedang_aktif else "Simpan perubahan (aktif)", type="primary",
                 width="stretch", disabled=not kerja["events"]):
        kerja["id"] = repo.simpan_skenario(kerja)
        repo.set_skenario_aktif(kerja["id"])
        st.rerun()

# ---------- pratinjau ----------
with kanan:
    st.markdown("**Pratinjau dampak pada ranking**")
    if not kerja["events"]:
        st.caption("Tambahkan event untuk melihat pratinjau.")
    else:
        w = ahp(repo.matriks_ahp()).bobot
        r0, _ = keputusan.ranking(repo.ringkasan_untuk([]), w)
        r1, _ = keputusan.ranking(repo.ringkasan_untuk(kerja["events"]), w)
        bd = keputusan.bandingkan(r0, r1)
        geser = int((bd.gerak.fillna(0) != 0).sum())
        keluar = int(bd.peringkat_skenario.isna().sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Unit berpindah peringkat", ui.angka(geser))
        m2.metric("Selisih skor terbesar", ui.angka(np.nanmax(np.abs(bd.selisih_skor)) if bd.selisih_skor.notna().any() else 0, 4))
        m3.metric("Unit keluar", ui.angka(keluar))
        if np.nanmax(np.abs(bd.selisih_skor.fillna(0))) < 1e-9 and keluar == 0:
            st.info("Skor tidak berubah. Kenaikan yang merata pada satu kriteria tidak memengaruhi TOPSIS, "
                    "karena normalisasi vektor membagi setiap kolom dengan panjangnya: perkalian yang sama "
                    "untuk semua unit saling meniadakan.", icon=":material/info:")
        bd["status"] = np.where(bd.peringkat_skenario.isna(), "Keluar",
                                np.where(bd.gerak > 0, "Naik", np.where(bd.gerak < 0, "Turun", "")))

        status = dict(zip(bd.id, bd.status))

        def sorot(row):
            warna = {"Naik": "background-color:#FBEBDD", "Turun": "background-color:#E4EEF0",
                     "Keluar": "color:#8A94A0"}.get(status[row.id], "")
            return [warna] * len(row)

        ui.tabel(
            bd[["id", "peringkat_aktual", "peringkat_skenario", "gerak", "skor_aktual", "skor_skenario",
                "selisih_skor"]],
            {"peringkat_aktual": ui.fmt(0), "peringkat_skenario": ui.fmt(0), "gerak": ui.fmt_gerak,
             "skor_aktual": ui.fmt(4), "skor_skenario": ui.fmt(4),
             "selisih_skor": lambda x: "–" if x != x else (("+" if x > 0 else "") + ui.angka(x, 4))},
            gaya=sorot, hide_index=True, width="stretch", height=520, column_config={
                "id": st.column_config.TextColumn("Unit", width="small"),
                "peringkat_aktual": "Pk. aktual",
                "peringkat_skenario": "Pk. skenario",
                "gerak": "Gerak",
                "skor_aktual": "Cᵢ aktual",
                "skor_skenario": "Cᵢ skenario",
                "selisih_skor": "Selisih",
            })
        st.caption("Baris oranye: naik peringkat (makin mendesak). Baris biru: turun peringkat. "
                   "TOPSIS memakai agregat 12 bulan, jadi event yang dimulai di akhir periode hanya "
                   "memengaruhi sebagian data. Lihat jumlah hari terdampak pada setiap event.")

ui.kaki()
