#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesar.py - Generador de Dashboard: Lecturas Faltantes y Avisos de Pago
Procesa archivos CSV de lecturas y avisos, genera métricas y HTML interactivo.
"""

import os
import sys
import glob
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# ============================================================================
# CONFIGURACION
# ============================================================================
CARPETA_BASE = Path(__file__).parent.parent
CARPETA_IN = CARPETA_BASE / "input"
CARPETA_OUT = CARPETA_BASE / "output"
ARCHIVO_HTML = CARPETA_OUT / "index.html"

# Mapeo de columnas (adaptar si tus archivos tienen nombres diferentes)
MAPEO_LECTURAS = {
    "ZONA": "ZONA",
    "RUTA": "RUTA",
    "CUENTA": "CUENTA",
    "FECHA_PROGRAMADA": "FECHA_PROGRAMADA",
    "FECHA_LECTURA": "FECHA_LECTURA",
    "LECTURA": "LECTURA",
    "ESTADO": "ESTADO",
}

MAPEO_AVISOS = {
    "ZONA": "ZONA",
    "RUTA": "RUTA",
    "CUENTA": "CUENTA",
    "FECHA_IMPRESION": "FECHA_IMPRESION",
    "FOLIO": "FOLIO",
    "PERIODO": "PERIODO",
}

# Colores del semáforo
COLORES = {
    "VERDE": "#4CAF50",
    "AMARILLO": "#FFC107",
    "ROJO": "#F44336",
}

# ============================================================================
# FUNCIONES UTILITARIAS
# ============================================================================
def log(msg):
    """Imprime mensaje con timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def clasificar_semaforo(pct_cobertura, dias_sin_aviso, tenia_algun_aviso=True):
    """Retorna 'VERDE', 'AMARILLO' o 'ROJO' según condiciones."""
    if not tenia_algun_aviso:
        return "ROJO"
    if pct_cobertura >= 90 and dias_sin_aviso <= 2:
        return "VERDE"
    if (70 <= pct_cobertura < 90) or (3 <= dias_sin_aviso <= 5):
        return "AMARILLO"
    return "ROJO"

def get_data_html_escape(obj):
    """Convierte objeto a JSON string y escapa para atributo data-* HTML."""
    s = json.dumps(obj, default=str)
    return s.replace('"', "&quot;")

# ============================================================================
# CARGA DE DATOS
# ============================================================================
def cargar_lecturas():
    """Carga todos los archivos lecturas_*.csv y .xlsx"""
    datos = []
    for ext in ["*.csv", "*.xlsx"]:
        archivos = glob.glob(str(CARPETA_IN / f"lecturas_{ext}"))
        for ruta in archivos:
            log(f"Leyendo: {Path(ruta).name}")
            if ruta.endswith(".xlsx"):
                df = pd.read_excel(ruta)
            else:
                df = pd.read_csv(ruta)
            # Renombrar columnas según mapeo
            df = df.rename(columns={v: k for k, v in MAPEO_LECTURAS.items()
                                     if v in df.columns})
            datos.append(df)
    if not datos:
        log("ERROR: No se encontraron archivos lecturas_*.csv o .xlsx")
        return pd.DataFrame()
    return pd.concat(datos, ignore_index=True)

def cargar_avisos():
    """Carga todos los archivos avisos_*.csv y .xlsx"""
    datos = []
    for ext in ["*.csv", "*.xlsx"]:
        archivos = glob.glob(str(CARPETA_IN / f"avisos_{ext}"))
        for ruta in archivos:
            log(f"Leyendo: {Path(ruta).name}")
            if ruta.endswith(".xlsx"):
                df = pd.read_excel(ruta)
            else:
                df = pd.read_csv(ruta)
            df = df.rename(columns={v: k for k, v in MAPEO_AVISOS.items()
                                     if v in df.columns})
            datos.append(df)
    if not datos:
        log("ERROR: No se encontraron archivos avisos_*.csv o .xlsx")
        return pd.DataFrame()
    return pd.concat(datos, ignore_index=True)

# ============================================================================
# CALCULO DE METRICAS
# ============================================================================
def calcular_metricas(df_lec, df_avi):
    """Calcula métricas por zona y global."""
    if df_lec.empty or df_avi.empty:
        log("ERROR: Datos de entrada vacíos")
        return {}, {}

    # Limpiar columnas de fecha
    for df, col in [(df_lec, "FECHA_LECTURA"), (df_avi, "FECHA_IMPRESION")]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    hoy = datetime.now().date()

    metricas_zona = {}
    for zona in sorted(df_lec["ZONA"].unique()):
        lec_zona = df_lec[df_lec["ZONA"] == zona]
        avi_zona = df_avi[df_avi["ZONA"] == zona]

        total_cuentas = len(lec_zona)
        leidas = (lec_zona["ESTADO"] == "LEIDA").sum()
        faltantes = (lec_zona["ESTADO"] == "FALTANTE").sum()
        pct_cobertura_lec = (leidas / total_cuentas * 100) if total_cuentas > 0 else 0

        avisos_impresos = avi_zona["FECHA_IMPRESION"].notna().sum()
        avisos_faltantes = total_cuentas - avisos_impresos
        pct_cobertura_avi = (avisos_impresos / total_cuentas * 100) if total_cuentas > 0 else 0

        # Días sin impresión
        fechas_impresas = pd.to_datetime(avi_zona["FECHA_IMPRESION"], errors='coerce')
        fecha_max_aviso = fechas_impresas.max()
        if pd.isna(fecha_max_aviso):
            dias_sin_aviso = 999  # nunca imprimió
            tenia_algun_aviso = False
        else:
            dias_sin_aviso = (hoy - fecha_max_aviso.date()).days
            tenia_algun_aviso = True

        estado = clasificar_semaforo(pct_cobertura_avi, dias_sin_aviso, tenia_algun_aviso)

        # Métricas por ruta
        rutas_data = {}
        for ruta in sorted(lec_zona["RUTA"].unique()):
            lec_ruta = lec_zona[lec_zona["RUTA"] == ruta]
            avi_ruta = avi_zona[avi_zona["RUTA"] == ruta]

            tot_r = len(lec_ruta)
            lei_r = (lec_ruta["ESTADO"] == "LEIDA").sum()
            fal_r = tot_r - lei_r
            pct_r = (lei_r / tot_r * 100) if tot_r > 0 else 0

            avi_r = avi_ruta["FECHA_IMPRESION"].notna().sum()
            fec_r = pd.to_datetime(avi_ruta["FECHA_IMPRESION"], errors='coerce').max()
            dias_r = 999 if pd.isna(fec_r) else (hoy - fec_r.date()).days

            rutas_data[str(ruta)] = {
                "cuentas": tot_r,
                "leidas": lei_r,
                "faltantes": fal_r,
                "pct_cobertura": round(pct_r, 1),
                "avisos": avi_r,
                "dias_sin_aviso": dias_r,
            }

        metricas_zona[zona] = {
            "total_cuentas": total_cuentas,
            "leidas": leidas,
            "faltantes": faltantes,
            "pct_cobertura_lec": round(pct_cobertura_lec, 1),
            "avisos_impresos": avisos_impresos,
            "avisos_faltantes": avisos_faltantes,
            "pct_cobertura_avi": round(pct_cobertura_avi, 1),
            "dias_sin_aviso": dias_sin_aviso,
            "estado": estado,
            "rutas": rutas_data,
        }

    # Métricas globales
    total_global = len(df_lec)
    leidas_global = (df_lec["ESTADO"] == "LEIDA").sum()
    avisos_global = df_avi["FECHA_IMPRESION"].notna().sum()

    estado_global = max([metricas_zona[z]["estado"] for z in metricas_zona],
                        key=lambda x: {"ROJO": 3, "AMARILLO": 2, "VERDE": 1}.get(x, 0),
                        default="VERDE")

    metricas_global = {
        "total_cuentas": total_global,
        "leidas": leidas_global,
        "faltantes": total_global - leidas_global,
        "pct_cobertura_lec": round(leidas_global / total_global * 100, 1) if total_global > 0 else 0,
        "avisos_impresos": avisos_global,
        "avisos_faltantes": total_global - avisos_global,
        "pct_cobertura_avi": round(avisos_global / total_global * 100, 1) if total_global > 0 else 0,
        "estado": estado_global,
    }

    return metricas_zona, metricas_global

# ============================================================================
# GENERADOR HTML
# ============================================================================
def generar_html(metricas_zona, metricas_global):
    """Genera el archivo HTML del dashboard."""
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Preparar datos para Chart.js
    zonas_list = sorted(metricas_zona.keys())
    datos_grafica = {
        "zonas": zonas_list,
        "coberturas_lec": [metricas_zona[z]["pct_cobertura_lec"] for z in zonas_list],
        "coberturas_avi": [metricas_zona[z]["pct_cobertura_avi"] for z in zonas_list],
        "estados": [metricas_zona[z]["estado"] for z in zonas_list],
    }

    colores_estados = [
        {"VERDE": COLORES["VERDE"], "AMARILLO": COLORES["AMARILLO"], "ROJO": COLORES["ROJO"]}[
            datos_grafica["estados"][i]
        ] for i in range(len(zonas_list))
    ]

    # Convertir datos_grafica a JSON para la gráfica Chart.js
    datos_grafica_json = json.dumps(datos_grafica, default=str)

    # Tabla de zonas (html)
    filas_tabla = []
    for zona in zonas_list:
        m = metricas_zona[zona]
        color = COLORES[m["estado"]]
        rutas = len(m["rutas"])
        estado_txt = f"<span style='color:{color}; font-weight:bold;'>● {m['estado']}</span>"

        filas_tabla.append(f"""
        <tr style='background-color: {color}20;'>
            <td><strong>{zona}</strong></td>
            <td>{rutas}</td>
            <td>{m['total_cuentas']}</td>
            <td>{m['leidas']}</td>
            <td>{m['faltantes']}</td>
            <td>{m['pct_cobertura_lec']:.1f}%</td>
            <td>{m['avisos_impresos']}</td>
            <td>{m['avisos_faltantes']}</td>
            <td>{m['dias_sin_aviso']}</td>
            <td>{estado_txt}</td>
        </tr>
        """)

    tabla_zonas = "\n".join(filas_tabla)

    # Rutas críticas (ROJO o dias_sin_aviso > 3)
    rutas_criticas = []
    for zona in zonas_list:
        for ruta, datos_ruta in metricas_zona[zona]["rutas"].items():
            if datos_ruta["dias_sin_aviso"] > 3 or metricas_zona[zona]["estado"] == "ROJO":
                rutas_criticas.append({
                    "zona": zona,
                    "ruta": ruta,
                    "cuentas": datos_ruta["cuentas"],
                    "faltantes": datos_ruta["faltantes"],
                    "dias": datos_ruta["dias_sin_aviso"],
                })

    filas_criticas = "\n".join([
        f"""<tr>
            <td>{r['zona']}</td>
            <td>{r['ruta']}</td>
            <td>{r['cuentas']}</td>
            <td>{r['faltantes']}</td>
            <td style='color:red;'><strong>{r['dias']} días</strong></td>
        </tr>"""
        for r in sorted(rutas_criticas, key=lambda x: x["dias"], reverse=True)
    ])

    # HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor de Lecturas y Avisos de Pago</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            color: #333;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        header .meta {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .container {{
            max-width: 1400px;
            margin: 30px auto;
            padding: 0 20px;
        }}
        .kpis {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .kpi {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }}
        .kpi h3 {{
            color: #999;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}
        .kpi .numero {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .kpi .porcentaje {{
            font-size: 1.2em;
            color: #667eea;
        }}
        .semaforo-global {{
            text-align: center;
            font-size: 3em;
            margin: 20px 0;
        }}
        .seccion {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 40px;
        }}
        .seccion h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        table thead {{
            background: #f9f9f9;
            font-weight: bold;
        }}
        table th, table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        table tr:hover {{
            background: #f0f0f0;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
        }}
        @media (max-width: 768px) {{
            header h1 {{
                font-size: 1.5em;
            }}
            .kpis {{
                grid-template-columns: 1fr;
            }}
            table {{
                font-size: 0.9em;
            }}
            .chart-container {{
                height: 300px;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Monitor de Lecturas y Avisos de Pago</h1>
        <div class="meta">
            <p>Semana 35 | Corte: 28/08/2026 | Período: 01/08 - 28/08/2026</p>
            <p>Generado: {ahora}</p>
        </div>
    </header>

    <div class="container">
        <div class="semaforo-global">
            <span style="color: {COLORES[metricas_global['estado']]};;">●</span>
            <span style="font-size: 0.5em; vertical-align: super;">{metricas_global['estado']}</span>
        </div>

        <div class="kpis">
            <div class="kpi">
                <h3>Total de Cuentas Activas</h3>
                <div class="numero">{metricas_global['total_cuentas']:,}</div>
            </div>
            <div class="kpi">
                <h3>Lecturas Tomadas</h3>
                <div class="numero">{metricas_global['leidas']:,}</div>
                <div class="porcentaje">{metricas_global['pct_cobertura_lec']:.1f}% cobertura</div>
            </div>
            <div class="kpi">
                <h3>Lecturas Faltantes</h3>
                <div class="numero">{metricas_global['faltantes']:,}</div>
            </div>
            <div class="kpi">
                <h3>Avisos Impresos</h3>
                <div class="numero">{metricas_global['avisos_impresos']:,}</div>
                <div class="porcentaje">{metricas_global['pct_cobertura_avi']:.1f}% cobertura</div>
            </div>
        </div>

        <div class="seccion">
            <h2>Cobertura por Zona (Lecturas vs Avisos)</h2>
            <div class="chart-container">
                <canvas id="chartCobertura"></canvas>
            </div>
        </div>

        <div class="seccion">
            <h2>Detalle por Zona</h2>
            <table>
                <thead>
                    <tr>
                        <th>Zona</th>
                        <th>Rutas</th>
                        <th>Cuentas</th>
                        <th>Lecturas OK</th>
                        <th>Faltantes</th>
                        <th>% Cobertura Lec</th>
                        <th>Avisos Impresos</th>
                        <th>Sin Aviso</th>
                        <th>Días sin Impresión</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {tabla_zonas}
                </tbody>
            </table>
        </div>

        <div class="seccion">
            <h2>Rutas Críticas (Rojo o > 3 días sin impresión)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Zona</th>
                        <th>Ruta</th>
                        <th>Cuentas</th>
                        <th>Faltantes</th>
                        <th>Días sin Impresión</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_criticas if filas_criticas else "<tr><td colspan='5'>Sin rutas críticas</td></tr>"}
                </tbody>
            </table>
        </div>

    </div>

    <script>
        // Gráfica: Cobertura por zona
        const ctx = document.getElementById('chartCobertura').getContext('2d');
        const datosGrafica = {datos_grafica_json};
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: datosGrafica.zonas,
                datasets: [
                    {{
                        label: 'Cobertura Lecturas (%)',
                        data: datosGrafica.coberturas_lec,
                        backgroundColor: 'rgba(102, 126, 234, 0.6)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1,
                    }},
                    {{
                        label: 'Cobertura Avisos (%)',
                        data: datosGrafica.coberturas_avi,
                        backgroundColor: 'rgba(118, 75, 162, 0.6)',
                        borderColor: 'rgba(118, 75, 162, 1)',
                        borderWidth: 1,
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'top',
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    return html

# ============================================================================
# MAIN
# ============================================================================
def main():
    log("=== Generador de Dashboard: Lecturas Faltantes ===")

    if not CARPETA_IN.exists():
        CARPETA_IN.mkdir(parents=True, exist_ok=True)
        log(f"Creada carpeta: {CARPETA_IN}")

    if not CARPETA_OUT.exists():
        CARPETA_OUT.mkdir(parents=True, exist_ok=True)

    # Cargar datos
    log("Cargando datos...")
    df_lec = cargar_lecturas()
    df_avi = cargar_avisos()

    if df_lec.empty or df_avi.empty:
        log("ERROR: No se pudieron cargar los datos")
        return 1

    # Calcular métricas
    log("Calculando métricas...")
    metricas_zona, metricas_global = calcular_metricas(df_lec, df_avi)

    # Generar HTML
    log("Generando HTML...")
    html = generar_html(metricas_zona, metricas_global)

    # Guardar
    with open(ARCHIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"[OK] Dashboard generado: {ARCHIVO_HTML}")
    log(f"[OK] Total cuentas: {metricas_global['total_cuentas']:,}")
    log(f"[OK] Lecturas tomadas: {metricas_global['leidas']:,} ({metricas_global['pct_cobertura_lec']:.1f}%)")
    log(f"[OK] Avisos impresos: {metricas_global['avisos_impresos']:,} ({metricas_global['pct_cobertura_avi']:.1f}%)")
    log("=== LISTO ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
