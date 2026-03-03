import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# load model once at module level — avoid reloading on every call
# all-MiniLM-L6-v2 is lightweight, fast, and good enough for resume matching
print("[INFO] Loading sentence transformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("[INFO] Model loaded.")


#  Convert text into a vector embedding

def get_embedding(text: str):
    if not text.strip():
        return None
    return model.encode(text, convert_to_numpy=True)


#  Calculate similarity score between two texts
#  Returns a score between 0.0 and 1.0

def calculate_similarity(text1: str, text2: str) -> float:
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)

    if emb1 is None or emb2 is None:
        return 0.0

    # reshape needed for sklearn cosine_similarity (expects 2D arrays)
    score = cosine_similarity([emb1], [emb2])[0][0]

    # clamp between 0 and 1 just in case of floating point edge cases
    return round(float(np.clip(score, 0.0, 1.0)), 4)


#  Build a focused summary from extracted info
#  Better input = better match score

def build_resume_summary(extracted_info: dict) -> str:
    parts = []

    if extracted_info.get("roles"):
        parts.append("Roles: " + ", ".join(extracted_info["roles"]))

    if extracted_info.get("skills"):
        parts.append("Skills: " + ", ".join(extracted_info["skills"]))

    if extracted_info.get("experience_years"):
        parts.append("Experience: " + extracted_info["experience_years"])

    if extracted_info.get("education"):
        parts.append("Education: " + " | ".join(extracted_info["education"]))

    # fallback — just use raw text if nothing was extracted
    if not parts:
        return extracted_info.get("text", "")

    return "\n".join(parts)


#  Match a single resume against a job description

def match_resume_to_jd(extracted_info: dict, jd_text: str) -> dict:
    if not jd_text.strip():
        return {"error": "Job description is empty", "score": 0.0}

    resume_summary = build_resume_summary(extracted_info)

    if not resume_summary.strip():
        return {"error": "Resume has no extractable content", "score": 0.0}

    # score 1 — semantic similarity on structured summary vs JD
    summary_score = calculate_similarity(resume_summary, jd_text)

    # score 2 — raw full text vs JD (catches context summary_score might miss)
    full_text_score = calculate_similarity(
        extracted_info.get("text", ""),
        jd_text
    )

    # weighted blend — structured summary matters more
    final_score = round((summary_score * 0.65) + (full_text_score * 0.35), 4)
    percentage = round(final_score * 100, 2)

    return {
        "name":             extracted_info.get("name", "Unknown"),
        "email":            extracted_info.get("email", "Not found"),
        "score":            final_score,
        "percentage":       percentage,
        "summary_score":    round(summary_score * 100, 2),
        "fulltext_score":   round(full_text_score * 100, 2),
        "skills":           extracted_info.get("skills", []),
        "roles":            extracted_info.get("roles", []),
        "experience_years": extracted_info.get("experience_years", "Not mentioned"),
        "error":            None
    }


#  Match MULTIPLE resumes and rank them

def match_multiple_resumes(extracted_list: list, jd_text: str) -> list:
    results = []

    print(f"\n[INFO] Matching {len(extracted_list)} resume(s) against job description...")

    for info in extracted_list:
        result = match_resume_to_jd(info, jd_text)
        results.append(result)
        print(f"  → {result['name']:<25} Score: {result['percentage']}%")

    # rank by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # add rank number
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results


#  Pretty Print Results

def print_results(ranked_results: list):
    print(f"\n{'='*55}")
    print(f"  CANDIDATE RANKING")
    print(f"{'='*55}")

    for r in ranked_results:
        print(f"\n  #{r['rank']}  {r['name']}")
        print(f"      Email        : {r['email']}")
        print(f"      Match Score  : {r['percentage']}%")
        print(f"      Summary Score: {r['summary_score']}%")
        print(f"      Fulltext Score:{r['fulltext_score']}%")
        print(f"      Experience   : {r['experience_years']}")
        print(f"      Skills       : {', '.join(r['skills'][:8]) or 'None found'}")
        print(f"      Roles        : {', '.join(r['roles']) or 'None found'}")

    print(f"\n{'='*55}")


#  Quick Test — run this file directly

if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from src.parser import parse_multiple_resumes
    from src.extractor import extract_all

    if len(sys.argv) < 3:
        print("Usage: python src/matcher.py <resumes_folder> <jd_text_file>")
        sys.exit(1)

    resumes_folder = sys.argv[1]
    jd_file        = sys.argv[2]

    # read job description
    with open(jd_file, "r") as f:
        jd_text = f.read()

    # parse all resumes
    parsed_list = parse_multiple_resumes(resumes_folder)

    # extract info from each
    extracted_list = []
    for parsed in parsed_list:
        if not parsed.get("error"):
            info = extract_all(parsed["text"])
            info["text"] = parsed["text"]       # keep raw text for full_text_score
            info["filename"] = parsed["filename"]
            extracted_list.append(info)

    # match and rank
    ranked = match_multiple_resumes(extracted_list, jd_text)

    # display
    print_results(ranked)