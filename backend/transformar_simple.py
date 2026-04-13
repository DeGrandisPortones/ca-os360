#!/usr/bin/env python3
import os
import re
from pathlib import Path

import pandas as pd

FILTER_ZERO_AS_EMPTY = False

DIVIDE_BY_10_CODES = {
    "ALAMB140200",
    "ALAMB140201",
    "ALAMB140202",
    "ALAMB140203",
    "ALAMB140204",
    "ALAMB140205",
    "ALAMB140206",
}

MULTIPLY_BY_10_CODES = {
    "CLAVO142100",
    "CLAVO142103",
    "CLAVO142108",
    "CLAVO142009",
    "CLAVO142010",
    "CLAVO142011",
    "CLAVO142012",
    "CLAVO142302",
    "CLAVO142303",
    "CLAVO142305",
    "CLAVO142306",
}


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


def normalize_price_columns(df: pd.DataFrame):
    columns = set(df.columns)

    if "Precio Unitario - Medida" in columns:
        c_text = df["Precio Unitario - Medida"].astype(str)
        d_text = df["Precio Unitario - Medida.1"].astype(str) if "Precio Unitario - Medida.1" in columns else pd.Series([""] * len(df))

        c_num = df["Precio Unitario - Medida"].apply(to_number)
        d_num = df["Precio Unitario - Medida.1"].apply(to_number) if "Precio Unitario - Medida.1" in columns else pd.Series([None] * len(df))
        return c_text, d_text, c_num, d_num

    if "Precio Unitario" in columns and "Medida" in columns:
        c_price = df["Precio Unitario"]
        c_measure = df["Medida"]

        d_price = df["Precio Unitario.1"] if "Precio Unitario.1" in columns else pd.Series([None] * len(df))
        d_measure = df["Medida.1"] if "Medida.1" in columns else pd.Series([""] * len(df))

        c_text = (c_price.apply(s) + " " + c_measure.apply(s)).str.strip()
        d_text = (d_price.apply(s) + " " + d_measure.apply(s)).str.strip()

        c_num = c_price.apply(to_number)
        d_num = d_price.apply(to_number)
        return c_text, d_text, c_num, d_num

    raise ValueError(
        "Columnas esperadas: 'Código', 'Producto' y alguno de estos formatos: "
        "(1) 'Precio Unitario - Medida' (+ '.1' opcional) o "
        "(2) 'Precio Unitario', 'Medida', 'Precio Unitario.1', 'Medida.1'. "
        f"Columnas reales: {list(df.columns)}"
    )


def adjust_price_by_code(code, price):
    if price is None or (isinstance(price, float) and pd.isna(price)):
        return price

    normalized_code = s(code).strip()
    if normalized_code in DIVIDE_BY_10_CODES:
        return price / 10
    if normalized_code in MULTIPLY_BY_10_CODES:
        return price * 10
    return price


def transform_dataframe(df: pd.DataFrame, force_d_codes=None) -> pd.DataFrame:
    force_d_codes = force_d_codes or set()

    col_codigo = "Código"
    col_producto = "Producto"

    required = [col_codigo, col_producto]
    if not all(c in df.columns for c in required):
        raise ValueError(
            "Faltan columnas obligatorias. "
            f"Columnas reales: {list(df.columns)}"
        )

    c_text, d_text, c_num, d_num = normalize_price_columns(df)

    use_d = []
    for code, ct, dt in zip(df[col_codigo].astype(str), c_text, d_text):
        if code in force_d_codes:
            use_d.append(True)
        else:
            use_d.append(("UN" in dt.upper()) and ("KG" in ct.upper()))

    precio = []
    for code, ud, cval, dval in zip(df[col_codigo], use_d, c_num, d_num):
        if ud and dval is not None:
            selected_price = dval
        else:
            selected_price = cval
        precio.append(adjust_price_by_code(code, selected_price))

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
