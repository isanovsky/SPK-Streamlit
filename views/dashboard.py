import streamlit as st

from spk import charts, metrics, scenario
from spk import repository as repo
from spk import ui

ui.kepala("Dashboard Armada", "Kondisi armada 12 bulan terakhir sebagai dasar keputusan peremajaan.")

batas = repo.batas_usia()
r = repo.ringkasan()
k = metrics.kpi(r, batas)
aktif = repo.skenario_aktif()
k0 = metrics.kpi(repo.ringkasan_aktual(), batas) if aktif else None


def delta(kunci, fmt, kebalikan=False):
    if not k0:
        return None
    d = k[kunci] - k0[kunci]
    return None if abs(d) < 1e-9 else fmt(d)


c = st.columns(3) + st.columns(3)
c[0].metric("Armada aktif", ui.angka(k["armada_aktif"]), delta(
    "armada_aktif", lambda d: ui.angka(d)))
c[1].metric("Rata-rata umur", f'{ui.angka(k["rata_umur"], 1)} th',
            delta("rata_umur", lambda d: ui.angka(d, 1)), delta_color="inverse")
c[2].metric("Ketersediaan", ui.persen(k["ketersediaan"]),
            delta("ketersediaan", lambda d: f"{ui.angka(d, 2)} poin"))
c[3].metric("Biaya perawatan", f'{ui.rp(k["biaya_per_km"])}/km',
            delta("biaya_per_km", lambda d: ui.rp(d)), delta_color="inverse")
c[4].metric("Mendekati batas usia", ui.angka(k["mendekati_batas"]),
            delta("mendekati_batas", lambda d: ui.angka(d)), delta_color="inverse",
            help=f"Umur {batas - 5}–{batas} tahun")
c[5].metric("Melewati batas usia", ui.angka(k["lewat_batas"]),
            delta("lewat_batas", lambda d: ui.angka(d)), delta_color="inverse",
            help=f"Umur di atas {batas} tahun: wajib diremajakan")

b_aktual = metrics.bulanan(repo.log_aktual())
if aktif:
    p = repo.parameter()
    tanda = [(e["mulai"], scenario.JENIS_EVENT[e["jenis"]].split(" (")[0]) for e in aktif["events"]
             if e["mulai"] >= p["periode"]["mulai"]]
    fig = charts.tren_biaya(b_aktual, metrics.bulanan(repo.log()), tanda)
else:
    fig = charts.tren_biaya(b_aktual)

kiri, kanan = st.columns([3, 2])
with kiri:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with kanan:
    st.plotly_chart(charts.sebaran_umur(r[r.status_unit == "Aktif"], batas), width="stretch",
                    config={"displayModeBar": False})

kiri, kanan = st.columns([3, 2])
with kiri:
    st.plotly_chart(charts.umur_vs_kerusakan(r[r.status_unit == "Aktif"]), width="stretch",
                    config={"displayModeBar": False})
with kanan:
    with st.container(border=True):
        st.markdown("**Perlu perhatian**")
        perhatian = r[(r.status_unit == "Aktif") & ((r.anomali != "") | (r.umur > batas))]
        for _, u in perhatian.sort_values("umur", ascending=False).iterrows():
            label = f"Anomali simulasi: {u.anomali}" if u.anomali else f"Melewati batas usia {batas} tahun"
            st.markdown(f"**{u.id}** · {u.kelas.title()} · {u.umur} th  \n"
                        f":gray[{label} · {ui.angka(u.kerusakan_per_10rb, 2)} kerusakan/10.000 km · "
                        f"{ui.rp(u.biaya_per_km)}/km]")
        st.page_link("views/topsis.py", label="Lihat ranking prioritas", icon=":material/arrow_forward:")

ui.kaki()
