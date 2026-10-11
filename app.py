import streamlit as st
import numpy as np
import sqlite3
import datetime

# Configuración de página móvil
st.set_page_config(page_title="Sistema Quant de Fútbol Pro", layout="wide", page_icon="🏆")
st.title("🏆 Sistema Quant de Fútbol Profesional (Sincronización Global)")

# --- BASE DE DATOS ---
def conectar_db():
    conn = sqlite3.connect("futbol_quant_final.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, forma TEXT, xg_favor REAL, xg_contra REAL, corners REAL, faltas REAL, amarillas REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_apuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, visitante TEXT, 
            mercado_apostado TEXT, cuota REAL, monto REAL, probabilidad_nuestra REAL, resultado_real TEXT, beneficio REAL
        )
    """)
    conn.commit()
    return conn

conn = conectar_db()

# --- ACTUALIZADOR GLOBAL DE LIGAS (API MOCK / PASARELA DE DATOS) ---
def sincronizar_liga_pais(pais):
    """Carga de forma masiva los bloques estadísticos reales por país elegido"""
    ligas_mundiales = {
        "Ecuador (LigaPro)": {
            "LDU Quito": ["V,V,E,V,V", 1.9, 0.7, 5.8, 11.2, 2.3],
            "Barcelona SC": ["V,E,D,V,E", 1.6, 1.1, 5.2, 13.4, 2.8],
            "Independiente del Valle": ["V,V,V,E,D", 2.1, 0.8, 6.1, 10.5, 1.9],
            "Emelec": ["E,D,V,E,V", 1.3, 1.2, 4.7, 14.1, 3.1]
        },
        "Argentina (Liga Profesional)": {
            "River Plate": ["V,E,V,V,E", 2.0, 0.9, 6.2, 10.8, 2.0],
            "Boca Juniors": ["E,V,D,E,V", 1.5, 1.2, 5.1, 12.9, 2.9],
            "Racing Club": ["V,D,V,E,V", 1.7, 1.0, 5.5, 11.5, 2.4]
        },
        "España (LaLiga)": {
            "Real Madrid": ["V,V,E,V,D", 2.2, 0.8, 6.4, 10.2, 1.5],
            "Barcelona": ["V,V,V,D,V", 2.4, 1.1, 5.8, 12.1, 2.1],
            "Atlético Madrid": ["E,V,E,V,E", 1.6, 0.7, 5.0, 14.5, 2.8]
        },
        "Inglaterra (Premier League)": {
            "Manchester City": ["V,E,V,V,V", 2.6, 0.9, 7.5, 8.5, 1.2],
            "Arsenal": ["V,E,V,D,V", 2.1, 0.8, 6.1, 11.0, 1.9],
            "Liverpool": ["V,V,D,V,V", 2.3, 1.0, 6.8, 10.5, 1.6]
        }
    }
    
    if pais in ligas_mundiales:
        cursor = conn.cursor()
        for nombre, d in ligas_mundiales[pais].items():
            cursor.execute("""
                INSERT INTO equipos (nombre, forma, xg_favor, xg_contra, corners, faltas, amarillas)
                VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(nombre) DO UPDATE SET
                forma=excluded.forma, xg_favor=excluded.xg_favor, xg_contra=excluded.xg_contra,
                corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas
            """, (nombre, d[0], d[1], d[2], d[3], d[4], d[5]))
        conn.commit()
        return True
    return False

# --- MODELO MATEMÁTICO ---
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
    poder_base *= (1.0 - min(num_bajas * tasa_penalizacion, 0.40))
    
    if clima_extremo: poder_base *= 0.92
    if altitud_alta and not es_local: poder_base *= 0.85
    return max(poder_base, 0.05)

def calcular_kelly(probabilidad, cuota_casa, fraccion=0.25):
    if cuota_casa <= 1: return 0.0
    f_kelly = ((cuota_casa - 1) * probabilidad - (1.0 - probabilidad)) / (cuota_casa - 1)
    return max(f_kelly * fraccion, 0.0)

# --- MENÚ ---
menu = st.sidebar.radio("Navegación", ["Análisis y Cuotas", "Auditoría de Backtesting", "Configurar Ligas"])

lista_existente = [row[0] for row in conn.cursor().execute("SELECT nombre FROM equipos").fetchall()]

if menu == "Configurar Ligas":
    st.header("⚙️ Sincronizador de Ligas Internacionales")
    
    st.subheader("Sincronización por Países")
    pais_seleccionado = st.selectbox("Selecciona el país/liga que deseas importar", ["Ecuador (LigaPro)", "Argentina (Liga Profesional)", "España (LaLiga)", "Inglaterra (Premier League)"])
    
    if st.button("🔄 Importar todos los equipos de esta Liga"):
        if sincronizar_liga_pais(pais_seleccionado):
            st.success(f"¡Ligas e historiales de {pais_seleccionado} cargados correctamente!")
            st.rerun()

    st.markdown("---")
    st.subheader("🗄️ Registro y Creación Manual de Equipos Individuales")
    with st.form("form_nuevo_equipo"):
        nom = st.text_input("Nombre del Nuevo Equipo").strip()
        forma_n = st.text_input("Últimos 5 partidos (Ej: V,V,E,D,V)", "V,E,V,D,V")
        xg_f_n = st.number_input("xG Promedio a Favor", 0.0, 5.0, 1.5, 0.1)
        xg_c_n = st.number_input("xG Promedio en Contra", 0.0, 5.0, 1.2, 0.1)
        corn_n = st.number_input("Promedio de Córners", 0.0, 20.0, 5.5, 0.5)
        fl_n = st.number_input("Promedio de Faltas", 0.0, 40.0, 12.0, 0.5)
        am_n = st.number_input("Promedio de Amarillas", 0.0, 10.0, 2.0, 0.1)
        if st.form_submit_button("💾 Guardar Equipo"):
            if nom:
                conn.execute("INSERT INTO equipos VALUES (?,?,?,?,?,?,?) ON CONFLICT(nombre) DO UPDATE SET forma=excluded.forma, xg_favor=excluded.xg_favor, xg_contra=excluded.xg_contra, corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas", (nom, forma_n, xg_f_n, xg_c_n, corn_n, fl_n, am_n))
                conn.commit()
                st.success(f"¡{nom} guardado exitosamente!")
                st.rerun()

elif menu == "Auditoría de Backtesting":
    st.header("📊 Registro Histórico de Apuestas Realizadas")
    apuestas_abiertas = conn.execute("SELECT id, local, visitante, mercado_apostado, monto, cuota FROM historial_apuestas WHERE resultado_real = 'Pendiente'").fetchall()
    if apuestas_abiertas:
        for ap in apuestas_abiertas:
            with st.form(f"form_{ap[0]}"):
                st.write(f"**{ap[1]} vs {ap[2]}** | Apostado: {ap[3]} | Monto: ${ap[4]} | Cuota: {ap[5]}")
                res_real = st.selectbox("Resultado", ["Ganada", "Perdida"])
                if st.form_submit_button("Cerrar Apuesta"):
                    beneficio = (ap[4] * ap[5] - ap[4]) if res_real == "Ganada" else -ap[4]
                    conn.execute("UPDATE historial_apuestas SET resultado_real = ?, beneficio = ? WHERE id = ?", (res_real, beneficio, ap[0]))
                    conn.commit()
                    st.rerun()
    else:
        st.info("No hay transacciones pendientes en tu bitácora.")

elif menu == "Análisis y Cuotas":
    if not lista_existente:
        st.warning("⚠️ Tu base de datos está vacía. Ve primero a la pestaña 'Configurar Ligas' para importar equipos.")
    else:
        banca_total = st.sidebar.number_input("💵 Tu Banca Total ($)", min_value=10.0, value=1000.0, step=50.0)
        perfil_riesgo = st.sidebar.selectbox("🛡️ Riesgo (Kelly)", ["Conservador (1/4)", "Moderado (1/2)", "Agresivo (Full)"])
        fraccion_kelly = 0.25 if "Conservador" in perfil_riesgo else 0.50 if "Moderado" in perfil_riesgo else 1.00

        st.subheader("🏟️ Parámetros del Entorno")
        col_env1, col_env2 = st.columns(2)
        clima_ext = col_env1.checkbox("🌧️ ¿Clima Extremo? (Tormenta/Nieve)")
        altitud_alta = col_env2.checkbox("🏔️ ¿Partido en Altura? (>2500m)")

        col1, col2 = st.columns(2)
        with col1:
            st.header("Local")
            eq_l = st.selectbox("Seleccionar Local", lista_existente, index=0)
            _, f_l, xgf_l, xgc_l, c_l, fa_l, am_l = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_l,)).fetchone()
            bajas_l = st.number_input("Bajas Local", 0, 11, 0)
            imp_l = st.selectbox("Impacto Bajas", ["Bajo", "Medio", "Muy Alto"], key="il")

        with col2:
            st.header("Visitante")
            eq_v = st.selectbox("Seleccionar Visitante", lista_existente, index=min(1, len(lista_existente)-1))
            _, f_v, xgf_v, xgc_v, c_v, fa_v, am_v = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_v,)).fetchone()
            bajas_v = st.number_input("Bajas Visitante", 0, 11, 0)
            imp_v = st.selectbox("Impacto Bajas", ["Bajo", "Medio", "Muy Alto"], key="iv")

        st.markdown("---")
        st.subheader("💰 Cuotas de la Casa")
        col_c1, col_c2, col_c3 = st.columns(3)
        cuota_casa_l = col_c1.number_input(f"Cuota {eq_l}", min_value=1.01, value=2.00)
        cuota_casa_e = col_c2.number_input("Cuota Empate", min_value=1.01, value=3.20)
        cuota_casa_v = col_c3.number_input(f"Cuota {eq_v}", min_value=1.01, value=3.50)

        if st.button("📊 Calcular Probabilidad y Stake Óptimo"):
            p_l = calcular_poder_equipo(f_l, xgf_l, xgc_l, True, c_l, fa_l, am_l, bajas_l, imp_l, clima_ext, altitud_alta)
            p_v = calcular_poder_equipo(f_v, xgf_v, xgc_v, False, c_v, fa_v, am_v, bajas_v, imp_v, clima_ext, altitud_alta)
            
            total = p_l + p_v
            prob_l, prob_v = (p_l / total) * 0.78, (p_v / total) * 0.78
            prob_e = 1.0 - (prob_l + prob_v)
            
            k_l = calcular_kelly(prob_l, cuota_casa_l, fraccion_kelly)
            k_e = calcular_kelly(prob_e, cuota_casa_e, fraccion_kelly)
