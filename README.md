# AsceMarket

A market for reusable protection, combined positions and fully funded payouts.

The current design is defined by:

- [Product vision and experience](AsceMarket.md)
- [Generic v2 cover kernel](v2-kernel-spec.md)

These documents specify the intended product and engine. A finite-state v2 research model now exists; it is not a deployed or audited implementation.

## V2 reference model

- [Implementation and reproduction instructions](model_v2/README.md)
- [Kernel tests, replay results and quantitative findings](model_v2/results.md)
- [Portable exact-value fixtures](model_v2/fixtures.json)

Run the v2 kernel tests and synthetic lifecycle backtests:

```sh
python3 -B -m unittest model_v2.test_kernel -q
python3 -B -m model_v2.research --seeds 200 --steps 100
```

These checks validate accounting behavior on specified cases. They do not backtest market prices or maker profitability.

## Historical research

The earlier `model/` implementation has been removed. The files in `research/` retain historical analysis and evidence; they are not the current product specification.

- [Historical repository review](research/product-review-2026-09-19.md)
- [Plain-language kernel guide](v2-kernel-explained.md)
- [Frontend vision](frontend-vision.md)
- [Interactive markets mockup](mockups/markets.html)
