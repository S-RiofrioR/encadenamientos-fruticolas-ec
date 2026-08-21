###############################################################################
# SCRIPT: 01_etl_supercias_sri.R  (v4.2 - VERSION FINAL DATOS REALES)
#
# Correcciones integradas:
#   [v4.0] Formato real ranking_2024.xlsx y sri_ventas_*.csv
#   [v4.1] Columna de actividad detectada dinamicamente (actividad_econ_mica)
#   [v4.2] make.unique() para nombres duplicados (posici_n____, a_o____)
#
# SALIDAS:
#   data/processed/df_empresas_fruticolas.csv
#   data/processed/df_sri_compras_ventas.csv
###############################################################################

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(readxl)
  library(stringr)
  library(fs)
})

options(scipen = 999, digits = 2)

# ---------------------------------------------------------------------------
# RUTAS
# ---------------------------------------------------------------------------
SCRIPT_DIR <- this.path::this.dir()
BASE_DIR   <- fs::path_dir(SCRIPT_DIR)
if (!fs::dir_exists(fs::path(BASE_DIR, "data", "raw"))) BASE_DIR <- fs::path_dir(BASE_DIR)
RAW_DIR  <- fs::path(BASE_DIR, "data", "raw")
PROC_DIR <- fs::path(BASE_DIR, "data", "processed")
fs::dir_create(PROC_DIR)

cat("=== ETL v4.2 (formatos reales) ===\n")
cat("Directorio base:", BASE_DIR, "\n")

# ---------------------------------------------------------------------------
# AUXILIARES
# ---------------------------------------------------------------------------
to_num <- function(x) {
  if (is.numeric(x)) return(x)
  x <- str_trim(as.character(x))
  out <- suppressWarnings(as.numeric(x))
  vals <- out[x != "" & !is.na(x)]
  if (length(vals) > 0 && mean(is.na(vals)) > 0.5)
    out <- suppressWarnings(as.numeric(str_remove_all(x, ",")))
  out
}

# ===========================================================================
# 1. SUPERCias: RANKING 2024
# ===========================================================================
cat("\n[1/2] SUPERCias - ranking_2024.xlsx\n")
df <- read_excel(fs::path(RAW_DIR, "ranking_2024.xlsx"), skip = 1)

# Limpieza de nombres: "Activio\n2024" -> "activo"
names(df) <- str_replace_all(names(df), "\n.*$", "")
names(df) <- tolower(names(df))
names(df) <- str_replace_all(names(df), "activio", "activo")   # typo oficial
names(df) <- str_replace_all(names(df), "[^a-z_]", "_")
names(df) <- make.unique(names(df))   # v4.2: posici_n____, posici_n____.1, ...

# Deteccion DINAMICA de la columna de actividad (la o acentuada -> _)
col_act <- grep("^actividad", names(df), value = TRUE)[1]
cat("  Columna actividad detectada:", col_act, "\n")

# Extraer codigo CIIU embebido: "A0122.09 - ..." -> letra + 4 digitos
df$actividad_txt <- str_trim(as.character(df[[col_act]]))
m_ciiu   <- str_match(df$actividad_txt, "^([A-Z])([0-9]{4})")
df$letra <- m_ciiu[, 2]
df$ciiu4 <- m_ciiu[, 3]

# Clasificacion por eslabon de la cadena fruticola
df$segmento <- case_when(
  df$letra == "A" & df$ciiu4 %in% c("0121","0122","0123","0124","0125","0126","0127")
  ~ "cultivo_fruticola",
  df$letra == "G" & df$ciiu4 %in% c("4620","4630","4631") ~ "comercio_mayorista",
  df$letra == "C" & df$ciiu4 %in% c("1030","1073")        ~ "procesamiento",
  TRUE ~ NA_character_
)

# Flag de frutas de alto valor (texto de la actividad)
df$foco_alto_valor <- str_detect(
  df$actividad_txt,
  "(?i)ar[aá]ndano|pitahaya|uvilla|aguacate|granadilla|mora|frambuesa|fresa"
)

df_f <- df %>% filter(!is.na(segmento))

# Homologacion financiera (Pasivo derivado por identidad contable)
df_out <- df_f %>%
  transmute(
    ruc_norm        = str_trim(as.character(expediente)),   # ID = Expediente
    razon_social    = str_trim(as.character(nombre)),
    ciiu_norm       = paste0(letra, ciiu4),
    actividad       = actividad_txt,
    segmento        = segmento,
    foco_alto_valor = foco_alto_valor,
    provincia       = str_trim(as.character(provincia)),
    cant_empleados  = to_num(cant__empleados),
    activo_total    = to_num(activo),
    patrimonio      = to_num(patrimonio),
    pasivo_total    = to_num(activo) - to_num(patrimonio),  # identidad contable
    ventas_netas    = to_num(ingreso_por_ventas),
    utilidad_operativa = to_num(utilidad_antes_del_impuesto),
    utilidad_neta   = to_num(utilidad_neta),
    anio            = 2024
  ) %>%
  filter(!is.na(ventas_netas), ventas_netas > 0)

cat(sprintf("  Empresas cadena fruticola: %d\n", nrow(df_out)))
print(as.data.frame(count(df_out, segmento)))
cat(sprintf("  Empresas con foco alto valor (arandano/pitahaya/uvilla/aguacate): %d\n",
            sum(df_out$foco_alto_valor, na.rm = TRUE)))

# QA: nulos en columnas financieras
cat(sprintf("  QA - activo nulo: %d | patrimonio nulo: %d | utilidad nula: %d\n",
            sum(is.na(df_out$activo_total)),
            sum(is.na(df_out$patrimonio)),
            sum(is.na(df_out$utilidad_neta))))

write_csv(df_out, fs::path(PROC_DIR, "df_empresas_fruticolas.csv"))
cat("  -> df_empresas_fruticolas.csv\n")

cat("\n  TOP 5 por ventas (cadena fruticola):\n")
print(as.data.frame(
  df_out %>% arrange(desc(ventas_netas)) %>%
    select(razon_social, segmento, provincia, ventas_netas, utilidad_neta) %>%
    head(5)
))

# ===========================================================================
# 2. SRI: VENTAS / COMPRAS / EXPORTACIONES (delimitador '|')
# ===========================================================================
cat("\n[2/2] SRI - sri_ventas_*.csv\n")
archivos_sri <- fs::dir_ls(RAW_DIR, regexp = "(?i)sri.*\\.(csv|txt)$")

df_sri <- tibble()
for (arch in archivos_sri) {
  cat("  Leyendo:", basename(arch), "\n")
  d <- read_delim(
    arch, delim = "|", trim_ws = TRUE, show_col_types = FALSE,
    locale = locale(encoding = "Latin1", decimal_mark = ",")
  )
  names(d) <- tolower(names(d))
  names(d) <- str_replace_all(names(d), "a.o", "anio")   # AÑO -> anio
  d$anio <- as.integer(d$anio)
  df_sri <- bind_rows(df_sri, d)
}

agg_sri <- df_sri %>%
  filter(codigo_sector_n1 %in% c("A", "C", "G")) %>%
  mutate(
    eslabon = case_when(
      codigo_sector_n1 == "A" ~ "A_cultivo",
      codigo_sector_n1 == "C" ~ "C_procesamiento",
      codigo_sector_n1 == "G" ~ "G_comercio"
    )
  ) %>%
  group_by(anio, eslabon, provincia) %>%
  summarise(
    ventas        = sum(total_ventas,  na.rm = TRUE),
    compras       = sum(total_compras, na.rm = TRUE),
    exportaciones = sum(exportaciones, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    margen_valor_agregado_pct = round((ventas - compras) / pmax(ventas, 1) * 100, 2),
    intensidad_export_pct     = round(exportaciones / pmax(ventas, 1) * 100, 2)
  )

cat(sprintf("  Registros agregados SRI: %d\n", nrow(agg_sri)))

cat("\n  Intensidad exportadora por eslabon (2024, nacional):\n")
print(as.data.frame(
  agg_sri %>% filter(anio == 2024) %>%
    group_by(eslabon) %>%
    summarise(
      ventas_M       = round(sum(ventas) / 1e6, 1),
      exp_M          = round(sum(exportaciones) / 1e6, 1),
      int_export_pct = round(100 * sum(exportaciones) / sum(ventas), 2),
      .groups = "drop"
    )
))

write_csv(agg_sri, fs::path(PROC_DIR, "df_sri_compras_ventas.csv"))
cat("  -> df_sri_compras_ventas.csv\n")

cat("\n=== ETL v4.2 COMPLETADO ===\n")