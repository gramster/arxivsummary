import os
from arxivsummary import generate_report


generate_report(["Python"], token=None, out="--", verbose=False, show_all=True, max_entries=1, persistent=True)