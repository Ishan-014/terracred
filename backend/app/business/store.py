from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from backend.app.business.models import (
    BusinessProfile,
    OperationalVulnerability,
    SupplierRelationship,
)


def default_database_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    database_dir = root / "data"
    database_dir.mkdir(exist_ok=True, parents=True)
    return database_dir / "terracred.db"


class BusinessStore:
    def __init__(self, database_path: str | os.PathLike[str] | None = None):
        self.database_path = str(Path(database_path) if database_path is not None else os.getenv("TERRACRED_DB_PATH", default_database_path()))
        self._lock = RLock()
        database_file = Path(self.database_path)
        database_file.parent.mkdir(exist_ok=True, parents=True)
        self._connection = sqlite3.connect(self.database_path, timeout=30, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS businesses (
                    business_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS suppliers (
                    supplier_id TEXT PRIMARY KEY,
                    business_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS operational_vulnerability (
                    vulnerability_id TEXT PRIMARY KEY,
                    business_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
                )
                """
            )

    def _serialize_model(self, model) -> str:
        return json.dumps(model.model_dump(mode="json"), separators=(",", ":"), default=str)

    def create_business(self, profile: BusinessProfile) -> BusinessProfile:
        with self._lock:
            with self._connection:
                try:
                    self._connection.execute(
                        "INSERT INTO businesses (business_id, payload) VALUES (?, ?)",
                        (profile.business_id, self._serialize_model(profile)),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError(f"Business '{profile.business_id}' already exists.") from exc
            return profile

    def get_business(self, business_id: str) -> BusinessProfile | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM businesses WHERE business_id = ?",
                (business_id,),
            ).fetchone()
            if row is None:
                return None
            return BusinessProfile.model_validate_json(row["payload"])

    def list_businesses(self) -> list[BusinessProfile]:
        with self._lock:
            rows = self._connection.execute("SELECT payload FROM businesses ORDER BY rowid").fetchall()
            return [BusinessProfile.model_validate_json(row["payload"]) for row in rows]

    def update_business(self, business_id: str, update: dict) -> BusinessProfile | None:
        with self._lock:
            existing = self.get_business(business_id)
            if existing is None:
                return None
            updated = existing.model_copy(update=update)
            updated.updated_at = datetime.now(timezone.utc)
            with self._connection:
                self._connection.execute(
                    "UPDATE businesses SET payload = ? WHERE business_id = ?",
                    (self._serialize_model(updated), business_id),
                )
            return updated

    def add_supplier(self, business_id: str, supplier: SupplierRelationship) -> SupplierRelationship:
        with self._lock:
            if self.get_business(business_id) is None:
                raise KeyError(f"Business '{business_id}' does not exist.")
            with self._connection:
                try:
                    self._connection.execute(
                        "INSERT INTO suppliers (supplier_id, business_id, payload) VALUES (?, ?, ?)",
                        (supplier.supplier_id, business_id, self._serialize_model(supplier)),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError(f"Supplier '{supplier.supplier_id}' already exists.") from exc
            return supplier

    def list_suppliers(self, business_id: str) -> list[SupplierRelationship]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT payload FROM suppliers WHERE business_id = ? ORDER BY rowid",
                (business_id,),
            ).fetchall()
            return [SupplierRelationship.model_validate_json(row["payload"]) for row in rows]

    def get_supplier(self, business_id: str, supplier_id: str) -> SupplierRelationship | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM suppliers WHERE business_id = ? AND supplier_id = ?",
                (business_id, supplier_id),
            ).fetchone()
            if row is None:
                return None
            return SupplierRelationship.model_validate_json(row["payload"])

    def delete_supplier(self, business_id: str, supplier_id: str) -> bool:
        with self._lock:
            with self._connection:
                cursor = self._connection.execute(
                    "DELETE FROM suppliers WHERE business_id = ? AND supplier_id = ?",
                    (business_id, supplier_id),
                )
            return cursor.rowcount > 0

    def create_operational_vulnerability(
        self,
        business_id: str,
        vulnerability: OperationalVulnerability,
    ) -> OperationalVulnerability:
        with self._lock:
            if self.get_business(business_id) is None:
                raise KeyError(f"Business '{business_id}' does not exist.")
            with self._connection:
                try:
                    self._connection.execute(
                        "INSERT INTO operational_vulnerability (vulnerability_id, business_id, payload) VALUES (?, ?, ?)",
                        (vulnerability.vulnerability_id, business_id, self._serialize_model(vulnerability)),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError(f"Operational vulnerability for business '{business_id}' already exists.") from exc
            return vulnerability

    def get_operational_vulnerability(self, business_id: str) -> OperationalVulnerability | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM operational_vulnerability WHERE business_id = ?",
                (business_id,),
            ).fetchone()
            if row is None:
                return None
            return OperationalVulnerability.model_validate_json(row["payload"])

    def list_operational_vulnerabilities(self) -> list[OperationalVulnerability]:
        with self._lock:
            rows = self._connection.execute("SELECT payload FROM operational_vulnerability ORDER BY rowid").fetchall()
            return [OperationalVulnerability.model_validate_json(row["payload"]) for row in rows]

    def create_business_id(self) -> str:
        return uuid4().hex

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()


_store: BusinessStore | None = None


def get_store(database_path: str | os.PathLike[str] | None = None, *, refresh: bool = False) -> BusinessStore:
    global _store
    selected_path = str(Path(database_path) if database_path is not None else os.getenv("TERRACRED_DB_PATH", default_database_path()))
    if _store is None or refresh or getattr(_store, "database_path", None) != selected_path:
        if _store is not None:
            _store.close()
        _store = BusinessStore(selected_path)
    return _store
