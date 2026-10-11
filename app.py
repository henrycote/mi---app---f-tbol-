import streamlit as st
import numpy as np
import sqlite3
import datetime

st.set_page_config(page_title="Sistema Quant de Fútbol Pro", layout="wide", page_icon="🏆")
st.title("🏆 Sistema Quant de Fútbol Profesional (Versión Global)")

def conectar_db():
    conn = sqlite3.connect("futbol_quant_completo.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS equipos (nombre TEXT PRIMARY KEY, forma TEXT, xg_favor REAL, xg_contra REAL, corners REAL, faltas REAL, amarillas REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS historial_apuestas (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, visitante TEXT, mercado_apostado TEXT, cuota REAL, monto REAL, probabilidad_nuestra REAL, resultado_real TEXT, beneficio REAL)")
    conn.commit()
    return conn

conn = conectar_db()

def sincronizar_liga_pais(pais):
    # CORRECCIÓN DE RAÍZ: Los datos ahora se inyectan como valores numéricos puros y texto plano, solucionando el bloqueo en SQLite
    ligas_mundiales = {
        "Ecuador (LigaPro Completa)": [
            ("LDU Quito", "V,V,E,V,V", 1.9, 0.7, 5.8, 11.2, 2.3),
            ("Barcelona SC", "V,E,D,V,E", 1.6, 1.1, 5.2, 13.4, 2.8),
            ("Independiente del Valle", "V,V,V,E,D", 2.1, 0.8, 6.1, 10.5, 1.9),
            ("Emelec", "E,D,V,E,V", 1.3, 1.2, 4.7, 14.1, 3.1),
            ("El Nacional", "V,D,D,V,E", 1.4, 1.3, 5.0, 12.5, 2.7),
            ("Delfín SC", "E,V,D,E,D", 1.1, 1.2, 4.2, 13.8, 2.4),
            ("Aucas", "D,E,V,V,D", 1.5, 1.4, 4.9, 11.9, 2.9),
            ("Universidad Católica", "V,E,V,D,V", 1.7, 1.1, 5.4, 10.8, 2.2),
            ("Mushuc Runa", "E,D,V,E,V", 1.2, 1.5, 4.1, 15.0, 3.2),
            ("Macará", "D,V,E,D,E", 1.1, 1.3, 4.5, 12.2, 2.5)
        ],
        "Argentina (Liga Profesional Completa)": [
            ("River Plate", "V,E,V,V,E", 2.0, 0.9, 6.2, 10.8, 2.0),
            ("Boca Juniors", "E,V,D,E,V", 1.5, 1.2, 5.1, 12.9, 2.9),
            ("Racing Club", "V,D,V,E,V", 1.7, 1.0, 5.5, 11.5, 2.4),
            ("Independiente", "E,E,V,D,E", 1.2, 1.1, 4.8, 14.2, 3.0),
            ("San Lorenzo", "D,E,V,E,D", 1.1, 1.2, 4.4, 13.5, 2.8),
            ("Talleres Córdoba", "V,E,D,V,V", 1.6, 1.1, 5.3, 11.0, 2.3),
            ("Estudiantes LP", "E,V,E,D,V", 1.4, 1.1, 4.9, 12.1, 2.5),
            ("Vélez Sarsfield", "V,V,E,V,D", 1.8, 0.9, 5.7, 10.9, 2.1)
        ],
        "España (LaLiga Completa)": [
            ("Real Madrid", "V,V,E,V,D", 2.2, 0.8, 6.4, 10.2, 1.5),
            ("Barcelona", "V,V,V,D,V", 2.4, 1.1, 5.8, 12.1, 2.1),
            ("Atlético Madrid", "E,V,E,V,E", 1.6, 0.7, 5.0, 14.5, 2.8)
        ],
        "Inglaterra (Premier League Completa)": [
            ("Manchester City", "V,E,V,V,V", 2.6, 0.9, 7.5, 8.5, 1.2),
            ("Arsenal", "V,E,V,D,V", 2.1, 0.8, 6.1, 11.0, 1.9),
            ("Liverpool", "V,V,D,V,V", 2.3, 1.0, 6.8, 10.5, 1.6)
        ]
    }
    if pais in ligas_mundiales:
        cursor = conn.cursor()
        for eq in ligas_mundiales[pais]:
            cursor.execute("INSERT INTO equipos (nombre, forma, xg_favor, xg_contra, corners, faltas, amarillas) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(nombre) DO UPDATE SET forma=excluded.forma, xg_favor=excluded.xg_favor, xg_contra=excluded.xg_contra, corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas", eq)
        conn.commit()
        return True
    return False

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

menu = st.sidebar.radio("Navegación Móvil", ["Análisis y Cuotas", "Auditoría de Backtesting", "Configurar Ligas"])

# TRUCO CORREGIDO: Desempaquetamos los nombres de la tupla para que las listas desplegables queden limpias desde el inicio
lista_raw = conn.cursor().execute("SELECT nombre FROM equipos ORDER BY nombre ASC").fetchall()
lista_existente = [r[0] for r in lista_raw]

if menu == "Configurar Ligas":
    st.header("⚙️ Importación e Inyección de Ligas")
    pais_seleccionado = st.selectbox("Selecciona la liga para cargar sus equipos", ["Ecuador (LigaPro Completa)", "Argentina (Liga Profesional Completa)", "España (LaLiga Completa)", "Inglaterra (Premier League Completa)"])
    if st.button("🔄 Cargar Equipos Oficiales"):
        if sincronizar_liga_pais(pais_seleccionado):
            st.success("¡Base de datos actualizada correctamente!")
            st.rerun()
    st.markdown("---")
    st.subheader("➕ Agregar Cualquier Otro Equipo Manualmente")
    with st.form("form_manual"):
        nom = st.text_input("Nombre del Club").strip()
        forma_n = st.text_input("Últimos 5 partidos (Ej: V,E,V,D,V)", "V,E,V")
        xg_f_n = st.number_input("xG Promedio a Favor", 0.0, 5.0, 1.5, 0.1)
        xg_c_n = st.number_input("xG Promedio en Contra", 0.0, 5.0, 1.2, 0.1)
        corn_n = st.number_input("Promedio de Córners", 0.0, 20.0, 5.5, 0.5)
        fl_n = st.number_input("Promedio de Faltas", 0.0, 40.0, 12.0, 0.5)
        am_n = st.number_input("Promedio de Amarillas", 0.0, 10.0, 2.0, 0.1)
        if st.form_submit_button("💾 Guardar en Teléfono"):
            if nom:
                conn.execute("INSERT INTO equipos VALUES (?,?,?,?,?,?,?) ON CONFLICT(nombre) DO UPDATE SET forma=excluded.forma, xg_favor=excluded.xg_favor, xg_contra=excluded.xg_contra, corners=excluded.corners, faltas=excluded.faltas, amarillas=excluded.amarillas", (nom, forma_n, xg_f_n, xg_c_n, corn_n, fl_n, am_n))
                conn.commit()
                st.success("¡Equipo guardado!")
                st.rerun()

elif menu == "Auditoría de Backtesting":
    st.header("📊 Registro Histórico de Rendimiento")
    apuestas_abiertas = conn.execute("SELECT id, local, visitante, mercado_apostado, monto, cuota FROM historial_apuestas WHERE resultado_real = 'Pendiente'").fetchall()
    if apuestas_abiertas:
        for ap in apuestas_abiertas:
            with st.form(f"form_{ap[0]}"):
                st.write(f"⚽ **{ap[1]} vs {ap[2]}** | Apostado: {ap[3]} | Monto: ${ap[4]:.2f}")
                res_real = st.selectbox("Resultado Real", ["Ganada", "Perdida"], key=f"sel_{ap[0]}")
                if st.form_submit_button("Cerrar Transacción"):
                    beneficio = (ap[4] * ap[5] - ap[4]) if res_real == "Ganada" else -ap[4]
                    conn.execute("UPDATE historial_apuestas SET resultado_real = ?, beneficio = ? WHERE id = ?", (res_real, beneficio, ap[0]))
                    conn.commit()
                    st.rerun()
    else:
        st.info("No tienes análisis pendientes por calificar.")

elif menu == "Análisis y Cuotas":
    if not lista_existente:
        st.warning("⚠️ Base de datos limpia. Ve a 'Configurar Ligas' para cargar la liga de tu país.")
    else:
        banca_total = st.sidebar.number_input("💵 Tu Banca Total ($)", min_value=10.0, value=1000.0, step=50.0)
        perfil_riesgo = st.sidebar.selectbox("🛡️ Gestión de Riesgo", ["Conservador (1/4)", "Moderado (1/2)", "Agresivo (Full)"])
        fraccion_kelly = 0.25 if "Conservador" in perfil_riesgo else 0.50 if "Moderado" in perfil_riesgo else 1.00
        st.subheader("🏟️ Entorno Táctico")
        c1, c2 = st.columns(2)
        clima_ext = c1.checkbox("🌧️ Clima Extremo")
        altitud_alta = c2.checkbox("🏔️ Partido en Altura (>2500m)")
        
        st.markdown("### 🏠 Configuración del Local")
        eq_l = st.selectbox("Seleccionar Local", lista_existente, index=0)
        _, f_l, xgf_l, xgc_l, c_l, fa_l, am_l = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_l,)).fetchone()
        bajas_l = st.number_input("Bajas Local", 0, 11, 0, key="bajas_local_input")
        imp_l = st.selectbox("Impacto Bajas Local", ["Bajo", "Medio", "Muy Alto"], key="impacto_local_input")
        
        st.markdown("### 🚀 Configuración del Visitante")
        eq_v = st.selectbox("Seleccionar Visitante", lista_existente, index=min(1, len(lista_existente)-1))
        _, f_v, xgf_v, xgc_v, c_v, fa_v, am_v = conn.execute("SELECT * FROM equipos WHERE nombre = ?", (eq_v,)).fetchone()
        bajas_v = st.number_input("Bajas Visitante", 0, 11, 0, key="bajas_visitante_input")
        imp_v = st.selectbox("Impacto Bajas Visitante", ["Bajo", "Medio", "Muy Alto"], key="impacto_visitante_input")
        
        st.markdown("---")
        st.subheader("💰 Cuotas de las Casas de Apuestas")
        cuota_casa_l = st.number_input(f"Cuota {eq_l}", min_value=1.01, value=2.00, step=0.05, key="cuota_l_in")
        cuota_casa_e = st.number_input("Cuota Empate", min_value=1.01, value=3.20, step=0.05, key="cuota_e_in")
        cuota_casa_v = st.number_input(f"Cuota {eq_v}", min_value=1.01, value=3.50, step=0.05, key="cuota_v_in")
        
