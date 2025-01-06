import feedparser
import openai
import json
import requests
import os
import sys
import time
from datetime import datetime
from PyPDF2 import PdfReader


# Note: Feeds are updated daily at midnight Eastern Standard Time.

RSS_FEED_URL = "http://export.arxiv.org/rss/cs"  # RSS feed for CS papers.

# Users home directory
HOME_DIR = os.path.expanduser("~")
ANALYZED_IDS_FILE = os.path.join(HOME_DIR, ".arxivsummary", "analyzed_papers.json")
PDF_DOWNLOAD_DIR = os.path.join(HOME_DIR, ".arxivsummary", "tmp")
MAX_RETRIES = 5


client: openai.OpenAI|None = None


def ids_file(topics: list[str]) -> str:
    return os.path.join(HOME_DIR, ".arxivsummary", f"analyzed_papers_{'_'.join(sorted(topics))}.json")


def report_file(date_range, topics: list[str]) -> str:
    return os.path.join(f"arxiv_summary_{'_'.join(sorted(topics))}_{date_range}.md")


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
def analyze_paper(title, abstract, topics, model, verbose) -> bool:
    assert(client is not None)
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
def summarize_text(text, model) -> str | None:
    assert(client is not None)
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
def generate_summary(out, papers, date_range, topics) -> None:
    if out == '--':
        f = sys.stdout
    else:
        f = open(out if out else report_file(date_range, topics), "w")

    f.write(f"# arXiv Paper Summary ({datetime.now().strftime('%Y-%m-%d')})\n\n")
    f.write(f"### Examined Papers Date Range: {date_range}\n\n")
    sep = '\t\n'
    f.write(f"### Topics:\n{sep.join(topics)}\n\n\n")    

    for paper in papers:
        f.write(f"## {paper['title']}\n")
        f.write(f"**Link:** [{paper['link']}]({paper['link']})\n\n")
        f.write(f"**Abstract:** {paper['abstract']}\n\n")
        f.write(f"**Analysis:** {paper['analysis']}\n\n")
        f.write("---\n\n")

    for paper in papers:
        f.write(f"## {paper['title']}\n")
        f.write(f"**Link:** [{paper['link']}]({paper['link']})\n\n")
        f.write(f"**PDF Summary:** {paper['summary']}\n\n")
        f.write("---\n\n")

    if out != '--':
        f.close()


def generate_report(topics: list[str],
                    token: str|None = os.environ.get("OPENAI_TOKEN"),
                    out: str|None = None, 
                    verbose:bool = False, 
                    show_all: bool = False,
                    max_entries: int = -1, 
                    persistent: bool = True,
                    classify_model: str = 'gpt-3.5-turbo',
                    summarize_model: str = 'gpt-4-turbo'
                    ):
    #openai.api_key = token
    global client
    if token == 'ollama':
        if verbose:
            print('Using local model')
        classify_model = summarize_model = 'vanilj/Phi-4'
        client = openai.OpenAI(base_url='http://localhost:11434/v1/', api_key=token)
    else:
        client = openai.OpenAI(api_key=token)
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
            if paper_id in last_analyzed_ids:
                if verbose:
                    print(f'{i}/{len(feed.entries)}> old: {title}')                
                continue
        
        result = analyze_paper(title, abstract, topics, classify_model, verbose)
        if verbose:
            print(f'{i}/{len(feed.entries)}> {"yes" if result else "no "}: {title}')
        if result:
            pdf_file = download_pdf(paper_id, entry.link)
            if pdf_file:
                paper_text = extract_text_from_pdf(pdf_file)
                if paper_text:
                    if max_entries >= 0 and count >= max_entries:
                        break                    
                    summary = summarize_text(paper_text, summarize_model)
                    relevant_papers.append({
                        "title": title,
                        "abstract": abstract,
                        "link": entry.link,
                        "analysis": result,
                        "summary": summary
                    })
                    count += 1

    if persistent and not show_all:
        save_analyzed_ids(analyzed_ids, topics)

    if examined_dates:
        date_range = f"{min(examined_dates)} to {max(examined_dates)}"
    else:
        date_range = "No new papers examined"

    generate_summary(out, relevant_papers, date_range, topics)
    # Delete the PDF download directory and its contents
    if os.path.exists(PDF_DOWNLOAD_DIR):
        for file in os.listdir(PDF_DOWNLOAD_DIR):
            os.remove(os.path.join(PDF_DOWNLOAD_DIR, file))
        os.rmdir(PDF_DOWNLOAD_DIR)
