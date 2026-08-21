"""Diagnostico rapido: que valores toma la variable de rama detectada."""
from pathlib import Path
import pyreadstat

BASE_DIR = Path(__file__).resolve().parents[1]
ENEMDU_SAV = BASE_DIR / "data" / "raw" / "1_BDD_ENEMDU_2025_12_SPSS" / "enemdu_persona_2025_12.sav"

df, meta = pyreadstat.read_sav(ENEMDU_SAV)

# Buscar cualquier columna con "rama" o "activ"
candidatas = [c for c in meta.column_names if "rama" in c.lower() or "activ" in c.lower() or "ciii" in c.lower()]
print("Columnas candidatas de rama/actividad:", candidatas)

for c in candidatas:
    print(f"\n=== {c} ===")
    print("Etiqueta:", meta.column_names_labels.get(c, "N/A") if hasattr(meta, "column_names_labels") else "")
    print("Categorias (value labels):", meta.variable_value_labels.get(c, "sin etiquetas"))
    print("Valores unicos en datos:", df[c].dropna().unique()[:20])
    print("Conteos:\n", df[c].value_counts().head(15))