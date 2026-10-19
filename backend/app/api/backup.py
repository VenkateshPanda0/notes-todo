import os
import tempfile
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from ..schemas.backup import AutoBackupList, ImportResult
from ..services import backup as backup_service
from ..services.backup import BackupFileError
from .deps import get_db, require_unlocked

router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(require_unlocked)])


def _attachment(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


def _stamp() -> str:
    return date.today().isoformat()


@router.get("/export.json")
def export_json(db: Session = Depends(get_db)) -> JSONResponse:
    """Everything as one JSON file that can be imported again."""
    return JSONResponse(
        backup_service.export_json(db), headers=_attachment(f"taskflow-export-{_stamp()}.json")
    )


@router.get("/export.zip")
def export_markdown(db: Session = Depends(get_db)) -> Response:
    """One Markdown file per item (with front matter), zipped. Opens in Obsidian and similar apps."""
    return Response(
        backup_service.export_markdown_zip(db),
        media_type="application/zip",
        headers=_attachment(f"taskflow-markdown-{_stamp()}.zip"),
    )


@router.get("/database")
def download_database(db: Session = Depends(get_db)) -> FileResponse:
    """A consistent copy of the SQLite database file."""
    handle, path = tempfile.mkstemp(suffix=".db", prefix="taskflow-copy-")
    os.close(handle)
    try:
        backup_service.snapshot_database(db.get_bind(), path)  # type: ignore[arg-type]
    except BackupFileError as exc:
        os.unlink(path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="application/vnd.sqlite3",
        headers=_attachment(f"taskflow-{_stamp()}.db"),
        background=BackgroundTask(os.unlink, path),
    )


@router.post("/import", response_model=ImportResult)
async def import_file(
    request: Request,
    mode: str = Query(default="merge", pattern="^(merge|replace)$"),
    db: Session = Depends(get_db),
) -> ImportResult:
    """Import a TaskFlow JSON export or a zip of Markdown files (the request body is the file).

    `merge` adds what is missing and skips items already present; `replace` swaps everything.
    """
    limit = backup_service.MAX_UPLOAD_BYTES
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="That file is too large to import.")
    raw = await request.body()
    try:
        items = backup_service.parse_upload(raw)
        if mode == "replace":
            # Parse first so a bad file never triggers it; abort if the safety copy can't be made.
            backup_service.snapshot_before_import(db.get_bind())  # type: ignore[arg-type]
        imported, skipped = backup_service.import_items(db, items, mode)
    except BackupFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ImportResult(mode=mode, imported=imported, skipped=skipped)  # type: ignore[arg-type]


@router.get("/auto", response_model=AutoBackupList)
def list_auto_backups(db: Session = Depends(get_db)) -> AutoBackupList:
    """The automatic daily backups (the newest 7 are kept next to the database)."""
    engine = db.get_bind()
    directory = backup_service.backup_directory(engine)  # type: ignore[arg-type]
    return AutoBackupList(
        enabled=directory is not None,
        directory=str(directory) if directory else None,
        backups=backup_service.list_auto_backups(engine),  # type: ignore[arg-type]
    )


@router.post("/auto/run", response_model=AutoBackupList)
def run_auto_backup_now(db: Session = Depends(get_db)) -> AutoBackupList:
    """Take (or refresh) today's automatic backup right now."""
    engine = db.get_bind()
    if backup_service.run_auto_backup(engine, force=True) is None:  # type: ignore[arg-type]
        raise HTTPException(status_code=400, detail="Backups are not available for this database.")
    return list_auto_backups(db)
