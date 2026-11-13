"""Tests for the command-line interface."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from chatlore import __version__
from chatlore.cli import app, default_home, load_env_file, run
from chatlore.llm import LLMAnswerError
from tests.fakes import FakeEmbedder, FakeLLM

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"chatlore {__version__}"


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "doctor" in result.output


def test_no_arguments_shows_help() -> None:
    result = runner.invoke(app, [])

    assert "Usage" in result.output


def test_default_home_falls_back_to_user_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHATLORE_HOME", raising=False)

    assert default_home() == Path.home() / ".chatlore"


def test_default_home_honours_environment_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CHATLORE_HOME", str(tmp_path))

    assert default_home() == tmp_path


def test_doctor_reports_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CHATLORE_HOME", str(tmp_path))

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "python" in result.output
    assert "exists" in result.output


_KEY_VARS = (
    "CHATLORE_LLM_BASE_URL",
    "CHATLORE_LLM_MODEL",
    "CHATLORE_LLM_API_KEY",
    "OPENROUTER_API_KEY",
    "CHATLORE_EMBEDDING_PROVIDER",
    "CHATLORE_EMBEDDING_API_KEY",
    "CHATLORE_EMBEDDING_MODEL",
)


@pytest.fixture
def key_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CHATLORE_HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "200")
    for name in _KEY_VARS:
        monkeypatch.delenv(name, raising=False)


def test_doctor_validates_both_keys_with_the_provider(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("CHATLORE_EMBEDDING_API_KEY", "sk-embed")
    calls: list[tuple[str, str]] = []

    def check(url: str, key: str) -> int:
        calls.append((url, key))
        return 200

    monkeypatch.setattr("chatlore.cli._url_status", check)
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    rows = [line for line in result.output.splitlines() if "│" in line]
    assert any("model key" in line and " valid " in line for line in rows)
    assert any("embedding key" in line and " valid " in line for line in rows)
    assert calls == [
        ("https://openrouter.ai/api/v1/key", "sk-chat"),
        ("https://openrouter.ai/api/v1/key", "sk-embed"),
    ]


def test_doctor_reports_a_rejected_key(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setattr("chatlore.cli._url_status", lambda url, key: 401)

    result = runner.invoke(app, ["doctor"])

    assert "rejected (HTTP 401)" in result.output


def test_doctor_says_when_a_key_cannot_be_checked(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setattr("chatlore.cli._url_status", lambda url, key: None)

    result = runner.invoke(app, ["doctor"])

    assert "could not check" in result.output


def test_doctor_probe_answers_with_the_configured_models(
    key_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("CHATLORE_EMBEDDING_API_KEY", "sk-embed")
    monkeypatch.setattr("chatlore.cli.make_llm", lambda: FakeLLM())
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())

    result = runner.invoke(app, ["doctor", "--probe"])

    assert result.exit_code == 0, result.output
    assert "spends a little credit" in result.output
    assert result.output.count("answered") == 2


def test_doctor_probe_names_the_remedy_when_the_key_has_no_balance(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("CHATLORE_EMBEDDING_API_KEY", "sk-embed")
    monkeypatch.setattr("chatlore.cli.make_llm", lambda: FakeLLM(payment_on_request=1))
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())

    result = runner.invoke(app, ["doctor", "--probe"])

    assert "credits" in result.output
    assert "openrouter.ai/settings/credits" in result.output


def test_doctor_probe_counts_a_probe_cut_off_as_reaching_the_model(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A reasoning model can spend the probe's tiny budget thinking; the point of
    # the probe is that the key reaches the model, so say that instead of failing.
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("CHATLORE_EMBEDDING_API_KEY", "sk-embed")

    class CutOff(FakeLLM):
        def complete(self, messages: Any, **kwargs: Any) -> Any:
            raise LLMAnswerError("fake model stopped at the token limit before finishing")

    monkeypatch.setattr("chatlore.cli.make_llm", lambda: CutOff())
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())

    result = runner.invoke(app, ["doctor", "--probe"])

    assert "reached the model" in result.output


def test_process_without_an_embedding_key_says_what_it_will_use(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())

    result = runner.invoke(app, ["process"])

    assert "local FastEmbed" in result.output
    assert "CHATLORE_EMBEDDING_PROVIDER=openrouter" in result.output


def test_process_with_openrouter_and_no_key_names_the_variable(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())

    result = runner.invoke(app, ["process"])

    assert "CHATLORE_EMBEDDING_API_KEY" in result.output
    assert "local FastEmbed" not in result.output


def test_extract_without_a_model_key_says_what_needs_one(key_environment: None) -> None:
    result = runner.invoke(app, ["extract"])

    assert "No model API key set" in result.output
    assert "CHATLORE_LLM_API_KEY" in result.output


def test_search_semantic_without_an_embedding_key_warns(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())

    result = runner.invoke(app, ["search", "anything", "--semantic"])

    assert "No embedding API key set" in result.output


def test_serve_without_keys_warns_about_both(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("uvicorn.run", lambda app, **options: None)

    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 0, result.output
    assert "No model API key set" in result.output
    assert "No embedding API key set" in result.output


def test_a_configured_setup_warns_about_nothing(
    key_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHATLORE_LLM_API_KEY", "sk-chat")
    monkeypatch.setenv("CHATLORE_EMBEDDING_PROVIDER", "openrouter")
    monkeypatch.setenv("CHATLORE_EMBEDDING_API_KEY", "sk-embed")
    monkeypatch.setattr("chatlore.cli.make_embedder", lambda home: FakeEmbedder())
    monkeypatch.setattr("chatlore.cli.make_llm", lambda: FakeLLM())

    extract = runner.invoke(app, ["extract"])
    process = runner.invoke(app, ["process"])

    assert "No model API key set" not in extract.output
    assert "No embedding API key set" not in process.output
    assert "local FastEmbed" not in process.output


def test_doctor_names_the_model_without_showing_the_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CHATLORE_HOME", str(tmp_path))
    monkeypatch.delenv("CHATLORE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("CHATLORE_LLM_MODEL", raising=False)
    monkeypatch.delenv("CHATLORE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CHATLORE_LLM_REASONING", raising=False)
    monkeypatch.setenv("COLUMNS", "200")
    missing = runner.invoke(app, ["doctor"])
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-secret")

    present = runner.invoke(app, ["doctor"])

    assert "deepseek/deepseek-v4-flash" in missing.output
    assert "reasoning off" in missing.output
    assert "set OPENROUTER_API_KEY" in missing.output
    assert "API key set" in present.output
    assert "sk-or-secret" not in present.output


def test_display_path_shortens_the_home_directory(tmp_path: Path) -> None:
    from chatlore.cli import display_path

    assert display_path(Path.home() / ".chatlore" / "x") == "~/.chatlore/x"
    assert display_path(tmp_path) == str(tmp_path) or display_path(tmp_path).startswith("~/")


@pytest.fixture
def env_file_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset the variables these tests read, and restore them afterwards.

    load_dotenv writes straight into os.environ, so each variable is set once
    through monkeypatch first; that way teardown removes whatever a test loaded.
    """
    for name in ("OPENROUTER_API_KEY", "CHATLORE_LLM_MODEL"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


@pytest.mark.usefixtures("env_file_variables")
def test_env_file_fills_in_missing_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-or-from-file\n", encoding="utf-8")
    nested = tmp_path / "some" / "folder"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    load_env_file()

    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-from-file"


@pytest.mark.usefixtures("env_file_variables")
def test_the_environment_wins_over_the_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text(
        "OPENROUTER_API_KEY=sk-or-from-file\nCHATLORE_LLM_MODEL=from-file\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CHATLORE_LLM_MODEL", "from-shell")

    load_env_file()

    assert os.environ["CHATLORE_LLM_MODEL"] == "from-shell"
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-from-file"


@pytest.mark.usefixtures("env_file_variables")
def test_no_env_file_is_fine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("chatlore.cli.find_dotenv", lambda usecwd: "")

    load_env_file()

    assert "OPENROUTER_API_KEY" not in os.environ


@pytest.mark.usefixtures("env_file_variables")
def test_the_chatlore_command_reads_the_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-or-from-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CHATLORE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("COLUMNS", "200")
    for name in ("CHATLORE_LLM_BASE_URL", "CHATLORE_LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("sys.argv", ["chatlore", "doctor"])

    with pytest.raises(SystemExit) as exited:
        run()

    output = capsys.readouterr().out
    assert exited.value.code == 0
    assert "API key set" in output
    assert "sk-or-from-file" not in output
