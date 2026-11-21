import streamlit as st

st.set_page_config(page_title="SPK Peremajaan Armada", page_icon=":material/directions_bus:",
                   layout="wide", initial_sidebar_state="auto")

halaman = {
    "Ringkasan": [
        st.Page("views/dashboard.py", title="Dashboard", icon=":material/space_dashboard:", default=True),
        st.Page("views/armada.py", title="Data Armada", icon=":material/directions_bus:"),
    ],
    "Keputusan": [
        st.Page("views/ahp.py", title="Pembobotan AHP", icon=":material/balance:"),
        st.Page("views/topsis.py", title="Hasil TOPSIS", icon=":material/format_list_numbered:"),
        st.Page("views/rekomendasi.py", title="Rekomendasi", icon=":material/task_alt:"),
        st.Page("views/simulasi.py", title="Simulasi Skenario", icon=":material/science:"),
        st.Page("views/riwayat.py", title="Riwayat Keputusan", icon=":material/history:"),
    ],
    "Informasi": [
        st.Page("views/tentang.py", title="Tentang Sistem", icon=":material/info:"),
    ],
}

with st.sidebar:
    st.markdown("**SPK Peremajaan Armada**  \nPO Bus AKAP · AHP–TOPSIS")

st.navigation(halaman).run()
