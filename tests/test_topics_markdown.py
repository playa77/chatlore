"""The topics Markdown report."""

from __future__ import annotations

from chatlore.archive import topics_markdown
from chatlore.store import Label, Node


def _topic(title: str, size: int, entities: list[str], findings: list[str], summary: str) -> Node:
    return Node(
        f"topic:{title.lower()}",
        Label.TOPIC,
        {
            "title": title,
            "summary": summary,
            "findings": findings,
            "size": size,
            "entities": entities,
        },
    )


def test_each_topic_is_a_section_with_summary_findings_and_members() -> None:
    text = topics_markdown(
        [
            _topic(
                "Moving Tidewater off Postgres",
                3,
                ["Tidewater", "Postgres", "SQLite"],
                ["Tidewater moved to SQLite for the demo.", "Backups run nightly."],
                "Why the project left Postgres and how SQLite took over.",
            )
        ]
    )

    assert text.startswith("# Topics")
    assert "## Moving Tidewater off Postgres" in text
    assert "Why the project left Postgres and how SQLite took over." in text
    assert "- Tidewater moved to SQLite for the demo." in text
    assert "- Backups run nightly." in text
    assert "*3 entities*: Tidewater, Postgres, SQLite" in text


def test_topics_come_out_largest_first_in_the_given_order() -> None:
    text = topics_markdown(
        [
            _topic("Big", 9, ["A", "B"], [], "s"),
            _topic("Small", 2, ["C"], [], "s"),
        ]
    )

    assert text.index("## Big") < text.index("## Small")


def test_a_topic_without_findings_or_members_still_renders() -> None:
    text = topics_markdown([_topic("Bare", 0, [], [], "Just a summary.")])

    assert "## Bare" in text
    assert "Just a summary." in text
    assert "*0 entities*:" in text
    assert "- " not in text.replace("*0 entities*:", "")


def test_no_topics_at_all_is_just_the_header() -> None:
    assert topics_markdown([]).strip() == "# Topics"
