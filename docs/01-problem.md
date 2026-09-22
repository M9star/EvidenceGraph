# 01 — Problem

## Statement

> Compare the latest EV incentives available in France, Germany, the UK, and India. Search
> official government or trusted sources for each country, extract the eligibility rules and
> benefits, and return one consolidated comparison with citations.

## Why this problem is a good teacher

It looks simple, and a single prompt to a chatbot will produce a confident answer. That answer
is usually stale, uncited, or partly invented. Making it trustworthy forces every hard part of
agentic engineering:

- **Multiple independent sub-tasks**: four countries, four languages, four source systems.
- **Untrusted inputs**: the open web contains blogs, dealer ads, and outdated news.
- **Policies change**: incentives are cut, capped, or replaced. "Latest" must be defensible.
- **Partial failure is normal**: a government site will be slow or down on some day.
- **Output must be checkable**: a human must be able to click every citation.

## Inputs and outputs

- **Input:** a query and a list of country codes (default: `FR`, `DE`, `UK`, `IN`).
- **Output:** a `Comparison` containing one `CountryReport` per country. Each report has a
  status (`ok` or `insufficient_evidence`) and a list of `IncentiveRecord`s. Every record has at
  least one `Citation` with URL, title, and retrieval time.

## In scope

- Passenger EV purchase and ownership incentives at national level.
- Official government sources on an explicit allowlist per country.
- A single consolidated structured answer with citations.

## Non-goals (for now)

- Regional or city-level incentives.
- Commercial fleets, two-wheelers, charging hardware grants.
- Legal or tax advice. The system reports what sources say; it does not advise.
- A chat UI. The API and tests come first.

## Success criteria

- Every claim in the output is backed by a citation to an allowlisted domain.
- If a country cannot be researched, the output says so explicitly instead of guessing.
- The same request is traceable end to end: which pages, which model calls, how long, what cost.
- A regression in quality is caught by CI before it reaches users.
