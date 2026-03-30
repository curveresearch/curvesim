Triage and Refactor Plan
========================

This document captures a practical plan for working through the current
Curvesim backlog without blocking on the full simulation redesign.

Status
------

This plan is based on repository and GitHub state as of March 29, 2026.

There are three distinct workstreams:

1. Stabilize current user-facing breakages in data access and simulation entrypoints.
2. Clean up the open PR queue so there is one canonical path for each change.
3. Split the simulation redesign into mergeable slices that preserve current behavior.


Guiding Principles
------------------

- Do not block urgent fixes on the full redesign epic.
- Keep ``autosim`` working until there is a proven replacement path.
- Prefer small, testable, mergeable changes over one large refactor PR.
- Use integration smoke tests to protect all external data dependencies.
- Close or supersede stale PRs once a canonical branch exists.


Current Assessment
------------------

The highest-priority issues are external data and API breakages:

- Issue ``#304``: subgraph URL does not exist
- Issue ``#300``: hosted subgraph URLs are no longer available
- Issue ``#174``: transition away from fragile subgraph usage
- Issue ``#296``: ``matic`` bug in Coingecko path
- Issue ``#290``: stale README and docs around data access
- Issue ``#81``: missing live API integration tests

The key open PRs need triage before implementation starts:

- PR ``#303`` should be treated as the main candidate for the current data fix path.
- PR ``#305`` appears to overlap heavily with ``#303`` and should likely be closed or folded in.
- PR ``#298`` is an older, narrower version of the same subgraph migration theme.
- PR ``#301`` is too large to merge whole and should be decomposed into smaller follow-on changes.

The redesign epic is already partially represented in ``main``:

- ``curvesim/templates/data_source.py`` has ``DataSource`` and ``FileDataSource`` scaffolding.
- ``curvesim/templates/time_sequence.py`` has ``TimeSequence`` support.
- ``curvesim/templates/sim_asset.py`` has ``SimAsset`` abstractions.

However, the new abstractions are not fully wired through the pipeline:

- ``curvesim/templates/trader.py`` still keeps state via ``self.pool``.
- ``curvesim/metrics/state_log/log.py`` still keeps state via ``self.pool``.
- ``curvesim/sim/__init__.py`` still exposes ``autosim`` as the primary entrypoint.
- ``FileDataSource`` exists as a template, but the end-to-end integration described in
  issue ``#287`` is not complete.


Execution Plan
--------------

Phase 1: Stabilize current behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objectives:

- Restore working metadata, volume, and price fetches for supported pools.
- Fix obvious low-risk bugs that block current flows.
- Update the minimum user-facing documentation needed to reflect reality.

Checklist:

- [ ] Review PR ``#303`` against ``main`` and identify what can be reused directly.
- [ ] Confirm whether PR ``#305`` is a duplicate or partial continuation of ``#303``.
- [ ] Implement or extract a canonical fix for subgraph and Curve API endpoint breakages.
- [ ] Fix issue ``#296`` if still present on ``main``.
- [ ] Update docs and notebook references that still describe deprecated endpoints.
- [ ] Close or supersede PRs ``#298`` and ``#305`` once the canonical fix path is chosen.

Exit criteria:

- ``curvesim.pool.get(...)`` works for at least one known mainnet pool.
- ``autosim(...)`` works on a known stable pool path.
- Docs no longer reference clearly obsolete endpoints.


Phase 2: Add regression coverage around external integrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objectives:

- Catch future API and endpoint breakages quickly.
- Keep tests small enough to run regularly.

Checklist:

- [ ] Add a smoke test for metadata fetch.
- [ ] Add a smoke test for pool volume fetch.
- [ ] Add a smoke test for ``autosim`` on a representative pool.
- [ ] Decide whether tests should hit live services directly or use deterministic recorded fixtures.
- [ ] Document how these tests should be run in CI and locally.

Exit criteria:

- A minimal integration suite exists for the current data path.
- The suite fails cleanly when an endpoint changes or disappears.


Phase 3: Clean and reorder the PR / issue queue
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objectives:

- Reduce backlog ambiguity.
- Make the remaining work easy to assign and review.

Checklist:

- [ ] Pick one canonical issue for the "current data path is broken" cluster.
- [ ] Mark overlapping issues and PRs as blocked, superseded, or closed.
- [ ] Convert PR ``#301`` into a tracked stack of smaller implementation slices.
- [ ] Move broad redesign notes into issue checklists rather than leaving them implicit in a large PR.

Exit criteria:

- Each active workstream has one clear owner artifact: issue, PR, or checklist item.
- There is no ambiguity about whether ``#298``, ``#303``, and ``#305`` are all still active.


Phase 4: Split the simulation redesign into mergeable slices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Objectives:

- Continue the refactor without breaking current users.
- Land architectural improvements in a sequence that preserves reviewability.
- Use a broker-centered runtime model so execution, logging, and future
  multi-venue behavior can be introduced incrementally.

See also:

- ``docs/simulation_redesign.rst`` for the current runtime design note and
  phased execution model.

Proposed slice order:

1. Introduce broker-side execution objects and a thin venue adapter around the
   current pool simulation path, keeping the current volume-limited arbitrage
   pipeline largely intact.
2. Complete issue ``#288`` by making ``Trader`` and ``StateLog`` stateless and
   routing execution through the broker rather than directly through the trader.
3. Add an adapter from broker output to the current metric and results path so
   existing metrics remain usable during the transition.
4. Introduce a native ``Simulation`` runtime that owns the event loop and
   re-expresses current pipeline entrypoints as wrappers over that runtime.
5. Continue broader abstractions such as multi-venue execution or richer market
   models only after the brokered immediate-execution path is stable.
6. Deprecate ``autosim`` only after the new path has parity, docs, and tests.

Checklist:

- [ ] Write down the minimal broker order, execution, and event contracts before
  changing core pipeline code.
- [ ] Introduce a thin venue adapter for the current pool execution path.
- [ ] Finish ``DataSource`` integration without removing current public APIs.
- [ ] Remove ``pool`` state from trader and state-log components.
- [ ] Add a compatibility layer from broker output to today's metrics.
- [ ] Introduce ``Simulation`` as the native runtime without removing current
  pipeline entrypoints.
- [ ] Keep public pipeline entrypoints backward-compatible during the migration.
- [ ] Add tests for each slice before deprecating old behavior.
- [ ] Document the migration path before changing the default entrypoint.

Exit criteria:

- Each slice can merge independently.
- The redesign no longer depends on a single large PR.
- ``autosim`` remains functional until explicitly deprecated.


Deferred Work
-------------

The following should generally wait until Phases 1 through 3 are complete unless
they directly support stabilization:

- Issue ``#299``: StableSwap NG oracle support
- Issue ``#297``: exponential smoothing
- Issue ``#294``: price impact tool
- Issue ``#292``: extend pool factory to cryptoswap
- Issue ``#291``: Altair deprecation warning


Recommended Next Actions
------------------------

1. Review PR ``#303`` first and decide whether it should be revived or replaced by a
   fresh smaller PR.
2. Triage PRs ``#298`` and ``#305`` relative to that decision.
3. Fix the current data path on ``main`` before starting new feature work.
4. Open explicit child tasks for issue ``#287`` and issue ``#288`` if they need to
   be broken down further.
5. Treat PR ``#301`` as a design source, not as the next merge target.
