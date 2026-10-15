"""Retrieval helpers. Everything returned comes from the dataframe."""
import re
import pandas as pd

REF_PATTERN = re.compile(r"^\s*(.+?)\s+(\d+)(?::(\d+)(?:\s*[-\u2013]\s*(\d+))?)?\s*$")


def get_books(df: pd.DataFrame, testament: str) -> list:
    return list(df[df["testament"] == testament]["book"].drop_duplicates())


def get_chapters(df: pd.DataFrame, book: str) -> list:
    return sorted(df[df["book"] == book]["chapter"].unique().tolist())


def get_verse_numbers(df: pd.DataFrame, book: str, chapter: int) -> list:
    return sorted(df[(df["book"] == book) & (df["chapter"] == chapter)]["verse"].tolist())


def get_passage(df: pd.DataFrame, book: str, chapter: int, start: int, end: int) -> pd.DataFrame:
    mask = (df["book"] == book) & (df["chapter"] == chapter) & df["verse"].between(start, end)
    return df[mask].sort_values("verse")


def is_complete_passage(passage_df: pd.DataFrame, start: int, end: int) -> bool:
    """Return whether every verse in the requested range is present."""
    expected = set(range(start, end + 1))
    return set(passage_df["verse"].tolist()) == expected


def select_relevant_passage(
    df: pd.DataFrame,
    message: str,
    preference: str,
) -> tuple[pd.DataFrame, str]:
    """Select a contiguous passage from verified rows using local text matching."""
    if df.empty:
        return df.iloc[0:0].copy(), ""

    length = {
        "Short passage": 2,
        "Complete passage": 6,
        "Let the system choose": 4,
    }.get(preference, 4)
    terms = re.findall(r"[a-z]{4,}", message.lower())
    terms = list(dict.fromkeys(terms))
    searchable = df["text"].astype(str).str.lower()
    scores = pd.Series(0, index=df.index, dtype="int64")
    for term in terms:
        scores = scores.add(
            searchable.str.contains(re.escape(term), regex=True, na=False).astype("int64")
        )
    if scores.max() == 0:
        candidate_position = 0
    else:
        candidate_position = int(scores.to_numpy().argmax())

    candidate = df.iloc[candidate_position]
    chapter_rows = df[
        (df["book"] == candidate["book"]) & (df["chapter"] == candidate["chapter"])
    ].sort_values("verse")
    verses = chapter_rows["verse"].tolist()
    hit_position = verses.index(candidate["verse"])
    start_position = min(hit_position, max(0, len(verses) - length))
    selected_verses = verses[start_position:start_position + length]
    while selected_verses and not is_complete_passage(
        chapter_rows[chapter_rows["verse"].isin(selected_verses)],
        selected_verses[0],
        selected_verses[-1],
    ):
        selected_verses = selected_verses[:-1]
    if not selected_verses:
        return df.iloc[0:0].copy(), ""
    start, end = selected_verses[0], selected_verses[-1]
    passage = get_passage(df, candidate["book"], int(candidate["chapter"]), start, end)
    return passage, format_reference(candidate["book"], int(candidate["chapter"]), start, end)


def format_reference(book: str, chapter: int, start: int, end: int) -> str:
    if start == end:
        return f"{book} {chapter}:{start}"
    return f"{book} {chapter}:{start}\u2013{end}"


def search_reference(df: pd.DataFrame, query: str):
    """Understands 'John 3', 'John 3:16', 'John 3:16-18'. Returns (book, chapter, start, end) or None."""
    match = REF_PATTERN.match(query)
    if not match:
        return None
    name, chapter, start, end = match.groups()
    books = {b.lower(): b for b in df["book"].unique()}
    book = books.get(name.strip().lower())
    if book is None:
        return None
    chapter = int(chapter)
    verses = get_verse_numbers(df, book, chapter)
    if not verses:
        return None
    start = int(start) if start else verses[0]
    end = int(end) if end else (start if match.group(3) else verses[-1])
    if start not in verses or end not in verses or end < start:
        return None
    return book, chapter, start, end


def search_keyword(df: pd.DataFrame, keyword: str, limit: int = 50) -> pd.DataFrame:
    keyword = keyword.strip()
    if not keyword:
        return df.iloc[0:0]
    hits = df[df["text"].str.contains(keyword, case=False, regex=False, na=False)]
    return hits.head(limit)
