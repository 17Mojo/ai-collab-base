"""Unit tests for archive executor."""

import json

from ai_collab.archive_inventory import (
    ArchiveManifest,
    create_archive_manifest,
    execute_archive,
    generate_archive_id,
    print_archive_summary,
    rollback_archive,
    scan_directory,
    write_archive_manifest,
)


class TestArchiveManifest:
    """Tests for ArchiveManifest dataclass."""

    def test_manifest_creation(self):
        """Test creating an archive manifest."""
        manifest = ArchiveManifest(
            archive_id="archive-20260313-120000",
            archive_type="results",
            source_dir="collaboration/results",
            target_dir="archive/results-2026-03-13",
            created_at="2026-03-13T12:00:00",
            files_count=5,
            files_list=["file1.md", "file2.md"],
            dry_run=False,
            status="pending",
        )

        assert manifest.archive_id == "archive-20260313-120000"
        assert manifest.archive_type == "results"
        assert manifest.source_dir == "collaboration/results"
        assert manifest.target_dir == "archive/results-2026-03-13"
        assert manifest.files_count == 5
        assert manifest.files_list == ["file1.md", "file2.md"]
        assert manifest.dry_run is False
        assert manifest.status == "pending"

    def test_to_dict(self):
        """Test converting manifest to dictionary."""
        manifest = ArchiveManifest(
            archive_id="archive-20260313-120000",
            archive_type="results",
            source_dir="collaboration/results",
            target_dir="archive/results-2026-03-13",
            created_at="2026-03-13T12:00:00",
            files_count=2,
            files_list=["file1.md", "file2.md"],
        )

        result = manifest.to_dict()

        assert result["archive_id"] == "archive-20260313-120000"
        assert result["archive_type"] == "results"
        assert result["source_dir"] == "collaboration/results"
        assert result["target_dir"] == "archive/results-2026-03-13"
        assert result["files_count"] == 2
        assert result["files_list"] == ["file1.md", "file2.md"]


class TestGenerateArchiveId:
    """Tests for generate_archive_id function."""

    def test_generate_archive_id(self):
        """Test generating archive ID."""
        archive_id = generate_archive_id()

        assert archive_id.startswith("archive-")
        assert len(archive_id) == len("archive-20260313-120000")


class TestScanDirectory:
    """Tests for scan_directory function."""

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning empty directory."""
        files = scan_directory(tmp_path)

        assert files == []

    def test_scan_directory_with_files(self, tmp_path):
        """Test scanning directory with files."""
        # Create test files
        (tmp_path / "file1.md").write_text("content1")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.md").write_text("content2")

        files = scan_directory(tmp_path)

        assert len(files) == 2
        assert any(f.name == "file1.md" for f in files)
        assert any(f.name == "file2.md" for f in files)

    def test_scan_nonexistent_directory(self, tmp_path):
        """Test scanning nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        files = scan_directory(nonexistent)

        assert files == []


class TestCreateArchiveManifest:
    """Tests for create_archive_manifest function."""

    def test_create_manifest_with_files(self, tmp_path):
        """Test creating manifest with files."""
        # Create source directory with files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.md").write_text("content1")
        (source_dir / "file2.md").write_text("content2")

        target_dir = tmp_path / "target"

        manifest = create_archive_manifest(
            archive_type="results",
            source_dir=source_dir,
            target_dir=target_dir,
            dry_run=False,
        )

        assert manifest.archive_type == "results"
        assert manifest.files_count == 2
        assert len(manifest.files_list) == 2
        assert manifest.dry_run is False
        assert manifest.status == "pending"

    def test_create_manifest_empty_directory(self, tmp_path):
        """Test creating manifest for empty directory."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"

        manifest = create_archive_manifest(
            archive_type="research",
            source_dir=source_dir,
            target_dir=target_dir,
            dry_run=True,
        )

        assert manifest.archive_type == "research"
        assert manifest.files_count == 0
        assert manifest.files_list == []
        assert manifest.dry_run is True


class TestExecuteArchive:
    """Tests for execute_archive function."""

    def test_execute_archive_dry_run(self, tmp_path):
        """Test executing archive in dry-run mode."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.md").write_text("content1")

        target_dir = tmp_path / "target"

        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir=str(source_dir.relative_to(tmp_path)),
            target_dir=str(target_dir.relative_to(tmp_path)),
            created_at="2026-03-13T12:00:00",
            files_count=1,
            files_list=["file1.md"],
            dry_run=True,
            status="pending",
        )

        result = execute_archive(manifest=manifest, workspace=tmp_path)

        assert result.status == "completed"
        # Files should not be moved in dry-run mode
        assert (source_dir / "file1.md").exists()
        assert not (target_dir / "file1.md").exists()

    def test_execute_archive_apply(self, tmp_path):
        """Test executing archive in apply mode."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.md").write_text("content1")

        target_dir = tmp_path / "target"

        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir=str(source_dir.relative_to(tmp_path)),
            target_dir=str(target_dir.relative_to(tmp_path)),
            created_at="2026-03-13T12:00:00",
            files_count=1,
            files_list=["file1.md"],
            dry_run=False,
            status="pending",
        )

        result = execute_archive(manifest=manifest, workspace=tmp_path)

        assert result.status == "completed"
        # Files should be moved in apply mode
        assert not (source_dir / "file1.md").exists()
        assert (target_dir / "file1.md").exists()

    def test_execute_archive_nonexistent_source(self, tmp_path):
        """Test executing archive with nonexistent source."""
        source_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / "target"

        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir=str(source_dir.relative_to(tmp_path)),
            target_dir=str(target_dir.relative_to(tmp_path)),
            created_at="2026-03-13T12:00:00",
            files_count=0,
            files_list=[],
            dry_run=False,
            status="pending",
        )

        result = execute_archive(manifest=manifest, workspace=tmp_path)

        assert result.status == "failed"


class TestRollbackArchive:
    """Tests for rollback_archive function."""

    def test_rollback_archive_dry_run(self, tmp_path):
        """Test rolling back archive in dry-run mode."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"

        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir=str(source_dir.relative_to(tmp_path)),
            target_dir=str(target_dir.relative_to(tmp_path)),
            created_at="2026-03-13T12:00:00",
            files_count=1,
            files_list=["file1.md"],
            dry_run=True,
            status="completed",
        )

        result = rollback_archive(manifest=manifest, workspace=tmp_path)

        assert result.status == "rolled_back"

    def test_rollback_archive_apply(self, tmp_path):
        """Test rolling back archive in apply mode."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "file1.md").write_text("content1")

        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir=str(source_dir.relative_to(tmp_path)),
            target_dir=str(target_dir.relative_to(tmp_path)),
            created_at="2026-03-13T12:00:00",
            files_count=1,
            files_list=["file1.md"],
            dry_run=False,
            status="completed",
        )

        result = rollback_archive(manifest=manifest, workspace=tmp_path)

        assert result.status == "rolled_back"
        # Files should be moved back
        assert (source_dir / "file1.md").exists()
        assert not (target_dir / "file1.md").exists()


class TestWriteArchiveManifest:
    """Tests for write_archive_manifest function."""

    def test_write_manifest(self, tmp_path):
        """Test writing manifest to file."""
        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir="collaboration/results",
            target_dir="archive/results-2026-03-13",
            created_at="2026-03-13T12:00:00",
            files_count=2,
            files_list=["file1.md", "file2.md"],
        )

        write_archive_manifest(
            manifest=manifest,
            workspace=tmp_path,
            manifest_path="test_manifest.json",
        )

        manifest_file = tmp_path / "test_manifest.json"
        assert manifest_file.exists()

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest_data["archive_id"] == "archive-test"
        assert manifest_data["archive_type"] == "results"


class TestPrintArchiveSummary:
    """Tests for print_archive_summary function."""

    def test_print_summary(self, tmp_path, capsys):
        """Test printing summary to console."""
        manifest = ArchiveManifest(
            archive_id="archive-test",
            archive_type="results",
            source_dir="collaboration/results",
            target_dir="archive/results-2026-03-13",
            created_at="2026-03-13T12:00:00",
            files_count=2,
            files_list=["file1.md", "file2.md"],
            dry_run=False,
            status="completed",
        )

        print_archive_summary(manifest=manifest)
        captured = capsys.readouterr()

        assert "Archive Summary" in captured.out
        assert "Archive ID: archive-test" in captured.out
        assert "Type: results" in captured.out
        assert "Files Count: 2" in captured.out
        assert "Status: completed" in captured.out
