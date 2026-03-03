# Resume Screener

A local resume screening and skill matching system that ranks candidates against a job description using semantic similarity and skill gap analysis.

---

## What it does

- Parses resumes from PDF and DOCX formats
- Extracts name, email, phone, skills, education, experience, and roles using NLP
- Matches each candidate to the job description using sentence embeddings
- Ranks all candidates by a weighted similarity score
- Produces a skill gap report showing matched, missing, and bonus skills per candidate
- Displays everything in a clean Streamlit dashboard

---

## Project Structure

```
resume-screening/
│
├── src/
│   ├── parser.py          # Extracts raw text from PDF and DOCX files
│   ├── extractor.py       # Pulls structured info using spaCy and regex
│   ├── matcher.py         # Sentence Transformer embeddings + cosine similarity scoring
│   └── skill_gap.py       # Compares candidate skills vs JD skills
│
├── data/
│   ├── resumes/           # Place your PDF / DOCX resumes here
│   ├── skills_list.json   # Skill taxonomy used for extraction and matching
│   └── job_description.txt  # Optional — paste JD here for CLI testing
│
├── app.py                 # Streamlit dashboard (main entry point)
├── requirements.txt
└── README.md
```

---

## Setup

**1. Clone or download the project**

```bash
git clone https://github.com/yourname/resume-screening.git
cd resume-screening
```

**2. Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Download the spaCy language model**

```bash
python -m spacy download en_core_web_sm
```

---

## Running the App

```bash
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

1. Upload one or more resumes (PDF or DOCX) from the sidebar
2. Paste the job description into the text area
3. Click **Run Analysis**

---

## Pipeline Overview

```
Upload Resumes (PDF / DOCX)
        │
        ▼
  parser.py  ──  Extract raw text from each file
        │
        ▼
  extractor.py  ──  Pull name, email, skills, education, experience
        │
        ▼
  matcher.py  ──  Generate embeddings → calculate similarity score
        │
        ▼
  skill_gap.py  ──  Compare skills → matched / missing / bonus
        │
        ▼
  app.py  ──  Ranked table + detailed candidate reports
```

---

## How Scoring Works

Each candidate gets a final match score based on two signals:

| Signal | Description | Weight |
|---|---|---|
| Summary score | Structured info (skills, roles, education) vs JD | 65% |
| Full text score | Raw resume text vs JD | 35% |

Scores are calculated using cosine similarity on `all-MiniLM-L6-v2` embeddings from Sentence Transformers. This captures meaning rather than just keyword overlap — so a resume mentioning "built REST APIs with Django" will correctly match a JD asking for "backend web development experience".

---

## Skill Gap Analysis

For each candidate the system produces three lists:

- **Matched** — skills the candidate has that the JD requires
- **Missing** — skills the JD requires that the candidate lacks
- **Bonus** — additional skills the candidate has beyond the JD requirements

A plain-English verdict is also generated based on the match score:

| Score | Verdict |
|---|---|
| 70% and above | Strong match |
| 45% – 69% | Moderate match |
| Below 45% | Weak match |

---

## Customising the Skill Taxonomy

Open `data/skills_list.json` and add or remove skills as needed:

```json
{
  "skills": [
    "Python", "Django", "PostgreSQL", "Docker", "AWS",
    "your custom skill here"
  ]
}
```

The taxonomy is used by both `extractor.py` (to pull skills from resumes) and `skill_gap.py` (to find required skills in the job description).

---

## CLI Testing (without the UI)

Each module can be run independently from the terminal for quick testing:

```bash
# Test parser only
python src/parser.py data/resumes/

# Test extractor on a single resume
python src/extractor.py data/resumes/sample.pdf

# Run full match + ranking
python src/matcher.py data/resumes/ data/job_description.txt

# Run full pipeline including skill gap report
python src/skill_gap.py data/resumes/ data/job_description.txt
```

---

## Dependencies

| Package | Purpose |
|---|---|
| pdfplumber | Extract text from PDF files |
| python-docx | Extract text from DOCX files |
| spacy | NLP entity extraction |
| sentence-transformers | Semantic text embeddings |
| scikit-learn | Cosine similarity calculation |
| numpy | Vector operations |
| streamlit | Web dashboard |
| pandas | Table rendering |

---

## Known Limitations

- Name extraction via spaCy NER can miss uncommon names. The fallback uses the first line of the resume, which works for most standard formats.
- Scanned PDF resumes (image-based) are not supported. The resume must have selectable text.
- Match scores are relative — a score of 60% does not mean the candidate is 60% qualified, it means they are a closer semantic match than candidates who scored lower.
