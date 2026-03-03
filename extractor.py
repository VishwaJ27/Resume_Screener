import re
import json
import spacy


# load spaCy model once at module level (avoid reloading on every call)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("[ERROR] spaCy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None


#  Load Skills Taxonomy from JSON

def load_skills_list(json_path: str = "data/skills_list.json") -> list:
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            return [skill.lower() for skill in data.get("skills", [])]

    except FileNotFoundError:
        print(f"[WARN] skills_list.json not found at {json_path}. Using default list.")

        # fallback default skill set
        return [
            "python", "java", "javascript", "typescript", "c++", "c#", "sql",
            "html", "css", "react", "node.js", "django", "flask", "fastapi",
            "machine learning", "deep learning", "nlp", "data analysis",
            "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
            "docker", "kubernetes", "aws", "gcp", "azure", "git", "linux",
            "mongodb", "postgresql", "mysql", "redis", "rest api", "graphql",
            "excel", "power bi", "tableau", "spark", "hadoop", "airflow",
            "communication", "leadership", "teamwork", "problem solving"
        ]


#  Extract Skills by matching against taxonomy

def extract_skills(text: str, skills_list: list) -> list:
    text_lower = text.lower()
    found = []

    for skill in skills_list:
        # use word boundary to avoid partial matches (e.g "java" inside "javascript")
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)

    return sorted(set(found))


#  Extract Name using spaCy NER

def extract_name(text: str) -> str:
    if not nlp:
        return "Unknown"

    # check only first 300 chars — name is almost always at the top
    doc = nlp(text[:300])

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()

    # fallback — first line is usually the name
    first_line = text.strip().splitlines()[0]
    if len(first_line.split()) <= 4:
        return first_line.strip()

    return "Unknown"


#  Extract Email & Phone using Regex

def extract_email(text: str) -> str:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else "Not found"


def extract_phone(text: str) -> str:
    match = re.search(r'(\+?\d[\d\s\-().]{7,}\d)', text)
    return match.group(0).strip() if match else "Not found"


#  Extract Education by looking for keywords

def extract_education(text: str) -> list:
    education = []

    degree_keywords = [
        "b.tech", "b.e", "b.sc", "bachelor", "m.tech", "m.sc", "master",
        "mba", "phd", "diploma", "10th", "12th", "high school", "undergraduate",
        "postgraduate", "b.com", "b.a", "m.a", "m.com"
    ]

    lines = text.splitlines()

    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in degree_keywords):
            cleaned = line.strip()
            if cleaned and len(cleaned) > 3:
                education.append(cleaned)

    return education[:5]  # cap at 5 entries to avoid noise


#  Extract Years of Experience

def extract_experience_years(text: str) -> str:
    # pattern like "3 years", "5+ years", "2-3 years of experience"
    pattern = r'(\d+\+?\s*(?:to|-)\s*\d+|\d+\+?)\s*years?\s*(?:of\s*)?(?:experience)?'
    match = re.search(pattern, text.lower())

    if match:
        return match.group(0).strip()

    return "Not mentioned"


#  Extract Job Titles / Roles from text

def extract_roles(text: str) -> list:
    role_keywords = [
        "software engineer", "data scientist", "data analyst", "ml engineer",
        "backend developer", "frontend developer", "full stack developer",
        "devops engineer", "cloud engineer", "product manager", "project manager",
        "business analyst", "web developer", "android developer", "ios developer",
        "database administrator", "system analyst", "ui/ux designer", "intern"
    ]

    text_lower = text.lower()
    found = []

    for role in role_keywords:
        if role in text_lower:
            found.append(role)

    return found


#  Master Function — extract everything at once

def extract_all(resume_text: str, skills_path: str = "data/skills_list.json") -> dict:
    if not resume_text.strip():
        return {"error": "Empty resume text provided"}

    skills_list = load_skills_list(skills_path)

    result = {
        "name":             extract_name(resume_text),
        "email":            extract_email(resume_text),
        "phone":            extract_phone(resume_text),
        "skills":           extract_skills(resume_text, skills_list),
        "education":        extract_education(resume_text),
        "experience_years": extract_experience_years(resume_text),
        "roles":            extract_roles(resume_text),
        "error":            None
    }

    return result


#  Quick Test — run this file directly

if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from src.parser import parse_resume

    if len(sys.argv) < 2:
        print("Usage: python src/extractor.py <path_to_resume.pdf or .docx>")
        sys.exit(1)

    filepath = sys.argv[1]

    # step 1 — parse
    parsed = parse_resume(filepath)
    if parsed.get("error"):
        print(f"[ERROR] {parsed['error']}")
        sys.exit(1)

    # step 2 — extract
    info = extract_all(parsed["text"])

    # display results
    print(f"\n{'='*50}")
    print(f"  Name             : {info['name']}")
    print(f"  Email            : {info['email']}")
    print(f"  Phone            : {info['phone']}")
    print(f"  Experience       : {info['experience_years']}")
    print(f"  Roles Found      : {', '.join(info['roles']) or 'None'}")
    print(f"  Education        :")
    for edu in info["education"]:
        print(f"    - {edu}")
    print(f"  Skills ({len(info['skills'])} found) :")
    for skill in info["skills"]:
        print(f"    - {skill}")
    print(f"{'='*50}")