import html
from pathlib import Path
from typing import cast

import altair as alt
import streamlit as st

from utils.data_loader import load_bible
from utils.scripture_retriever import (
    get_books, get_chapters, get_verse_numbers, get_passage,
    format_reference, search_reference, search_keyword, select_relevant_passage,
)
from utils.safety_checks import is_crisis_message, CRISIS_MESSAGE
from utils.ai_reflection import generate_reflection

APP_NAME = "MARK"
APP_MEANING = "Messenger of Almighty Righteous King"
APP_SUBTITLE = "A digital Bible"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = ["Home", "Bible Library", "Vent"]
NAV_LABELS = {
    "Home": "🏠 Home",
    "Bible Library": "📖 Bible Library",
    "Vent": "💛 Vent Your Heart",
}
NAV_PAGES = {label: page for page, label in NAV_LABELS.items()}
EMOTIONS = ["Hopeful", "Sad", "Worried", "Angry", "Lonely", "Grateful",
            "Confused", "Disappointed", "Anxious", "Overwhelmed", "Afraid",
            "Tired", "Other"]
LANGUAGES = ["🇬🇧 English", "🇵🇭 Bisaya (Cebuano)", "🇵🇭 Tagalog"]
PRIVACY_NOTICE = (
    "Your message is used to generate a temporary Bible-based reflection. "
    "Avoid sharing sensitive personal information. This application is for reflection "
    "and educational purposes and is not a replacement for professional, pastoral, "
    "or emergency support."
)

css_file = Path(__file__).parent / "styles.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)


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


st.sidebar.markdown(
    '<div class="sidebar-brand">'
    '<div class="brand-mark" aria-label="MARK logo">'
    '<span class="brand-initials">MARK</span>'
    '<span class="book-stack" aria-hidden="true">'
    '<span class="book-spine book-spine-back"></span>'
    '<span class="book-spine book-spine-middle"></span>'
    '<span class="book-spine book-spine-front"></span>'
    '</span>'
    '</div>'
    '<div class="brand-copy">'
    f'<div class="brand-meaning">{html.escape(APP_MEANING)}</div>'
    f'<div class="brand-subtag">{html.escape(APP_SUBTITLE)}</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    '<div class="sidebar-intro">'
    '<span class="sidebar-intro-kicker">A moment for you</span>'
    '<span class="sidebar-intro-copy">Read slowly. Speak honestly. Leave with a little more light.</span>'
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
    render_page_title("What is on your heart today?")
    st.write("Explore Scripture, reflect on God's Word, and take a moment to share what you are feeling.")

    with st.container(border=True):
        st.markdown('<div class="home-actions-heading">Choose your next step</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        col1.button("💛 Vent Your Heart", type="primary", width="stretch", on_click=go, args=("Vent",))
        col2.button("📖 Read the Bible", width="stretch", on_click=go, args=("Bible Library",))

    st.subheader("Featured Scripture")
    if not require_bible_data():
        st.info("The featured passage will appear here once bible_verses.csv is added.")
    else:
        book = df["book"].iloc[0]
        chapter = get_chapters(df, book)[0]
        verses = get_verse_numbers(df, book, chapter)
        end = min(verses[0] + 4, verses[-1])
        passage = get_passage(df, book, chapter, verses[0], end)
        render_passage(passage, format_reference(book, chapter, verses[0], end), passage["testament"].iloc[0])
        st.markdown(
            '<div class="home-note">'
            '<strong>📌 Reading preview</strong><br>'
            'Placeholder rule for now: shows the first verses in the file. '
            'A daily pick comes later.'
            '</div>',
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown('<div class="home-stats-heading">📚 Library at a glance</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Verses loaded", f"{len(df):,}")
        c2.metric("Books", df["book"].nunique())
        c3.metric("Testaments", df["testament"].nunique())

    if not is_placeholder:
        with st.container(border=True):
            st.markdown(
                '<div class="insights-heading">📊 Bible Dataset Insights</div>'
                '<div class="insights-caption">Explore how the verified Bible dataset is distributed.</div>',
                unsafe_allow_html=True,
            )

            testament_options = ["All"] + list(df["testament"].drop_duplicates())
            selected_testament = st.selectbox(
                "Filter by testament",
                testament_options,
                key="insights_testament",
            )
            filtered_df = df if selected_testament == "All" else df[
                df["testament"] == selected_testament
            ]

            book_order = list(df["book"].drop_duplicates())
            available_books = [book for book in book_order if book in set(filtered_df["book"])]
            selected_books = st.multiselect(
                "Choose Bible books (optional)",
                available_books,
                default=[],
                key="insights_book_filter",
                help="Leave this empty to show every book in the selected testament.",
            )

            chart_books = selected_books or available_books
            chart_df = filtered_df[filtered_df["book"].isin(chart_books)]
            verses_per_book = (
                chart_df.groupby("book").size()
                .reindex([book for book in book_order if book in chart_books], fill_value=0)
                .rename("Verses")
                .to_frame()
            )
            st.markdown('<div class="chart-heading">Verses per Bible book</div>', unsafe_allow_html=True)
            st.caption(f"Showing {len(chart_books)} of {len(available_books)} available book(s).")
            book_chart_height = max(420, 28 * len(verses_per_book) + 100)
            book_chart_df = verses_per_book.reset_index().rename(
                columns={"book": "Book", "Verses": "Verses"}
            )
            book_chart = alt.Chart(book_chart_df).mark_bar(
                size=16, cornerRadiusEnd=4
            ).encode(
                x=alt.X(
                    "Verses:Q",
                    title="Verses",
                    axis=alt.Axis(format=",.0f", labelFontSize=12, titleFontSize=13),
                ),
                y=alt.Y(
                    "Book:N",
                    title="Bible book",
                    sort=[book for book in book_order if book in chart_books],
                    axis=alt.Axis(
                        labelFontSize=12,
                        titleFontSize=13,
                        labelLimit=150,
                        labelOverlap=False,
                    ),
                    scale=alt.Scale(paddingInner=0.5, paddingOuter=0.25),
                ),
                color=alt.value("#1f77b4"),
                tooltip=[
                    alt.Tooltip("Book:N", title="Book"),
                    alt.Tooltip("Verses:Q", title="Verses", format=",.0f"),
                ],
            ).properties(height=book_chart_height)
            book_labels = book_chart.mark_text(
                align="left",
                baseline="middle",
                dx=7,
                fontSize=12,
                color="#294552",
                clip=False,
            ).encode(text=alt.Text("Verses:Q", format=",.0f"))
            book_chart = (book_chart + book_labels).properties(
                padding={"left": 12, "right": 55, "top": 18, "bottom": 18}
            ).configure_view(stroke=None)
            st.altair_chart(book_chart, width="stretch")

            testament_values = list(df["testament"].dropna().drop_duplicates())
            if testament_values:
                testament_counts = (
                    df.groupby("testament").size()
                    .reindex(testament_values, fill_value=0)
                    .rename("Verses")
                    .to_frame()
                )
                st.markdown(
                    '<div class="chart-heading">📜 Old Testament vs. New Testament</div>',
                    unsafe_allow_html=True,
                )
                testament_chart_df = testament_counts.reset_index().rename(
                    columns={"testament": "Testament", "Verses": "Verses"}
                )
                testament_chart = alt.Chart(testament_chart_df).mark_bar(
                    size=34, cornerRadiusEnd=4
                ).encode(
                    x=alt.X("Verses:Q", title="Verses", axis=alt.Axis(format=",.0f")),
                    y=alt.Y("Testament:N", title="Testament", sort=testament_values),
                    color=alt.value("#1f77b4"),
                    tooltip=[
                        alt.Tooltip("Testament:N", title="Testament"),
                        alt.Tooltip("Verses:Q", title="Verses", format=",.0f"),
                    ],
                ).properties(height=280)
                testament_labels = testament_chart.mark_text(
                    align="left", dx=5, color="#294552"
                ).encode(text=alt.Text("Verses:Q", format=",.0f"))
                st.altair_chart(testament_chart + testament_labels, width="stretch")
            else:
                st.info("Testament information is not available in this dataset.")


# ---------------- Bible Library ----------------
def page_library():
    render_page_title("Bible Library", "📖")
    show_data_warning()
    if not require_bible_data():
        return
    tab_browse, tab_search = st.tabs(["Browse", "Search"])

    with tab_browse:
        testaments = list(df["testament"].drop_duplicates())
        if st.session_state.get("library_testament") not in testaments:
            st.session_state["library_testament"] = testaments[0]
        testament_col, book_col, chapter_col, start_col, end_col = st.columns(
            [1.15, 1.5, .85, 1.1, 1.1]
        )
        testament = cast(str, testament_col.selectbox(
            "📖 Testament", testaments, key="library_testament"
        ))

        books = get_books(df, testament)
        if st.session_state.get("library_book") not in books:
            st.session_state["library_book"] = books[0]
        book = cast(str, book_col.selectbox(
            "📚 Book", books, key="library_book"
        ))

        chapters = get_chapters(df, book)
        if st.session_state.get("library_chapter") not in chapters:
            st.session_state["library_chapter"] = chapters[0]
        chapter = cast(int, chapter_col.selectbox(
            "🔢 Chapter", chapters, key="library_chapter"
        ))

        verses = get_verse_numbers(df, book, chapter)
        if st.session_state.get("library_start") not in verses:
            st.session_state["library_start"] = verses[0]
        start = cast(int, start_col.selectbox(
            "🔽 From Verse", verses, key="library_start"
        ))

        end_options = [v for v in verses if v >= start]
        if st.session_state.get("library_end") not in end_options:
            st.session_state["library_end"] = end_options[-1]
        end = cast(int, end_col.selectbox(
            "🔽 To Verse", end_options, key="library_end"
        ))

        passage = get_passage(df, book, chapter, start, end)
        render_passage(passage, format_reference(book, chapter, start, end), testament)
        st.markdown('<div class="library-nav-label">📚 Continue reading</div>', unsafe_allow_html=True)
        previous_col, next_col = st.columns(2)
        previous_col.button(
            "⬅️ Previous Verse",
            disabled=verses.index(start) == 0,
            use_container_width=True,
            on_click=move_library_verse,
            args=(-1,),
        )
        next_col.button(
            "➡️ Next Verse",
            type="primary",
            use_container_width=True,
            on_click=move_library_verse,
            args=(1,),
        )
        if st.session_state.get("library_notice"):
            st.info(st.session_state["library_notice"])

    with tab_search:
        st.write("Search by reference (for example `John 3:16-18`) or by a keyword.")
        query = st.text_input("Reference or keyword", placeholder="e.g. John 3:16 or peace")
        if query.strip():
            ref = search_reference(df, query)
            if ref:
                book, chapter, start, end = ref
                passage = get_passage(df, book, chapter, start, end)
                if passage.empty:
                    st.warning("That verse range was not found in the dataset.")
                else:
                    render_passage(passage, format_reference(book, chapter, start, end), passage["testament"].iloc[0])
            else:
                hits = search_keyword(df, query)
                if hits.empty:
                    st.warning("No matching reference or keyword found. Try a different search.")
                else:
                    st.success(f"Showing {len(hits)} matching verse(s) (limit 50).")
                    st.dataframe(hits[["reference", "text"]], use_container_width=True, hide_index=True)


# ---------------- Vent ----------------
def page_vent():
    render_page_title("Vent Your Heart out", "🙏")
    show_data_warning()

    with st.container(border=True):
        st.write("A quiet place to share what is on your heart and receive a gentle Scripture-based reflection.")
        emotion_col, language_col, passage_col = st.columns(3)
        emotion = emotion_col.selectbox("😊 How are you feeling?", EMOTIONS)
        language = language_col.selectbox("🌐 Preferred Language", LANGUAGES)
        preference = passage_col.selectbox(
            "📖 Passage length (optional)",
            ["Let the system choose", "Short passage", "Complete passage"],
        )
        message = st.text_area(
            "💭 Your message",
            placeholder="Share what is on your heart...",
            height=150,
        )
        button_left, button_center, button_right = st.columns([1, 1.2, 1])
        guidance_clicked = button_center.button(
            "🙏 I Need His Guidance",
            type="primary",
            use_container_width=True,
        )

    if guidance_clicked:
        if not message.strip():
            st.warning("Please write a few words about what is on your heart first. Take your time.")
        elif is_crisis_message(message):
            st.error(CRISIS_MESSAGE)
        elif is_placeholder:
            st.warning("Add a verified Bible CSV before requesting an AI reflection.")
        else:
            with st.spinner("Preparing your Scripture reflection..."):
                passage, passage_reference = select_relevant_passage(
                    df, emotion, message, preference
                )
                result = generate_reflection(
                    emotion, message, passage, passage_reference, language
                )
            if not result.ok:
                st.warning(result.message)
            else:
                st.session_state["vent"] = {
                    "emotion": emotion,
                    "language": language,
                    "message": message,
                    "preference": preference,
                    "reference": passage_reference,
                }
                st.success("Your reflection is ready.")
                st.markdown(
                    f'<div class="emotion-summary"><strong>Reflection focus:</strong> '
                    f'{html.escape(emotion)} · <span>{html.escape(passage_reference)}</span></div>',
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


{"Home": page_home, "Bible Library": page_library, "Vent": page_vent}[st.session_state["page"]]()
