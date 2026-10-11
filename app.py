import streamlit as st
import numpy as np
import sqlite3

st.set_page_config(page_title="Sistema Quant de Fútbol Pro", layout="wide", page_icon="🏆")
st.title("🏆 Sistema Quant de Fútbol Profesional (Versión Élite PRO)")

# Conexión limpia y optimizada a la nueva base de datos estructurada
@st.cache_resource
def conectar_db():
    conn = sqlite3.connect("futbol_quant_elite.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, 
            forma TEXT, 
            xg_favor_local REAL, 
            xg_contra_local REAL, 
            xg_favor_vis REAL, 
            xg_contra_vis REAL, 
            corners REAL, 
            faltas REAL, 
            amarillas REAL
        )
    """)
    conn.commit()
    return conn

conn = conectar_db()

def sincronizar_liga_pais(pais):
    # Inyección de datos desglosados (Ataque/Defensa de Local VS Ataque/Defensa de Visitante)
    # Formato: (Nombre, Forma, xGF_Local, xGC_Local, xGF_Vis, xGC_Vis, Córners, Faltas, Amarillas)
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
            ("Atlético Madrid", "E,V,E,V,E", 1.9, 0.5, 1.3, 0.9, 5.0, 14.5, 2.8)
        ],
        "Inglaterra (Premier League Completa)": [
            ("Manchester City", "V,E,V,V,V", 2.8, 0.7, 2.4, 1.1, 7.5, 8.5, 1.2),
            ("Arsenal", "V,E,V,D,V", 2.3, 0.6, 1.9, 1.0, 6.1, 11.0, 1.9),
            ("Liverpool", "V,V,D,V,V", 2.5, 0.8, 2.1, 1.2, 6.8, 10.5, 1.6)
        ]
    }
    if pais in ligas_mundiales:
        cursor = conn.cursor()
        for eq in ligas_mundiales[pais]:
            cursor.execute("""
                INSERT INTO equipos (nombre, forma, xg_favor_local, xg_contra_local, xg_favor_vis, xg_contra_vis, corners, faltas, amarillas) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
                ON CONFLICT(nombre) DO UPDATE SET 
                forma=excluded.forma, xg_favor_local=excluded.xg_favor_local, xg_contra_local=excluded.xg_contra_local, 
                xg_favor_vis=excluded.xg_favor_vis, xg_contra_vis=excluded.xg_contra_vis, corners=excluded.corners, 
                faltas=excluded.faltas, amarillas=excluded.amarillas
            """, eq)
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
lista_existente = [r for r in lista_raw]

if menu == "Configurar Ligas":
    st.header("⚙️ Importación e Inyección de Ligas")
    pais_seleccionado = st.selectbox("Selecciona la liga para cargar sus equipos", ["Ecuador (LigaPro Completa)", "España (LaLiga Completa)", "Inglaterra (Premier League Completa)"])
    if st.button("🔄 Cargar Equipos Oficiales"):
        if sincronizar_liga_pais(pais_seleccionado):
            st.success("¡Base de datos Élite actualizada con éxito!")
            st.rerun()
            
    st.markdown("---")
    st.subheader("➕ REGISTRO MANUAL ÉLITE: Agregar o Actualizar Cualquier Equipo")
    with st.form("form_manual_pro"):
        nom = st.text_input("Nombre del Club").strip()
        forma_n = st.text_input("Últimos 5 partidos (Ej: V,E,V,D,V)", "V,E,V")
        xg_f_l_n = st.number_input("xG de Local a Favor", 0.0, 5.0, 1.6, 0.1)
        xg_c_l_n = st.number_input("xG de Local en Contra", 0.0, 5.0, 1.0, 0.1)
        xg_f_v_n = st.number_input("xG de Visitante a Favor", 0.0, 5.0, 1.2, 0.1)
        xg_c_v_n = st.number_input("xG de Visitante en Contra", 0.0, 5.0, 1.4, 0.1)
        corn_n = st.number_input("Promedio de Córners", 0.0, 20.0, 5.5, 0.5)
        fl_n = st.number_input("Promedio de Faltas", 0.0, 40.0, 12.0, 0.5)
        am_n = st.number_input("Promedio de Amarillas", 0.0, 10.0, 2.0, 0.1)
        if st.form_submit_button("💾 Guardar y Registrar Equipo"):
            if nom:
                conn.execute("INSERT INTO equipos VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(nombre) DO UPDATE SET forma=excluded.forma, xg_favor_local=excluded.xg_favor_local, xg_contra_local=excluded.xg_contra_local, xg_favor_vis=excluded.xg_favor_vis, xg_contra_vis=excluded.xg_contra_vis, corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas", (nom, forma_n, xg_f_l_n, xg_c_l_n, xg_f_v_n, xg_c_v_n, corn_n, fl_n, am_n))
                conn.commit()
                st.success(f"¡{nom} registrado exitosamente!")
                st.rerun()

elif menu == "Análisis y Cuotas":
    if not lista_existente:
        st.warning("⚠️ Base de datos limpia. Ve a 'Configurar Ligas' para cargar la liga de tu país.")
    else:
        banca_total = st.sidebar.number_input("💵 Tu Banca Total ($)", min_value=10.0, value=1000.0, step=50.0)
        perfil_riesgo = st.sidebar.selectbox("🛡️ Gestión de Riesgo", ["Conservador (1/4)", "Moderado (1/2)", "Agresivo (Full)"])
        fraccion_kelly = 0.25 if "Conservador" in perfil_riesgo else 0.50 if "Moderado" in perfil_riesgo else 1.00
        
        st.subheader("🏟️ Entorno Táctico")
        clima_ext = st.checkbox("🌧️ Clima Extremo")
        altitud_alta = st.checkbox("🏔️ Partido en Altura (>2500m)")
        
        st.markdown("### 🏠 Configuración del Local")
        eq_l = st.selectbox("Seleccionar Local", [r[0] for r in lista_existente], index=0)
        _, f_l, xgf_l_h, xgc_l_h, xgf_l_a, xgc_l_a, c_l, fa_l, am_l = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_l,)).fetchone()
        bajas_l = st.number_input("Bajas Local", 0, 11, 0, key="bajas_l_in")
        imp_l = st.selectbox("Impacto Bajas Local", ["Bajo", "Medio", "Muy Alto"], key="imp_l_in")
        
        st.markdown("### 🚀 Configuración del Visitante")
        eq_v = st.selectbox("Seleccionar Visitante", [r[0] for r in lista_existente], index=min(1, len(lista_existente)-1))
        _, f_v, xgf_v_h, xgc_v_h, xgf_v_a, xgc_v_a, c_v, fa_v, am_v = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_v,)).fetchone()
        bajas_v = st.number_input("Bajas Visitante", 0, 11, 0, key="bajas_v_in")
        imp_v = st.selectbox("Impacto Bajas Visitante", ["Bajo", "Medio", "Muy Alto"], key="imp_v_in")
        
        st.markdown("---")
        st.subheader("💰 Cuotas de las Casas de Apuestas")
        col_cuo1, col_cuo2, col_cuo3 = st.columns(3)
        cuota_casa_l = col_cuo1.number_input(f"Cuota {eq_l}", min_value=1.01, value=2.00, step=0.05, key="c_l_in")
        cuota_casa_e = col_cuo2.number_input("Cuota Empate", min_value=1.01, value=3.20, step=0.05, key="c_e_in")
        cuota_casa_v = col_cuo3.number_input(f"Cuota {eq_v}", min_value=1.01, value=3.50, step=0.05, key="c_v_in")
        
        st.markdown("### ⚽ Cuotas para Goles (Mercado Over / Under 2.5)")
        col_g1, col_g2 = st.columns(2)
        cuota_over_25 = col_g1.number_input("Cuota Más de 2.5 Goles", min_value=1.01, value=1.90, step=0.05)
        cuota_under_25 = col_g2.number_input("Cuota Menos de 2.5 Goles", min_value=1.01, value=1.90, step=0.05)
        
        if st.button("📊 Analizar y Ejecutar Escáner de Valor"):
            # REFINAMIENTO PRO: Cruzamos xG de Local en Casa contra xG de Visitante Fuera de Casa
            p_l = calcular_poder_equipo(f_l, xgf_l_h, xgc_l_h, True, c_l, fa_l, am_l, bajas_l, imp_l, clima_ext, altitud_alta)
            p_v = calcular_poder_equipo(f_v, xgf_v_a, xgc_v_a, False, c_v, fa_v, am_v, bajas_v, imp_v, clima_ext, altitud_alta)
            total = p_l + p_v
            prob_l, prob_v = (p_l / total) * 0.78, (p_v / total) * 0.78
            prob_e = 1.0 - (prob_l + prob_v)
            
