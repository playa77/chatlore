# Using this fork from local AI assistants (MCP)

Install and configure [this fork](../README.md#install-this-fork) first. Import
and process the library; extraction adds the entities, facts and topics that
the graph tools use. Run the server from the checkout so it reads the same
`.env` as your CLI:

```bash
uv --directory /absolute/path/to/chatlore run --locked chatlore mcp
```

The assistant normally launches this command. It communicates over standard
input/output and opens no network listener. Tools read the library without
editing it, but semantic retrieval sends queries to OpenRouter and needs
`CHATLORE_EMBEDDING_API_KEY`. The assistant uses its own model to answer, so the
MCP server does not use the ChatLore LLM key. Returned conversation text goes
to the assistant and its model provider.

## Configure a client

Use an absolute checkout path and an absolute path to `uv` if the desktop app
cannot find it on `PATH` (`Get-Command uv` in PowerShell or `command -v uv` in a
POSIX shell). JSON paths on Windows need escaped backslashes or forward slashes.

For Claude Desktop, add this entry through its developer configuration and
restart the client. Cursor uses the same `mcpServers` shape in its MCP settings:

```json
{
  "mcpServers": {
    "chatlore": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/chatlore", "run", "--locked", "chatlore", "mcp"],
      "env": { "CHATLORE_HOME": "/absolute/path/to/library" }
    }
  }
}
```

Omit `CHATLORE_HOME` to use `~/.chatlore`. Keep credentials in the checkout's
ignored `.env`, not in committed client configuration. Client environment
variables override `.env`; remove conflicting model/provider variables from
the launcher. Changing the library directory does not select a different `.env`.

For Claude Code:

```bash
claude mcp add chatlore -- uv --directory /absolute/path/to/chatlore run --locked chatlore mcp
```

Use the client's user/project scope option as appropriate. For another library,
put `--home /absolute/path/to/library` before `mcp` in the server arguments.
Other MCP clients that launch local processes can use the same command.

## Local HTTP transport

```bash
uv run --locked chatlore serve --host 127.0.0.1
```

The tools are also at `http://127.0.0.1:8000/mcp` over streamable HTTP. For
example, in a second terminal:

```bash
claude mcp add --transport http chatlore http://127.0.0.1:8000/mcp
```

MCP has transport hostname protections in private mode. Ordinary REST routes
have different protections; see [the security review](security-review.md).
Neither transport adds a login. Public hosting and remote assistant connectors
are outside this phase; no hosted demo URL is maintained for this fork.

## Tools

| Tool | What it returns |
|---|---|
| `ask_context` | Numbered passages relevant to a question plus graph context; no generated answer |
| `search` | Messages ranked by words, meaning and entities, optionally filtered by source |
| `conversation` | Conversation messages, in parts of about 30,000 characters |
| `entity` | Summary, other names, topic, relationships, facts and source conversations |
| `facts` | Decisions, preferences, plans and findings, with source messages |
| `topics` | Topics by size or matching words |
| `topic` | One topic's report and entities |

Results include IDs for follow-up calls. Read-only annotations describe library
writes; they do not mean offline operation or zero embedding cost. Query
embeddings are not saved in the passage cache.

## Checking the configuration

```bash
uv --directory /absolute/path/to/chatlore run --locked chatlore doctor
```

Confirm the correct library and embeddings via `openrouter`. The MCP process's
stdout is the protocol, so it does not print an interactive prompt. If retrieval
fails, check the embedding key, selected model, network access and whether the
library's vectors were built with that same model. Avoid using the inherited
demo library with the remote model configuration.
