# AsceMarket contract documentation

**Current specification for approval: [AsceExecutor local prototype](asce-executor-prototype-spec.md).**

The user's clarified scope uses bounded piecewise-linear payoffs with explicit jumps, an internal clearing ledger, offchain signed quotes and direct collateral settlement. The prototype specifies one event/observation, immutable collateral, a mock oracle and local tests. It has not been implemented or approved for implementation yet.

The specification explains orders, libraries, contract storage, risk checks, rounding and settlement. It supersedes earlier statements here that native CTF was the chosen general implementation or that exchange execution remained undecided.

The [CTF cover architecture](ctf-cover-architecture.md) remains a restricted native-claims comparison. Its earlier handoff prompt is historical and must not override the current prototype specification. Shared CTF complete sets/interpolation bases remain important controls; flexible scalar claims alone do not prove that all CTF infrastructure should be replaced.

Supporting research:

- [Unified payoff and clearing design](../research/unified-payoff-clearing-design-2026-10-01.md)
- [Scalar-AMM library review](../research/scalar-payoff-library-review-2026-10-01.md)
- [Polymarket exchange review](../research/polymarket-exchange-review-2026-10-01.md)
- [CTF marketplace test findings](../research/cover-marketplace-test-findings.md)
- [AsceManager alternative](ascemanager-design.md) — research, not the selected custody system
- [Graph verifier alternative](graph-verifier-design.md) — research, not an MVP dependency

The repository contains design documents and research fixtures. Those fixtures are not production or audited contracts.
