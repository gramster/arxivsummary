# arxivsummary - Generate summary reports from arxiv

See CONTRIBUTING.md for build instructions, or install from PyPI with:

```
python -m pip install arxivsummary
```

Use `arxivsummary -h` for help.

For an example report, see https://github.com/gramster/arxivsummary/blob/main/example.md

The example was generated with:

    python -m arxivsummary report -T DBG -t ollama -v

using ollama running locally with the vanilj/Phi-4 model.

## Development

This project uses `flit`. First install `flit`:

```
python -m pip install flit
```

Then to build:

```
flit build
```

To install locally:

```
flit install
```

To publish to PyPI:

```
flit publish
```

## Version History

0.1 Initial release

