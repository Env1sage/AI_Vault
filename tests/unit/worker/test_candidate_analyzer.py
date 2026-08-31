import uuid
from datetime import UTC, datetime, timedelta

from vault_shared.db.models import File
from worker.storage_intelligence.candidate_analyzer import CandidateAnalyzer

_NOW = datetime(2026, 8, 24, tzinfo=UTC)


def _file(
    *,
    name: str = "file.txt",
    size_bytes: int | None = 1000,
    modified_at: datetime | None = None,
    viewed_at: datetime | None = None,
) -> File:
    return File(
        id=uuid.uuid4(),
        storage_source_id=uuid.uuid4(),
        provider_file_id=str(uuid.uuid4()),
        name=name,
        path=f"/{name}",
        size_bytes=size_bytes,
        provider_modified_at=modified_at,
        provider_viewed_at=viewed_at,
        scanned_at=_NOW,
    )


class TestLargeFileThreshold:
    def test_exactly_at_threshold_counts_as_large(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [_file(size_bytes=100)], now=_NOW, large_file_bytes=100
        )
        assert summary.large_file_count == 1

    def test_just_below_threshold_does_not_count(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [_file(size_bytes=99)], now=_NOW, large_file_bytes=100
        )
        assert summary.large_file_count == 0

    def test_above_threshold_counts(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [_file(size_bytes=101)], now=_NOW, large_file_bytes=100
        )
        assert summary.large_file_count == 1


class TestOldFileBoundaries:
    def test_file_modified_exactly_at_cutoff_is_not_old(self) -> None:
        """`< cutoff` (strictly older), matching the repository's SQL —
        a file modified precisely at the boundary hasn't gone stale yet."""
        cutoff_moment = _NOW - timedelta(days=30)
        summary = CandidateAnalyzer().analyze(
            [_file(modified_at=cutoff_moment)], now=_NOW, old_file_days=30
        )
        assert summary.old_file_count == 0

    def test_file_modified_one_second_past_the_cutoff_is_old(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [_file(modified_at=_NOW - timedelta(days=30, seconds=1))],
            now=_NOW,
            old_file_days=30,
        )
        assert summary.old_file_count == 1

    def test_recently_modified_file_is_not_old(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [_file(modified_at=_NOW - timedelta(days=1))], now=_NOW, old_file_days=90
        )
        assert summary.old_file_count == 0

    def test_file_with_no_modified_time_is_never_counted_as_old(self) -> None:
        """No guessing (Phase 1 spec §9/§10) — missing data is never
        treated as evidence of staleness."""
        summary = CandidateAnalyzer().analyze([_file(modified_at=None)], now=_NOW)
        assert summary.old_file_count == 0


class TestActivityClassification:
    def test_file_with_no_timestamps_at_all_is_never_inactive(self) -> None:
        summary = CandidateAnalyzer().analyze([_file(modified_at=None, viewed_at=None)], now=_NOW)
        assert summary.inactive_file_count == 0

    def test_recent_view_keeps_a_file_out_of_inactive_even_if_modified_long_ago(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [
                _file(
                    modified_at=_NOW - timedelta(days=1000),
                    viewed_at=_NOW - timedelta(days=1),
                )
            ],
            now=_NOW,
            inactive_file_days=365,
        )
        assert summary.inactive_file_count == 0

    def test_both_timestamps_old_is_inactive(self) -> None:
        summary = CandidateAnalyzer().analyze(
            [
                _file(
                    modified_at=_NOW - timedelta(days=800),
                    viewed_at=_NOW - timedelta(days=700),
                )
            ],
            now=_NOW,
            inactive_file_days=365,
        )
        assert summary.inactive_file_count == 1


class TestTemporaryCandidateHeuristics:
    def test_tmp_extension_matches(self) -> None:
        summary = CandidateAnalyzer().analyze([_file(name="draft.tmp")], now=_NOW)
        assert summary.temporary_candidate_count == 1

    def test_backup_in_name_matches(self) -> None:
        summary = CandidateAnalyzer().analyze([_file(name="report_backup.pdf")], now=_NOW)
        assert summary.temporary_candidate_count == 1

    def test_copy_suffix_matches(self) -> None:
        summary = CandidateAnalyzer().analyze([_file(name="Notes copy.docx")], now=_NOW)
        assert summary.temporary_candidate_count == 1

    def test_ordinary_filename_does_not_match(self) -> None:
        """False-positive check (Phase 1 spec §23) — an ordinary business
        document must not be flagged."""
        summary = CandidateAnalyzer().analyze(
            [_file(name="Q3 Financial Report.pdf")], now=_NOW
        )
        assert summary.temporary_candidate_count == 0

    def test_a_filename_that_merely_contains_the_word_company_is_not_flagged(self) -> None:
        """Guards against an overly broad substring match — "company" was
        never a temp-file signal and must not trip the "copy" pattern."""
        summary = CandidateAnalyzer().analyze([_file(name="company-handbook.pdf")], now=_NOW)
        assert summary.temporary_candidate_count == 0


class TestSavingsSizeExposure:
    def test_temporary_candidate_sizes_are_keyed_by_file_id(self) -> None:
        file = _file(name="old.bak", size_bytes=5000)
        summary = CandidateAnalyzer().analyze([file], now=_NOW)
        assert summary.temporary_candidate_sizes == {file.id: 5000}
