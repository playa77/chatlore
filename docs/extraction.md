# The knowledge graph

```bash
uv run --locked chatlore process                 # chunk and embed first
uv run --locked chatlore extract --limit 10 --workers 1  # start with a small sample
uv run --locked chatlore extract                 # read the rest; safe to repeat and to interrupt
uv run --locked chatlore topics                  # what the conversations are about
uv run --locked chatlore entity "Postgres"       # one entity, its links, and where it came up
uv run --locked chatlore facts backups           # what was decided or found, and where
```

`chatlore extract` builds a graph from your conversations with the configured
language model (see [models.md](models.md)), in four steps:

1. **Entities, relationships, and facts.** Each chunk is read, and the model
   names the entities it mentions, how they relate, and the facts it states
   about them. Every chunk links to the entities it mentions, and every fact to
   the messages that said it, so anything in the graph leads back to where it
   came from.
2. **Summaries.** An entity mentioned in several places gets one short summary.
3. **Duplicates.** Names that may mean the same thing, such as "AWS" and "Amazon
   Web Services", are checked by the model and linked when they do.
4. **Topics.** Closely related entities are grouped, and the model writes a
   short report on each group.

Usable model answers are cached; a later run reuses matching inputs, models and
prompt versions. Invalid or missing answers can be requested again.

## What it costs

The fork's configured LLM is `z-ai/glm-5.3-flash` through OpenRouter, with
reasoning left to the model. Embedding is a separate paid operation; see
[models.md](models.md). No current cost or throughput benchmark has been
validated for these settings.

The CLI defaults to four chunks per extraction request and eight workers.
Start with `--limit 10 --workers 1` and review provider usage before scaling up.
`--batch-size` changes extraction chunks per request; `--workers` controls
concurrent requests. `--limit` only limits new extraction chunks: entity
summaries, duplicate checks and topic reports can still add calls. The token
summary is not a provider dollar cap; configure credit limits on both keys.

## Only new text is read

Answers are stored in `~/.chatlore/cache/extractions.db`: extractions by the
model, the prompt version, and the chunk text; summaries by the entity's name and
set of descriptions; duplicate verdicts by the pair of names; topic reports by
the set of entities in the topic. Cache keys also include the relevant model and
prompt version. An interrupted run keeps completed work; missing or unusable
answers can be requested again. Switching models or changing inputs/prompt
versions can cause new requests.

The graph is rebuilt from those stored answers at the end of every run. Text
removed by a re-import takes its entities with it, and after
`chatlore index --rebuild` and `chatlore process`, `chatlore extract` restores
the graph from matching caches. Missing entries or changed enrichment inputs
can still call the model; keep both model settings and caches when migrating.

## What an entity is

The model picks a type for each entity. It is asked to prefer person,
organization, project, tool, concept, place, and event, and may use another
single word when none fits.
Types that clearly mean one of them, such as company, city, or language, are
counted as that one. The model is also asked to skip labels that only make sense
inside their passage, such as "Solution A" or "Step 3".

Mentions are one entity when their names match ignoring case, spacing, hyphens
and underscores between words, trailing punctuation, and a plural "s" on the
last word: "Drive D:" and "drive d", or "Challenge fees" and "Challenge fee".
Punctuation inside a name counts, so "C++", "C#", and "C" stay apart.

## Facts

A fact is something a passage establishes that is worth remembering later: a
decision, a preference, a plan, a setting or number, a finding, or a problem and
its fix. General knowledge and options that were only considered are left out.
Each fact is one self-contained sentence about one entity, such as "The shop
backend moved from MySQL to PostgreSQL to get JSON columns.", and may involve a
second entity.

In the graph a fact links to its entity (`SUBJECT`), to the second entity if any
(`OBJECT`), and with `ASSERTED_IN` to every message that said it. The same
sentence said in several places, ignoring case, spacing, and trailing
punctuation, is one fact with all of those messages, and it is gone once none
of them is left. The latest 20 are kept on the fact with their conversation,
title, and date, for showing where it was said.

`chatlore facts` lists facts, newest first, and `chatlore facts <words>` finds
those that mention the words; each shows the conversation and date it was last
said in. `chatlore entity <name>` shows the facts about an entity, the web
interface shows them in the entity drawer with a link to the message, the MCP
server has a `facts` tool, and chat gets the facts about the entities a
question names.

Facts are implemented in this checkout. Older extracted libraries or changed
extraction prompts may need fresh extraction to populate them. Check a small
sample with `--limit` first; regeneration can incur provider charges.

## Summaries

Every distinct description of an entity is kept. An entity described once uses
that description as its summary. One described more often gets a summary of at
most 50 words from the model, written from up to 20 of its descriptions, and it
is written again only when a new description turns up.

## Duplicates

Different names for one thing are found in two passes. A cheap first pass
proposes pairs: one name starting with the other or spelled almost alike, one
being the other with words added, or one being the other's initials. The model
then judges each pair from both summaries; different versions, different
products of one company, and a part and its whole do not count as the same.
Confirmed pairs are linked with `SAME_AS`, and both entities stay.

Name similarity only proposes candidates; model verdicts can be wrong. Source
messages remain the evidence for interpreting or correcting an apparent match.

## Topics

Entities weighted by their relationships form a graph, and Leiden community
detection splits it into groups linked more densely inside than to each other.
Entities linked as duplicates count as one, entities with no relationships are
left out, and a group over 40 entities is split again on its own, so one
well-connected entity cannot pull half the graph into one topic. Each group of
at least three entities becomes a topic with a report: a title, a summary of at
most 80 words, and up to five findings. A topic whose entities are unchanged
keeps its report; new text can move entities between topics, and those topics
get new reports.

A topic can stay over 40 entities when community detection finds no useful split.

`chatlore topics` lists topics, largest first, and `chatlore topics <words>`
finds those whose report mentions the words. `chatlore entity <name>` shows an
entity's summary, its other names, its topic, its strongest relationships, the
facts about it, and the conversations that mention it.

## Search

`chatlore search --hybrid` also finds messages through the graph: a message whose
chunks mention an entity matching the query by name or summary joins the ranking,
and such hits say `entities` among the ways they matched.
