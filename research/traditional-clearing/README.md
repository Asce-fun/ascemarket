# Traditional clearing: useful methods, different guarantee

Reviewed 30 September 2026. This is a methodology comparison, not legal advice, a clearing-member rule analysis or measured venue margin.

| System | Risk calculation described by its primary source | Difference from Asce's first model |
|---|---|---|
| CME SPAN | Aggregates contract risk arrays across price/volatility scenarios, with spread treatment, delivery charges and short-option minimums | A finite stress array is not every possible terminal payoff; spread recognition is prior art |
| CME SPAN 2 | Historical/stress risk with liquidity and concentration components | Designed around market-move/default-closeout exposure, not a locked exhaustive terminal domain |
| OCC customer portfolio margin / TIMS | Applies portfolio methodology to OCC-provided profit/loss inputs and customer positions | Portfolio aggregation already exists; scenario support is different |
| OCC clearing-member STANS | Full portfolio Monte Carlo, two-day horizon, expected shortfall and stress adjustments; daily margin and possible intraday calls | Statistical coverage and margin replenishment are not a no-top-up settlement proof |

Primary sources: [CME SPAN methodology](https://www.cmegroup.com/clearing/files/span-methodology.pdf), [CME SPAN 2 methodology](https://www.cmegroup.com/clearing/risk-management/span-overview/span-2-methodology.html), [OCC CPM/TIMS](https://www.theocc.com/risk-management/customer-portfolio-margin), [OCC STANS](https://www.theocc.com/risk-management/margin-methodology).

These systems have different jobs from a prepaid event vault. Default closeout, changing option marks, collateral risk, liquidity and intraday obligations can matter before terminal settlement. They can hold less than absolute terminal loss because they use a risk horizon, confidence coverage and operational/default arrangements; their margin number is not a direct substitute for Asce's worst contractual liability.

Deterministic replication is nevertheless old: an option spread or complementary contingent claims can cap aggregate liability by contract, independent of empirical correlation. Asce does not invent recognizing a bounded spread. Its first model restricts the state domain and asset semantics to make the complete maximum easy to compute and permanently fund.

Useful ideas to retain: account segregation, immutable contract specifications, atomic matched novation, clear cash and fee history, incremental exposure records, intraday admissibility checks, reconciliation, independent risk controls and operational finality. Avoid importing cross-commodity credits, volatility scan ranges, probabilistic confidence levels or a liquidation/default waterfall when exact terminal funding makes them unnecessary for this scope.

Do not claim Asce “outperforms CME/OCC margin” numerically without matching settlement guarantees, collateral, obligations and trading paths. A lower statistical margin can be a different risk service; a higher cash guarantee can be the price of eliminating forced closeout.
