"""Archive executor for results and research directories."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ArchiveManifest:
    """Manifest for archive operation."""

    archive_id: str
    archive_type: str  # "results" or "research"
    source_dir: str
    target_dir: str
    created_at: str
    files_count: int = 0
    files_list: list[str] = field(default_factory=list)
    dry_run: bool = False
    status: str = "pending"  # pending, completed, failed, rolled_back

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "archive_id": self.archive_id,
            "archive_type": self.archive_type,
            "source_dir": self.source_dir,
            "target_dir": self.target_dir,
            "created_at": self.created_at,
            "files_count": self.files_count,
            "files_list": self.files_list,
            "dry_run": self.dry_run,
            "status": self.status,
        }


def generate_archive_id() -> str:
    """Generate unique archive ID."""
    return f"archive-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def scan_directory(directory: Path) -> list[Path]:
    """Scan directory and return list of files."""
    if not directory.exists():
        return []

    files = []
    for item in directory.rglob("*"):
        if item.is_file():
            files.append(item)

    return sorted(files)


def create_archive_manifest(
    *,
    archive_type: str,
    source_dir: Path,
    target_dir: Path,
    dry_run: bool = False,
) -> ArchiveManifest:
    """Create archive manifest."""
    archive_id = generate_archive_id()
    files = scan_directory(source_dir)

    return ArchiveManifest(
        archive_id=archive_id,
        archive_type=archive_type,
        source_dir=str(source_dir),
        target_dir=str(target_dir),
        created_at=datetime.now().isoformat(),
        files_count=len(files),
        files_list=[str(f.relative_to(source_dir)) for f in files],
        dry_run=dry_run,
        status="pending",
    )


def execute_archive(
    *,
    manifest: ArchiveManifest,
    workspace: Path,
) -> ArchiveManifest:
    """Execute archive operation."""
    source_path = workspace / manifest.source_dir
    target_path = workspace / manifest.target_dir

    if not source_path.exists():
        manifest.status = "failed"
        return manifest

    if manifest.dry_run:
        manifest.status = "completed"
        return manifest

    try:
        # Create target directory
        target_path.mkdir(parents=True, exist_ok=True)

        # Move files
        for file_relpath in manifest.files_list:
            source_file = source_path / file_relpath
            target_file = target_path / file_relpath

            if source_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_file), str(target_file))

        manifest.status = "completed"
    except Exception as exc:  # noqa: BLE001
        manifest.status = "failed"
        print(f"Archive failed: {exc}")

    return manifest


def rollback_archive(
    *,
    manifest: ArchiveManifest,
    workspace: Path,
) -> ArchiveManifest:
    """Rollback archive operation."""
    source_path = workspace / manifest.source_dir
    target_path = workspace / manifest.target_dir

    if manifest.dry_run:
        manifest.status = "rolled_back"
        return manifest

    try:
        # Move files back
        for file_relpath in manifest.files_list:
            source_file = source_path / file_relpath
            target_file = target_path / file_relpath

            if target_file.exists():
                source_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target_file), str(source_file))

        # Remove target directory if empty
        if target_path.exists() and not any(target_path.iterdir()):
            target_path.rmdir()

        manifest.status = "rolled_back"
    except Exception as exc:  # noqa: BLE001
        print(f"Rollback failed: {exc}")

    return manifest


def write_archive_manifest(
    *,
    manifest: ArchiveManifest,
    workspace: Path,
    manifest_path: str = "logs/archive_manifest.json",
) -> None:
    """Write archive manifest to file."""
    manifest_file = workspace / manifest_path
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def print_archive_summary(*, manifest: ArchiveManifest) -> None:
    """Print archive summary to console."""
    print("\n" + "=" * 60)
    print("Archive Summary")
    print("=" * 60)
    print(f"Archive ID: {manifest.archive_id}")
    print(f"Type: {manifest.archive_type}")
    print(f"Source: {manifest.source_dir}")
    print(f"Target: {manifest.target_dir}")
    print(f"Created At: {manifest.created_at}")
    print(f"Files Count: {manifest.files_count}")
    print(f"Dry Run: {manifest.dry_run}")
    print(f"Status: {manifest.status}")

    if manifest.files_list and len(manifest.files_list) <= 10:
        print("\nFiles:")
        for file_path in manifest.files_list:
            print(f"  - {file_path}")
    elif manifest.files_list:
        print(f"\nFiles: {len(manifest.files_list)} files (list truncated)")

    print("=" * 60)
