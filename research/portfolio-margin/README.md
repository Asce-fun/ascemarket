# Portfolio margin versus deterministic terminal funding

For Asce, “scenario” means **each contractually allowed terminal state**, not sampled price/volatility shocks. All states are retained until finality. The portfolio is evaluated jointly and exactly; probabilities have no role in the reserve.

Deribit's published portfolio-margin methodology aggregates simulated price/volatility PnL and adds other risk charges. Its described worst scenario is the worst in its test set, not the maximum possible loss. It also explains that long-option portfolios can be liquidated in portfolio-margin mode when the account uses leverage. [Official methodology](https://support.deribit.com/hc/en-us/articles/25944756247837-Portfolio-Margin)

This is a stronger portfolio-aware alternative than separately funding each Asce cap. It is still not the same fully funded all-outcome/no-liquidation product. No authenticated simulator requests were made in this review, and no numerical superiority over Deribit is asserted. The repository's [prepared requests](../deribit-margin-requests.json) and [earlier comparison](../competitive-followup.md) remain explicit evidence boundaries; their old expiry/instruments should not be reused without revalidation.

For a meaningful comparison, record portfolio quantities, actual consideration, fees, cash, signed marked option value, equity, initial/maintenance requirement, withdrawable funds, timestamps and margin mode. Compare capital through identical entry/close/settlement paths. Do not compare a displayed initial margin directly with Asce's `maximum liability − premiums`.

Fully funded deterministic offsets can be used without liquidation. Statistical coverage, asset haircuts, borrowing and leveraged mark-based positions may need replenishment or closeout. The research deliberately chooses the former and does not generalize that guarantee to the latter.
