import base64
import hashlib
import html
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import streamlit as st
import pandas as pd

from utils.data_loader import load_bible
from utils.scripture_retriever import (
    get_books, get_chapters, get_verse_numbers, get_passage,
    format_reference, search_reference, select_relevant_passage,
)
from utils.safety_checks import is_crisis_message, CRISIS_MESSAGE
from utils.ai_reflection import generate_reflection, generate_study, STUDY_MODES

APP_NAME = "Alai"
APP_MEANING = "Alai"
APP_SUBTITLE = "AI-powered Digital Bible"
_logo_jpg = Path(__file__).parent / "logo" / "logo.jpg"
APP_LOGO_DATA_URI = (
    "data:image/jpeg;base64," + base64.b64encode(_logo_jpg.read_bytes()).decode("ascii")
)
st.set_page_config(
    page_title=APP_NAME,
    page_icon=str(Path(__file__).parent / "static" / "alai_logo.png"),
    layout="wide",
    initial_sidebar_state="auto",
)

PAGES = ["Home", "Bible Study", "Bible Library", "Vent"]
NAV_LABELS = {
    "Home": "🏠 Home",
    "Bible Study": "📜 Bible Study",
    "Bible Library": "📖 Bible Library",
    "Vent": "💛 Vent Your Heart",
}
NAV_PAGES = {label: page for page, label in NAV_LABELS.items()}
LANGUAGES = ["🇬🇧 English", "🇵🇭 Bisaya (Cebuano)", "🇵🇭 Tagalog"]
PRIVACY_NOTICE = (
    "Your message is used to generate a temporary Bible-based reflection. "
    "Avoid sharing sensitive personal information. This application is for reflection "
    "and educational purposes and is not a replacement for professional, pastoral, "
    "or emergency support."
)

css_file = Path(__file__).parent / "styles.css"
# Study mode centering CSS reload marker.
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

with st.sidebar.container(key="background-music-player"):
    st.audio(
        str(Path(__file__).parent / "bg_music" / "leberch-worship-instrumental-587285.mp3"),
        format="audio/mp3",
        loop=True,
    )

st.html(
    """
    <style>
      .mark-study-scroll-indicator {
        position: fixed;
        right: 1.5rem;
        bottom: 1.25rem;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: .55rem;
        max-width: min(320px, calc(100vw - 2rem));
        padding: .65rem .85rem;
        border-radius: 999px;
        background: rgba(17, 32, 28, 0.82);
        border: 1px solid rgba(214, 180, 99, 0.7);
        box-shadow: 0 14px 28px rgba(0, 0, 0, 0.26);
        color: #f5f0e5;
        font-size: .82rem;
        line-height: 1.35;
        opacity: 1;
        transform: translateY(0);
        transition: opacity .25s ease, transform .25s ease;
        backdrop-filter: blur(10px);
      }
      .mark-study-scroll-indicator[hidden] {
        display: none !important;
      }
      .mark-study-scroll-indicator__icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.5rem;
        height: 1.5rem;
        border-radius: 50%;
        background: rgba(214, 180, 99, 0.18);
        color: #f8d58a;
        font-size: 1rem;
        font-weight: 700;
        animation: markStudyScrollBounce 1.3s ease-in-out infinite;
      }
      .mark-study-scroll-indicator__text {
        color: #f5f0e5;
        font-size: .78rem;
        font-weight: 600;
        letter-spacing: .01em;
      }
      @keyframes markStudyScrollBounce {
        0%, 100% { transform: translateY(0); opacity: 0.8; }
        50% { transform: translateY(6px); opacity: 1; }
      }
      @media (max-width: 700px) {
        .mark-study-scroll-indicator {
          right: .75rem;
          bottom: .9rem;
          max-width: min(260px, calc(100vw - 1.25rem));
          padding: .5rem .7rem;
        }
        .mark-study-scroll-indicator__text {
          font-size: .72rem;
        }
      }
    </style>
    <script>
      (() => {
        if (window.__markStudyHintControllerV2) return;
        window.__markStudyHintControllerV2 = true;

        const PAGE_MARKER_ID = 'mark-study-page-marker';
        const INDICATOR_ID = 'mark-study-scroll-indicator';
        const STATE_KEY = 'markStudyScrollHintStateV2';
        let buttonObserver = null;
        let observedMain = null;

        function getHint() {
          return document.getElementById(INDICATOR_ID);
        }

        function setHintState(isVisible) {
          const hint = getHint();
          if (!hint) return;
          hint.hidden = !isVisible;
        }

        function dismissHint() {
          sessionStorage.setItem(STATE_KEY, 'dismissed');
          setHintState(false);
          if (buttonObserver) buttonObserver.disconnect();
        }

        function hasReachedGenerateButton(main) {
          const buttons = main.querySelectorAll('button');
          const button = Array.from(buttons).find(
            (item) => item.innerText.includes('Generate study')
          );
          if (!button) return false;

          const buttonRect = button.getBoundingClientRect();
          const mainRect = main.getBoundingClientRect();
          return buttonRect.top < mainRect.bottom && buttonRect.bottom > mainRect.top;
        }

        function handleMainScroll() {
          const main = document.querySelector('[data-testid="stMain"]');
          if (main && hasReachedGenerateButton(main)) dismissHint();
        }

        function observeGenerateButton() {
          const marker = document.getElementById(PAGE_MARKER_ID);
          if (!marker || sessionStorage.getItem(STATE_KEY) === 'dismissed') return;

          const main = document.querySelector('[data-testid="stMain"]');
          if (!main) return;
          if (observedMain !== main) {
            if (observedMain) observedMain.removeEventListener('scroll', handleMainScroll);
            observedMain = main;
            observedMain.addEventListener('scroll', handleMainScroll, { passive: true });
          }

          const buttons = main ? main.querySelectorAll('button') : [];
          const generateButton = Array.from(buttons).find(
            (button) => button.innerText.includes('Generate study')
          );
          if (!generateButton) return;

          if (!('IntersectionObserver' in window)) {
            if (hasReachedGenerateButton(main)) dismissHint();
            return;
          }

          if (!buttonObserver) {
            buttonObserver = new IntersectionObserver((entries) => {
              if (entries.some((entry) => entry.intersectionRatio >= 0.15)) dismissHint();
            }, { root: main, threshold: 0.15 });
          }
          buttonObserver.observe(generateButton);
          if (hasReachedGenerateButton(main)) dismissHint();
        }

        function syncStudyPage() {
          const marker = document.getElementById(PAGE_MARKER_ID);
          if (!marker) return;

          if (sessionStorage.getItem(STATE_KEY) === null) {
            sessionStorage.setItem(STATE_KEY, 'ready');
          }

          setHintState(sessionStorage.getItem(STATE_KEY) !== 'dismissed');
          observeGenerateButton();
        }

        function setup() {
          syncStudyPage();
          const observer = new MutationObserver(() => {
            syncStudyPage();
          });
          observer.observe(document.body, { childList: true, subtree: true });
        }

        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', setup, { once: true });
        } else {
          setup();
        }
      })();
    </script>
    """,
    unsafe_allow_javascript=True,
)

if "unsafe_allow_javascript" in inspect.signature(st.html).parameters:
    st.html(
        """<script>
        (() => {
          if (window.__markFormHintCopy) return;
          window.__markFormHintCopy = true;
          const hintsToRemove = [
            "Press Enter to submit form",
            "Press Enter to submit",
            "Press Ctrl+Enter to apply",
          ];

          function updateText(node) {
            if (node.nodeType === Node.TEXT_NODE) {
              let text = node.nodeValue;
              for (const hint of hintsToRemove) {
                text = text.replaceAll(hint, "");
              }
              if (text !== node.nodeValue) node.nodeValue = text;
              return;
            }
            if (node.nodeType !== Node.ELEMENT_NODE) return;
            const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
            let textNode;
            while ((textNode = walker.nextNode())) {
              let text = textNode.nodeValue;
              for (const hint of hintsToRemove) {
                text = text.replaceAll(hint, "");
              }
              if (text !== textNode.nodeValue) textNode.nodeValue = text;
            }
          }

          updateText(document.body);
          new MutationObserver((mutations) => {
            for (const mutation of mutations) {
              if (mutation.type === "characterData") {
                updateText(mutation.target);
              } else {
                mutation.addedNodes.forEach(updateText);
              }
            }
          }).observe(document.body, { childList: true, characterData: true, subtree: true });
        })();
        </script>""",
        unsafe_allow_javascript=True,
    )
    st.html(
        """<script>
        (() => {
          if (window.__markResponsiveSidebarClose) return;
          window.__markResponsiveSidebarClose = true;
          document.addEventListener("click", (event) => {
            const target = event.target;
            const navButton = target && target.closest
              ? target.closest('section[data-testid="stSidebar"] button')
              : null;
            if (!navButton || window.innerWidth > 1024) return;
            window.setTimeout(() => {
              const sidebar = document.querySelector('section[data-testid="stSidebar"]');
              const closeButton = sidebar
                ? sidebar.querySelector('[data-testid="stSidebarCollapseButton"] button')
                : null;
              if (sidebar && sidebar.getAttribute("aria-expanded") === "true" && closeButton) {
                closeButton.click();
              }
            }, 700);
          });
        })();
        </script>""",
        unsafe_allow_javascript=True,
    )
    st.html(
        """<script>
        (() => {
          if (window.__markScrollReveal || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
          window.__markScrollReveal = true;
          const selector = [
            ".verse-of-day",
            ".featured-study",
            ".scripture-card",
            ".result-card",
            ".passage-summary",
            ".jump-help",
            ".home-section-heading",
            ".st-key-home-actions",
            ".st-key-library-jump",
            ".st-key-library-passage-selectors",
            ".st-key-library-continue-reading",
            ".st-key-study-jump",
            ".st-key-study-passage-selectors",
            ".st-key-vent-options"
          ].join(",");
          const pending = new Set();
          let activeScrollTarget = null;
          let scanScheduled = false;

          function observeWithin(node) {
            if (!(node instanceof Element)) return;
            if (node.matches(selector)) {
              node.classList.add("mark-scroll-reveal");
              pending.add(node);
            }
            node.querySelectorAll(selector).forEach((element) => {
              element.classList.add("mark-scroll-reveal");
              pending.add(element);
            });
            scanVisible();
          }

          function scanVisible() {
            if (scanScheduled) return;
            scanScheduled = true;
            window.setTimeout(() => {
              scanScheduled = false;
              const root = document.querySelector('[data-testid="stMain"]');
              const bounds = root ? root.getBoundingClientRect() : { top: 0, bottom: window.innerHeight };
              const revealLine = bounds.bottom - Math.min(54, (bounds.bottom - bounds.top) * 0.06);
              for (const element of pending) {
                if (!element.isConnected) {
                  pending.delete(element);
                  continue;
                }
                const rect = element.getBoundingClientRect();
                if (rect.top <= revealLine && rect.bottom >= bounds.top + 24) {
                  element.classList.add("is-visible");
                  pending.delete(element);
                }
              }
            }, 40);
          }

          function attachScrollListener() {
            const root = document.querySelector('[data-testid="stMain"]');
            const target = root || window;
            if (target === activeScrollTarget) return;
            if (activeScrollTarget) activeScrollTarget.removeEventListener("scroll", scanVisible);
            activeScrollTarget = target;
            activeScrollTarget.addEventListener("scroll", scanVisible, { passive: true });
          }

          observeWithin(document.body);
          attachScrollListener();
          document.addEventListener("scroll", scanVisible, { passive: true, capture: true });
          window.addEventListener("resize", scanVisible, { passive: true });
          new MutationObserver((mutations) => {
            for (const mutation of mutations) {
              mutation.addedNodes.forEach(observeWithin);
            }
            attachScrollListener();
          }).observe(document.body, { childList: true, subtree: true });
        })();
        </script>""",
        unsafe_allow_javascript=True,
    )

@st.cache_data
def get_data():
    return load_bible()


df, status, status_message = get_data()
is_placeholder = status != "ok"

if "page" not in st.session_state:
    st.session_state["page"] = "Home"
if "navigation" not in st.session_state:
    st.session_state["navigation"] = NAV_LABELS[st.session_state["page"]]


def go(page: str):
    st.session_state["page"] = page
    st.session_state["navigation"] = NAV_LABELS[page]
    st.session_state["page_navigation_id"] = st.session_state.get("page_navigation_id", 0) + 1


def _daily_seed(date: str) -> int:
    """Stable integer seed from a date string so every user gets the same daily pick."""
    digest = hashlib.sha256(date.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def verse_of_the_day() -> tuple[pd.Series, str]:
    """Return (verse row, date label). Same verse all day for everyone in UTC."""
    if df.empty:
        return None, ""
    today = datetime.now(timezone.utc).date().isoformat()
    row = df.iloc[_daily_seed(today) % len(df)]
    return row, today


# Curated featured passages, rotated daily. Each maps to a real book/chapter in the dataset.
FEATURED_STUDIES = [
    {"book": "Psalms", "chapter": 23, "start": 1, "end": 6,
     "topic": "Trusting the Shepherd",
     "description": "Reflect on God's tender care and what it means to follow a good Shepherd."},
    {"book": "John", "chapter": 3, "start": 16, "end": 21,
     "topic": "God's love for the world",
     "description": "Consider the depth of God's love and the light that came into the world."},
    {"book": "Philippians", "chapter": 4, "start": 4, "end": 9,
     "topic": "Peace that guards the heart",
     "description": "Learn to trade anxiety for prayer and receive a peace beyond understanding."},
    {"book": "Romans", "chapter": 8, "start": 28, "end": 39,
     "topic": "Nothing can separate us",
     "description": "Rest in the promise that God works all things together for those who love Him."},
    {"book": "Matthew", "chapter": 11, "start": 25, "end": 30,
     "topic": "Rest for the weary",
     "description": "Accept Jesus' invitation to lay down your burdens and find rest for your soul."},
    {"book": "Proverbs", "chapter": 3, "start": 1, "end": 8,
     "topic": "Trust with all your heart",
     "description": "Discover the wisdom of leaning on God rather than your own understanding."},
    {"book": "Isaiah", "chapter": 40, "start": 28, "end": 31,
     "topic": "Strength for the waiting",
     "description": "Find renewed strength when you wait upon the Lord and hope in Him."},
]


def featured_study() -> dict | None:
    """Pick a featured study for today, verified to exist in the dataset."""
    if df.empty:
        return None
    today = datetime.now(timezone.utc).date().isoformat()
    order = list(FEATURED_STUDIES)
    start = _daily_seed(today) % len(order)
    rotated = order[start:] + order[:start]
    for study in rotated:
        verses = get_verse_numbers(df, study["book"], study["chapter"])
        if not verses:
            continue
        start_v = min(study["start"], verses[-1])
        end_v = min(study["end"], verses[-1])
        passage = get_passage(df, study["book"], study["chapter"], start_v, end_v)
        if passage.empty:
            continue
        return {**study, "start": start_v, "end": end_v}
    return None


def explore_in_study(book: str, chapter: int, start: int, end: int):
    """Open the Bible Study page with a specific passage selected."""
    st.session_state["study_book"] = book
    st.session_state["study_chapter"] = chapter
    st.session_state["study_start"] = start
    st.session_state["study_end"] = end
    st.session_state["study_mode"] = "overview"
    st.session_state["study_result"] = None
    st.session_state["study_result_key"] = None
    st.session_state["study_loading_message"] = "Opening selected passage…"
    go("Bible Study")


def open_in_library(book: str, chapter: int, start: int, end: int):
    """Open the Bible Library page with a specific passage selected."""
    st.session_state["library_book"] = book
    st.session_state["library_chapter"] = chapter
    st.session_state["library_start"] = start
    st.session_state["library_end"] = end
    st.session_state["library_notice"] = ""
    st.session_state["library_loading_message"] = "Opening selected passage…"
    go("Bible Library")


def move_library_verse(direction: int):
    """Move the Library passage by one verse without changing pages."""
    book = st.session_state.get("library_book")
    chapter = st.session_state.get("library_chapter")
    current = st.session_state.get("library_start")
    if book is None or chapter is None or current is None:
        return
    verses = get_verse_numbers(df, book, chapter)
    if not verses:
        return
    current_position = verses.index(current)
    target_position = current_position + direction
    if target_position < 0:
        st.session_state["library_notice"] = "You are already at the first verse of this chapter."
        return
    if target_position >= len(verses):
        st.session_state["library_notice"] = "You have reached the end of this chapter."
        return
    target = verses[target_position]
    st.session_state["library_start"] = target
    st.session_state["library_end"] = target
    st.session_state["library_notice"] = ""
    if direction == 1 and st.session_state.get("library_tutorial_state_v3") == "go_to_verse":
        st.session_state["library_tutorial_state_v3"] = "completed"
    st.session_state["library_loading_message"] = "Opening selected verse…"


def move_library_chapter(direction: int):
    """Move the Library to the previous/next chapter of the current book."""
    book = st.session_state.get("library_book")
    chapter = st.session_state.get("library_chapter")
    if book is None or chapter is None:
        return
    chapters = get_chapters(df, book)
    if not chapters:
        return
    current_position = chapters.index(chapter)
    target_position = current_position + direction
    if target_position < 0:
        st.session_state["library_notice"] = "You are already at the first chapter of this book."
        return
    if target_position >= len(chapters):
        st.session_state["library_notice"] = "You have reached the last chapter of this book."
        return
    target_chapter = chapters[target_position]
    verses = get_verse_numbers(df, book, target_chapter)
    if not verses:
        return
    st.session_state["library_chapter"] = target_chapter
    st.session_state["library_start"] = verses[0]
    st.session_state["library_end"] = verses[-1]
    st.session_state["library_notice"] = ""
    st.session_state["library_loading_message"] = "Loading chapter…"


st.sidebar.markdown(
    '<div class="sidebar-brand">'
    '<div class="brand-mark">'
    f'<img class="brand-logo" src="{APP_LOGO_DATA_URI}" alt="Alai logo">'
    '</div>'
    f'<div class="brand-meaning">{html.escape(APP_MEANING)}</div>'
    f'<div class="brand-subtag">{html.escape(APP_SUBTITLE)}</div>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    '<div class="sidebar-intro">'
    '<span class="sidebar-intro-copy">Offer your life to Him</span>'
    '<span class="sidebar-intro-copy">Surrender all to Him</span>'
    '<span class="sidebar-intro-tagline">He has everything, yet He wants you &#129309;</span>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown('<div class="sidebar-nav-heading">Explore</div>', unsafe_allow_html=True)
for page, label in NAV_LABELS.items():
    st.sidebar.button(
        label,
        key=f"sidebar_nav_{page.lower().replace(' ', '_')}",
        type="primary" if st.session_state["page"] == page else "secondary",
        width="stretch",
        on_click=go,
        args=(page,),
    )
def show_data_warning():
    if is_placeholder:
        st.warning(status_message)


def _render_action_loading(
    placeholder,
    message: str,
    detail: str,
    *,
    overlay: bool = False,
) -> None:
    """Render a MARK-themed loading state inside its owning feature area."""
    card = (
        '<div class="mark-action-loading" role="status" aria-live="polite">'
        '<span class="mark-action-loading__spinner" aria-hidden="true"></span>'
        '<div><strong>'
        f'{html.escape(message)}'
        '</strong><div class="mark-action-loading__detail">'
        f'{html.escape(detail)}'
        '</div></div></div>'
    )
    markup = f'<div class="mark-action-overlay">{card}</div>' if overlay else card
    with placeholder.container():
        st.markdown(markup, unsafe_allow_html=True)


def _set_library_loading(message: str) -> None:
    st.session_state["library_loading_message"] = message
    if message.startswith("Applying verse range") and st.session_state.get("library_tutorial_state_v3") == "select_verse":
        st.session_state["library_tutorial_state_v3"] = "go_to_verse"


def _set_study_loading(message: str) -> None:
    st.session_state["study_loading_message"] = message


def _render_library_tutorial_hint(container) -> None:
    container.button(
        "👆",
        key="library_tutorial_go",
        type="secondary",
        on_click=move_library_verse,
        args=(1,),
    )


def render_passage(passage_df, reference: str, testament: str):
    """Shows Scripture exactly as stored in the dataset (HTML-escaped only)."""
    translation = passage_df["translation"].iloc[0]
    verses = "".join(
        f"<sup>{int(r.verse)}</sup>{html.escape(str(r.text))} " for r in passage_df.itertuples()
    )
    st.markdown(
        '<section class="scripture-card">'
        '<div class="card-heading">📖 Original Scripture</div>'
        f'<div class="scripture-ref">{html.escape(reference)}</div>'
        f'<div class="scripture-meta">{html.escape(testament)} · {html.escape(str(translation))}</div>'
        f'<div class="scripture">{verses}</div>'
        '<div class="card-label">Shown directly from the verified Bible dataset.</div>'
        '</section>',
        unsafe_allow_html=True,
    )


def render_result_card(title: str, icon: str, content: str, variant: str, label: str = ""):
    """Render generated content separately from original Scripture."""
    safe_content = html.escape(content).replace("\n", "<br>")
    safe_label = f'<div class="card-label">{html.escape(label)}</div>' if label else ""
    st.markdown(
        f'<section class="result-card {variant}">'
        f'<div class="card-heading">{icon} {html.escape(title)}</div>'
        f'<div class="result-copy">{safe_content}</div>'
        f'{safe_label}</section>',
        unsafe_allow_html=True,
    )


def require_bible_data() -> bool:
    """Stop Scripture views from rendering when no verified CSV is loaded."""
    if is_placeholder:
        st.info("Add a verified public-domain Bible CSV at data/bible_verses.csv to use this section.")
        return False
    return True


def render_page_title(title: str, icon: str = ""):
    """Render a consistent title panel for each main page."""
    safe_icon = html.escape(icon)
    safe_title = html.escape(title)
    icon_markup = f'<div class="page-title-icon">{safe_icon}</div>' if safe_icon else ""
    st.markdown(
        f'<section class="page-title-container">{icon_markup}'
        f'<h1>{safe_title}</h1></section>',
        unsafe_allow_html=True,
    )


# ---------------- Home ----------------
def page_home():
    # Feature 1: Welcome / hero section
    st.markdown(
        '<section class="home-hero">'
        f'<div class="home-hero-kicker">{html.escape(APP_NAME)} · {html.escape(APP_SUBTITLE)}</div>'
        '<h2 class="home-hero-heading">Grow in God&rsquo;s Word</h2>'
        '<p class="home-hero-sub">Take a quiet moment to read, study, and reflect on Scripture '
        'that meets you right where you are today.</p>'
        '</section>',
        unsafe_allow_html=True,
    )
    with st.container(key="home-actions"):
        btn1, btn2, btn3 = st.columns(3)
        btn1.button("📜 Start Bible Study", type="primary", width="stretch", on_click=go, args=("Bible Study",))
        btn2.button("📖 Read the Bible", width="stretch", on_click=go, args=("Bible Library",))
        btn3.button("💛 Vent Your Heart", width="stretch", on_click=go, args=("Vent",))

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)

    # Feature 2: Verse of the Day
    st.markdown('<div class="home-section-heading">🕊️ Verse of the Day</div>', unsafe_allow_html=True)
    if not require_bible_data():
        st.info("A daily verse will appear here once a verified Bible CSV is added.")
    else:
        row, _date = verse_of_the_day()
        if row is None:
            st.info("No verse is available yet. Add a verified Bible CSV to see the daily verse.")
        else:
            translation = str(row["translation"])
            st.markdown(
                '<section class="verse-of-day">'
                f'<div class="verse-of-day-ref">{html.escape(str(row["reference"]))}</div>'
                f'<div class="verse-of-day-text">{html.escape(str(row["text"]))}</div>'
                f'<div class="verse-of-day-meta">{html.escape(translation)}</div>'
                '</section>',
                unsafe_allow_html=True,
            )
            v1, v2 = st.columns([1, 1])
            v1.button(
                "📖 Read full passage",
                width="stretch",
                on_click=open_in_library,
                args=(row["book"], int(row["chapter"]), int(row["verse"]), int(row["verse"])),
            )
            v2.button(
                "🔎 Explore this verse",
                type="primary",
                width="stretch",
                on_click=explore_in_study,
                args=(row["book"], int(row["chapter"]), int(row["verse"]), int(row["verse"])),
            )

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)

    # Feature 3: Featured Bible Study
    st.markdown('<div class="home-section-heading">📜 Featured Bible Study</div>', unsafe_allow_html=True)
    if not require_bible_data():
        st.info("A featured study will appear here once a verified Bible CSV is added.")
    else:
        study = featured_study()
        if study is None:
            st.info("No featured study is available right now. Please try the Bible Study page.")
        else:
            passage = get_passage(df, study["book"], study["chapter"], study["start"], study["end"])
            st.markdown(
                '<section class="featured-study">'
                f'<div class="featured-study-topic">{html.escape(study["topic"])}</div>'
                f'<div class="featured-study-desc">{html.escape(study["description"])}</div>'
                '</section>',
                unsafe_allow_html=True,
            )
            render_passage(
                passage,
                format_reference(study["book"], study["chapter"], study["start"], study["end"]),
                passage["testament"].iloc[0],
            )
            st.button(
                "✨ Study this passage",
                type="primary",
                width="stretch",
                on_click=explore_in_study,
                args=(study["book"], study["chapter"], study["start"], study["end"]),
            )


# ---------------- Bible Library ----------------
def page_library():
    render_page_title("Bible Library", "📖")
    show_data_warning()
    if not require_bible_data():
        return
    if "library_tutorial_state_v3" not in st.session_state:
        st.session_state["library_tutorial_state_v3"] = "select_verse"
    # Single browsing area — no tabs.
    with st.container():
        # Fast path: type a reference and jump straight to it.
        st.markdown(
            '<div class="jump-help">'
            '<div class="jump-help-title">How to search &mdash; try these in order:</div>'
            '<div class="jump-help-step"><span class="jump-help-badge">1</span>'
            '<span>Read a whole chapter &mdash; <code>Psalms 23</code></span></div>'
            '<div class="jump-help-step"><span class="jump-help-badge">2</span>'
            '<span>Go to one verse &mdash; <code>John 3:16</code></span></div>'
            '<div class="jump-help-step"><span class="jump-help-badge">3</span>'
            '<span>Read a range of verses &mdash; <code>Genesis 1:1-5</code></span></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        # Keep the quick-reference search centered without spacer columns on small screens.
        with st.container(key="library-jump"):
            st.markdown('<div class="library-nav-label">⚡ Jump to a reference</div>', unsafe_allow_html=True)
            with st.form("library_jump_form"):
                jump_inner_col, jump_btn = st.columns([3, 1])
                jump_query = jump_inner_col.text_input(
                    "Go to",
                    placeholder="Search Bible content here",
                    key="library_jump",
                    label_visibility="collapsed",
                )
                jump_clicked = jump_btn.form_submit_button(
                    ":material/search: Search",
                    type="primary",
                    width="stretch",
                )
            jump_loading = st.empty()

        if jump_clicked:
            query = jump_query
            _render_action_loading(
                jump_loading,
                "Searching Bible passages…",
                "Finding the requested book, chapter, and verse.",
                overlay=True,
            )
            opening_passage = False
            try:
                reference = search_reference(df, query)
                if reference is None:
                    st.session_state["library_notice"] = (
                        f"Couldn't find '{query.strip()}'. Try a format like 'John 3:16' or 'Genesis 1:1-5'."
                    )
                else:
                    book, chapter, start, end = reference
                    st.session_state["library_testament"] = (
                        df[df["book"] == book]["testament"].iloc[0]
                    )
                    st.session_state["library_book"] = book
                    st.session_state["library_chapter"] = chapter
                    st.session_state["library_start"] = start
                    st.session_state["library_end"] = end
                    st.session_state["library_notice"] = ""
                    st.session_state["library_loading_message"] = "Opening requested passage…"
                    opening_passage = True
                    _render_action_loading(
                        jump_loading,
                        "Opening requested passage…",
                        "Applying the matching Bible reference.",
                        overlay=True,
                    )
            finally:
                if not opening_passage:
                    jump_loading.empty()

        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)

        # Testament filters the Book list; all passage selectors share one desktop row.
        with st.container(key="library-passage-selectors"):
            testament_col, book_col, chapter_col, start_col, end_col = st.columns(
                [1, 1.3, .8, 1, 1]
            )
        testaments = list(df["testament"].drop_duplicates())
        if st.session_state.get("library_testament") not in testaments:
            st.session_state["library_testament"] = testaments[0]
        testament = cast(str, testament_col.selectbox(
            "📖 Testament", testaments, key="library_testament",
            on_change=_set_library_loading, args=("Applying Bible selection…",),
        ))

        books = get_books(df, testament)
        if st.session_state.get("library_book") not in books:
            st.session_state["library_book"] = books[0]
        book = cast(str, book_col.selectbox(
            "📚 Book", books, key="library_book",
            on_change=_set_library_loading, args=("Loading selected book…",),
        ))

        chapters = get_chapters(df, book)
        if st.session_state.get("library_chapter") not in chapters:
            st.session_state["library_chapter"] = chapters[0]
        chapter = cast(int, chapter_col.selectbox(
            "🔢 Chapter", chapters, key="library_chapter",
            on_change=_set_library_loading, args=("Loading chapter…",),
        ))

        verses = get_verse_numbers(df, book, chapter)
        if st.session_state.get("library_start") not in verses:
            st.session_state["library_start"] = verses[0]
        start = cast(int, start_col.selectbox(
            "🔽 From Verse", verses, key="library_start",
            on_change=_set_library_loading, args=("Applying verse range…",),
        ))

        end_options = [v for v in verses if v >= start]
        default_end = 31 if 31 in end_options else end_options[-1]
        old_default_end = end_options[min(4, len(end_options) - 1)]
        current_end = st.session_state.get("library_end")
        if current_end not in end_options or (
            start == verses[0] and current_end == old_default_end
        ):
            st.session_state["library_end"] = default_end
        with end_col.container(key="library_to_verse_guide"):
            end = cast(int, st.selectbox(
                "🔽 To Verse", end_options, key="library_end",
                on_change=_set_library_loading, args=("Applying verse range…",),
            ))

            if st.session_state.get("library_tutorial_state_v3") == "go_to_verse":
                _render_library_tutorial_hint(st)

        action_loading = st.empty()
        loading_message = st.session_state.get("library_loading_message")
        if loading_message:
            _render_action_loading(
                action_loading,
                loading_message,
                "Applying your selection to the Bible passage.",
                overlay=True,
            )
        try:
            passage = get_passage(df, book, chapter, start, end)
            render_passage(passage, format_reference(book, chapter, start, end), testament)
        finally:
            action_loading.empty()
            st.session_state.pop("library_loading_message", None)
            if jump_clicked and st.session_state.get("library_notice") == "":
                jump_loading.empty()

        # Reading flow: prev/next verse AND prev/next chapter
        st.markdown('<div class="library-nav-label">📚 Continue reading</div>', unsafe_allow_html=True)
        with st.container(key="library-continue-reading"):
            c1, c2, c3, c4 = st.columns(4)
            c1.button(
                "⏮️ Prev chapter",
                width="stretch",
                on_click=move_library_chapter,
                args=(-1,),
            )
            c2.button(
                "◀️ Prev verse",
                disabled=verses.index(start) == 0,
                width="stretch",
                on_click=move_library_verse,
                args=(-1,),
            )
            c3.button(
                "▶️ Next verse",
                disabled=verses.index(start) >= len(verses) - 1,
                width="stretch",
                on_click=move_library_verse,
                args=(1,),
            )
            c4.button(
                "⏭️ Next chapter",
                width="stretch",
                on_click=move_library_chapter,
                args=(1,),
            )
        if st.session_state.get("library_notice"):
            st.info(st.session_state["library_notice"])


# ---------------- Vent ----------------
def page_vent():
    render_page_title("Vent Your Heart out", "🙏")
    show_data_warning()

    with st.container(border=True):
        st.write("A quiet place to share what is on your heart and receive a gentle Scripture-based reflection.")
        with st.container(key="vent-options"):
            language_col, passage_col = st.columns(2)
            language = language_col.selectbox("🌐 Preferred Language", LANGUAGES)
            preference = passage_col.selectbox(
                "📖 Passage length (optional)",
                ["Let the system choose", "Short passage", "Complete passage"],
            )
        message = st.text_area(
            "💭 Your message",
            placeholder="Type here... Feeling lost, sad, or disappointed? What seems to be the problem? Are you okay? You can rant here and ask for His guidance.",
            height=150,
            key="vent_message",
        )
        button_left, button_center, button_right = st.columns([1, 1.2, 1])
        guidance_clicked = button_center.button(
            "🙏 I Need His Guidance",
            type="primary",
            width="stretch",
        )
        response_loading = st.empty()

    if guidance_clicked:
        if not message.strip():
            st.warning("Please write a few words about what is on your heart first. Take your time.")
        elif is_crisis_message(message):
            st.error(CRISIS_MESSAGE)
        elif is_placeholder:
            st.warning("Add a verified Bible CSV before requesting an AI reflection.")
        else:
            _render_action_loading(
                response_loading,
                "Preparing your Scripture reflection…",
                "Please wait while Alai finds a passage and prepares your reflection and prayer.",
            )
            try:
                passage, passage_reference = select_relevant_passage(
                    df, message, preference
                )
                result = generate_reflection(
                    message, passage, passage_reference, language
                )
            finally:
                response_loading.empty()
            if not result.ok:
                st.warning(result.message)
            else:
                st.session_state["vent"] = {
                    "language": language,
                    "message": message,
                    "preference": preference,
                    "reference": passage_reference,
                }
                st.success("Your reflection is ready.")
                st.markdown(
                    f'<div class="passage-summary"><strong>Selected passage:</strong> '
                    f'<span>{html.escape(passage_reference)}</span></div>',
                    unsafe_allow_html=True,
                )
                render_passage(passage, passage_reference, passage["testament"].iloc[0])
                result_col, prayer_col = st.columns([1.15, .85])
                with result_col:
                    render_result_card(
                        "Passage explanation", "💡", result.explanation, "explanation"
                    )
                    render_result_card(
                        "AI Bible Reflection", "✨", result.reflection, "reflection",
                        "AI-generated reflection, not original Scripture or a direct message from God.",
                    )
                with prayer_col:
                    render_result_card("Prayer", "🙏", result.prayer, "prayer")


# ---------------- Bible Study ----------------
def _study_state_key() -> tuple:
    """Identify the exact passage + mode the current study result belongs to."""
    return (
        st.session_state.get("study_book"),
        st.session_state.get("study_chapter"),
        st.session_state.get("study_start"),
        st.session_state.get("study_end"),
        st.session_state.get("study_mode"),
    )


def _reset_study_on_change():
    """Clear a cached study when the reader changes the passage, mode, or language."""
    if st.session_state.get("study_result_key") != _study_state_key():
        st.session_state["study_result"] = None
        st.session_state["study_result_key"] = None


def render_study_sections(sections):
    """Render generated study sections separately from original Scripture."""
    for heading, body in sections:
        render_result_card(heading, "", body, "study")


def page_bible_study():
    render_page_title("Bible Study", "📜")
    st.markdown(
        '<div id="mark-study-page-marker" aria-hidden="true" style="display:none"></div>',
        unsafe_allow_html=True,
    )
    show_data_warning()
    if not require_bible_data():
        return

    st.markdown(
        '<div class="jump-help">'
        '<div class="jump-help-title">How to search &mdash; try these in order:</div>'
        '<div class="jump-help-step"><span class="jump-help-badge">1</span>'
        '<span>Read a whole chapter &mdash; <code>Psalms 23</code></span></div>'
        '<div class="jump-help-step"><span class="jump-help-badge">2</span>'
        '<span>Go to one verse &mdash; <code>John 3:16</code></span></div>'
        '<div class="jump-help-step"><span class="jump-help-badge">3</span>'
        '<span>Read a range of verses &mdash; <code>Genesis 1:1-5</code></span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="study-jump"):
        st.markdown(
            '<div class="library-nav-label">⚡ Jump to a reference</div>',
            unsafe_allow_html=True,
        )
        with st.form("study_jump_form"):
            jump_input_col, jump_btn = st.columns([3, 1])
            jump_query = jump_input_col.text_input(
                "Go to",
                placeholder="Search Bible content here",
                key="study_jump",
                label_visibility="collapsed",
            )
            jump_clicked = jump_btn.form_submit_button(
                ":material/search: Search",
                type="primary",
                width="stretch",
            )
        jump_loading = st.empty()

    if jump_clicked:
        _render_action_loading(
            jump_loading,
            "Searching Bible passages…",
            "Finding the requested book, chapter, and verse.",
            overlay=True,
        )
        opening_passage = False
        try:
            selected_reference = search_reference(df, jump_query)
            if selected_reference is None:
                st.session_state["study_notice"] = (
                    f"Couldn't find '{jump_query.strip()}'. Try a format like "
                    "'John 3:16' or 'Genesis 1:1-5'."
                )
            else:
                selected_book, selected_chapter, selected_start, selected_end = (
                    selected_reference
                )
                st.session_state["study_testament"] = (
                    df[df["book"] == selected_book]["testament"].iloc[0]
                )
                st.session_state["study_book"] = selected_book
                st.session_state["study_chapter"] = selected_chapter
                st.session_state["study_start"] = selected_start
                st.session_state["study_end"] = selected_end
                st.session_state["study_notice"] = ""
                st.session_state["study_loading_message"] = "Opening requested passage…"
                opening_passage = True
                _render_action_loading(
                    jump_loading,
                    "Opening requested passage…",
                    "Applying the matching Bible reference.",
                    overlay=True,
                )
        finally:
            if not opening_passage:
                jump_loading.empty()

    if st.session_state.get("study_notice"):
        st.info(st.session_state["study_notice"])

    st.markdown(
        '''
        <div id="mark-study-scroll-indicator" class="mark-study-scroll-indicator" aria-live="polite" hidden>
          <div class="mark-study-scroll-indicator__icon">↓</div>
          <div class="mark-study-scroll-indicator__text">Scroll down to the AI study tools</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # Keep all passage selectors on one desktop row and group them responsively.
    with st.container(key="study-passage-selectors"):
        testament_col, book_col, chapter_col, start_col, end_col = st.columns(
            [1, 1.3, .8, 1, 1]
        )
    testaments = list(df["testament"].drop_duplicates())
    if st.session_state.get("study_testament") not in testaments:
        st.session_state["study_testament"] = testaments[0]
    testament = cast(str, testament_col.selectbox(
        "📖 Testament", testaments, key="study_testament",
        on_change=_set_study_loading, args=("Applying Bible selection…",),
    ))

    books = get_books(df, testament)
    if st.session_state.get("study_book") not in books:
        st.session_state["study_book"] = books[0]
    book = cast(str, book_col.selectbox(
        "📚 Book", books, key="study_book",
        on_change=_set_study_loading, args=("Loading selected book…",),
    ))

    chapters = get_chapters(df, book)
    if st.session_state.get("study_chapter") not in chapters:
        st.session_state["study_chapter"] = chapters[0]
    chapter = cast(int, chapter_col.selectbox(
        "🔢 Chapter", chapters, key="study_chapter",
        on_change=_set_study_loading, args=("Loading chapter…",),
    ))

    verses = get_verse_numbers(df, book, chapter)
    if st.session_state.get("study_start") not in verses:
        st.session_state["study_start"] = verses[0]
    start = cast(int, start_col.selectbox(
        "🔽 From Verse", verses, key="study_start",
        on_change=_set_study_loading, args=("Applying verse range…",),
    ))

    end_options = [v for v in verses if v >= start]
    default_end = 31 if 31 in end_options else end_options[-1]
    old_default_end = end_options[min(4, len(end_options) - 1)]
    current_end = st.session_state.get("study_end")
    if current_end not in end_options or (
        start == verses[0] and current_end == old_default_end
    ):
        st.session_state["study_end"] = default_end
    end = cast(int, end_col.selectbox(
        "🔽 To Verse", end_options, key="study_end",
        on_change=_set_study_loading, args=("Applying verse range…",),
    ))

    # Studies are generated in English (language selector removed).
    language = "🇬🇧 English"

    reference = format_reference(book, chapter, start, end)
    passage = get_passage(df, book, chapter, start, end)

    # Always show the original, dataset-backed Scripture first.
    study_selection_loading = st.empty()
    loading_message = st.session_state.get("study_loading_message")
    if loading_message:
        _render_action_loading(
            study_selection_loading,
            loading_message,
            "Applying your selection to the Bible passage.",
            overlay=True,
        )
    try:
        render_passage(passage, reference, testament)
    finally:
        study_selection_loading.empty()
        st.session_state.pop("study_loading_message", None)
        if jump_clicked:
            jump_loading.empty()

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="home-section-heading study-section-heading">✨ Study this passage</div>', unsafe_allow_html=True)

    mode_labels = [STUDY_MODES[mode]["label"] for mode in STUDY_MODES]
    mode_keys = list(STUDY_MODES.keys())
    if st.session_state.get("study_mode") not in mode_keys:
        st.session_state["study_mode"] = "overview"

    with st.container(key="study-mode-selector"):
        st.markdown('<div class="study-mode-label">Study mode</div>', unsafe_allow_html=True)
        selected_label = st.segmented_control(
            "Study mode",
            mode_labels,
            key="study_mode_control",
            default=STUDY_MODES[st.session_state["study_mode"]]["label"],
            label_visibility="collapsed",
            width="stretch",
        )
    if selected_label in mode_labels:
        st.session_state["study_mode"] = mode_keys[mode_labels.index(selected_label)]

    description = STUDY_MODES[st.session_state["study_mode"]]["description"]
    st.markdown(
        f'<div class="study-mode-description">{html.escape(description)}</div>',
        unsafe_allow_html=True,
    )

    # Invalidate any cached study that no longer matches the current selection.
    _reset_study_on_change()

    left_button, center_button, right_button = st.columns([1, 2.1, 1])
    with center_button:
        generate_clicked = st.button(
            "✨ Generate study",
            type="primary",
            width="stretch",
        )
    study_response_loading = st.empty()

    if generate_clicked:
        _render_action_loading(
            study_response_loading,
            "Preparing your Bible study…",
            "Please wait while Alai studies the selected passage.",
        )
        try:
            result = generate_study(passage, reference, st.session_state["study_mode"], language)
        finally:
            study_response_loading.empty()
        st.session_state["study_result"] = result
        st.session_state["study_result_key"] = _study_state_key()

    result = st.session_state.get("study_result")
    if result is not None and st.session_state.get("study_result_key") == _study_state_key():
        if not result.ok:
            st.warning(result.message)
        else:
            st.markdown(
                '<div class="card-label">AI-generated study, not original Scripture or a direct '
                'message from God.</div>',
                unsafe_allow_html=True,
            )
            render_study_sections(result.sections)


page = st.session_state["page"]
page_key = page.lower().replace(" ", "-")
with st.container(key=f"menu-content-{page_key}"):
    {"Home": page_home, "Bible Study": page_bible_study, "Bible Library": page_library, "Vent": page_vent}[page]()

st.html(
    f"""<script>
    (() => {{
      const navigationId = {json.dumps(st.session_state.get("page_navigation_id", 0))};
      if (window.__alaiLastNavigationId === navigationId) return;
      window.__alaiLastNavigationId = navigationId;
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        const main = document.querySelector('[data-testid="stMain"]');
        if (main) main.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
        window.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      }}));
    }})();
    </script>""",
    unsafe_allow_javascript=True,
)

st.markdown(
    '<footer class="app-footer">'
    '<div class="app-footer-credit">Developed by kay-madelo</div>'
    '<div class="app-footer-title">Alai</div>'
    '</footer>',
    unsafe_allow_html=True,
)

st.html(
    f"""<style>
      #alai-install-button {{
        background: #c5a15b; border: 1px solid #e3c77f; border-radius: 10px;
        color: #14251d; cursor: pointer; display: block;
        font: 700 .95rem 'DM Sans', sans-serif; min-height: 44px;
        padding: .65rem 1rem; position: fixed;
        right: max(18px, env(safe-area-inset-right)); top: 50%; width: auto;
        z-index: 2147482000; box-shadow: 0 8px 22px rgba(0, 0, 0, .35);
        transform: translateY(-50%);
        transition: transform .18s ease, background .18s ease, box-shadow .18s ease;
      }}
      #alai-install-button:hover {{
        background: #dfbd70; box-shadow: 0 10px 26px rgba(0, 0, 0, .42);
        transform: translateY(calc(-50% - 2px));
      }}
      #alai-install-button:focus-visible {{ outline: 3px solid #f7d58f; outline-offset: 3px; }}
      #alai-install-overlay {{
        align-items: center; background: rgba(7, 15, 11, .72); display: flex;
        inset: 0; justify-content: center; opacity: 0;
        padding: max(18px, env(safe-area-inset-top)) 18px max(18px, env(safe-area-inset-bottom));
        position: fixed; transition: opacity .24s ease; z-index: 2147482001;
      }}
      #alai-install-overlay[hidden] {{ display: none; }}
      #alai-install-overlay.is-visible {{ opacity: 1; }}
      #alai-install-card {{
        background: #1a3024; border: 1px solid #c5a15b; border-radius: 20px;
        box-shadow: 0 18px 50px rgba(0, 0, 0, .48); box-sizing: border-box;
        color: #f5f0e5; max-width: 25rem; padding: 1.5rem; text-align: center;
        transform: scale(.96) translateY(8px); transition: transform .24s ease; width: 100%;
      }}
      #alai-install-overlay.is-visible #alai-install-card {{ transform: scale(1) translateY(0); }}
      #alai-install-logo {{
        border: 1px solid rgba(226, 190, 111, .8); border-radius: 50%;
        display: block; height: 76px; margin: 0 auto .7rem; object-fit: cover; width: 76px;
      }}
      #alai-install-title {{ color: #f7d58f; font-size: 1.55rem; margin: 0 0 .35rem; }}
      #alai-install-description {{ line-height: 1.55; margin: 0 0 .75rem; }}
      #alai-install-status {{ color: #d6c8a8; font-size: .92rem; line-height: 1.45; min-height: 2.7em; }}
      #alai-install-actions {{ display: flex; gap: .7rem; justify-content: center; margin-top: 1.1rem; }}
      #alai-install-actions button {{
        border-radius: 10px; cursor: pointer; font: 700 .95rem 'DM Sans', sans-serif;
        min-height: 44px; padding: .65rem 1rem;
      }}
      #alai-install-confirm {{ background: #c5a15b; border: 1px solid #e3c77f; color: #14251d; }}
      #alai-install-cancel {{ background: transparent; border: 1px solid #58705f; color: #f5f0e5; }}
      #alai-install-actions button:focus-visible {{ outline: 3px solid #f7d58f; outline-offset: 3px; }}
      @media (max-width: 480px) {{
        #alai-install-card {{ border-radius: 17px; padding: 1.25rem 1rem; }}
        #alai-install-actions {{ flex-direction: column; }}
        #alai-install-actions button {{ width: 100%; }}
      }}
      @media (prefers-reduced-motion: reduce) {{ #alai-install-overlay, #alai-install-card {{ transition: none; }} }}
    </style>
    <div id="alai-install-overlay" hidden>
      <section id="alai-install-card" role="dialog" aria-modal="true" aria-labelledby="alai-install-title">
        <img id="alai-install-logo" src="/app/static/alai_icon_192.png" alt="Alai logo">
        <h2 id="alai-install-title">Install Alai</h2>
        <p id="alai-install-description">AI-powered Digital Bible</p>
        <p id="alai-install-status" aria-live="polite">Add Alai to your home screen for quick access to Scripture and reflection.</p>
        <div id="alai-install-actions">
          <button id="alai-install-confirm" type="button">Add to Home Screen</button>
          <button id="alai-install-cancel" type="button">Cancel</button>
        </div>
      </section>
    </div>
    <script>
      (() => {{
        if (window.__alaiPwaUiInitialized) return;
        window.__alaiPwaUiInitialized = true;

        const manifestLink = document.createElement("link");
        manifestLink.rel = "manifest";
        manifestLink.type = "application/manifest+json";
        manifestLink.href = window.location.origin + "/manifest.webmanifest";
        document.head.appendChild(manifestLink);

        if ("serviceWorker" in navigator && window.isSecureContext) {{
          navigator.serviceWorker.register("/sw.js", {{ scope: "/" }}).catch((error) => {{
            console.warn("Alai install support could not register its service worker.", error);
          }});
        }}

        const appleIcon = document.createElement("link");
        appleIcon.rel = "apple-touch-icon";
        appleIcon.href = window.location.origin + "/app/static/alai_icon_512.png";
        appleIcon.sizes = "512x512";
        document.head.appendChild(appleIcon);
        const appleCapable = document.createElement("meta");
        appleCapable.name = "apple-mobile-web-app-capable";
        appleCapable.content = "yes";
        document.head.appendChild(appleCapable);

        const overlay = document.getElementById("alai-install-overlay");
        const status = document.getElementById("alai-install-status");
        const confirmButton = document.getElementById("alai-install-confirm");
        const cancelButton = document.getElementById("alai-install-cancel");
        if (!overlay || !status || !confirmButton || !cancelButton) return;

        const installButton = document.createElement("button");
        installButton.id = "alai-install-button";
        installButton.type = "button";
        installButton.textContent = "Install Alai";
        installButton.setAttribute("aria-label", "Install Alai on this device");
        document.body.appendChild(installButton);

        const isStandalone = window.matchMedia("(display-mode: standalone)").matches
          || window.navigator.standalone === true;
        const userAgent = window.navigator.userAgent || "";
        const isIOS = /iPhone|iPad|iPod/i.test(userAgent)
          || (/Macintosh/i.test(userAgent) && navigator.maxTouchPoints > 1);
        const isFacebook = /FBAN|FBAV|FB_IAB|Messenger/i.test(userAgent);
        const dismissalKey = "alai-install-dismissed-this-session";
        let installPrompt = null;
        let closeTimer = null;
        if (isStandalone) installButton.hidden = true;

        const sessionDismissed = () => {{
          try {{ return window.sessionStorage.getItem(dismissalKey) === "1"; }} catch (_) {{ return false; }}
        }};
        const rememberDismissal = () => {{
          try {{ window.sessionStorage.setItem(dismissalKey, "1"); }} catch (_) {{}}
        }};
        const browserInstructions = () => {{
          if (isIOS) return "On iPhone or iPad, open Alai in Safari, tap Share, then choose Add to Home Screen.";
          if (isFacebook) return "Open Alai in Chrome or your device browser first. Facebook's in-app browser cannot install it.";
          if (/Android/i.test(userAgent)) return "This browser has not offered its install prompt. In Chrome, use Install app or Add to Home screen from the browser menu.";
          return "This browser has not offered an install prompt. Use its Install app option if available, or keep using Alai here.";
        }};
        const showPopup = (ignoreSessionDismissal = false) => {{
          if (isStandalone || (!ignoreSessionDismissal && sessionDismissed())) return;
          if (closeTimer) window.clearTimeout(closeTimer);
          overlay.hidden = false;
          requestAnimationFrame(() => overlay.classList.add("is-visible"));
          if (isIOS || isFacebook || !installPrompt) status.textContent = browserInstructions();
          else status.textContent = "Alai is ready to install. Your browser will ask you to confirm.";
        }};
        const hidePopup = (remember = true) => {{
          if (remember) rememberDismissal();
          overlay.classList.remove("is-visible");
          closeTimer = window.setTimeout(() => {{ overlay.hidden = true; }}, 250);
        }};

        installButton.addEventListener("click", () => showPopup(true));
        cancelButton.addEventListener("click", () => hidePopup(true));
        overlay.addEventListener("click", (event) => {{ if (event.target === overlay) hidePopup(true); }});
        document.addEventListener("keydown", (event) => {{
          if (event.key === "Escape" && !overlay.hidden) hidePopup(true);
        }});

        window.addEventListener("beforeinstallprompt", (event) => {{
          event.preventDefault();
          if (isIOS || isFacebook) {{
            installPrompt = null;
            if (!overlay.hidden) status.textContent = browserInstructions();
            return;
          }}
          installPrompt = event;
          if (!overlay.hidden) status.textContent = "Alai is ready to install. Your browser will ask you to confirm.";
        }});
        window.addEventListener("appinstalled", () => {{
          installPrompt = null;
          installButton.hidden = true;
          status.textContent = "Alai is installed. You can open it from your home screen.";
          confirmButton.hidden = true;
          cancelButton.textContent = "Done";
          if (overlay.hidden) showPopup(true);
          window.setTimeout(() => hidePopup(true), 2200);
        }});

        confirmButton.addEventListener("click", async () => {{
          if (!installPrompt) {{ status.textContent = browserInstructions(); return; }}
          const promptEvent = installPrompt;
          installPrompt = null;
          try {{
            await promptEvent.prompt();
            const choice = await promptEvent.userChoice;
            if (choice && choice.outcome === "accepted") {{
              status.textContent = "Alai is being added. Your browser will confirm when it is ready.";
              confirmButton.disabled = true;
            }} else {{
              status.textContent = "No problem. Alai is still available in your browser.";
              hidePopup(true);
            }}
          }} catch (error) {{ status.textContent = browserInstructions(); }}
        }});

        const showAfterLoad = () => window.setTimeout(() => {{
          if (!isStandalone && !sessionDismissed()) showPopup();
        }}, 1100);
        if (document.readyState === "complete") showAfterLoad();
        else window.addEventListener("load", showAfterLoad, {{ once: true }});
      }})();
    </script>""",
    unsafe_allow_javascript=True,
)

st.html(
    """<script>
      (() => {
        const player = document.querySelector(".st-key-background-music-player audio");
        if (!player) return;

        let audio = window.__markBackgroundMusic;
        const playerSource = player.currentSrc || player.src;
        if (!audio) {
          audio = player;
          window.__markBackgroundMusic = audio;
        } else if (playerSource && audio.src !== playerSource) {
          audio.pause();
          audio.src = playerSource;
          audio.load();
        }
        audio.loop = true;
        audio.preload = "auto";
        audio.volume = 0.65;

        const startMusic = () => {
          audio.play().catch(() => {});
        };
        if (!window.__markMusicGestureRegistered) {
          document.addEventListener("pointerdown", startMusic, { once: true, capture: true });
          window.__markMusicGestureRegistered = true;
        }
        startMusic();
      })();
    </script>""",
    unsafe_allow_javascript=True,
)

st.html(
    r"""
    <style>
      #alai-browser-prompt {
        align-items: center;
        background: rgba(20, 37, 29, .97);
        border: 1px solid #c5a15b;
        border-radius: 14px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, .42);
        color: #f5f0e5;
        display: flex;
        flex-wrap: wrap;
        gap: .75rem 1rem;
        justify-content: space-between;
        left: 50%;
        max-width: min(40rem, calc(100vw - 1.5rem));
        padding: .85rem 1rem;
        position: fixed;
        top: max(.75rem, env(safe-area-inset-top));
        transform: translateX(-50%);
        width: max-content;
        z-index: 2147483000;
      }
      #alai-browser-prompt[hidden] { display: none; }
      #alai-browser-prompt .alai-browser-copy { flex: 1 1 14rem; }
      #alai-browser-prompt strong { color: #f7d58f; }
      #alai-browser-prompt small { color: #d2cbb8; display: block; margin-top: .2rem; }
      #alai-browser-prompt .alai-browser-actions { align-items: center; display: flex; gap: .55rem; }
      #alai-browser-prompt a,
      #alai-browser-prompt button {
        border: 1px solid #c5a15b;
        border-radius: 9px;
        cursor: pointer;
        font: inherit;
        min-height: 40px;
        padding: .45rem .75rem;
        text-decoration: none;
      }
      #alai-browser-prompt a { background: #c5a15b; color: #14251d; font-weight: 700; }
      #alai-browser-prompt button { background: transparent; color: #f5f0e5; }
      @media (max-width: 540px) {
        #alai-browser-prompt { align-items: stretch; }
        #alai-browser-prompt .alai-browser-actions { justify-content: flex-end; }
      }
    </style>
    <aside id="alai-browser-prompt" role="dialog" aria-label="Open Alai in your browser" hidden>
      <div class="alai-browser-copy">
        <strong>Open Alai in your browser?</strong>
        <small id="alai-browser-hint">Continue in your device’s browser for the best experience.</small>
      </div>
      <div class="alai-browser-actions">
        <a id="alai-open-browser" href="#">Open in browser</a>
        <button id="alai-stay-here" type="button">Stay here</button>
      </div>
    </aside>
    <script>
      (() => {
        const userAgent = navigator.userAgent || "";
        const isFacebookBrowser = /FBAN|FBAV|FB_IAB|Messenger/i.test(userAgent);
        if (!isFacebookBrowser) return;
        try {
          if (window.sessionStorage.getItem("alai-external-browser-dismissed") === "1") return;
        } catch (_) {}

        const prompt = document.getElementById("alai-browser-prompt");
        const openLink = document.getElementById("alai-open-browser");
        const stayButton = document.getElementById("alai-stay-here");
        const hint = document.getElementById("alai-browser-hint");
        if (!prompt || !openLink || !stayButton) return;

        const pageUrl = window.location.href;
        if (/Android/i.test(userAgent)) {
          const browserUrl = new URL(pageUrl);
          openLink.href = `intent://${browserUrl.host}${browserUrl.pathname}${browserUrl.search}${browserUrl.hash}`
            + `#Intent;scheme=${browserUrl.protocol.slice(0, -1)};action=android.intent.action.VIEW;`
            + "category=android.intent.category.BROWSABLE;end";
        } else {
          openLink.href = pageUrl;
          openLink.target = "_blank";
          openLink.rel = "noopener noreferrer";
          if (/iPhone|iPad|iPod/i.test(userAgent) && hint) {
            hint.textContent = "If it stays in Facebook, tap ••• and choose Open in browser.";
          }
        }

        stayButton.addEventListener("click", () => {
          try { window.sessionStorage.setItem("alai-external-browser-dismissed", "1"); } catch (_) {}
          prompt.remove();
        });
        prompt.hidden = false;
      })();
    </script>
    """,
    unsafe_allow_javascript=True,
)
