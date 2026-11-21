import streamlit as st

from spk import charts, metrics, scenario
from spk import repository as repo
from spk import ui

ui.kepala("Data Armada", "Nilai kriteria C1–C5 per unit, dihitung dari log harian 12 bulan.")

batas = repo.batas_usia()
r = repo.ringkasan().merge(repo.trayek()[["id", "nama"]].rename(columns={"id": "trayek_id", "nama": "trayek"}),
                           on="trayek_id", how="left")
terdampak = set()
for e in repo.events_aktif():
    terdampak |= set(scenario.unit_terdampak(e, repo.armada()))

f1, f2, f3, f4 = st.columns([1.2, 1.6, 1.2, 1.6])
kelas = f1.multiselect("Kelas", sorted(r.kelas.unique()), placeholder="Semua kelas")
trayek = f2.multiselect("Trayek", sorted(r.trayek.unique()), placeholder="Semua trayek")
merek = f3.multiselect("Merek sasis", sorted(r.merek_sasis.unique()), placeholder="Semua merek")
cari = f4.text_input("Cari ID unit", placeholder="mis. B05")

d = r.copy()
if kelas:
    d = d[d.kelas.isin(kelas)]
if trayek:
    d = d[d.trayek.isin(trayek)]
if merek:
    d = d[d.merek_sasis.isin(merek)]
if cari:
    d = d[d.id.str.contains(cari.strip(), case=False)]


def status(u):
    tanda = []
    if u.status_unit == "Keluar":
        tanda.append("Keluar")
    if u.umur > batas:
        tanda.append("Lewat batas usia")
    if u.id in terdampak and u.status_unit != "Keluar":
        tanda.append("Terdampak skenario")
    return " · ".join(tanda)


d["status"] = d.apply(status, axis=1)
tabel = d[["id", "kelas", "trayek", "merek_sasis", "umur", "biaya_per_km", "kerusakan_per_10rb",
           "km_per_liter", "ketersediaan", "km", "status"]].sort_values("id")

st.caption(f"{len(tabel)} dari {len(r)} unit")
pilih = ui.tabel(
    tabel, {"umur": ui.fmt(0), "biaya_per_km": ui.fmt(0), "kerusakan_per_10rb": ui.fmt(2),
            "km_per_liter": ui.fmt(2), "ketersediaan": ui.fmt(1), "km": ui.fmt(0)},
    hide_index=True, width="stretch", height=430, on_select="rerun", selection_mode="single-row",
    column_config={
        "id": st.column_config.TextColumn("ID", width="small"),
        "kelas": st.column_config.TextColumn("Kelas"),
        "trayek": st.column_config.TextColumn("Trayek"),
        "merek_sasis": st.column_config.TextColumn("Merek sasis"),
        "umur": "C1 Umur (th)",
        "biaya_per_km": "C2 Biaya (Rp/km)",
        "kerusakan_per_10rb": "C3 Kerusakan /10rb km",
        "km_per_liter": "C4 BBM (km/l)",
        "ketersediaan": "C5 Ketersediaan (%)",
        "km": "Km tempuh",
        "status": st.column_config.TextColumn("Status"),
    },
)

baris = pilih.selection.rows
if baris:
    u = tabel.iloc[baris[0]]
    full = r[r.id == u.id].iloc[0]
    st.subheader(f"Detail unit {u.id}")
    a, b, c, e = st.columns(4)
    a.metric("Tahun pembuatan", str(full.tahun))
    b.metric("Kapasitas", f"{full.kapasitas} kursi")
    c.metric("Load factor", ui.persen(full.load_factor))
    e.metric("Hari operasi", f"{ui.angka(full.hari_operasi)} / {ui.angka(full.hari_tercatat)}")
    if full.anomali:
        st.info(f"Anomali simulasi: {full.anomali}. Unit ini sengaja dibuat berbeda oleh generator "
                "agar ranking tidak sekadar mengikuti umur.", icon=":material/info:")
    st.plotly_chart(charts.bulanan_unit(metrics.bulanan_unit(repo.log(), u.id)), width="stretch",
                    config={"displayModeBar": False})
else:
    st.caption("Pilih satu baris untuk melihat detail unit.")

ui.kaki()
