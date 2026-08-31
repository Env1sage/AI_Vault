from vault_shared.storage_intelligence.mime_category import (
    classify_mime_category,
    size_bucket_for,
)

_BUCKETS = [
    ("< 1 MB", 0, 1024),
    ("1 KB-1 MB", 1024, 1_048_576),
    ("> 1 MB", 1_048_576, None),
]


class TestClassifyMimeCategory:
    def test_none_mime_type_is_other(self) -> None:
        assert classify_mime_category(None) == "Other"

    def test_empty_string_mime_type_is_other(self) -> None:
        assert classify_mime_category("") == "Other"

    def test_unrecognized_mime_type_is_other(self) -> None:
        assert classify_mime_category("application/x-something-unheard-of") == "Other"

    def test_image_prefix(self) -> None:
        assert classify_mime_category("image/png") == "Images"

    def test_video_prefix(self) -> None:
        assert classify_mime_category("video/mp4") == "Videos"

    def test_audio_prefix(self) -> None:
        assert classify_mime_category("audio/mpeg") == "Audio"

    def test_plain_text_is_text_not_code(self) -> None:
        assert classify_mime_category("text/plain") == "Text"

    def test_code_like_text_prefix_is_code(self) -> None:
        assert classify_mime_category("text/x-python") == "Code"

    def test_google_doc_is_documents(self) -> None:
        assert classify_mime_category("application/vnd.google-apps.document") == "Documents"

    def test_google_sheet_is_spreadsheets(self) -> None:
        assert classify_mime_category("application/vnd.google-apps.spreadsheet") == "Spreadsheets"

    def test_google_slides_is_presentations(self) -> None:
        assert classify_mime_category("application/vnd.google-apps.presentation") == "Presentations"

    def test_pdf_is_documents(self) -> None:
        assert classify_mime_category("application/pdf") == "Documents"

    def test_zip_is_archives(self) -> None:
        assert classify_mime_category("application/zip") == "Archives"

    def test_google_folder_is_folders(self) -> None:
        assert classify_mime_category("application/vnd.google-apps.folder") == "Folders"


class TestSizeBucketFor:
    def test_none_size_is_unknown(self) -> None:
        assert size_bucket_for(None, _BUCKETS) == "Unknown size"

    def test_lower_boundary_is_inclusive(self) -> None:
        assert size_bucket_for(0, _BUCKETS) == "< 1 MB"

    def test_upper_boundary_is_exclusive_of_the_next_bucket(self) -> None:
        assert size_bucket_for(1024, _BUCKETS) == "1 KB-1 MB"

    def test_value_just_below_a_boundary_stays_in_the_lower_bucket(self) -> None:
        assert size_bucket_for(1023, _BUCKETS) == "< 1 MB"

    def test_open_ended_top_bucket(self) -> None:
        assert size_bucket_for(10_000_000, _BUCKETS) == "> 1 MB"
