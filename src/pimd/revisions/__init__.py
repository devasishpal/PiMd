"""Collaborative editing support — document revision model.

Provides a complete revision tracking system for documents,
including insertions, deletions, comments, annotations, and
review metadata. Designed for future collaborative workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RevisionType(Enum):
    """Type of revision operation."""
    INSERTION = "insertion"
    DELETION = "deletion"
    REPLACEMENT = "replacement"
    FORMATTING = "formatting"


class RevisionStatus(Enum):
    """Status of a revision."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class Revision:
    """A single tracked change in the document.

    Attributes:
        revision_id: Unique identifier for this revision.
        revision_type: Type of change (insertion, deletion, etc.).
        author: Name or identifier of the author.
        timestamp: When the revision was made.
        start_pos: Starting position of the change (character offset).
        end_pos: Ending position of the change.
        old_text: Text before the change (empty for insertions).
        new_text: Text after the change (empty for deletions).
        description: Human-readable description of the change.
        status: Review status (pending, accepted, rejected).
        metadata: Additional revision metadata.
    """
    revision_id: str
    revision_type: RevisionType
    author: str
    timestamp: datetime
    start_pos: int
    end_pos: int
    old_text: str = ""
    new_text: str = ""
    description: str = ""
    status: RevisionStatus = RevisionStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Comment:
    """A comment or annotation on a document.

    Attributes:
        comment_id: Unique identifier.
        author: Name or identifier of the commenter.
        timestamp: When the comment was created.
        text: The comment text.
        start_pos: Starting position of the annotated range.
        end_pos: Ending position of the annotated range.
        resolved: Whether the comment has been resolved.
        resolved_by: Who resolved the comment.
        resolved_at: When the comment was resolved.
        parent_id: ID of the parent comment (for threading).
        metadata: Additional comment metadata.
    """
    comment_id: str
    author: str
    timestamp: datetime
    text: str
    start_pos: int = 0
    end_pos: int = 0
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewMetadata:
    """Metadata for a document review session.

    Attributes:
        document_id: Unique document identifier.
        title: Document title.
        reviewers: List of reviewer identifiers.
        status: Review status.
        created_at: When the review was created.
        updated_at: Last update time.
        due_date: Optional review deadline.
        metadata: Additional review metadata.
    """
    document_id: str
    title: str = ""
    reviewers: list[str] = field(default_factory=list)
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    due_date: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RevisionTracker:
    """Tracks document revisions for collaborative editing.

    Manages a collection of revisions, comments, and review metadata
    for a single document. Provides APIs for adding, querying, and
    exporting review information.

    Usage::

        tracker = RevisionTracker(document_id="doc-123")
        tracker.add_revision(
            revision_type=RevisionType.INSERTION,
            author="alice",
            start_pos=42,
            end_pos=42,
            new_text="new content",
        )
        tracker.add_comment(
            author="bob",
            text="Please review this paragraph",
            start_pos=10,
            end_pos=200,
        )
        report = tracker.export_review_summary()
    """

    def __init__(self, document_id: str = "", title: str = "") -> None:
        self.metadata = ReviewMetadata(
            document_id=document_id or f"doc-{datetime.utcnow().timestamp()}",
            title=title,
        )
        self._revisions: list[Revision] = []
        self._comments: list[Comment] = []
        self._next_revision_num = 1
        self._next_comment_num = 1

    # ------------------------------------------------------------------
    # Revision management
    # ------------------------------------------------------------------

    def add_revision(
        self,
        revision_type: RevisionType,
        author: str,
        start_pos: int,
        end_pos: int,
        old_text: str = "",
        new_text: str = "",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Revision:
        """Add a tracked revision to the document.

        Args:
            revision_type: Type of change.
            author: Author identifier.
            start_pos: Start character offset.
            end_pos: End character offset.
            old_text: Text before change.
            new_text: Text after change.
            description: Optional description.
            metadata: Additional revision metadata.

        Returns:
            The created Revision.
        """
        revision = Revision(
            revision_id=self._next_id("rev"),
            revision_type=revision_type,
            author=author,
            timestamp=datetime.utcnow(),
            start_pos=start_pos,
            end_pos=end_pos,
            old_text=old_text,
            new_text=new_text,
            description=description,
            status=RevisionStatus.PENDING,
            metadata=metadata or {},
        )
        self._revisions.append(revision)
        self._next_revision_num += 1
        self.metadata.updated_at = datetime.utcnow()
        return revision

    def get_revisions(
        self,
        status: RevisionStatus | None = None,
        author: str | None = None,
        revision_type: RevisionType | None = None,
    ) -> list[Revision]:
        """Get revisions, optionally filtered.

        Args:
            status: Filter by revision status.
            author: Filter by author.
            revision_type: Filter by change type.

        Returns:
            List of matching Revision objects.
        """
        result = self._revisions[:]
        if status:
            result = [r for r in result if r.status == status]
        if author:
            result = [r for r in result if r.author == author]
        if revision_type:
            result = [r for r in result if r.revision_type == revision_type]
        return result

    def accept_revision(self, revision_id: str) -> bool:
        """Accept a pending revision.

        Args:
            revision_id: ID of the revision to accept.

        Returns:
            True if accepted, False if not found.
        """
        for rev in self._revisions:
            if rev.revision_id == revision_id and rev.status == RevisionStatus.PENDING:
                rev.status = RevisionStatus.ACCEPTED
                self.metadata.updated_at = datetime.utcnow()
                return True
        return False

    def reject_revision(self, revision_id: str) -> bool:
        """Reject a pending revision.

        Args:
            revision_id: ID of the revision to reject.

        Returns:
            True if rejected, False if not found.
        """
        for rev in self._revisions:
            if rev.revision_id == revision_id and rev.status == RevisionStatus.PENDING:
                rev.status = RevisionStatus.REJECTED
                self.metadata.updated_at = datetime.utcnow()
                return True
        return False

    # ------------------------------------------------------------------
    # Comment management
    # ------------------------------------------------------------------

    def add_comment(
        self,
        author: str,
        text: str,
        start_pos: int = 0,
        end_pos: int = 0,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Comment:
        """Add a comment or annotation to the document.

        Args:
            author: Commenter identifier.
            text: Comment text.
            start_pos: Start of annotated range.
            end_pos: End of annotated range.
            parent_id: For threaded replies.
            metadata: Additional metadata.

        Returns:
            The created Comment.
        """
        comment = Comment(
            comment_id=self._next_id("cmt"),
            author=author,
            timestamp=datetime.utcnow(),
            text=text,
            start_pos=start_pos,
            end_pos=end_pos,
            parent_id=parent_id,
            metadata=metadata or {},
        )
        self._comments.append(comment)
        self._next_comment_num += 1
        self.metadata.updated_at = datetime.utcnow()
        return comment

    def get_comments(
        self,
        resolved: bool | None = None,
        author: str | None = None,
    ) -> list[Comment]:
        """Get comments, optionally filtered.

        Args:
            resolved: Filter by resolved status.
            author: Filter by author.

        Returns:
            List of matching Comment objects.
        """
        result = self._comments[:]
        if resolved is not None:
            result = [c for c in result if c.resolved == resolved]
        if author:
            result = [c for c in result if c.author == author]
        return result

    def resolve_comment(
        self, comment_id: str, resolved_by: str = ""
    ) -> bool:
        """Mark a comment as resolved.

        Args:
            comment_id: ID of the comment to resolve.
            resolved_by: Who resolved it.

        Returns:
            True if resolved, False if not found.
        """
        for cmt in self._comments:
            if cmt.comment_id == comment_id and not cmt.resolved:
                cmt.resolved = True
                cmt.resolved_by = resolved_by
                cmt.resolved_at = datetime.utcnow()
                self.metadata.updated_at = datetime.utcnow()
                return True
        return False

    # ------------------------------------------------------------------
    # Statistics and export
    # ------------------------------------------------------------------

    @property
    def revision_count(self) -> int:
        """Total number of revisions."""
        return len(self._revisions)

    @property
    def comment_count(self) -> int:
        """Total number of comments."""
        return len(self._comments)

    @property
    def pending_revision_count(self) -> int:
        """Number of pending (unreviewed) revisions."""
        return sum(1 for r in self._revisions if r.status == RevisionStatus.PENDING)

    @property
    def unresolved_comment_count(self) -> int:
        """Number of unresolved comments."""
        return sum(1 for c in self._comments if not c.resolved)

    def export_review_summary(self) -> dict[str, Any]:
        """Export a summary of all review information.

        Returns:
            Dictionary with review metadata, revision stats, and comment stats.
        """
        return {
            "document_id": self.metadata.document_id,
            "title": self.metadata.title,
            "status": self.metadata.status,
            "reviewers": self.metadata.reviewers,
            "created_at": self.metadata.created_at.isoformat(),
            "updated_at": self.metadata.updated_at.isoformat(),
            "revisions": {
                "total": self.revision_count,
                "pending": self.pending_revision_count,
                "accepted": sum(
                    1 for r in self._revisions if r.status == RevisionStatus.ACCEPTED
                ),
                "rejected": sum(
                    1 for r in self._revisions if r.status == RevisionStatus.REJECTED
                ),
                "items": [
                    {
                        "id": r.revision_id,
                        "type": r.revision_type.value,
                        "author": r.author,
                        "timestamp": r.timestamp.isoformat(),
                        "description": r.description,
                        "status": r.status.value,
                    }
                    for r in self._revisions
                ],
            },
            "comments": {
                "total": self.comment_count,
                "unresolved": self.unresolved_comment_count,
                "items": [
                    {
                        "id": c.comment_id,
                        "author": c.author,
                        "timestamp": c.timestamp.isoformat(),
                        "text": c.text[:200],
                        "resolved": c.resolved,
                    }
                    for c in self._comments
                ],
            },
        }

    def export_docx_revisions(
        self, document: Any
    ) -> None:
        """Apply tracked revisions as Word revision marks (future).

        Args:
            document: A python-docx Document object.

        Note:
            This is a future API for exporting revisions as native
            Word tracked changes. Currently a placeholder.
        """
        # Future: apply revisions as native Word tracked changes
        pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _next_id(self, prefix: str) -> str:
        """Generate a unique identifier."""
        ts = int(datetime.utcnow().timestamp() * 1000000)
        return f"{prefix}_{ts}_{self._next_revision_num}"
