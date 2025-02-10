import os
from arxivsummary import generate_report, TOPICS


generate_report(TOPICS["DBG"], summarize_model='ollama/phi-4', classify_model='ollama/phi-4')