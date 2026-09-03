"""Offline, local-only runtime recovery. No configuration or provider imports.

The operator must stop every API worker and cleanup job before backup/restore.
Bundles contain sensitive learner data and must live on access-controlled storage.
Checksums detect accidental corruption; they do not authenticate a hostile bundle.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3

from .database import SCHEMA


DATABASE = "learning.sqlite3"


class RecoveryError(ValueError):
    """Safe operator-facing failure, without learner content or credentials."""


def _plain_path(path: Path) -> Path:
    path = path.absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise RecoveryError("Linked paths are not supported")
    return path.resolve()


def _name(value: str) -> str:
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,220}", value)
            or value.endswith(".")
            or value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}):
        raise RecoveryError("Unsafe upload filename")
    return value


def _digest(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def _read_database(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


def _check_database(db: sqlite3.Connection) -> None:
    required = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))
    present = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not required.issubset(present):
        raise RecoveryError("Runtime schema is incomplete for this application revision")
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise RecoveryError("Database integrity check failed")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise RecoveryError("Database contains broken ownership references")


def _paths(db: sqlite3.Connection) -> tuple[list[tuple[str, str]], list[str]]:
    documents = db.execute("SELECT id, stored_path FROM documents").fetchall()
    pending = [row[0] for row in db.execute("SELECT stored_path FROM pending_file_deletions")]
    return documents, pending


def _new_target(source: Path, destination: Path) -> Path:
    destination = _plain_path(destination)
    if destination == source or source in destination.parents or destination in source.parents:
        raise RecoveryError("Source and destination must not overlap")
    if destination.exists():
        raise RecoveryError("Destination must not already exist")
    if not destination.parent.is_dir():
        raise RecoveryError("Destination parent must already exist")
    destination.mkdir(mode=0o700)
    return destination


def create_backup(runtime: Path, destination: Path, *, offline_confirmed: bool = False) -> None:
    if not offline_confirmed:
        raise RecoveryError("Stop all API workers and cleanup jobs, then confirm offline operation")
    runtime = _plain_path(runtime)
    source_db = _plain_path(runtime / DATABASE)
    uploads = _plain_path(runtime / "uploads")
    if not source_db.is_file() or not uploads.is_dir():
        raise RecoveryError("Runtime database or uploads directory is missing")
    destination = _new_target(runtime, destination)
    (destination / "uploads").mkdir(mode=0o700)
    # SQLite backup includes committed WAL content; a raw database-file copy does not.
    with closing(_read_database(source_db)) as source, closing(sqlite3.connect(destination / DATABASE)) as snapshot:
        source.backup(snapshot)
        _check_database(snapshot)
        documents, pending = _paths(snapshot)
        mapped: dict[str, str] = {}
        for stored in [path for _, path in documents] + pending:
            target = _plain_path(Path(stored))
            if target.parent != uploads:
                raise RecoveryError("Stored upload path is outside the configured runtime")
            mapped[stored] = "uploads/" + _name(target.name)
        if len(set(mapped.values())) != len(mapped):
            raise RecoveryError("Stored upload paths collide")
        live = {stored for _, stored in documents}
        if live.intersection(pending):
            raise RecoveryError("A live document is also queued for deletion")
        for stored in live:
            source_file = _plain_path(Path(stored))
            if not source_file.is_file():
                raise RecoveryError("A referenced upload is missing")
            shutil.copyfile(source_file, destination / mapped[stored])
        # Portable paths also keep the original machine's directory out of the bundle.
        with snapshot:
            for document_id, stored in documents:
                snapshot.execute("UPDATE documents SET stored_path = ? WHERE id = ?", (mapped[stored], document_id))
            for stored in pending:
                snapshot.execute("UPDATE pending_file_deletions SET stored_path = ? WHERE stored_path = ?", (mapped[stored], stored))
        _check_database(snapshot)
    files = {DATABASE: _digest(destination / DATABASE)}
    files.update({mapped[stored]: _digest(destination / mapped[stored]) for stored in live})
    # Written last: an interrupted/incomplete copy cannot pass verification.
    with (destination / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump({"format": 1, "files": files}, stream, indent=2, sort_keys=True)
    verify_backup(destination)


def verify_backup(bundle: Path) -> dict:
    bundle = _plain_path(bundle)
    manifest_path = _plain_path(bundle / "manifest.json")
    if not manifest_path.is_file() or manifest_path.stat().st_size > 10 * 1024 * 1024:
        raise RecoveryError("Backup manifest is missing or too large")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != 1 or not isinstance(manifest.get("files"), dict):
        raise RecoveryError("Unsupported backup manifest")
    files = manifest["files"]
    if DATABASE not in files:
        raise RecoveryError("Backup database is missing")
    for relative, expected in files.items():
        if relative != DATABASE:
            if not relative.startswith("uploads/") or relative != "uploads/" + _name(relative[8:]):
                raise RecoveryError("Unsafe manifest path")
        file = _plain_path(bundle / relative)
        if not file.is_file() or _digest(file) != expected:
            raise RecoveryError("Backup file is missing or has changed")
    actual = set()
    for path in bundle.rglob("*"):
        _plain_path(path)
        if path.is_file():
            actual.add(path.relative_to(bundle).as_posix())
    if actual != set(files) | {"manifest.json"}:
        raise RecoveryError("Backup contains unlisted files")
    with closing(_read_database(bundle / DATABASE)) as db:
        _check_database(db)
        documents, pending = _paths(db)
        live = {path for _, path in documents}
        for path in live | set(pending):
            if not path.startswith("uploads/") or path != "uploads/" + _name(path[8:]):
                raise RecoveryError("Backup contains a nonportable upload path")
        if live.intersection(pending) or set(files) != {DATABASE} | live:
            raise RecoveryError("Backup upload inventory does not match the database")
    return {"documents": len(documents), "upload_files": len(live), "pending_deletions": len(pending)}


def restore_backup(bundle: Path, destination: Path, *, offline_confirmed: bool = False) -> None:
    if not offline_confirmed:
        raise RecoveryError("Stop all API workers and cleanup jobs, then confirm offline operation")
    bundle = _plain_path(bundle)
    verify_backup(bundle)
    destination = _new_target(bundle, destination)
    (destination / "uploads").mkdir(mode=0o700)
    shutil.copyfile(bundle / DATABASE, destination / DATABASE)
    with closing(sqlite3.connect(destination / DATABASE)) as db:
        documents, pending = _paths(db)
        for relative in {path for _, path in documents}:
            shutil.copyfile(bundle / relative, destination / relative)
        with db:
            for document_id, relative in documents:
                db.execute("UPDATE documents SET stored_path = ? WHERE id = ?", (str(destination / relative), document_id))
            for relative in pending:
                db.execute("UPDATE pending_file_deletions SET stored_path = ? WHERE stored_path = ?", (str(destination / relative), relative))
        _check_database(db)
    # Verify copies before signalling that this new runtime is ready for an offline drill.
    for relative in {path for _, path in documents}:
        if _digest(bundle / relative) != _digest(destination / relative):
            raise RecoveryError("Restored upload verification failed")
    (destination / "RESTORE_COMPLETE").touch(exist_ok=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "verify", "restore"))
    parser.add_argument("source", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--offline-confirmed", action="store_true")
    args = parser.parse_args()
    try:
        if args.operation == "verify":
            result = verify_backup(args.source)
            print("Verified local backup:", json.dumps(result, sort_keys=True))
        else:
            if args.destination is None:
                raise RecoveryError("A new destination is required")
            operation = create_backup if args.operation == "backup" else restore_backup
            operation(args.source, args.destination, offline_confirmed=args.offline_confirmed)
            print("Completed local " + args.operation + "; production recovery is not yet verified")
    except (OSError, sqlite3.Error, ValueError, TypeError):
        # Lower-level exceptions may include paths, SQL or data. Keep CLI output safe.
        print("Recovery operation failed. Check offline status, paths, integrity and free space. Do not use an incomplete destination.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
