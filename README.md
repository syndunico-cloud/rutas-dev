# Monitor de Lecturas Faltantes y Avisos de Pago

Sistema de monitoreo semanal para seguimiento de **lecturas tomadas** vs **lecturas faltantes** y su correlación con **impresión de avisos de pago**.

Cubre: **10 zonas → 272 rutas → ~85,300 cuentas activas**.

---

## 📊 Qué es

Un dashboard interactivo que muestra:

1. **KPIs globales**: total de cuentas, lecturas tomadas/faltantes, avisos impresos
2. **Tabla por zona**: detalle de cobertura, días sin impresión, estado (semáforo)
3. **Gráficas**: comparativa de cobertura de lecturas vs avisos por zona
4. **Rutas críticas**: identificación de rutas con >3 días sin impresión o estado ROJO

### Semáforo

- 🟢 **VERDE**: ≥90% cobertura avisos + ≤2 días sin impresión
- 🟡 **AMARILLO**: 70–89% cobertura O 3–5 días sin impresión
- 🔴 **ROJO**: <70% cobertura O >5 días sin impresión O sin ningún aviso

---

## 📁 Estructura

```
dashboard_lecturas/
├── input/                              # Archivos de entrada
│   ├── lecturas_semana_35.csv
│   └── avisos_semana_35.csv
├── output/                             # Salida
│   └── index.html                      # Dashboard generado
├── scripts/
│   └── procesar.py                     # Script de procesamiento
├── .github/
│   └── workflows/
│       └── generar_dashboard.yml       # GitHub Action
├── requirements.txt
└── README.md
```

---

## 🚀 Cómo usar

### 1. Instalación local

```bash
# Clonar o descargar este repositorio
cd dashboard_lecturas

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Preparar archivos de entrada

Coloca en la carpeta `input/`:

#### `lecturas_semana_XX.csv`

Columnas requeridas:
- `ZONA`: identificador de zona (ZONA_01, ZONA_02, etc.)
- `RUTA`: número de ruta
- `CUENTA`: número de cuenta
- `FECHA_PROGRAMADA`: fecha prevista
- `FECHA_LECTURA`: fecha real (vacío = faltante)
- `LECTURA`: valor leído
- `ESTADO`: `LEIDA` / `FALTANTE` / `INCIDENCIA`

#### `avisos_semana_XX.csv`

Columnas requeridas:
- `ZONA`: identificador de zona
- `RUTA`: número de ruta
- `CUENTA`: número de cuenta
- `FECHA_IMPRESION`: fecha de impresión (vacío = no impreso)
- `FOLIO`: número de folio/aviso
- `PERIODO`: período de facturación (ej. 2026-08)

**Nota:** El sufijo `_XX` en el nombre de archivo debe ser el número de semana ISO (01–52).

### 3. Ejecutar el script

```bash
python scripts/procesar.py
```

Esto genera `output/index.html` automáticamente.

### 4. Ver el dashboard

Abre en tu navegador:
```
output/index.html
```

El HTML es **autocontenido**: funciona offline sin dependencias externas (Chart.js viene de CDN con fallback).

---

## 🔄 Automatización con GitHub

Si subes este repositorio a GitHub, el dashboard se regenera automáticamente cada lunes a las 8:00 AM UTC.

### Configurar GitHub Pages

1. Ve a **Settings → Pages**
2. Selecciona **Branch**: `gh-pages`
3. El dashboard se publica en: `https://tuusuario.github.io/dashboard_lecturas/`

### Ejecutar manualmente

En GitHub:
1. Ve a **Actions**
2. Elige **Generar Dashboard**
3. Haz clic en **Run workflow**

---

## 📊 Convención de nombres

### Archivos de entrada

- `lecturas_semana_01.csv` → Semana 1
- `lecturas_semana_35.csv` → Semana 35 (vigente)
- `avisos_semana_01.csv` → Semana 1
- `avisos_semana_35.csv` → Semana 35 (vigente)

El script detecta automáticamente la semana más reciente y la procesa.

### Soporta múltiples semanas

Si hay datos de varias semanas en `input/`, el script procesa todo automáticamente:
- Cálculos por zona se hacen con los datos más recientes
- Se guarda un historial completo (útil para tendencias futuras)

---

## 🔧 Personalización

### Cambiar mapeo de columnas

Si tus archivos tienen nombres de columna distintos, edita `scripts/procesar.py`:

```python
MAPEO_LECTURAS = {
    "ZONA": "tu_nombre_zona",
    "RUTA": "tu_nombre_ruta",
    # ...
}

MAPEO_AVISOS = {
    "ZONA": "tu_nombre_zona",
    # ...
}
```

### Colores del semáforo

```python
COLORES = {
    "VERDE": "#4CAF50",
    "AMARILLO": "#FFC107",
    "ROJO": "#F44336",
}
```

### Criterios del semáforo

Edita la función `clasificar_semaforo()` en `scripts/procesar.py`.

---

## 📈 Métricas calculadas

Por zona:
- **Total de cuentas**: COUNT(CUENTA)
- **Lecturas tomadas**: COUNT(ESTADO='LEIDA')
- **Lecturas faltantes**: COUNT(ESTADO='FALTANTE')
- **% Cobertura de lecturas**: (tomadas / total) × 100
- **Avisos impresos**: COUNT(FECHA_IMPRESION no nulo)
- **% Cobertura de avisos**: (impresos / total) × 100
- **Días sin impresión**: hoy - max(FECHA_IMPRESION)
- **Estado (semáforo)**: basado en cobertura + días

---

## 💾 Soporta archivos

- ✅ `.csv` (UTF-8)
- ✅ `.xlsx` (Excel)

El script detecta automáticamente el formato y lo carga.

---

## ⚡ Rendimiento

- Tiempo de generación: < 30 segundos para ~85,300 registros
- Sin dependencias de backend (Flask, FastAPI, etc.)
- HTML puro + Chart.js (CDN)
- Responsive: funciona en desktop, tablet, móvil

---

## 🐛 Solución de problemas

### "No se encontraron archivos lecturas_*.csv"

- Verifica que los archivos están en `input/`
- Comprueba que el nombre cumple `lecturas_semana_XX.csv`

### Las columnas no se reconocen

- Edita `MAPEO_LECTURAS` y `MAPEO_AVISOS` en `scripts/procesar.py`
- Asegúrate de que los nombres exactos coincidan

### El gráfico Chart.js no aparece

- Verifica que tienes internet (CDN)
- O descarga `chart.min.js` localmente y ajusta la referencia en `procesar.py`

---

## 📞 Soporte

Para modificaciones, reporta un issue o contacta al equipo.

---

**Última actualización**: 2026-08-28  
**Versión**: 1.0
