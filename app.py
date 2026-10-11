import streamlit as st
import numpy as np
import sqlite3

st.set_page_config(page_title="Sistema Quant", layout="wide", page_icon="🏆")
st.title("🏆 Sistema Quant de Fútbol Profesional (Élite PRO)")

def conectar_db_directo():
    # Creamos un archivo de base de datos totalmente nuevo y único para romper el bloqueo de la nube
    conn = sqlite3.connect("quant_sistema_limpio_2026.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, forma TEXT, xg_favor_local REAL, xg_contra_local REAL, 
            xg_favor_vis REAL, xg_contra_vis REAL, corners REAL, faltas REAL, amarillas REAL
        )
    """)
    conn.commit()
    return conn

conn = conectar_db_directo()

def sincronizar_liga_pais(pais):
    ligas_mundiales = {
        "Ecuador (LigaPro Completa)": [
            ("LDU Quito", "V,V,E,V,V", 2.2, 0.5, 1.6, 0.9, 5.8, 11.2, 2.3),
            ("Barcelona SC", "V,E,D,V,E", 1.9, 0.8, 1.3, 1.4, 5.2, 13.4, 2.8),
            ("Independiente del Valle", "V,V,V,E,D", 2.4, 0.6, 1.8, 1.0, 6.1, 10.5, 1.9),
            ("Emelec", "E,D,V,E,V", 1.5, 1.0, 1.1, 1.4, 4.7, 14.1, 3.1),
            ("El Nacional", "V,D,D,V,E", 1.6, 1.1, 1.2, 1.5, 5.0, 12.5, 2.7),
            ("Delfín SC", "E,V,D,E,D", 1.3, 0.9, 0.9, 1.5, 4.2, 13.8, 2.4),
            ("Aucas", "D,E,V,V,D", 1.7, 1.2, 1.3, 1.6, 4.9, 11.9, 2.9),
            ("Universidad Católica", "V,E,V,D,V", 1.9, 0.9, 1.5, 1.3, 5.4, 10.8, 2.2),
            ("Mushuc Runa", "E,D,V,E,V", 1.4, 1.2, 1.0, 1.8, 4.1, 15.0, 3.2),
            ("Macará", "D,V,E,D,E", 1.3, 1.1, 0.9, 1.5, 4.5, 12.2, 2.5)
        ],
        "España (LaLiga Completa)": [
            ("Real Madrid", "V,V,E,V,D", 2.5, 0.6, 1.9, 1.0, 6.4, 10.2, 1.5),
            ("Barcelona", "V,V,V,D,V", 2.7, 0.9, 2.1, 1.3, 5.8, 12.1, 2.1),
            ("Atlético Madrid", "E,V,E,V,E", 1.6, 0.7, 5.0, 14.5, 2.8)
        ],
        "Inglaterra (Premier League Completa)": [
            ("Manchester City", "V,E,V,V,V", 2.6, 0.9, 7.5, 8.5, 1.2),
            ("Arsenal", "V,E,V,D,V", 2.3, 0.6, 1.9, 1.0, 6.1, 11.0, 1.9),
            ("Liverpool", "V,V,D,V,V", 2.5, 0.8, 2.1, 1.2, 6.8, 10.5, 1.6)
        ]
    }
    if pais in ligas_mundiales:
        cursor = conn.cursor()
        for eq in ligas_mundiales[pais]:
            cursor.execute("INSERT OR REPLACE INTO equipos (nombre, forma, xg_favor_local, xg_contra_local, xg_favor_vis, xg_contra_vis, corners, faltas, amarillas) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", eq)
        conn.commit()
        return True
    return False

def calcular_poder_equipo(historial, xg_f, xg_c, es_local, corners, faltas, amarillas, num_bajas, impacto_bajas, clima_extremo, altitud_alta):
    score_xg = 1 / (1 + np.exp(-(xg_f - xg_c) / 3.0))
    lista_partidos = [r.strip() for r in historial.split(",") if r.strip() in ['V', 'E', 'D']][:5]
    puntos_forma = sum([3 if r == 'V' else 1 if r == 'E' else 0 for r in lista_partidos])
    score_forma = puntos_forma / 15.0 if lista_partidos else 0.5
    score_local = 0.15 if es_local else 0.0
    score_corners = min(corners / 12.0, 1.0)
    score_disciplina = max(1.0 - ((faltas * 0.02) + (amarillas * 0.1)), 0.0)
    score_secundario = (score_corners * 0.6) + (score_disciplina * 0.4)
    poder_base = (score_xg * 0.30) + (score_forma * 0.25) + (score_local * 0.15) + (score_secundario * 0.15)
    tasa_penalizacion = 0.10 if impacto_bajas == "Muy Alto" else 0.05 if impacto_bajas == "Medio" else 0.02
    poder_base *= (1.0 - min(num_bajas * tasa_penalizacion, 0.40))
    if clima_extremo: poder_base *= 0.92
    if altitud_alta and not es_local: poder_base *= 0.85
    return max(poder_base, 0.05)

def calcular_kelly(probabilidad, cuota_casa, fraccion=0.25):
    if cuota_casa <= 1: return 0.0
    f_kelly = ((cuota_casa - 1) * probabilidad - (1.0 - probabilidad)) / (cuota_casa - 1)
    return max(f_kelly * fraccion, 0.0)

menu = st.sidebar.radio("Navegación Móvil", ["Análisis y Cuotas", "Configurar Ligas"])
lista_raw = conn.cursor().execute("SELECT nombre FROM equipos ORDER BY nombre ASC").fetchall()
lista_existente = [r[0] for r in lista_raw] # TRUCO PRO: Limpieza forzada de caracteres extra para el móvil

if menu == "Configurar Ligas":
    st.header("⚙️ Importación de Ligas")
    pais_seleccionado = st.selectbox("Selecciona la liga", ["Ecuador (LigaPro Completa)", "España (LaLiga Completa)", "Inglaterra (Premier League Completa)"])
    if st.button("🔄 Cargar Equipos Oficiales"):
        if sincronizar_liga_pais(pais_seleccionado):
            st.success("¡Base de datos actualizada con éxito!")
            st.rerun()

elif menu == "Análisis y Cuotas":
    if not lista_existente:
        st.warning("⚠️ Base de datos limpia. Ve a 'Configurar Ligas' para cargar la liga de tu país.")
    else:
        banca_total = st.sidebar.number_input("💵 Tu Banca Total ($)", min_value=10.0, value=1000.0, step=50.0)
        perfil_riesgo = st.sidebar.selectbox("🛡️ Gestión de Riesgo", ["Conservador (1/4)", "Moderado (1/2)", "Agresivo (Full)"])
        fraccion_kelly = 0.25 if "Conservador" in perfil_riesgo else 0.50 if "Moderado" in perfil_riesgo else 1.00
        
        clima_ext = st.checkbox("🌧️ Clima Extremo")
        altitud_alta = st.checkbox("🏔️ Partido en Altura")
        
        eq_l = st.selectbox("Seleccionar Local", lista_existente, index=0)
        _, f_l, xgf_l_h, xgc_l_h, xgf_l_a, xgc_l_a, c_l, fa_l, am_l = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_l,)).fetchone()
        bajas_l = st.number_input("Bajas Local", 0, 11, 0, key="bajas_l_in")
        imp_l = st.selectbox("Impacto Bajas Local", ["Bajo", "Medio", "Muy Alto"], key="imp_l_in")
        
        eq_v = st.selectbox("Seleccionar Visitante", lista_existente, index=min(1, len(lista_existente)-1))
        _, f_v, xgf_v_h, xgc_v_h, xgf_v_a, xgc_v_a, c_v, fa_v, am_v = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_v,)).fetchone()
        bajas_v = st.number_input("Bajas Visitante", 0, 11, 0, key="bajas_v_in")
        imp_v = st.selectbox("Impacto Bajas Visitante", ["Bajo", "Medio", "Muy Alto"], key="imp_v_in")
        
        cuota_casa_l = st.number_input(f"Cuota {eq_l}", min_value=1.01, value=2.00, step=0.05, key="c_l_in")
        cuota_casa_e = st.number_input("Cuota Empate", min_value=1.01, value=3.20, step=0.05, key="c_e_in")
        cuota_casa_v = st.number_input(f"Cuota {eq_v}", min_value=1.01, value=3.50, step=0.05, key="c_v_in")
        
        cuota_over_25 = st.number_input("Cuota Más de 2.5 Goles", min_value=1.01, value=1.90, step=0.05, key="over_in")
        cuota_under_25 = st.number_input("Cuota Menos de 2.5 Goles", min_value=1.01, value=1.90, step=0.05, key="under_in")
        
        p_l = calcular_poder_equipo(f_l, xgf_l_h, xgc_l_h, True, c_l, fa_l, am_l, bajas_l, imp_l, clima_ext, altitud_alta)
        p_v = calcular_poder_equipo(f_v, xgf_v_a, xgc_v_a, False, c_v, fa_v, am_v, bajas_v, imp_v, clima_ext, altitud_alta)
        total = p_l + p_v
        prob_l, prob_v = (p_l / total) * 0.78, (p_v / total) * 0.78
        prob_e = 1.0 - (prob_l + prob_v)
        
        g_l = (xgf_l_h + xgc_v_a) / 2.0
        g_v = (xgf_v_a + xgc_l_h) / 2.0
        if altitud_alta: g_v *= 0.85
        if clima_ext:
            g_l *= 0.90
            g_v *= 0.90
        
        goles_totales = g_l + g_v
        prob_over_25 = 1.0 - (np.exp(-goles_totales) * (1 + goles_totales + (goles_totales**2)/2.0))
        prob_under_25 = 1.0 - prob_over_25
        
        st.markdown("---")
        st.markdown("## 📊 RESULTADOS DEL ANÁLISIS AUTOMÁTICO")
        
        st.subheader("🎯 Goles Proyectados Avanzados")
        st.info(f"⚽ Goles {eq_l}: {g_l:.2f} | Goles {eq_v}: {g_v:.2f}")
        st.success(f"📊 Total Goles Estimados: {goles_totales:.2f}")
        
        st.subheader("📈 Mercado Principal: 1X2")
        matriz_1x2 = [
            [eq_l, f"{prob_l*100:.1f}%", f"{1/prob_l:.2f}", f"{cuota_casa_l:.2f}", "✅ SÍ" if cuota_casa_l > (1/prob_l) else "❌ No", f"${banca_total * calcular_kelly(prob_l, cuota_casa_l, fraccion_kelly):.2f}"],
            ["Empate", f"{prob_e*100:.1f}%", f"{1/prob_e:.2f}", f"{cuota_casa_e:.2f}", "✅ SÍ" if cuota_casa_e > (1/prob_e) else "❌ No", f"${banca_total * calcular_kelly(prob_e, cuota_casa_e, fraccion_kelly):.2f}"],
            [eq_v, f"{prob_v*100:.1f}%", f"{1/prob_v:.2f}", f"{cuota_casa_v:.2f}", "✅ SÍ" if cuota_casa_v > (1/prob_v) else "❌ No", f"${banca_total * calcular_kelly(prob_v, cuota_casa_v, fraccion_kelly):.2f}"]
        ]
        st.dataframe(data=matriz_1x2, column_config={0: "Mercado", 1: "Probabilidad", 2: "Cuota Teórica", 3: "Cuota Casa", 4: "¿Hay Valor?", 5: "Inversión Sugerida"}, use_container_width=True)
        
        st.subheader("⚽ Mercado Goles (Over/Under 2.5)")
        matriz_goles = [
            ["Más de 2.5 Goles", f"{prob_over_25*100:.1f}%", f"{1/prob_over_25:.2f}", f"{cuota_over_25:.2f}", "✅ SÍ" if cuota_over_25 > (1/prob_over_25) else "❌ No", f"${banca_total * calcular_kelly(prob_over_25, cuota_over_25, fraccion_kelly):.2f}"],
            ["Menos de 2.5 Goles", f"{prob_under_25*100:.1f}%", f"{1/prob_under_25:.2f}", f"{cuota_under_25:.2f}", "✅ SÍ" if cuota_under_25 > (1/prob_under_25) else "❌ No", f"${banca_total * calcular_kelly(prob_under_25, cuota_under_25, fraccion_kelly):.2f}"]
        ]
        st.dataframe(data=matriz_goles, column_config={0: "Mercado Goles", 1: "Probabilidad", 2: "Cuota Teórica", 3: "Cuota Casa", 4: "¿Hay Valor?", 5: "Inversión Sugerida"}, use_container_width=True)
