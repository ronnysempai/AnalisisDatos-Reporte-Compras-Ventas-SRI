"""
=============================================================================
  ETL - Reporte SRI Ecuador 2024
  Servicio de Rentas Internas - Ventas y Compras Mensuales
=============================================================================
  Autor  : Ronny Solis | Analista de Datos
  Fecha  : 2024
  Fuente : Dataset oficial del SRI (sri_ventas_2024.csv)
-----------------------------------------------------------------------------
  Descripcion:
    Script de Extraccion, Limpieza y Transformacion (ETL) de los datos de
    ventas y compras declarados ante el SRI del Ecuador en el anio 2024.

    El script produce los siguientes artefactos en la carpeta resultados/:
      - resumen_mensual.csv       -> Totales agrupados por mes
      - top_provincias.csv        -> Top 10 provincias por volumen de ventas
      - sectores_economicos.csv   -> Top 15 sectores (codigo CIIU nivel 1)
      - kpis_generales.csv        -> KPIs anuales consolidados
=============================================================================
"""

import os
import sys
import pandas as pd

# Forzar UTF-8 en la salida de consola (necesario en Windows)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Rutas ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "DataSet", "sri_ventas_2024.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "resultados")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =============================================================================
# FASE 1: EXTRACCION
# =============================================================================
print("=" * 65)
print("  FASE 1 - EXTRACCION")
print("=" * 65)

df = pd.read_csv(
    INPUT_FILE,
    sep="|",            # separador de campo
    encoding="latin-1", # codificacion del archivo fuente
    decimal=",",        # decimales con coma (formato ecuatoriano)
)

print(f"[OK] Archivo cargado: {INPUT_FILE}")
print(f"     Filas    : {df.shape[0]:,}")
print(f"     Columnas : {df.shape[1]}")
print(f"\n     Columnas disponibles:")
for col in df.columns:
    print(f"       - {col}")


# =============================================================================
# FASE 2: LIMPIEZA
# =============================================================================
print("\n" + "=" * 65)
print("  FASE 2 - LIMPIEZA")
print("=" * 65)

# ── 2.1 Renombrar columna ANO ──────────────────────────────────────────────
# El primer campo puede llegar como 'A?O' o similar segun la codificacion;
# se detecta y renombra de forma segura.
df.columns = [c.strip() for c in df.columns]
rename_map = {
    c: "ANO"
    for c in df.columns
    if c.upper().startswith("A") and "O" in c.upper() and len(c) <= 4
}
if rename_map:
    df.rename(columns=rename_map, inplace=True)
    print(f"[OK] Columna anio renombrada: {list(rename_map.keys())[0]} -> ANO")
else:
    df.rename(columns={df.columns[0]: "ANO"}, inplace=True)
    print("[OK] Columna anio normalizada -> ANO")

# ── 2.2 Valores nulos ──────────────────────────────────────────────────────
nulos_total = df.isnull().sum().sum()
print(f"\n[OK] Revision de valores nulos: {nulos_total} encontrados en total")
if nulos_total > 0:
    print(df.isnull().sum()[df.isnull().sum() > 0].to_string())
    # Ausencia de declaracion equivale a 0
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].fillna(0)
    print("     -> Valores nulos numericos reemplazados con 0")

# ── 2.3 Tipos de datos ─────────────────────────────────────────────────────
print(f"\n[OK] Tipos de datos detectados:")
print(df.dtypes.to_string())

# ── 2.4 Validacion de meses ────────────────────────────────────────────────
meses_unicos = sorted(df["MES"].unique())
print(f"\n[OK] Meses presentes: {meses_unicos}")
meses_faltantes = [m for m in range(1, 13) if m not in meses_unicos]
if meses_faltantes:
    print(f"[WARN] Meses sin datos: {meses_faltantes}")
else:
    print("     -> Los 12 meses estan presentes en el dataset.")

# ── 2.5 Validacion de anio ────────────────────────────────────────────────
anos_unicos = df["ANO"].unique()
print(f"\n[OK] Anios presentes: {anos_unicos}")
if len(anos_unicos) > 1:
    print("[WARN] Se encontraron multiples anios. Filtrando solo 2024 ...")
    df = df[df["ANO"] == 2024].copy()
    print(f"     -> Registros tras el filtro: {df.shape[0]:,}")

# ── 2.6 Normalizar texto ──────────────────────────────────────────────────
df["PROVINCIA"] = df["PROVINCIA"].str.strip().str.upper()
df["CANTON"]    = df["CANTON"].str.strip().str.upper()
print(f"\n[OK] PROVINCIA y CANTON normalizados (strip + upper)")

print(f"\n     Resumen del dataset limpio:")
print(f"     Filas     : {df.shape[0]:,}")
print(f"     Provincias: {df['PROVINCIA'].nunique()}")
print(f"     Cantones  : {df['CANTON'].nunique()}")
print(f"     Sectores  : {df['CODIGO_SECTOR_N1'].nunique()}")


# =============================================================================
# FASE 3: TRANSFORMACION
# =============================================================================
print("\n" + "=" * 65)
print("  FASE 3 - TRANSFORMACION")
print("=" * 65)

MESES_ESP = {
    1: "Enero",      2: "Febrero",   3: "Marzo",
    4: "Abril",      5: "Mayo",      6: "Junio",
    7: "Julio",      8: "Agosto",    9: "Septiembre",
    10: "Octubre",   11: "Noviembre",12: "Diciembre",
}

# ── 3.1 Resumen mensual ────────────────────────────────────────────────────
print("\n[3.1] Agregacion mensual ...")

resumen_mensual = (
    df.groupby("MES")
    .agg(
        TOTAL_VENTAS      = ("TOTAL_VENTAS",           "sum"),
        TOTAL_COMPRAS     = ("TOTAL_COMPRAS",          "sum"),
        VENTAS_TARIFA_15  = ("VENTAS_NETAS_TARIFA_12", "sum"),  # tarifa 15% (antes 12%)
        VENTAS_TARIFA_0   = ("VENTAS_NETAS_TARIFA_0",  "sum"),
        EXPORTACIONES     = ("EXPORTACIONES",          "sum"),
        COMPRAS_TARIFA_15 = ("COMPRAS_NETAS_TARIFA_12","sum"),
        COMPRAS_TARIFA_0  = ("COMPRAS_NETAS_TARIFA_0", "sum"),
        IMPORTACIONES     = ("IMPORTACIONES",          "sum"),
        COMPRAS_RISE      = ("COMPRAS_RISE",           "sum"),
    )
    .reset_index()
    .sort_values("MES")
)

resumen_mensual["NOMBRE_MES"]      = resumen_mensual["MES"].map(MESES_ESP)
resumen_mensual["BALANCE"]         = resumen_mensual["TOTAL_VENTAS"] - resumen_mensual["TOTAL_COMPRAS"]
resumen_mensual["TOTAL_VENTAS_M"]  = (resumen_mensual["TOTAL_VENTAS"]  / 1e6).round(2)
resumen_mensual["TOTAL_COMPRAS_M"] = (resumen_mensual["TOTAL_COMPRAS"] / 1e6).round(2)
resumen_mensual["BALANCE_M"]       = (resumen_mensual["BALANCE"]       / 1e6).round(2)

print(f"[OK] Resumen mensual generado ({len(resumen_mensual)} filas)")
print(
    resumen_mensual[["NOMBRE_MES", "TOTAL_VENTAS_M", "TOTAL_COMPRAS_M", "BALANCE_M"]]
    .to_string(index=False)
)

# ── 3.2 Top 10 provincias por ventas ──────────────────────────────────────
print("\n[3.2] Top 10 provincias por ventas ...")

top_provincias = (
    df.groupby("PROVINCIA")
    .agg(
        TOTAL_VENTAS  = ("TOTAL_VENTAS",  "sum"),
        TOTAL_COMPRAS = ("TOTAL_COMPRAS", "sum"),
    )
    .reset_index()
    .sort_values("TOTAL_VENTAS", ascending=False)
    .head(10)
    .reset_index(drop=True)
)

total_ventas_pais = df["TOTAL_VENTAS"].sum()
top_provincias["PARTICIPACION_PCT"] = (
    top_provincias["TOTAL_VENTAS"] / total_ventas_pais * 100
).round(2)
top_provincias["BALANCE"]  = top_provincias["TOTAL_VENTAS"] - top_provincias["TOTAL_COMPRAS"]
top_provincias["VENTAS_M"] = (top_provincias["TOTAL_VENTAS"]  / 1e6).round(2)
top_provincias["COMPRAS_M"]= (top_provincias["TOTAL_COMPRAS"] / 1e6).round(2)
top_provincias["BALANCE_M"]= (top_provincias["BALANCE"]       / 1e6).round(2)

print("[OK] Top 10 provincias generado")
print(
    top_provincias[["PROVINCIA", "VENTAS_M", "COMPRAS_M", "PARTICIPACION_PCT"]]
    .to_string(index=False)
)

# ── 3.3 Sectores economicos (CIIU nivel 1) ────────────────────────────────
print("\n[3.3] Sectores economicos (CIIU nivel 1, Top 15) ...")

sectores = (
    df.groupby("CODIGO_SECTOR_N1")
    .agg(
        TOTAL_VENTAS  = ("TOTAL_VENTAS",  "sum"),
        TOTAL_COMPRAS = ("TOTAL_COMPRAS", "sum"),
        REGISTROS     = ("MES",           "count"),
    )
    .reset_index()
    .sort_values("TOTAL_VENTAS", ascending=False)
    .head(15)
    .reset_index(drop=True)
)

sectores["PARTICIPACION_PCT"] = (sectores["TOTAL_VENTAS"] / total_ventas_pais * 100).round(2)
sectores["BALANCE"]  = sectores["TOTAL_VENTAS"] - sectores["TOTAL_COMPRAS"]
sectores["VENTAS_M"] = (sectores["TOTAL_VENTAS"]  / 1e6).round(2)
sectores["COMPRAS_M"]= (sectores["TOTAL_COMPRAS"] / 1e6).round(2)

print(f"[OK] Sectores economicos generado ({len(sectores)} sectores)")
print(
    sectores[["CODIGO_SECTOR_N1", "VENTAS_M", "COMPRAS_M", "PARTICIPACION_PCT"]]
    .to_string(index=False)
)

# ── 3.4 KPIs generales ────────────────────────────────────────────────────
print("\n[3.4] KPIs generales anuales ...")

kpis = pd.DataFrame([{
    "TOTAL_VENTAS_USD":       df["TOTAL_VENTAS"].sum(),
    "TOTAL_COMPRAS_USD":      df["TOTAL_COMPRAS"].sum(),
    "EXPORTACIONES_USD":      df["EXPORTACIONES"].sum(),
    "IMPORTACIONES_USD":      df["IMPORTACIONES"].sum(),
    "VENTAS_TARIFA_15_USD":   df["VENTAS_NETAS_TARIFA_12"].sum(),
    "VENTAS_TARIFA_0_USD":    df["VENTAS_NETAS_TARIFA_0"].sum(),
    "COMPRAS_TARIFA_15_USD":  df["COMPRAS_NETAS_TARIFA_12"].sum(),
    "COMPRAS_TARIFA_0_USD":   df["COMPRAS_NETAS_TARIFA_0"].sum(),
    "COMPRAS_RISE_USD":       df["COMPRAS_RISE"].sum(),
    "BALANCE_COMERCIAL_USD":  df["TOTAL_VENTAS"].sum() - df["TOTAL_COMPRAS"].sum(),
    "TOTAL_REGISTROS":        len(df),
    "MES_MAYOR_VENTAS":       MESES_ESP[
        resumen_mensual.loc[resumen_mensual["TOTAL_VENTAS"].idxmax(), "MES"]
    ],
    "MES_MAYOR_COMPRAS":      MESES_ESP[
        resumen_mensual.loc[resumen_mensual["TOTAL_COMPRAS"].idxmax(), "MES"]
    ],
    "PROVINCIA_LIDER_VENTAS": top_provincias.loc[0, "PROVINCIA"],
}])

print("[OK] KPIs generales calculados:")
for col in kpis.columns:
    val = kpis[col].values[0]
    if isinstance(val, float):
        print(f"     {col:<35}: ${val:>22,.2f}")
    else:
        print(f"     {col:<35}: {val}")


# =============================================================================
# FASE 4: EXPORTACION
# =============================================================================
print("\n" + "=" * 65)
print("  FASE 4 - EXPORTACION")
print("=" * 65)

cols_mensual = [
    "MES", "NOMBRE_MES",
    "TOTAL_VENTAS", "TOTAL_COMPRAS", "BALANCE",
    "TOTAL_VENTAS_M", "TOTAL_COMPRAS_M", "BALANCE_M",
    "VENTAS_TARIFA_15", "VENTAS_TARIFA_0", "EXPORTACIONES",
    "COMPRAS_TARIFA_15", "COMPRAS_TARIFA_0", "IMPORTACIONES", "COMPRAS_RISE",
]
cols_prov = [
    "PROVINCIA",
    "TOTAL_VENTAS", "TOTAL_COMPRAS", "BALANCE",
    "VENTAS_M", "COMPRAS_M", "BALANCE_M", "PARTICIPACION_PCT",
]
cols_sector = [
    "CODIGO_SECTOR_N1",
    "TOTAL_VENTAS", "TOTAL_COMPRAS", "BALANCE",
    "VENTAS_M", "COMPRAS_M", "PARTICIPACION_PCT", "REGISTROS",
]

archivos = {
    "resumen_mensual.csv":     (resumen_mensual[cols_mensual], "Resumen mensual"),
    "top_provincias.csv":      (top_provincias[cols_prov],     "Top 10 provincias"),
    "sectores_economicos.csv": (sectores[cols_sector],         "Sectores economicos"),
    "kpis_generales.csv":      (kpis,                          "KPIs generales"),
}

for filename, (dataframe, descripcion) in archivos.items():
    ruta = os.path.join(OUTPUT_DIR, filename)
    dataframe.to_csv(ruta, index=False, encoding="utf-8-sig", decimal=".")
    print(f"[OK] {descripcion:<25} -> {ruta}")

print(f"\n{'=' * 65}")
print(f"  ETL completado exitosamente.")
print(f"  Archivos generados en: {OUTPUT_DIR}")
print(f"{'=' * 65}\n")
