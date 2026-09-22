# 08 — Authentication, authorization, and multi-user history

Status: **week 3**. Week 1 has no auth. Do not deploy week 1 publicly.

## Authentication with JWT

**What is it?** Every request carries a signed token (`Authorization: Bearer ...`) that proves
who the caller is. The API verifies the signature and expiry before doing anything else.

**Why do we need it?** Runs cost money and conversation history is private.

**What problem does it solve?** We know which user made every request, so we can enforce
quotas, ownership, and audit trails.

**What happens if we don't use it?** Anyone who finds the URL can run unlimited paid model calls
and read anyone's history.

**Design choice:** verify tokens issued by an identity provider (Auth0, Cognito, Entra, or
similar). Do not build password storage yourself.

## Authorization with roles (RBAC)

**What is it?** Rules that map roles to actions. Planned roles:

| Role | Can |
|---|---|
| `viewer` | Read their own threads |
| `researcher` | Everything `viewer` can, plus start new comparisons |
| `admin` | Manage quotas, view aggregate metrics |

**Why do we need it?** Not every authenticated user should be able to spend money.

**What problem does it solve?** It separates "who you are" from "what you may do".

**What happens if we don't use it?** Authorization logic gets scattered as `if user.email ==`
checks across routes, and one missed check becomes a data leak.

## Quotas

**What is it?** A limit on runs per user per day, checked at the API edge.

**Why do we need it?** A single user or a bug in a client can create unbounded cost.

**What problem does it solve?** Predictable cost per user.

**What happens if we don't use it?** One script in a loop becomes this month's bill.

## Multi-user conversation history

**What is it?** A persistent checkpointer (`PostgresSaver`) where every thread records its
owner's `user_id`, and every read or resume checks ownership.

**Why do we need it?** Users come back to earlier comparisons and ask follow-up questions.

**What problem does it solve?** Durable, per-user history that survives restarts and cannot
leak across users.

**What happens if we don't use it?** History disappears on restart (memory checkpointer), or
worse, `thread_id` alone becomes the only secret protecting someone's data.

**Rule:** a `thread_id` is an identifier, not a credential. Ownership is always checked
against the authenticated user.

## Where auth lives

Only in `api/` and `auth/`. The graph receives a `user_id` in its config for tracing and
ownership, but never parses tokens or checks roles. That keeps the graph testable without auth.
