#!/usr/bin/env python3
import os
import re
from pathlib import Path

import pandas as pd

FILTER_ZERO_AS_EMPTY = False


def s(x):
    try:
        return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)
    except Exception:
        return str(x)


def to_number(cell):
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return None
    ss = s(cell)
    keep = re.sub(r"[^0-9,\.]", "", ss)
    if not keep:
        return None
    if ("," in keep) and ("." in keep):
        keep = keep.replace(".", "").replace(",", ".")
    else:
        keep = keep.replace(",", ".")
    try:
        return float(keep)
    except Exception:
        return None


def code_item(codigo, producto):
    sc = s(codigo).strip()
    if producto is not None and s(producto).strip() != "" and sc.endswith("-"):
        return sc[:-1]
    return sc.replace(" - ", "  ")


def read_excel_file(input_path: Path):
    suffix = input_path.suffix.lower()
    if suffix == ".xlsx":
        return pd.read_excel(input_path, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(input_path, engine="xlrd")
    raise ValueError("Formato no soportado. Solo se aceptan .xls y .xlsx")


def transform_dataframe(df: pd.DataFrame, force_d_codes=None) -> pd.DataFrame:
    force_d_codes = force_d_codes or set()

    col_codigo = "Código"
    col_producto = "Producto"
    col_c = "Precio Unitario - Medida"
    col_d = "Precio Unitario - Medida.1"

    required = [col_codigo, col_producto, col_c]
    if not all(c in df.columns for c in required):
        raise ValueError(
            "Columnas esperadas: 'Código', 'Producto', 'Precio Unitario - Medida' (+ '.1' opcional). "
            f"Columnas reales: {list(df.columns)}"
        )

    c_text = df[col_c].astype(str)
    d_text = df[col_d].astype(str) if col_d in df.columns else pd.Series([""] * len(df))

    c_num = df[col_c].apply(to_number)
    d_num = df[col_d].apply(to_number) if col_d in df.columns else pd.Series([None] * len(df))

    use_d = []
    for code, ct, dt in zip(df[col_codigo].astype(str), c_text, d_text):
        if code in force_d_codes:
            use_d.append(True)
        else:
            use_d.append(("UN" in dt.upper()) and ("KG" in ct.upper()))

    precio = []
    for ud, cval, dval in zip(use_d, c_num, d_num):
        if ud and dval is not None:
            precio.append(dval)
        else:
            precio.append(cval)

    out = pd.DataFrame({
        "Código": [code_item(c, p) for c, p in zip(df[col_codigo], df[col_producto])],
        "Producto": df[col_producto],
        "Precio": precio,
    })

    mask_valido = out["Precio"].notna()
    if FILTER_ZERO_AS_EMPTY:
        mask_valido &= (out["Precio"] != 0)
    return out[mask_valido].reset_index(drop=True)


def load_force_d_codes(force_d_file: Path | None) -> set[str]:
    if force_d_file is None or not force_d_file.exists():
        return set()

    codes = set()
    for line in force_d_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            codes.add(line)
    return codes


def transform_excel(input_path: Path, output_path: Path, force_d_file: Path | None = None) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)

    df = read_excel_file(input_path)
    force_d_codes = load_force_d_codes(force_d_file)
    out = transform_dataframe(df, force_d_codes=force_d_codes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl", mode="w") as writer:
        out.to_excel(writer, index=False, header=False, sheet_name="Hoja1")
    return output_path


def main():
    base_dir = Path(__file__).resolve().parent
    input_candidates = [
        base_dir / "Lista base.xlsx",
        base_dir / "Lista base.xls",
    ]

    input_path = next((p for p in input_candidates if p.exists()), None)
    if input_path is None:
        print("ERROR al leer el archivo base: No encuentro 'Lista base.xlsx' ni 'Lista base.xls' en esta carpeta.")
        return

    output_path = base_dir / "for_import" / "Lista de import.xlsx"
    force_d_file = base_dir / "forzar_D.txt"

    try:
        transform_excel(input_path, output_path, force_d_file=force_d_file)
        print(f"OK -> {output_path} (SIN encabezado)")
    except PermissionError:
        alt = base_dir / "for_import" / "Lista de import (nuevo).xlsx"
        transform_excel(input_path, alt, force_d_file=force_d_file)
        print(f"Advertencia: '{output_path}' estaba en uso. Guardé en: {alt}")
    except Exception as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
