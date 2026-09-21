# ascemarket

Research prototype for trading bounded payouts with fully funded, portfolio-level accounting.

- [Product specification](ps.md)
- [Core design](core-design.md)
- [Quote workflow](quote-workflow.md)
- [Model and reproduction instructions](model/README.md)
- [Latest repository review](research/product-review-2026-09-19.md)

Run the accounting tests:

```sh
python3 -B -m unittest model.test_model -q
```

Run the local demonstration:

```sh
python3 -B -m model.server
```

Open http://127.0.0.1:8111. This is a research demonstration, not a production exchange. It has no real funds, wallet authentication or persistent trading accounts. See the repository review for known limitations.
