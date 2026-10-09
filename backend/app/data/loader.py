
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTED_EXTENSIONS = {".csv", ".json", ".parquet", ".xlsx", ".xls"}


def list_datasets() -> list[dict[str, Any]]:
    """List supported dataset files without inventing records."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    datasets = []
    for path in sorted(RAW_DATA_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            datasets.append({
                "filename": path.name,
                "format": path.suffix.lower().lstrip("."),
                "size_bytes": path.stat().st_size,
            })

    return datasets


def load_dataset(filename: str) -> pd.DataFrame:
    """Load a dataset from data/raw using a validated filename."""
    if Path(filename).name != filename:
        raise ValueError("Provide a filename, not a path.")

    path = RAW_DATA_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {filename}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported dataset format: {path.suffix}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        return pd.read_json(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError("Unsupported dataset format.")


def inspect_dataset(filename: str) -> dict[str, Any]:
    """Return actual dataset metadata and a small data preview."""
    df = load_dataset(filename)

    columns = []
    for column in df.columns:
        columns.append({
            "name": str(column),
            "dtype": str(df[column].dtype),
            "missing_values": int(df[column].isna().sum()),
            "unique_values": int(df[column].nunique()),
        })

    preview = df.head(5).astype(object).where(pd.notna(df.head(5)), None)

    return {
        "filename": filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "preview": preview.to_dict(orient="records"),
    }
