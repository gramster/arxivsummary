import feedparser
import openai
import json
import requests
import os
import re
import sys
import time
from datetime import datetime
from PyPDF2 import PdfReader


# Note: Feeds are updated daily at midnight Eastern Standard Time.

RSS_FEED_URL = "http://rss.arxiv.org/rss/cs"  # RSS feed for CS papers.

# Users home directory
HOME_DIR = os.path.expanduser("~")
ANALYZED_IDS_FILE = os.path.join(HOME_DIR, ".arxivsummary", "analyzed_papers.json")
PDF_DOWNLOAD_DIR = os.path.join(HOME_DIR, ".arxivsummary", "tmp")
MAX_RETRIES = 5


def ids_file(topics: list[str]) -> str:
    return os.path.join(HOME_DIR, ".arxivsummary", f"analyzed_papers_{'_'.join(sorted(topics))}.json")


def report_file(date_range, topics: list[str]) -> str:
    count = 1
    extra = ''
    while True:
        fname = os.path.join(f"arxiv_summary_{'_'.join(sorted(topics))}_{date_range}{extra}.md")
        if not os.path.exists(fname):
            return fname
        extra = f"-{count}"
        count += 1


# Load previously analyzed paper IDs
def load_analyzed_ids(topics: list[str]) -> set[str]:
    try:
        with open(ids_file(topics), "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


# Save analyzed paper IDs
def save_analyzed_ids(ids, topics: list[str]) -> None:
    with open(ids_file(topics), "w") as f:
        json.dump(list(ids), f)


# Analyze a paper using OpenAI ChatCompletion
def analyze_paper(title, abstract, topics, client, model, verbose) -> bool:
    assert (client is not None)
    retry = 0
    results = []
    while retry < MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a research assistant analyzing papers."},
                    {"role": "user", "content": f"Analyze the following research paper to determine if it is relevant to the topics {topics}. Title: {title} Abstract: {abstract}. Answer only Yes or No."}
                ]
            )
            result = response.choices[0].message.content
            results.append(result)
            if result:
                result = result.strip().lower()
                if result in ["yes", "no", "yes.", "no."]:
                    return result == "yes" or result == "yes."
            retry += 1
        except Exception as e:
            print(f"Error analyzing paper: {e}")
            retry += 1

    if verbose:
        print(f"Failed to analyze paper: {title}: {results}")
    return False


# Download PDF from arXiv
def download_pdf(paper_id, paper_link) -> str | None:
    pdf_url = paper_link.replace("abs", "pdf")
    pdf_file = os.path.join(PDF_DOWNLOAD_DIR, f"{paper_id}.pdf")
    response = requests.get(pdf_url, stream=True)

    if response.status_code == 200:
        with open(pdf_file, "wb") as f:
            f.write(response.content)
        return pdf_file
    return None


# Extract text from PDF
def extract_text_from_pdf(pdf_file) -> str | None:
    try:
        reader = PdfReader(pdf_file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_file}: {e}")
        return None


# Summarize paper text using OpenAI ChatCompletion
def summarize_text(text, client, model) -> str | None:    
    assert (client is not None)
    retry = 0
    while retry < MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a research assistant summarizing papers."},
                    {"role": "user", "content": f"Summarize the following research paper content in the form of detailed study notes:\n\n{text}"}
                ],
            )
            result = response.choices[0].message.content
            return result.strip() if result else None
        except Exception as e:
            print(f"Error summarizing text: {e}")
            retry += 1
    return None


# Generate Markdown summary
def output_report(out, papers, date_range, topics, include_summaries, include_json) -> None:
    fname = report_file(date_range, topics)
    if out == '--':
        f = sys.stdout
    else:
        f = open(out if out else fname, "w")

    f.write(f"# arXiv Paper Summary ({datetime.now().strftime('%Y-%m-%d')})\n\n")
    f.write(f"### Examined Papers Date Range: {date_range}\n\n")
    sep = '\t\n'
    f.write(f"### Topics:\n{sep.join(topics)}\n\n\n")    

    for paper in papers:
        f.write(f"- [{paper['title']}](#{paper['target']})\n")
    f.write("\n\n---\n\n")

    for paper in papers:
        f.write(f"<a name=\"{paper['target']}\">\n")
        if include_summaries:
            f.write(f"## [{paper['title']}](#summary-of-{paper['target']})\n</a>\n")
            f.write(f"**Link:** [{paper['link']}]({paper['link']})\n\n")
        else:
            f.write(f"## [{paper['title']}]({paper['link']})\n</a>\n")
        f.write(f"**Abstract:** {paper['abstract']}\n\n")
        f.write(f"**Analysis:** {paper['analysis']}\n\n")
        f.write("---\n\n")

    if include_summaries:
        for paper in papers:
            f.write(f"<a name=\"summary-of-{paper['target']}\">\n")
            f.write(f"## Summary of {paper['title']}\n</a>\n")
            f.write(f"**Link:** [{paper['link']}]({paper['link']})\n\n")
            f.write(f"**Summary:** {paper['summary']}\n\n")
            f.write("---\n\n")

    if out != '--':
        f.close()

    if include_json and out != '--':
        json_file = out.replace('.md', '.json') if out \
            else fname.replace('.md', '.json')
        with open(json_file, "w") as json_f:
            json.dump(papers, json_f, indent=4)


def parse_model(model: str, local_client: openai.OpenAI, \
                openai_client: openai.OpenAI) -> tuple[openai.OpenAI, str]:
    client, model_name = model.split('/')
    if client.strip() == 'openai':
        return openai_client, model_name.strip()
    else:
        return local_client, model_name.strip()
    

def generate_report(topics: list[str],
                    token: str|None = os.environ.get("OPENAI_TOKEN"),
                    out: str|None = None,
                    verbose: bool = False,
                    show_all: bool = False,
                    max_entries: int = -1,
                    persistent: bool = True,
                    classify_model: str = 'ollama/phi4',
                    summarize_model: str = '',
                    include_json: bool = False,
                    ):
    local_client = openai.OpenAI(base_url='http://localhost:11434/v1/',\
                                 api_key='ollama')
    if not token:
        token = os.environ.get('OPENAI_API_KEY')
    if token:
        openai_client = openai.OpenAI(api_key=token)        
    classify_client, classify_model = parse_model(classify_model, local_client, openai_client)
    if summarize_model:
        summarize_client, summarize_model = parse_model(summarize_model, local_client, openai_client)
    else:
        summarize_client, summarize_model = None, None

    feed = feedparser.parse(RSS_FEED_URL)
    last_analyzed_ids = load_analyzed_ids(topics)
    analyzed_ids = set()
    relevant_papers = []
    examined_dates = []

    if not os.path.exists(PDF_DOWNLOAD_DIR):
        os.makedirs(PDF_DOWNLOAD_DIR)

    count = 0
    i = 0
    if verbose:
        print(f"Analyzing {len(feed.entries)} papers")
    for entry in feed.entries:
        i += 1
        paper_id = entry.id.split('/')[-1]
        published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        examined_dates.append(published_date)
        title = entry.title
        abstract = entry.summary

        if not show_all:
            analyzed_ids.add(paper_id)
            if paper_id in last_analyzed_ids or entry['arxiv_announce_type'].startswith('replace'):
                if verbose:
                    print(f'{i}/{len(feed.entries)}> old: {title}')                
                continue
        
        include = analyze_paper(title, abstract, topics, classify_client, classify_model, verbose)
        if verbose:
            print(f'{i}/{len(feed.entries)}> {"yes" if include else "no "}: {title}')
        if include:
            summary = paper_text = ''
            if summarize_model: 
                include = False
                pdf_file = download_pdf(paper_id, entry.link)
                if pdf_file:
                    paper_text = extract_text_from_pdf(pdf_file)
                    if paper_text:                
                        summary = summarize_text(paper_text, summarize_client, summarize_model)
                        include = True

            if include:
                relevant_papers.append({
                    "title": title,
                    "abstract": abstract,
                    "link": entry.link,
                    "analysis": include,
                    "summary": summary,
                    "target": re.sub(r'[^a-z\-]', '', title.lower().replace(' ', '-'))   
                })
            count += 1
            if max_entries >= 0 and count >= max_entries:
                break

    if persistent and not show_all:
        save_analyzed_ids(analyzed_ids, topics)

    if examined_dates:
        date_range = f"{min(examined_dates)} to {max(examined_dates)}"
    else:
        date_range = "No new papers examined"

    output_report(out, relevant_papers, date_range, topics, bool(summarize_model), include_json)
    # Delete the PDF download directory and its contents
    if os.path.exists(PDF_DOWNLOAD_DIR):
        for file in os.listdir(PDF_DOWNLOAD_DIR):
            os.remove(os.path.join(PDF_DOWNLOAD_DIR, file))
        os.rmdir(PDF_DOWNLOAD_DIR)
