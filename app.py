import streamlit as st
import numpy as np
import sqlite3
import datetime

st.set_page_config(page_title="Sistema Quant de Fútbol Pro", layout="wide", page_icon="🏆")
st.title("🏆 Sistema Quant de Fútbol Profesional (Versión Definitiva)")

def conectar_db():
    conn = sqlite3.connect("futbol_quant_final.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, forma TEXT, xg_favor REAL, xg_contra REAL, corners REAL, faltas REAL, amarillas REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_apuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, visitante TEXT, 
            mercado_apostado TEXT, cuota REAL, monto REAL, probabilidad_nuestra REAL, resultado_real TEXT, beneficio REAL
        )
    ''')
    conn.commit()
    return conn

conn = conectar_db()

def simular_api_scraping():
    equipos_demo = {
        "Real Madrid": ["V,V,E,V,D", 2.2, 0.8, 6.4, 10.2, 1.5],
        "Barcelona": ["V,V,V,D,V", 2.4, 1.1, 5.8, 12.1, 2.1],
        "Atlético Madrid": ["E,V,E,V,E", 1.6, 0.7, 5.0, 14.5, 2.8],
        "Manchester City": ["V,E,V,V,V", 2.6, 0.9, 7.5, 8.5, 1.2],
        "Arsenal": ["V,E,V,D,V", 2.1, 0.8, 6.1, 11.0, 1.9],
        "Liverpool": ["V,V,D,V,V", 2.3, 1.0, 6.8, 10.5, 1.6]
    }
    cursor = conn.cursor()
    for nombre, d in equipos_demo.items():
        cursor.execute('''
            INSERT INTO equipos (nombre, forma, xg_favor, xg_contra, corners, faltas, amarillas)
            VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(nombre) DO UPDATE SET
            forma=excluded.forma, xg_favor=excluded.xg_favor, xg_contra=excluded.xg_contra,
            corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas
        ''', (nombre, d[0], d[1], d[2], d[3], d[4], d[5]))
    conn.commit()

def calcular_poder_equipo(historial, xg_f, xg_c, es_local, corners, faltas, amarillas, num_bajas, impacto_bajas, clima_extremo, altitud_alta):
    dif_xg = xg_f - xg_c
    score_xg = 1 / (1 + np.exp(-dif_xg / 3.0))
    lista_partidos = [r.strip() for r in historial.split(",") if r.strip() in ['V', 'E', 'D']][:5]
    puntos_forma = sum([3 if r == 'V' else 1 if r == 'E' else 0 for r in lista_partidos])
    score_forma = puntos_forma / 15.0 if lista_partidos else 0.5
    score_local = 0.15 if es_local else 0.0
    score_corners = min(corners / 12.0, 1.0)
    score_disciplina = max(1.0 - ((faltas * 0.02) + (amarillas * 0.1)), 0.0)
    score_secundario = (score_corners * 0.6) + (score_disciplina * 0.4)
    poder_base = (score_xg * 0.30) + (score_forma * 0.25) + (score_local * 0.15) + (score_secundario * 0.15)
    tasa_penalizacion = 0.10 if impacto_bajas == "Muy Alto" else 0.05 if impacto_bajas == "Medio" else 0.02
    penalizacion_bajas = min(num_bajas * tasa_penalizacion, 0.40)
    poder_base *= (1.0 - penalizacion_bajas)
    if clima_extremo: poder_base *= 0.92
    if altitud_alta and not es_local: poder_base *= 0.85
    return max(poder_base, 0.05)

def calcular_kelly(probabilidad, cuota_casa, fraccion=0.25):
    if cuota_casa <= 1: return 0.0
    b = cuota_casa - 1
    f_kelly = (b * probabilidad - (1.0 - probabilidad)) / b
    return max(f_kelly * fraccion, 0.0)

menu = st.sidebar.radio("Navegación", ["Análisis y Cuotas", "Auditoría de Backtesting", "Configuración"])
lista_existente = [row[0] for row in conn.cursor().execute("SELECT nombre FROM equipos").fetchall()]
if not lista_existente:
    simular_api_scraping()
    lista_existente = [row[0] for row in conn.cursor().execute("SELECT nombre FROM equipos").fetchall()]

if menu == "Configuración":
    st.header("⚙️ Sincronización y Datos Globales")
    if st.button("🔄 Sincronizar Base de Datos (API/Scraping Demo)"):
        simular_api_scraping()
        st.success("¡Equipos updated!")

elif menu == "Auditoría de Backtesting":
    st.header("📊 Registro Histórico y Validación del Modelo")
    st.subheader("Registrar Resultado Real de un Partido Analizado")
    cursor = conn.cursor()
    apuestas_abiertas = cursor.execute("SELECT id, local, visitante, mercado_apostado, monto, cuota FROM historial_apuestas WHERE resultado_real = 'Pendiente'").fetchall()
    if apuestas_abiertas:
        for ap in apuestas_abiertas:
            with st.form(f"form_cerrar_{ap[0]}"):
                st.write(f"**{ap[1]} vs {ap[2]}** | Apostado a: {ap[3]} | Riesgo: ${ap[4]:.2f} | Cuota: {ap[5]:.2f}")
                res_real = st.selectbox("Resultado Final Real", ["Ganada", "Perdida"], key=f"res_{ap[0]}")
                if st.form_submit_button("Cerrar Apuesta"):
                    beneficio = (ap[4] * ap[5] - ap[4]) if res_real == "Ganada" else -ap[4]
                    cursor.execute("UPDATE historial_apuestas SET resultado_real = ?, beneficio = ? WHERE id = ?", (res_real, beneficio, ap[0]))
                    conn.commit()
                    st.rerun()
    else: st.info("No hay apuestas pendientes.")
    st.markdown("---")
    st.subheader("📈 Rendimiento Financiero Consolidado")
    historial_df = conn.execute("SELECT * FROM historial_apuestas WHERE resultado_real != 'Pendiente'").fetchall()
    if historial_df:
        total_invertido = sum([r[6] for r in historial_df])
        retorno_total = sum([r[9] for r in historial_df])
        roi = (retorno_total / total_invertido) * 100 if total_invertido > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Balance Total Neto", f"${retorno_total:.2f}")
        c2.metric("ROI del Sistema", f"{roi:.2f}%")
        c3.metric("Apuestas Completadas", len(historial_df))
    else: st.warning("Aún no tienes apuestas resueltas.")

elif menu == "Análisis y Cuotas":
    banca_total = st.sidebar.number_input("💵 Tu Banca Total ($)", min_value=10.0, value=1000.0, step=50.0)
    perfil_riesgo = st.sidebar.selectbox("🛡️ Riesgo (Kelly)", ["Conservador (1/4)", "Moderado (1/2)", "Agresivo (Full)"])
    fraccion_kelly = 0.25 if "Conservador" in perfil_riesgo else 0.50 if "Moderado" in perfil_riesgo else 1.00
    st.subheader("🏟️ Parámetros del Entorno")
    col_env1, col_env2 = st.columns(2)
    clima_ext = col_env1.checkbox("🌧️ ¿Clima Extremo?")
    altitud_alta = col_env2.checkbox("🏔️ ¿Partido en Altura?")
    col1, col2 = st.columns(2)
    with col1:
        st.header("Local")
        eq_l = st.selectbox("Seleccionar Local", lista_existente, index=0)
        _, f_l, xgf_l, xgc_l, c_l, fa_l, am_l = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_l,)).fetchone()
        bajas_l = st.number_input("Bajas Local", 0, 11, 0)
        imp_l = st.selectbox("Impacto Bajas", ["Bajo", "Medio", "Muy Alto"], key="il")
    with col2:
        st.header("Visitante")
        eq_v = st.selectbox("Seleccionar Visitante", lista_existente, index=1)
        _, f_v, xgf_v, xgc_v, c_v, fa_v, am_v = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_v,)).fetchone()
        bajas_v = st.number_input("Bajas Visitante", 0, 11, 1)
        imp_v = st.selectbox("Impacto Bajas", ["Bajo", "Medio", "Muy Alto"], key="iv")
    st.markdown("---")
    st.subheader("💰 Cuotas de la Casa")
    col_c1, col_c2, col_c3 = st.columns(3)
    cuota_casa_l = col_c1.number_input(f"Cuota {eq_l}", min_value=1.01, value=1.95)
    cuota_casa_e = col_c2.number_input("Cuota Empate", min_value=1.01, value=3.40)
    cuota_casa_v = col_c3.number_input(f"Cuota {eq_v}", min_value=1.01, value=3.80)
    if st.button("📊 Analizar y Buscar Inversiones con Valor"):
        p_l = calcular_poder_equipo(f_l, xgf_l, xgc_l, True, c_l, fa_l, am_l, bajas_l, imp_l, clima_ext, altitud_alta)
        p_v = calcular_poder_equipo(f_v, xgf_v, xgc_v, False, c_v, fa_v, am_v, bajas_v, imp_v, clima_ext, altitud_alta)
        total = p_l + p_v
        prob_l, prob_v = (p_l / total) * 0.78, (p_v / total) * 0.78
        prob_e = 1.0 - (prob_l + prob_v)
        k_l = calcular_kelly(prob_l, cuota_casa_l, fraccion_kelly)
        k_e = calcular_kelly(prob_e, cuota_casa_e, fraccion_kelly)
        k_v = calcular_kelly(prob_v, cuota_casa_v, fraccion_kelly)
        st.markdown("### 🎯 Planificación Financiera")
        data_comp = {
            "Mercado": [eq_l, "Empate", eq_v],
            "Nuestra Probabilidad": [f"{prob_l*100:.1f}%", f"{prob_e*100:.1f}%", f"{prob_v*100:.1f}%"],
            "Nuestra Cuota": [f"{1/prob_l:.2f}", f"{1/prob_e:.2f}", f"{1/prob_v:.2f}"],
            "Cuota Casa": [f"{cuota_casa_l:.2f}", f"{cuota_casa_e:.2f}", f"{cuota_casa_v:.2f}"],
            "¿Hay Valor?": ["✅ SÍ" if cuota_casa_l > (1/prob_l) else "❌ No", "✅ SÍ" if cuota_casa_e > (1/prob_e) else "❌ No", "✅ SÍ" if cuota_casa_v > (1/prob_v) else "❌ No"],
            "Monto Sugerido ($)": [f"${banca_total * k_l:.2f}", f"${banca_total * k_e:.2f}", f"${banca_total * k_v:.2f}"]
        }
        st.table(data_comp)
        st.markdown("#### 📥 Registrar Selección en el Registro de Auditoría")
        c_b1, c_b2, c_b3 = st.columns(3)
        if k_l > 0 and c_b1.button(f"Registrar Apuesta por {eq_l}", key="btn_l"):
            conn.execute("INSERT INTO historial_apuestas (fecha, local, visitante, mercado_apostado, cuota, monto, probabilidad_nuestra, resultado_real, beneficio) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente', 0)", (str(datetime.date.today()), eq_l, eq_v, "Local", cuota_casa_l, banca_total * k_l, prob_l))
            conn.commit()
            st.success("Registrada")
        if k_e > 0 and c_b2.button("Registrar Apuesta por Empate", key="btn_e"):
            conn.execute("INSERT INTO historial_apuestas (fecha, local, visitante, mercado_apostado, cuota, monto, probabilidad_nuestra, resultado_real, beneficio) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente', 0)", (str(datetime.date.today()), eq_l, eq_v, "Empate", cuota_casa_e, banca_total * k_e, prob_e))
            conn.commit()
            st.success("Registrada")
        if k_v > 0 and c_b3.button(f"Registrar Apuesta por {eq_v}", key="btn_v"):
            conn.execute("INSERT INTO historial_apuestas (fecha, local, visitante, mercado_apostado, cuota, monto, probabilidad_nuestra, resultado_real, beneficio) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente', 0)", (str(datetime.date.today()), eq_l, eq_v, "Visitante", cuota_casa_v, banca_total * k_v, prob_v))
            conn.commit()
            st.success("Registrada")
# --- FORMULARIO MANUAL AGREGADO POR EL ASESOR ---
if menu == "Configuración":
    st.markdown("---")
    st.subheader("🗄️ Registro y Creación Manual de Equipos")
    with st.form("form_nuevo_equipo"):
        nom = st.text_input("Nombre del Nuevo Equipo").strip()
        forma_n = st.text_input("Últimos 5 partidos (Ej: V,V,E,D,V)", "V,E,V,D,V")
        xg_f_n = st.number_input("xG Promedio a Favor", min_value=0.0, max_value=5.0, value=1.5, step=0.1)
        xg_c_n = st.number_input("xG Promedio en Contra", min_value=0.0, max_value=5.0, value=1.2, step=0.1)
        corn_n = st.number_input("Promedio de Córners", min_value=0.0, max_value=20.0, value=5.5, step=0.5)
        fl_n = st.number_input("Promedio de Faltas", min_value=0.0, max_value=40.0, value=12.0, step=0.5)
        am_n = st.number_input("Promedio de Amarillas", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
        
        if st.form_submit_button("💾 Guardar Equipo en la Base de Datos"):
            if nom:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO equipos (nombre, forma, xg_favor, xg_contra, corners, faltas, amarillas)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(nombre) DO UPDATE SET
                        forma=excluded.forma, xg_favor=excluded.xg_favor, xg_contra=excluded.xg_contra,
                        corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas
                """, (nom, forma_n, xg_f_n, xg_c_n, corn_n, fl_n, am_n))
                conn.commit()
                st.success(f"¡{nom} ha sido guardado exitosamente en tu base de datos móvil!")
            else:
                st.error("Por favor, escribe un nombre válido para el equipo.")
                         
