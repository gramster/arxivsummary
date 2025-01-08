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

The following topics are supported, and expand to the terms shown:

    "ML": ["machine learning", "deep learning", "natural language processing"],
    "CV": ["computer vision", "image processing", "object detection"],
    "SE": ["software engineering", "programming languages", "software testing"],
    "DS": ["data science", "big data", "data visualization"],
    "DB": ["database systems", "data management", "data mining"],
    "AI": ["artificial intelligence", "expert systems", "knowledge representation"],
    "HCI": ["human-computer interaction", "user experience", "user interface design"],
    "CC": ["cloud computing", "distributed systems", "networking"],
    "SEC": ["cybersecurity", "information security", "cryptography"],
    "WEB": ["web development", "web design", "web applications"],
    "IOT": ["internet of things", "smart devices", "sensor networks"],
    "DBG": ["debugging", "fault localization", "breakpoints", "stack trace"],
    "TST": ["testing", "test automation", "test case generation", "test coverage"],

You can mix and match these; e.g.:

    python -m arxivsummary report -T WEB,IOT,networking -t ollama -v

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

