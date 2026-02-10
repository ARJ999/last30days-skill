"""Terminal UI utilities for last30days skill."""

import sys
import time
import threading
import random
from typing import Optional

# Check if we're in a real terminal (not captured by Claude Code)
IS_TTY = sys.stderr.isatty()


class Colors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ORANGE = '\033[38;5;208m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


BANNER = f"""{Colors.PURPLE}{Colors.BOLD}
  ██╗      █████╗ ███████╗████████╗██████╗  ██████╗ ██████╗  █████╗ ██╗   ██╗███████╗
  ██║     ██╔══██╗██╔════╝╚══██╔══╝╚════██╗██╔═████╗██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝
  ██║     ███████║███████╗   ██║    █████╔╝██║██╔██║██║  ██║███████║ ╚████╔╝ ███████╗
  ██║     ██╔══██║╚════██║   ██║    ╚═══██╗████╔╝██║██║  ██║██╔══██║  ╚██╔╝  ╚════██║
  ███████╗██║  ██║███████║   ██║   ██████╔╝╚██████╔╝██████╔╝██║  ██║   ██║   ███████║
  ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
{Colors.RESET}{Colors.DIM}  30 days of research. 30 seconds of work.{Colors.RESET}
"""

MINI_BANNER = f"""{Colors.PURPLE}{Colors.BOLD}/last30days{Colors.RESET} {Colors.DIM}· researching...{Colors.RESET}"""

# Source-specific status messages
REDDIT_MESSAGES = [
    "Diving into Reddit threads...",
    "Scanning subreddits for gold...",
    "Reading what Redditors are saying...",
    "Exploring the front page of the internet...",
    "Finding the good discussions...",
    "Scrolling through comments...",
]

X_MESSAGES = [
    "Checking what X is buzzing about...",
    "Reading the timeline...",
    "Finding the hot takes...",
    "Scanning tweets and threads...",
    "Discovering trending insights...",
    "Following the conversation...",
]

HN_MESSAGES = [
    "Browsing HackerNews discussions...",
    "Reading developer opinions...",
    "Scanning tech discussions...",
    "Finding the deep dives...",
    "Exploring Show HN posts...",
    "Mining developer insights...",
]

NEWS_MESSAGES = [
    "Scanning news headlines...",
    "Reading the latest articles...",
    "Finding breaking news...",
    "Checking news sources...",
    "Discovering recent coverage...",
]

WEB_MESSAGES = [
    "Searching the web...",
    "Finding relevant pages...",
    "Crawling blogs and docs...",
    "Discovering tutorials...",
    "Exploring web content...",
]

VIDEO_MESSAGES = [
    "Searching for videos...",
    "Finding video content...",
    "Discovering tutorials and talks...",
    "Scanning video platforms...",
]

SUMMARIZER_MESSAGES = [
    "Generating AI summary...",
    "Synthesizing key insights...",
    "Creating topic overview...",
]

ENRICHING_MESSAGES = [
    "Getting the juicy details...",
    "Fetching engagement metrics...",
    "Reading top comments...",
    "Extracting insights...",
    "Analyzing discussions...",
]

PROCESSING_MESSAGES = [
    "Crunching the data...",
    "Scoring and ranking...",
    "Finding patterns...",
    "Removing duplicates...",
    "Organizing findings...",
]

# Promo messages for missing API keys
PROMO_MESSAGE = f"""
{Colors.YELLOW}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}
{Colors.YELLOW}UNLOCK THE FULL POWER OF /last30days{Colors.RESET}

{Colors.DIM}Right now you're using HN only. Add API keys to unlock:{Colors.RESET}

  {Colors.ORANGE}Perplexity (via OpenRouter){Colors.RESET} - Reddit, News, Web, Videos, Discussions, AI Summary
     └─ Add OPENROUTER_API_KEY (get it at openrouter.ai/settings/keys)

  {Colors.CYAN}X (Twitter){Colors.RESET} - Real-time posts, likes, reposts from creators
     └─ Add XAI_API_KEY (uses xAI's live X search)

{Colors.DIM}Setup:{Colors.RESET} Edit {Colors.BOLD}~/.config/last30days/.env{Colors.RESET}
{Colors.YELLOW}{Colors.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}
"""

PROMO_MESSAGE_PLAIN = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNLOCK THE FULL POWER OF /last30days

Right now you're using HN only. Add API keys to unlock:

  Perplexity (via OpenRouter) - Reddit, News, Web, Videos, Discussions, AI Summary
     └─ Add OPENROUTER_API_KEY (get it at openrouter.ai/settings/keys)

  X (Twitter) - Real-time posts, likes, reposts from creators
     └─ Add XAI_API_KEY (uses xAI's live X search)

Setup: Edit ~/.config/last30days/.env
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

PROMO_SINGLE_KEY = {
    "openrouter": f"""
{Colors.DIM}Tip: Add {Colors.ORANGE}OPENROUTER_API_KEY{Colors.RESET}{Colors.DIM} to ~/.config/last30days/.env for Reddit, News, Web, Videos & AI Summary!{Colors.RESET}
""",
    "x": f"""
{Colors.DIM}Tip: Add {Colors.CYAN}XAI_API_KEY{Colors.RESET}{Colors.DIM} to ~/.config/last30days/.env for X/Twitter data with real likes & reposts!{Colors.RESET}
""",
}

PROMO_SINGLE_KEY_PLAIN = {
    "openrouter": "\nTip: Add OPENROUTER_API_KEY to ~/.config/last30days/.env for Reddit, News, Web, Videos & AI Summary!\n",
    "x": "\nTip: Add XAI_API_KEY to ~/.config/last30days/.env for X/Twitter data with real likes & reposts!\n",
}

# Spinner frames
SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']


class Spinner:
    """Animated spinner for long-running operations."""

    def __init__(self, message: str = "Working", color: str = Colors.CYAN):
        self.message = message
        self.color = color
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_idx = 0
        self.shown_static = False

    def _spin(self):
        while self.running:
            frame = SPINNER_FRAMES[self.frame_idx % len(SPINNER_FRAMES)]
            sys.stderr.write(f"\r{self.color}{frame}{Colors.RESET} {self.message}  ")
            sys.stderr.flush()
            self.frame_idx += 1
            time.sleep(0.08)

    def start(self):
        self.running = True
        if IS_TTY:
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            if not self.shown_static:
                sys.stderr.write(f"  {self.message}\n")
                sys.stderr.flush()
                self.shown_static = True

    def update(self, message: str):
        self.message = message
        if not IS_TTY and not self.shown_static:
            sys.stderr.write(f"  {message}\n")
            sys.stderr.flush()

    def stop(self, final_message: str = ""):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)
        if IS_TTY:
            sys.stderr.write("\r" + " " * 80 + "\r")
        if final_message:
            sys.stderr.write(f"  {final_message}\n")
        sys.stderr.flush()


class ProgressDisplay:
    """Progress display for research phases."""

    def __init__(self, topic: str, show_banner: bool = True):
        self.topic = topic
        self.spinner: Optional[Spinner] = None
        self.start_time = time.time()

        if show_banner:
            self._show_banner()

    def _show_banner(self):
        if IS_TTY:
            sys.stderr.write(MINI_BANNER + "\n")
            sys.stderr.write(f"{Colors.DIM}Topic: {Colors.RESET}{Colors.BOLD}{self.topic}{Colors.RESET}\n\n")
        else:
            sys.stderr.write(f"/last30days - researching: {self.topic}\n")
        sys.stderr.flush()

    def _stop_current(self):
        if self.spinner:
            self.spinner.stop()

    # Reddit
    def start_reddit(self):
        self._stop_current()
        msg = random.choice(REDDIT_MESSAGES)
        self.spinner = Spinner(f"{Colors.YELLOW}Reddit{Colors.RESET} {msg}", Colors.YELLOW)
        self.spinner.start()

    def end_reddit(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.YELLOW}Reddit{Colors.RESET} Found {count} threads")

    def start_reddit_enrich(self, current: int, total: int):
        self._stop_current()
        msg = random.choice(ENRICHING_MESSAGES)
        self.spinner = Spinner(f"{Colors.YELLOW}Reddit{Colors.RESET} [{current}/{total}] {msg}", Colors.YELLOW)
        self.spinner.start()

    def update_reddit_enrich(self, current: int, total: int):
        if self.spinner:
            msg = random.choice(ENRICHING_MESSAGES)
            self.spinner.update(f"{Colors.YELLOW}Reddit{Colors.RESET} [{current}/{total}] {msg}")

    def end_reddit_enrich(self):
        if self.spinner:
            self.spinner.stop(f"{Colors.YELLOW}Reddit{Colors.RESET} Enriched with engagement data")

    # X
    def start_x(self):
        self._stop_current()
        msg = random.choice(X_MESSAGES)
        self.spinner = Spinner(f"{Colors.CYAN}X{Colors.RESET} {msg}", Colors.CYAN)
        self.spinner.start()

    def end_x(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.CYAN}X{Colors.RESET} Found {count} posts")

    # HN
    def start_hn(self):
        self._stop_current()
        msg = random.choice(HN_MESSAGES)
        self.spinner = Spinner(f"{Colors.GREEN}HN{Colors.RESET} {msg}", Colors.GREEN)
        self.spinner.start()

    def end_hn(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.GREEN}HN{Colors.RESET} Found {count} stories")

    # News
    def start_news(self):
        self._stop_current()
        msg = random.choice(NEWS_MESSAGES)
        self.spinner = Spinner(f"{Colors.ORANGE}News{Colors.RESET} {msg}", Colors.ORANGE)
        self.spinner.start()

    def end_news(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.ORANGE}News{Colors.RESET} Found {count} articles")

    # Web
    def start_web(self):
        self._stop_current()
        msg = random.choice(WEB_MESSAGES)
        self.spinner = Spinner(f"{Colors.BLUE}Web{Colors.RESET} {msg}", Colors.BLUE)
        self.spinner.start()

    def end_web(self, count: int, discussion_count: int = 0):
        if self.spinner:
            extra = f" + {discussion_count} discussions" if discussion_count else ""
            self.spinner.stop(f"{Colors.BLUE}Web{Colors.RESET} Found {count} results{extra}")

    # Videos
    def start_videos(self):
        self._stop_current()
        msg = random.choice(VIDEO_MESSAGES)
        self.spinner = Spinner(f"{Colors.PURPLE}Video{Colors.RESET} {msg}", Colors.PURPLE)
        self.spinner.start()

    def end_videos(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.PURPLE}Video{Colors.RESET} Found {count} videos")

    # Summarizer
    def start_summarizer(self):
        self._stop_current()
        msg = random.choice(SUMMARIZER_MESSAGES)
        self.spinner = Spinner(f"{Colors.BLUE}Summary{Colors.RESET} {msg}", Colors.BLUE)
        self.spinner.start()

    def end_summarizer(self, has_summary: bool):
        if self.spinner:
            if has_summary:
                self.spinner.stop(f"{Colors.BLUE}Summary{Colors.RESET} AI summary generated")
            else:
                self.spinner.stop(f"{Colors.BLUE}Summary{Colors.RESET} No summary available")

    # Processing
    def start_processing(self):
        self._stop_current()
        msg = random.choice(PROCESSING_MESSAGES)
        self.spinner = Spinner(f"{Colors.PURPLE}Processing{Colors.RESET} {msg}", Colors.PURPLE)
        self.spinner.start()

    def end_processing(self):
        if self.spinner:
            self.spinner.stop()

    def show_complete(
        self,
        reddit_count: int = 0,
        x_count: int = 0,
        hn_count: int = 0,
        news_count: int = 0,
        web_count: int = 0,
        video_count: int = 0,
        discussion_count: int = 0,
    ):
        elapsed = time.time() - self.start_time
        if IS_TTY:
            sys.stderr.write(f"\n{Colors.GREEN}{Colors.BOLD}Research complete{Colors.RESET} ")
            sys.stderr.write(f"{Colors.DIM}({elapsed:.1f}s){Colors.RESET}\n")

            parts = []
            if reddit_count:
                parts.append(f"{Colors.YELLOW}Reddit:{Colors.RESET} {reddit_count}")
            if x_count:
                parts.append(f"{Colors.CYAN}X:{Colors.RESET} {x_count}")
            if hn_count:
                parts.append(f"{Colors.GREEN}HN:{Colors.RESET} {hn_count}")
            if news_count:
                parts.append(f"{Colors.ORANGE}News:{Colors.RESET} {news_count}")
            if web_count:
                parts.append(f"{Colors.BLUE}Web:{Colors.RESET} {web_count}")
            if video_count:
                parts.append(f"{Colors.PURPLE}Video:{Colors.RESET} {video_count}")
            if discussion_count:
                parts.append(f"Discussions: {discussion_count}")

            if parts:
                sys.stderr.write("  " + "  ".join(parts) + "\n")
            sys.stderr.write("\n")
        else:
            parts = []
            if reddit_count:
                parts.append(f"Reddit: {reddit_count}")
            if x_count:
                parts.append(f"X: {x_count}")
            if hn_count:
                parts.append(f"HN: {hn_count}")
            if news_count:
                parts.append(f"News: {news_count}")
            if web_count:
                parts.append(f"Web: {web_count}")
            if video_count:
                parts.append(f"Video: {video_count}")
            if discussion_count:
                parts.append(f"Discussions: {discussion_count}")
            sys.stderr.write(f"Research complete ({elapsed:.1f}s) - {', '.join(parts)}\n")
        sys.stderr.flush()

    def show_cached(self, age_hours: float = None):
        if age_hours is not None:
            age_str = f" ({age_hours:.1f}h old)"
        else:
            age_str = ""
        sys.stderr.write(f"{Colors.DIM}Using cached results{age_str} - use --refresh for fresh data{Colors.RESET}\n\n")
        sys.stderr.flush()

    def show_error(self, message: str):
        sys.stderr.write(f"{Colors.RED}Error:{Colors.RESET} {message}\n")
        sys.stderr.flush()

    def show_promo(self, missing: str = "both"):
        """Show promotional message for missing API keys."""
        if missing == "both":
            if IS_TTY:
                sys.stderr.write(PROMO_MESSAGE)
            else:
                sys.stderr.write(PROMO_MESSAGE_PLAIN)
        elif missing in PROMO_SINGLE_KEY:
            if IS_TTY:
                sys.stderr.write(PROMO_SINGLE_KEY[missing])
            else:
                sys.stderr.write(PROMO_SINGLE_KEY_PLAIN[missing])
        sys.stderr.flush()


def print_phase(phase: str, message: str):
    """Print a phase message."""
    colors = {
        "reddit": Colors.YELLOW,
        "x": Colors.CYAN,
        "hn": Colors.GREEN,
        "news": Colors.ORANGE,
        "web": Colors.BLUE,
        "video": Colors.PURPLE,
        "process": Colors.PURPLE,
        "done": Colors.GREEN,
        "error": Colors.RED,
    }
    color = colors.get(phase, Colors.RESET)
    sys.stderr.write(f"{color}>{Colors.RESET} {message}\n")
    sys.stderr.flush()
