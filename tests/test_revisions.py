"""Tests for collaborative editing / revision tracking."""

from __future__ import annotations

from pimd.revisions import (
    Comment,
    Revision,
    RevisionStatus,
    RevisionTracker,
    RevisionType,
    ReviewMetadata,
)


class TestRevisionTracker:
    def test_instantiation(self) -> None:
        tracker = RevisionTracker(document_id="doc-1", title="Test")
        assert tracker.metadata.document_id == "doc-1"
        assert tracker.metadata.title == "Test"

    def test_auto_document_id(self) -> None:
        tracker = RevisionTracker()
        assert tracker.metadata.document_id.startswith("doc-")

    def test_add_revision(self) -> None:
        tracker = RevisionTracker()
        rev = tracker.add_revision(
            revision_type=RevisionType.INSERTION,
            author="alice",
            start_pos=0,
            end_pos=0,
            new_text="Hello",
            description="Added greeting",
        )
        assert isinstance(rev, Revision)
        assert rev.revision_id.startswith("rev_")
        assert rev.revision_type == RevisionType.INSERTION
        assert rev.author == "alice"
        assert rev.new_text == "Hello"
        assert rev.status == RevisionStatus.PENDING

    def test_add_deletion_revision(self) -> None:
        tracker = RevisionTracker()
        rev = tracker.add_revision(
            revision_type=RevisionType.DELETION,
            author="bob",
            start_pos=5,
            end_pos=10,
            old_text="world",
            description="Removed word",
        )
        assert rev.revision_type == RevisionType.DELETION
        assert rev.old_text == "world"

    def test_add_replacement_revision(self) -> None:
        tracker = RevisionTracker()
        rev = tracker.add_revision(
            revision_type=RevisionType.REPLACEMENT,
            author="alice",
            start_pos=0,
            end_pos=5,
            old_text="Hello",
            new_text="Hi",
        )
        assert rev.revision_type == RevisionType.REPLACEMENT
        assert rev.old_text == "Hello"
        assert rev.new_text == "Hi"

    def test_revision_count(self) -> None:
        tracker = RevisionTracker()
        assert tracker.revision_count == 0
        tracker.add_revision(
            revision_type=RevisionType.INSERTION,
            author="a", start_pos=0, end_pos=0, new_text="x",
        )
        assert tracker.revision_count == 1
        tracker.add_revision(
            revision_type=RevisionType.DELETION,
            author="b", start_pos=0, end_pos=1, old_text="x",
        )
        assert tracker.revision_count == 2

    def test_accept_revision(self) -> None:
        tracker = RevisionTracker()
        rev = tracker.add_revision(
            revision_type=RevisionType.INSERTION,
            author="alice", start_pos=0, end_pos=0, new_text="x",
        )
        assert rev.status == RevisionStatus.PENDING
        assert tracker.accept_revision(rev.revision_id)
        assert rev.status == RevisionStatus.ACCEPTED

    def test_reject_revision(self) -> None:
        tracker = RevisionTracker()
        rev = tracker.add_revision(
            revision_type=RevisionType.INSERTION,
            author="alice", start_pos=0, end_pos=0, new_text="x",
        )
        assert tracker.reject_revision(rev.revision_id)
        assert rev.status == RevisionStatus.REJECTED

    def test_accept_nonexistent_revision(self) -> None:
        tracker = RevisionTracker()
        assert not tracker.accept_revision("nonexistent")

    def test_reject_nonexistent_revision(self) -> None:
        tracker = RevisionTracker()
        assert not tracker.reject_revision("nonexistent")

    def test_get_revisions_by_status(self) -> None:
        tracker = RevisionTracker()
        r1 = tracker.add_revision(RevisionType.INSERTION, "a", 0, 0, new_text="x")
        r2 = tracker.add_revision(RevisionType.DELETION, "b", 0, 1, old_text="y")
        tracker.accept_revision(r1.revision_id)

        pending = tracker.get_revisions(status=RevisionStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].revision_id == r2.revision_id

        accepted = tracker.get_revisions(status=RevisionStatus.ACCEPTED)
        assert len(accepted) == 1
        assert accepted[0].revision_id == r1.revision_id

    def test_get_revisions_by_author(self) -> None:
        tracker = RevisionTracker()
        tracker.add_revision(RevisionType.INSERTION, "alice", 0, 0, new_text="x")
        tracker.add_revision(RevisionType.INSERTION, "bob", 0, 0, new_text="y")

        alice_revs = tracker.get_revisions(author="alice")
        assert len(alice_revs) == 1

    def test_get_revisions_by_type(self) -> None:
        tracker = RevisionTracker()
        tracker.add_revision(RevisionType.INSERTION, "a", 0, 0, new_text="x")
        tracker.add_revision(RevisionType.DELETION, "b", 0, 1, old_text="y")

        insertions = tracker.get_revisions(revision_type=RevisionType.INSERTION)
        assert len(insertions) == 1

    def test_pending_revision_count(self) -> None:
        tracker = RevisionTracker()
        r1 = tracker.add_revision(RevisionType.INSERTION, "a", 0, 0, new_text="x")
        tracker.add_revision(RevisionType.INSERTION, "a", 0, 0, new_text="y")
        tracker.accept_revision(r1.revision_id)
        assert tracker.pending_revision_count == 1


class TestComments:
    def test_add_comment(self) -> None:
        tracker = RevisionTracker()
        cmt = tracker.add_comment(
            author="reviewer",
            text="Please fix this",
            start_pos=10,
            end_pos=100,
        )
        assert isinstance(cmt, Comment)
        assert cmt.comment_id.startswith("cmt_")
        assert cmt.author == "reviewer"
        assert cmt.text == "Please fix this"
        assert not cmt.resolved

    def test_comment_count(self) -> None:
        tracker = RevisionTracker()
        assert tracker.comment_count == 0
        tracker.add_comment(author="a", text="c1")
        assert tracker.comment_count == 1
        tracker.add_comment(author="b", text="c2")
        assert tracker.comment_count == 2

    def test_resolve_comment(self) -> None:
        tracker = RevisionTracker()
        cmt = tracker.add_comment(author="a", text="Fix this")
        assert tracker.resolve_comment(cmt.comment_id, resolved_by="manager")
        assert cmt.resolved
        assert cmt.resolved_by == "manager"
        assert cmt.resolved_at is not None

    def test_resolve_nonexistent_comment(self) -> None:
        tracker = RevisionTracker()
        assert not tracker.resolve_comment("nonexistent")

    def test_unresolved_comment_count(self) -> None:
        tracker = RevisionTracker()
        c1 = tracker.add_comment(author="a", text="c1")
        tracker.add_comment(author="b", text="c2")
        tracker.resolve_comment(c1.comment_id)
        assert tracker.unresolved_comment_count == 1

    def test_get_comments_by_resolved(self) -> None:
        tracker = RevisionTracker()
        c1 = tracker.add_comment(author="a", text="c1")
        tracker.add_comment(author="b", text="c2")
        tracker.resolve_comment(c1.comment_id)

        resolved = tracker.get_comments(resolved=True)
        assert len(resolved) == 1

        unresolved = tracker.get_comments(resolved=False)
        assert len(unresolved) == 1

    def test_get_comments_by_author(self) -> None:
        tracker = RevisionTracker()
        tracker.add_comment(author="alice", text="c1")
        tracker.add_comment(author="bob", text="c2")

        alice_cmts = tracker.get_comments(author="alice")
        assert len(alice_cmts) == 1

    def test_threaded_comments(self) -> None:
        tracker = RevisionTracker()
        parent = tracker.add_comment(author="a", text="Parent comment")
        child = tracker.add_comment(
            author="b", text="Reply", parent_id=parent.comment_id
        )
        assert child.parent_id == parent.comment_id


class TestReviewMetadata:
    def test_metadata_defaults(self) -> None:
        meta = ReviewMetadata(document_id="doc-1")
        assert meta.document_id == "doc-1"
        assert meta.status == "draft"
        assert meta.reviewers == []

    def test_reviewers_list(self) -> None:
        meta = ReviewMetadata(
            document_id="doc-1",
            reviewers=["alice", "bob"],
        )
        assert len(meta.reviewers) == 2
        assert "alice" in meta.reviewers

    def test_metadata_timestamps(self) -> None:
        meta = ReviewMetadata(document_id="doc-1")
        assert meta.created_at is not None
        assert meta.updated_at is not None

    def test_status_tracking(self) -> None:
        meta = ReviewMetadata(document_id="doc-1")
        meta.status = "approved"
        assert meta.status == "approved"

    def test_due_date(self) -> None:
        from datetime import datetime
        due = datetime(2026, 12, 31)
        meta = ReviewMetadata(document_id="doc-1", due_date=due)
        assert meta.due_date == due


class TestExportReviewSummary:
    def test_export_summary_structure(self) -> None:
        tracker = RevisionTracker(document_id="doc-1", title="Review Doc")
        tracker.add_revision(
            RevisionType.INSERTION, "alice", 0, 0, new_text="Hello"
        )
        tracker.add_comment(author="bob", text="Looks good")

        summary = tracker.export_review_summary()

        assert summary["document_id"] == "doc-1"
        assert summary["title"] == "Review Doc"
        assert summary["revisions"]["total"] == 1
        assert summary["revisions"]["pending"] == 1
        assert summary["comments"]["total"] == 1
        assert summary["comments"]["unresolved"] == 1

    def test_export_summary_revision_details(self) -> None:
        tracker = RevisionTracker()
        tracker.add_revision(
            RevisionType.INSERTION, "alice", 0, 0,
            new_text="Hello", description="Added text",
        )

        summary = tracker.export_review_summary()
        rev_item = summary["revisions"]["items"][0]
        assert rev_item["author"] == "alice"
        assert rev_item["type"] == "insertion"
        assert rev_item["description"] == "Added text"

    def test_export_summary_comment_details(self) -> None:
        tracker = RevisionTracker()
        tracker.add_comment(author="bob", text="Review comment")

        summary = tracker.export_review_summary()
        cmt_item = summary["comments"]["items"][0]
        assert cmt_item["author"] == "bob"
        assert "Review comment" in cmt_item["text"]
        assert not cmt_item["resolved"]
