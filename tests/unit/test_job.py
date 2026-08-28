import pytest

from app.constants import Default, Provider, SyncJobKey, SyncMode
from app.sync.job import SyncJob

pytestmark = pytest.mark.unit


def test_sync_job_defaults():
    job = SyncJob()

    assert job.table == Default.NOVEL_TABLE
    assert job.novels == []
    assert job.fields == []
    assert job.source == Provider.LOCAL
    assert job.mode == SyncMode.FILL_MISSING
    assert job.dry_run is False
    assert job.force is False
    assert job.options == {}
    assert job.profile == "Synchronization"


def test_sync_job_from_dict():
    data = {
        SyncJobKey.SOURCE: Provider.ONLINE,
        SyncJobKey.MODE: SyncMode.OVERWRITE,
        SyncJobKey.NOVELS: [1, 2, 3],
        SyncJobKey.FIELDS: ["author", "description"],
        SyncJobKey.DRY_RUN: True,
        SyncJobKey.FORCE: True,
    }

    job = SyncJob.from_dict(data, table="test_novels")

    assert job.table == "test_novels"
    assert job.source == Provider.ONLINE
    assert job.mode == SyncMode.OVERWRITE
    assert job.novels == [1, 2, 3]
    assert job.fields == ["author", "description"]
    assert job.dry_run is True
    assert job.force is True


def test_sync_job_from_dict_uses_default_table():
    job = SyncJob.from_dict({})

    assert job.table == Default.NOVEL_TABLE


def test_sync_job_rejects_non_dict():
    with pytest.raises(TypeError, match="Sync job must be an object"):
        SyncJob.from_dict([])


def test_sync_job_rejects_invalid_source():
    with pytest.raises(ValueError, match="Invalid sync source"):
        SyncJob.from_dict(
            {
                SyncJobKey.SOURCE: "invalid",
            }
        )


def test_sync_job_rejects_invalid_mode():
    with pytest.raises(ValueError, match="Invalid sync mode"):
        SyncJob.from_dict(
            {
                SyncJobKey.MODE: "invalid",
            }
        )


def test_sync_job_rejects_unknown_metadata_field():
    with pytest.raises(ValueError, match="Unknown metadata fields"):
        SyncJob.from_dict(
            {
                SyncJobKey.FIELDS: ["does_not_exist"],
            }
        )


def test_sync_job_rejects_non_list_fields():
    with pytest.raises(TypeError, match="Sync fields must be a list"):
        SyncJob.from_dict(
            {
                SyncJobKey.FIELDS: "author",
            }
        )


def test_sync_job_rejects_non_string_fields():
    with pytest.raises(ValueError, match="Sync fields must contain strings"):
        SyncJob.from_dict(
            {
                SyncJobKey.FIELDS: ["author", 123],
            }
        )


def test_sync_job_rejects_non_list_novels():
    with pytest.raises(TypeError, match="Novels must be a list"):
        SyncJob.from_dict(
            {
                SyncJobKey.NOVELS: 1,
            }
        )


def test_sync_job_rejects_non_integer_novel_ids():
    with pytest.raises(ValueError, match="Novel IDs must be integers"):
        SyncJob.from_dict(
            {
                SyncJobKey.NOVELS: [1, "2"],
            }
        )


def test_sync_job_rejects_non_boolean_dry_run():
    with pytest.raises(TypeError, match="dry_run must be a boolean"):
        SyncJob.from_dict(
            {
                SyncJobKey.DRY_RUN: "true",
            }
        )


def test_sync_job_rejects_non_boolean_force():
    with pytest.raises(TypeError, match="force must be a boolean"):
        SyncJob.from_dict(
            {
                SyncJobKey.FORCE: "true",
            }
        )
