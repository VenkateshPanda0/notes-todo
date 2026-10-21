"""Backups, exports and imports.

Three ways to get data out (and back in):
  * JSON  - a complete, versioned export that can be re-imported.
  * Markdown zip - one .md file per item with YAML front matter; opens in Obsidian and friends.
  * Database copy - a consistent snapshot of the SQLite file (safe even while the app is running).
Plus automatic rolling daily snapshots so a bad day never costs more than a day of work.
"""

import io
import json
import logging
import os
import re
import sqlite3
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..models.item import Item, ItemType, Priority
from ..models.tag import Tag
from ..schemas.backup import (
    EXPORT_FORMAT,
    EXPORT_VERSION,
    MAX_IMPORT_ITEMS,
    AutoBackupInfo,
    ExportFile,
    ExportItem,
)
from .items import _resolve_tags
from .recurrence import anchor_for
from .tags import normalize_tags

log = logging.getLogger("taskflow.backup")

AUTO_BACKUP_KEEP = 7
BEFORE_IMPORT_KEEP = 3
BEFORE_UPGRADE_KEEP = 3
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_ZIP_FILES = 20_000
_DAILY_NAME = re.compile(r"^flow-\d{4}-\d{2}-\d{2}\.db$")
_BEFORE_IMPORT_NAME = re.compile(r"^before-import-\d{8}-\d{6}\.db$")
_BEFORE_UPGRADE_NAME = re.compile(r"^before-upgrade-v\d+-\d{8}-\d{6}\.db$")


class BackupFileError(ValueError):
    """The uploaded file could not be understood. The message is safe to show to the user."""


# --- JSON export / import -------------------------------------------------------------------------


def export_json(db: Session) -> dict:
    items = db.execute(select(Item).order_by(Item.id)).scalars().all()
    payload = ExportFile(
        exported_at=datetime.now(timezone.utc),
        items=[
            ExportItem(
                title=i.title,
                content=i.content,
                type=i.item_type,
                completed=i.completed,
                priority=i.priority,
                due_date=i.due_date,
                recurrence=i.recurrence,
                recurrence_day=i.recurrence_day,
                tags=[t.name for t in i.tags],
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
    )
    return json.loads(payload.model_dump_json(by_alias=True))


def parse_export_json(raw: bytes) -> list[ExportItem]:
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise BackupFileError("That file is not valid JSON.") from exc
    if not isinstance(data, dict) or data.get("format") != EXPORT_FORMAT:
        raise BackupFileError("That is not a TaskFlow export file.")
    version = data.get("version")
    if not isinstance(version, int) or version > EXPORT_VERSION:
        raise BackupFileError(
            f"This export was made by a newer TaskFlow (format version {version}). Please update TaskFlow."
        )
    try:
        return ExportFile.model_validate(data).items
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise BackupFileError(f"The export file is damaged at '{where}': {first['msg']}") from exc


# --- Markdown export / import ---------------------------------------------------------------------

_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def _safe_filename(title: str) -> str:
    name = _UNSAFE_FILENAME.sub("-", title).strip(" .-")[:80].strip(" .-")
    return name or "untitled"


def _yaml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)  # JSON strings are valid YAML double-quoted strings


def _front_matter(item: Item) -> str:
    lines = [
        "---",
        f"title: {_yaml_str(item.title)}",
        f"type: {item.item_type.value.lower()}",
    ]
    if item.item_type == ItemType.TODO:
        lines.append(f"completed: {str(item.completed).lower()}")
        lines.append(f"priority: {item.priority.value.lower()}")
        if item.due_date:
            lines.append(f"due: {item.due_date.isoformat()}")
        if item.recurrence:
            lines.append(f"repeat: {item.recurrence}")
    if item.tags:
        lines.append("tags: [" + ", ".join(t.name for t in item.tags) + "]")
    lines.append(f"created: {item.created_at.isoformat()}")
    lines.append(f"updated: {item.updated_at.isoformat()}")
    lines.append("---")
    return "\n".join(lines)


def export_markdown_zip(db: Session) -> bytes:
    items = db.execute(select(Item).order_by(Item.id)).scalars().all()
    used: set[str] = set()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in items:
            folder = "Notes" if item.item_type == ItemType.NOTE else "Todos"
            base = _safe_filename(item.title)
            name, n = f"{folder}/{base}.md", 1
            while name.lower() in used:
                n += 1
                name = f"{folder}/{base} ({n}).md"
            used.add(name.lower())
            body = item.content.rstrip()
            archive.writestr(name, f"{_front_matter(item)}\n\n{body}\n" if body else f"{_front_matter(item)}\n")
    return buffer.getvalue()


def _parse_front_matter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """A small YAML subset: `key: value` lines plus tag lists in flow ([a, b]) or block (- a) form."""
    text = text.lstrip("﻿")
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return {}, text
    lines = text.splitlines()
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text
    meta: dict[str, str | list[str]] = {}
    current_list: str | None = None
    for line in lines[1:end]:
        if current_list and re.match(r"^\s+-\s+", line):
            value = re.sub(r"^\s+-\s+", "", line).strip().strip("\"'")
            meta[current_list].append(value)  # type: ignore[union-attr]
            continue
        current_list = None
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, raw = line.partition(":")
        key, raw = key.strip().lower(), raw.strip()
        if not raw:
            meta[key] = []
            current_list = key
        elif raw.startswith("[") and raw.endswith("]"):
            meta[key] = [v.strip().strip("\"'") for v in raw[1:-1].split(",") if v.strip()]
        else:
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                try:
                    raw = json.loads(raw) if raw[0] == '"' else raw[1:-1]
                except ValueError:
                    raw = raw[1:-1]
            meta[key] = raw
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body


def _as_text(value) -> str:
    return value if isinstance(value, str) else ""


def _parse_dt(value) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(_as_text(value)) if _as_text(value) else None
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed and parsed.tzinfo is None else parsed


def parse_markdown_zip(raw: bytes) -> list[ExportItem]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise BackupFileError("That file is not a valid zip archive.") from exc
    entries = [i for i in archive.infolist() if not i.is_dir() and i.filename.lower().endswith(".md")]
    if len(entries) > MAX_ZIP_FILES:
        raise BackupFileError(f"The archive has too many notes (limit {MAX_ZIP_FILES}).")
    if sum(i.file_size for i in entries) > MAX_UPLOAD_BYTES:
        raise BackupFileError("The archive is too large when unpacked.")
    items: list[ExportItem] = []
    for entry in entries:
        try:
            text = archive.read(entry).decode("utf-8", errors="replace")
        except (zipfile.BadZipFile, RuntimeError) as exc:
            raise BackupFileError(f"Could not read '{entry.filename}' from the archive.") from exc
        meta, body = _parse_front_matter(text)
        stem = Path(entry.filename).stem
        title = (_as_text(meta.get("title")) or stem).strip()[:255] or "untitled"
        kind = _as_text(meta.get("type")).lower()
        if not kind:  # without a type, folder names decide (our own export uses Notes/ and Todos/)
            kind = "todo" if "todo" in entry.filename.lower().split("/")[0] else "note"
        item_type = ItemType.TODO if kind == "todo" else ItemType.NOTE
        raw_tags = meta.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t for t in re.split(r"[\s,]+", raw_tags) if t]
        tags = []
        for tag in raw_tags:
            try:
                tags.extend(normalize_tags([tag]))
            except ValueError:
                continue  # skip tags we can't represent instead of failing the whole file
        priority = {"low": Priority.LOW, "high": Priority.HIGH}.get(_as_text(meta.get("priority")).lower(), Priority.MEDIUM)
        due_raw = _as_text(meta.get("due") or meta.get("due_date"))[:10]
        try:
            due = date.fromisoformat(due_raw) if due_raw else None
        except ValueError:
            due = None
        items.append(
            ExportItem(
                title=title,
                content=body.rstrip(),
                recurrence=_as_text(meta.get("repeat") or meta.get("recurrence")) or None,
                type=item_type,
                completed=_as_text(meta.get("completed")).lower() in ("true", "yes", "1"),
                priority=priority,
                due_date=due if item_type == ItemType.TODO else None,
                tags=list(dict.fromkeys(tags))[:20],
                created_at=_parse_dt(meta.get("created")),
                updated_at=_parse_dt(meta.get("updated")),
            )
        )
    if not items:
        raise BackupFileError("No Markdown (.md) files were found in that archive.")
    return items


# --- importing ------------------------------------------------------------------------------------


def parse_upload(raw: bytes) -> list[ExportItem]:
    """Detect a TaskFlow JSON export or a zip of Markdown files and parse it."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise BackupFileError("That file is too large to import.")
    if raw[:4] == b"PK\x03\x04":
        return parse_markdown_zip(raw)
    return parse_export_json(raw)


def _key(item_type: ItemType, title: str, content: str) -> tuple[str, str, str]:
    return item_type.value, title.strip().lower(), content.strip()


def import_items(db: Session, items: list[ExportItem], mode: str) -> tuple[int, int]:
    """Import items. `merge` skips ones already present; `replace` wipes everything first.

    Everything happens in one transaction, so a failure leaves the database untouched.
    Returns (imported, skipped).
    """
    if len(items) > MAX_IMPORT_ITEMS:
        raise BackupFileError(f"Too many items (limit {MAX_IMPORT_ITEMS}).")
    try:
        if mode == "replace":
            for existing in db.execute(select(Item)).scalars().all():
                db.delete(existing)  # cascades embeddings and tag links
            db.flush()
            seen: set = set()
        else:
            seen = {
                _key(i.item_type, i.title, i.content) for i in db.execute(select(Item)).scalars().all()
            }
        imported = skipped = 0
        for data in items:
            if mode == "merge" and _key(data.item_type, data.title, data.content) in seen:
                skipped += 1
                continue
            item = Item(
                title=data.title,
                content=data.content,
                item_type=data.item_type,
                completed=data.completed,
                priority=data.priority,
                due_date=data.due_date,
                recurrence=data.recurrence if data.item_type == ItemType.TODO else None,
                recurrence_day=(
                    (data.recurrence_day or anchor_for(data.due_date, data.recurrence))
                    if data.item_type == ItemType.TODO
                    else None
                ),
                tags=_resolve_tags(db, _clean_tags(data.tags)),
            )
            if data.created_at:
                item.created_at = data.created_at
            if data.updated_at:
                item.updated_at = data.updated_at
            db.add(item)
            db.flush()  # makes new tags visible to the next item's lookup
            imported += 1
        db.commit()
        return imported, skipped
    except Exception:
        db.rollback()
        raise


def _clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for tag in tags:
        try:
            cleaned.extend(normalize_tags([tag]))
        except ValueError:
            continue
    return list(dict.fromkeys(cleaned))[:20]


# --- database snapshots ---------------------------------------------------------------------------


def snapshot_database(engine: Engine, destination: str | os.PathLike) -> None:
    """Write a consistent copy of the SQLite database, even while the app is using it."""
    if engine.dialect.name != "sqlite":
        raise BackupFileError("Database copies are only supported for SQLite databases.")
    source = engine.raw_connection()
    try:
        target = sqlite3.connect(str(destination))
        try:
            source.driver_connection.backup(target)  # type: ignore[attr-defined]
        finally:
            target.close()
    finally:
        source.close()


def backup_directory(engine: Engine) -> Path | None:
    """Where automatic backups live: a `backups` folder next to the database file."""
    database = engine.url.database
    if engine.dialect.name != "sqlite" or not database or database == ":memory:":
        return None
    return Path(database).resolve().parent / "backups"


def list_auto_backups(engine: Engine) -> list[AutoBackupInfo]:
    """Daily and before-import snapshots, newest first."""
    directory = backup_directory(engine)
    if directory is None or not directory.is_dir():
        return []
    found = []
    for path in directory.iterdir():
        if any(p.match(path.name) for p in (_DAILY_NAME, _BEFORE_IMPORT_NAME, _BEFORE_UPGRADE_NAME)):
            stat = path.stat()
            found.append(
                AutoBackupInfo(
                    name=path.name, size=stat.st_size, modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                )
            )
    return sorted(found, key=lambda b: b.modified, reverse=True)


def _prune(directory: Path, pattern: re.Pattern[str], keep: int) -> None:
    for stale in sorted(p for p in directory.iterdir() if pattern.match(p.name))[:-keep]:
        stale.unlink(missing_ok=True)


def snapshot_before_import(engine: Engine, now: datetime | None = None) -> Path | None:
    """Safety copy taken right before a destructive (replace) import. Returns None if unavailable.

    These are kept separately from the daily backups so ordinary pruning never removes them.
    """
    directory = backup_directory(engine)
    if directory is None:
        return None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        target = directory / f"before-import-{stamp}.db"
        tmp = target.with_suffix(".tmp")
        snapshot_database(engine, tmp)
        os.replace(tmp, target)
        _prune(directory, _BEFORE_IMPORT_NAME, BEFORE_IMPORT_KEEP)
        return target
    except Exception:  # noqa: BLE001
        log.exception("Could not take a safety backup before importing")
        raise BackupFileError(
            "Could not make a safety backup before replacing your data, so nothing was changed."
        )


def snapshot_before_upgrade(engine: Engine, from_version: int, now: datetime | None = None) -> Path | None:
    """Copy the database right before a schema upgrade. Best effort: failing to copy is logged but never
    blocks the upgrade (the app would otherwise be unable to start)."""
    directory = backup_directory(engine)
    if directory is None:
        return None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        target = directory / f"before-upgrade-v{from_version}-{stamp}.db"
        tmp = target.with_suffix(".tmp")
        snapshot_database(engine, tmp)
        os.replace(tmp, target)
        _prune(directory, _BEFORE_UPGRADE_NAME, BEFORE_UPGRADE_KEEP)
        return target
    except Exception:  # noqa: BLE001
        log.exception("Could not take a safety backup before upgrading the database")
        return None


def run_auto_backup(engine: Engine, today: date | None = None, keep: int = AUTO_BACKUP_KEEP, force: bool = False) -> Path | None:
    """Make today's snapshot if there isn't one yet, then prune old ones. Never raises."""
    try:
        directory = backup_directory(engine)
        if directory is None:
            return None
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"flow-{(today or date.today()).isoformat()}.db"
        if force or not target.exists():
            tmp = target.with_suffix(".tmp")
            snapshot_database(engine, tmp)
            os.replace(tmp, target)  # never leave a half-written backup under the real name
        _prune(directory, _DAILY_NAME, keep)
        return target
    except Exception:  # noqa: BLE001 - a failed backup must never stop the app from starting
        log.exception("Automatic backup failed")
        return None
