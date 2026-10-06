# MARK
## Messenger of Almighty Righteous King

> A digital Bible for gentle reflection, Scripture, and thoughtful guidance.

---

## The Need

- People may want encouragement but not know where to begin.
- Finding a relevant Bible passage can take time.
- A supportive reflection should be personal, understandable, and mindful of safety.

---

## The Solution

MARK brings Bible reading and guided reflection together in one Streamlit app.

- Browse and search Bible passages.
- Share a feeling and a personal message.
- Receive a related Scripture passage, an AI-generated reflection, and a prayer.
- Choose a preferred response language: English, Bisaya, or Tagalog.

---

## Main Feature: Vent Your Heart

1. Choose how you are feeling.
2. Write a message and choose a language and passage length.
3. The app checks for crisis-related messages and verifies that Bible data is available.
4. The app selects a relevant passage and generates a reflection and prayer.
5. Scripture is displayed separately from AI-generated content.

---

## Age Field Example

Proposed age input for the reflection form:


This is the requested HTML example. The current interface is built with Streamlit and does not yet collect age.

---

## Source Files

| File | Responsibility |
| --- | --- |
| `streamlit_app.py` | Main app, page navigation, Bible Library, Vent workflow, and presentation of results |
| `utils/scripture_retriever.py` | Bible passage lookup, reference parsing, and keyword search |
| `utils/ai_reflection.py` | AI-generated explanation, reflection, and prayer |
| `utils/safety_checks.py` | Crisis-message checks and safety response |
| `utils/data_loader.py` | Loads and validates the Bible dataset |
| `data/bible_verses.csv` | Scripture data used by the app |
| `styles.css` | Visual styling |

---

## MVP: Minimum Viable Product

The smallest useful version that delivers the core experience:

- A working Bible Library with browsing and search.
- A Vent form for emotion, message, language, and passage length.
- Relevant Scripture with an AI reflection and prayer.
- Crisis-message handling and clear separation of Scripture from AI content.
- A verified Bible CSV and the required AI service configuration.

---

## MAP: Minimum Awesome Product

An enhanced version that makes the experience feel especially thoughtful and polished:

- Add an optional, validated age field to the Vent form, with a clear explanation of why it is requested.
- Improve age-appropriate wording without collecting more personal information than needed.
- Refine the reflection experience with accessible layouts and stronger language support.
- Add saved or shareable reflections only with explicit user consent and privacy safeguards.
- Provide a wider set of verified passages and more helpful search tools.

---

## Technology

- **App:** Python and Streamlit
- **Data:** pandas and a Bible verses CSV
- **Charts:** Altair
- **AI reflections:** Groq integration

---

## Purpose and Care

MARK supports personal reflection and Bible study. It is not a replacement for professional, pastoral, or emergency support. Users should avoid entering sensitive personal information.
