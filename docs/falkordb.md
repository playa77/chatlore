# Keeping the graph in FalkorDB

```bash
uv sync --locked --extra falkordb
docker run -d -p 127.0.0.1:6379:6379 --name falkordb falkordb/falkordb:v4.20.7
export CHATLORE_STORE=falkordb
uv run --locked chatlore index           # copy the library into FalkorDB
uv run --locked chatlore process         # chunks and embeddings
uv run --locked chatlore extract         # entities and topics, from the cached answers where possible
```

This backend is inherited and optional; the current local-only setup uses
SQLite. Run these examples from this fork's checkout, keeping the same
OpenRouter configuration. The local database server is not a local model.

By default ChatLore keeps its graph in a SQLite file in the library folder,
which needs nothing else. [FalkorDB](https://www.falkordb.com) is a graph
database that runs as a server. Use it when you want to query the graph with
Cypher, look at it with FalkorDB's browser, or share one graph between several
machines on a network (outside the current phase). Every command, the web interface, and the MCP server
work the same on both.

## Settings

| Variable | Meaning |
|---|---|
| `CHATLORE_STORE` | `sqlite` (default) or `falkordb`. |
| `CHATLORE_FALKORDB_URL` | The server, `redis://localhost:6379` by default. Add a password as `redis://:password@host:6379`. |
| `CHATLORE_FALKORDB_GRAPH` | The graph's name, `chatlore` by default. Give each library its own. |

`chatlore doctor` shows which store is in use.

## Moving a library into FalkorDB

The conversations stay in the library folder either way, and the caches of
embeddings and model answers too, so the graph can be rebuilt in FalkorDB
without computing anything again:

1. Set the variables above.
2. `chatlore index` copies every conversation into the graph.
3. `chatlore process` makes the chunks and takes their embeddings from the cache.
4. `chatlore extract` rebuilds entities, relationships, and topics from the
   cached model answers. It needs a model key, but only asks the model about
   text it has not read yet.

Going back to SQLite is the same with `CHATLORE_STORE` unset. An archive from
`chatlore export` imports into either store. `chatlore index --rebuild` deletes
the graph and builds it again from the library.

## What is in the graph

Every node has the label `Node`, with its id in `_id`, its ChatLore label
(`Conversation`, `Message`, `Chunk`, `Entity`, `Fact`, `Topic`) in `_label`, and all
of its properties as JSON in `_props`. Simple values are copied into `p_`
properties as well, so they can be queried: an entity's name is `p_name`, a
topic's title is `p_title`. Edges have their ChatLore type, such as `MENTIONS`,
`RELATED_TO`, or `IN_TOPIC`, with their properties as JSON in `_props`.

```cypher
MATCH (e:Node {_label: 'Entity'})-[r:RELATED_TO]-(o:Node)
WHERE e.p_name = 'Tidewater'
RETURN o.p_name, r._props
```

Everything ChatLore adds for search, the `_ft_` text copies and the
`_embedding` vectors, is indexed in FalkorDB. Treat the graph as ChatLore's:
changes made to it directly are lost on the next `chatlore index --rebuild`.

## Differences from SQLite

- FalkorDB has no transactions spanning several queries. Each write is atomic,
  but an import interrupted halfway leaves the conversations written so far;
  running it again finishes the job, as with SQLite.
- Word search matches the same words as SQLite, without stemming or stop words,
  and ignores accents. Its scores are FalkorDB's own, so results with equal
  matches can come back in a different order.
- The server has to be running. Commands fail with a connection error when it
  is not.
- Network latency and server load affect performance; no current benchmark is
  maintained for this fork. SQLite avoids the extra server and network round trips.

The Docker example binds only to loopback. It creates an ephemeral server
without a persistence volume; plan backups before storing a real graph there.
Application archives do not configure or secure the database service.
