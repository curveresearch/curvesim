Simulation Redesign
===================

This note sketches a phased redesign of the simulation runtime.  The intent is
to preserve today's working arbitrage pipelines while moving toward a runtime
that can support broader use-cases already envisioned in the docs, such as
multiple venues, LP-token or basket trading, and non-pool venues like a
collateralized debt position.


Goals
-----

The redesign should:

1. preserve today's public entrypoints during transition, especially
   :func:`curvesim.sim.autosim` and the existing pipeline functions
2. reduce implicit coupling between pool execution, strategy logic, and logging
3. make execution flow explicit enough to support delayed execution and richer
   venue behavior later
4. support future use-cases beyond a single Curve pool versus a single
   price-volume feed

The redesign should not:

1. require a big-bang rewrite
2. require a config framework to be usable
3. hide compatibility problems inside a large builder or container


Current Constraints
-------------------

Today's runtime is shaped around:

* a param sampler
* a price sampler
* a strategy
* a trader that directly executes against a pool
* a state log that records pool-centric state

That works for today's simple and volume-limited arbitrage flows, but it
creates tight coupling:

* execution is embedded in the trader
* logging is embedded in a pool-centric state log
* strategies assume immediate execution
* feeds are effectively modeled as ``PriceVolume``

This makes broader scenarios awkward:

* multiple venues in one run
* delayed execution or partial fills
* limit orders or timelocked protocol actions
* venues that are not naturally "pools"


Target Runtime Model
--------------------

The proposed direction is a brokered runtime.

Core runtime roles:

* ``Agent`` decides what to do
* ``Broker`` validates, routes, executes, and records
* ``Venue`` is anything that can accept economic actions
* ``MarketFeed`` provides observations to the runtime
* ``Recorder`` turns broker and venue state into metric inputs and results

The broker is the center of the execution model.  Agents do not execute
directly against venues.  Instead, they submit intents or orders to the broker,
which:

* checks compatibility
* routes to the right venue
* records fills, rejections, or pending states
* emits normalized execution and position events


Minimal Runtime Contracts
-------------------------

The first useful runtime should standardize a small set of contracts rather than
introducing many abstractions at once.

Suggested minimum contracts:

* ``OrderIntent``: what an agent wants to do
* ``Order``: broker-owned lifecycle state
* ``ExecutionUpdate``: venue response to a submitted order
* ``PositionUpdate``: broker-owned record of a change in holdings or liabilities
* ``Event``: normalized record for metrics, debugging, and auditability

The main point is not the exact class names.  The point is to separate:

* decision-making
* execution
* account or position effects
* logging


Phase 1: Broker Wrapper
-----------------------

The first baby step should look very similar to today's volume-limited
arbitrage flow.

The old pieces remain:

* ``PriceVolume``
* current pool simulation interfaces
* existing metric classes
* current pipeline entrypoints

New pieces are introduced as thin adapters:

* ``CurveVenue`` wraps a current sim pool
* ``VolumeLimitedArbAgent`` replaces the direct trader execution path
* ``Broker`` accepts intents and routes them to the venue
* ``Recorder`` or an adapter layer converts broker output into today's metric
  inputs

At this stage, execution can still be immediate and synchronous.  The point is
to prove the contracts without changing the public shape too much.

Illustrative flow:

1. current pipeline builds the pool and market data as it does today
2. pool is wrapped as a ``CurveVenue``
3. ``PriceVolume`` samples are exposed to the agent via a lightweight decision
   context
4. agent emits ``OrderIntent`` objects instead of directly trading
5. broker executes those intents against the venue and records the result
6. recorder adapts broker state into the current results path

Why this phase matters:

* execution becomes explicit
* logging moves out of the trader
* the broker becomes the single place to add delayed execution later
* the public APIs can remain largely unchanged


Phase 2: Native ``Simulation`` Runtime
--------------------------------------

Once the brokered contracts are proven, the next step is to make them native
instead of adapter-based.

The central runtime becomes a ``Simulation`` object responsible for:

* advancing time
* collecting observations from feeds
* giving each agent a read-only decision context
* routing intents through the broker
* recording results and producing metrics

The core user-facing shape becomes something like:

.. code-block:: python

   sim = Simulation(
       time_sequence=time_sequence,
       venues=[curve_3pool],
       feeds=[price_volume_feed],
       agents=[volume_limited_arb_agent],
       metrics=DEFAULT_METRICS,
   )
   results = sim.run()

This stage should remove the most fiddly transitional code:

* no manual broker setup in user code
* no manual decision-context assembly in user code
* no manual adaptation from event log to results

Old entrypoints remain as wrappers:

* ``autosim()`` builds a default ``Simulation``
* ``simple.pipeline()`` builds a simple-arbitrage ``Simulation``
* ``vol_limited_arb.pipeline()`` builds a volume-limited ``Simulation``


Phase 3: Order Lifecycle and Delayed Execution
----------------------------------------------

Once the broker is native, the runtime can start supporting richer venue
behavior without another conceptual rewrite.

Examples of capabilities that should become possible at this stage:

* delayed execution
* limit orders
* partial fills
* cancellation and expiry
* protocol actions with cooldowns or timelocks

This does not require changing the ``Simulation`` shape again.  It requires
extending the broker and venue interaction so that venues can return
``accepted`` or ``pending`` updates rather than always returning an immediate
fill.

That is why the broker is important: it creates a place for order lifecycle
state to live outside both the agent and the venue.


Phase 4: Multi-Venue and Non-Pool Use-Cases
-------------------------------------------

With the broker and native ``Simulation`` runtime in place, the framework can
expand to the use-cases already described in :doc:`advanced`:

* routing through multiple pools
* trading between competing venues
* trading LP tokens or baskets
* non-pool venues such as a collateralized debt position

At this point, the current ``SimPool`` naming may become too narrow.  The
important thing is not to force an early rename, but to ensure the runtime
contracts are general enough that a venue does not have to literally be a pool.


Metrics and Results Migration
-----------------------------

The existing metric system is valuable and should be preserved if possible.

In the early phases, broker output should be adapted into a structure that
today's metrics can consume.  That avoids a large rewrite while the runtime
contracts are still settling.

Later, metrics can move toward consuming normalized broker events and venue
snapshots directly.  This migration should be incremental and only happen after
the brokered execution model is stable.


Backward Compatibility
----------------------

Compatibility should be treated as a requirement, not a cleanup item.

During the transition:

* ``autosim()`` remains the main convenience API
* current pipeline functions remain available
* existing result objects should remain intact
* any new runtime objects should initially sit behind current entrypoints

This keeps the redesign from becoming a broad API break while the runtime model
is still being proven.


Open Questions
--------------

The following questions should be answered before large implementation work
begins:

1. What is the smallest useful ``OrderIntent`` / ``ExecutionUpdate`` model?
2. What must every ``Venue`` implement?
3. How should the broker represent positions or portfolios?
4. What is the minimal decision context agents should receive?
5. How should current metrics consume broker output during the transition?
6. How much of today's ``Strategy`` / ``Trader`` split should survive?

These questions are small enough to be answered directly in code and design
notes, and concrete enough to keep the redesign honest.


Recommended Implementation Order
--------------------------------

1. Introduce broker-side execution objects and a thin ``CurveVenue`` adapter.
2. Refactor the current volume-limited arbitrage path to submit intents through
   the broker instead of trading directly.
3. Add an adapter from broker output to the current metric/result path.
4. Introduce a native ``Simulation`` runtime that owns the event loop.
5. Re-express the current pipeline entrypoints as wrappers over ``Simulation``.
6. Extend the broker for delayed execution and richer venue behaviors only after
   the immediate-execution case is stable.

This ordering keeps each step small enough to review and keeps the current
product path alive while the redesign proceeds.
