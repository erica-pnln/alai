from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "bible_verses.csv"
REQUIRED_COLUMNS = ["book", "testament", "chapter", "verse", "reference", "text"]
OLD_TESTAMENT_BOOKS = {
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi",
}


def make_empty_bible() -> pd.DataFrame:
    """Return the expected schema without inventing verse content."""
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def clean_bible(df: pd.DataFrame) -> pd.DataFrame:
    """Trim text, fix number types, drop bad rows and duplicates."""
    df = df.copy()
    for col in ["book", "text"]:
        df[col] = df[col].astype(str).str.strip()
    df["chapter"] = pd.to_numeric(df["chapter"], errors="coerce")
    df["verse"] = pd.to_numeric(df["verse"], errors="coerce")
    df = df.dropna(subset=["chapter", "verse"])
    df["chapter"] = df["chapter"].astype(int)
    df["verse"] = df["verse"].astype(int)
    if "testament" not in df.columns:
        df["testament"] = df["book"].apply(
            lambda book: "Old Testament" if book in OLD_TESTAMENT_BOOKS else "New Testament"
        )
    else:
        df["testament"] = df["testament"].astype(str).str.strip()
    if "reference" not in df.columns:
        df["reference"] = (
            df["book"] + " " + df["chapter"].astype(str) + ":" + df["verse"].astype(str)
        )
    else:
        df["reference"] = df["reference"].astype(str).str.strip()
    df = df[(df["book"] != "") & (df["reference"] != "") & (df["text"] != "")]
    df = df.drop_duplicates(subset=["book", "chapter", "verse"])
    return df.reset_index(drop=True)


def load_bible():
    """Returns (dataframe, status, message). status: 'ok' | 'missing' | 'error'."""
    if not DATA_PATH.exists():
        return make_empty_bible(), "missing", (
            "The Bible file (data/bible_verses.csv) was not found. "
            "No Scripture is displayed until you add a verified public-domain "
            "Bible CSV."
        )
    try:
        df = pd.read_csv(DATA_PATH)
    except Exception:
        return make_empty_bible(), "error", (
            "The Bible file could not be read. Check that it is a valid CSV. "
            "No Scripture is displayed."
        )
    column_names = {column.strip().lower(): column for column in df.columns}
    if not {"book", "chapter", "verse", "text"}.issubset(column_names):
        missing = [c for c in ("book", "chapter", "verse", "text") if c not in column_names]
        return make_empty_bible(), "error", (
            f"The Bible file is missing these source columns: {', '.join(missing)}. "
            "No Scripture is displayed."
        )
    df = df.rename(columns={column: canonical for canonical, column in column_names.items() if canonical in REQUIRED_COLUMNS})
    if "book" not in df.columns:
        df = df.rename(columns={column_names["book"]: "book"})
    if "chapter" not in df.columns:
        df = df.rename(columns={column_names["chapter"]: "chapter"})
    if "verse" not in df.columns:
        df = df.rename(columns={column_names["verse"]: "verse"})
    if "text" not in df.columns:
        df = df.rename(columns={column_names["text"]: "text"})
    missing = [c for c in ("book", "chapter", "verse", "text") if c not in df.columns]
    if missing:
        return make_empty_bible(), "error", (
            f"The Bible file is missing these columns: {', '.join(missing)}. "
            "No Scripture is displayed."
        )
    df = clean_bible(df)
    if df.empty:
        return make_empty_bible(), "error", (
            "The Bible file has no usable rows. No Scripture is displayed."
        )
    return df, "ok", "Bible dataset loaded."
