"""arxivsummary - Arxiv summary report generator. """

__version__ = '0.8'

import os
import click
from .arxivsummary import generate_report


TOPICS = {
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
}


@click.group()
@click.version_option(version=__version__)
def cli():
    """arxivsummary."""
    pass


@cli.command()
@click.option('-o', '--out', type=click.Path(), help='Write output to specified file. Use "--" for stdout.')
@click.option('-v', '--verbose', is_flag=True, help='Show extra diagnostic output.')
@click.option('-a', '--all', is_flag=True, help='Show all relevant papers in RSS feed, not just those new since the last run.')
@click.option('-j', '--json', is_flag=True, help='Include a JSON version of the resulting data.')
@click.option('-t', '--token', help='OpenAI token, if not from OPENAI_API_KEY.', default='')
@click.option('-c', '--classify', help='Model to use for classification.', default='ollama/phi4')
@click.option('-s', '--summarize', help='Model to use for summarization, if any (e.g. openai/gpt-4o-mini).', default='')
@click.option('-T', '--topic', help='Comma-separated topic(s). Some (AI,ML,CV,DS,DB,HCI,CC,IOT,TST,DBG,WEB), will expand into multiple.', default='AI')
def report(out, verbose, all, json, token, classify, summarize, topic):
    topics = []
    for t in topic.split(','):
        topics.extend(TOPICS[t] if t in TOPICS else [t])
    generate_report(topics, token=token,out=out, verbose=verbose, show_all=all, \
                    classify_model=classify, summarize_model=summarize, include_json=json)


def main():
    cli()


