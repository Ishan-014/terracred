
from fastapi import APIRouter, HTTPException

from backend.app.data.loader import (
    inspect_dataset,
    list_datasets,
)

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.get("")
def get_datasets():
    return {"datasets": list_datasets()}


@router.get("/{filename}/inspect")
def get_dataset_metadata(filename: str):
    try:
        return inspect_dataset(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not inspect the dataset. Check its format and contents.",
        ) from exc
