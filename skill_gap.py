import re
import json


#  Extract required skills from a Job Description
#  (same logic as extractor.py but aimed at JD text)

def extract_jd_skills(jd_text: str, skills_path: str = "data/skills_list.json") -> list:
    try:
        with open(skills_path, "r") as f:
            data = json.load(f)
            skills_list = [s.lower() for s in data.get("skills", [])]
    except FileNotFoundError:
        print("[WARN] skills_list.json not found, using fallback list.")
        skills_list = [
            "python", "java", "javascript", "sql", "react", "node.js",
            "machine learning", "deep learning", "docker", "aws", "git",
            "postgresql", "mongodb", "rest api", "communication", "leadership"
        ]

    jd_lower = jd_text.lower()
    found = []

    for skill in skills_list:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, jd_lower):
            found.append(skill)

    return sorted(set(found))


#  Core Gap Analysis
#  Compare what candidate has vs what JD needs

def analyze_gap(candidate_skills: list, jd_skills: list) -> dict:
    candidate_set = set(candidate_skills)
    jd_set        = set(jd_skills)

    matched  = sorted(candidate_set & jd_set)       # skills in both
    missing  = sorted(jd_set - candidate_set)        # JD needs but candidate lacks
    extra    = sorted(candidate_set - jd_set)        # candidate has but JD didn't ask for

    # coverage = how many JD skills the candidate covers
    coverage = 0.0
    if jd_set:
        coverage = round(len(matched) / len(jd_set) * 100, 2)

    return {
        "matched_skills":  matched,
        "missing_skills":  missing,
        "extra_skills":    extra,
        "matched_count":   len(matched),
        "missing_count":   len(missing),
        "extra_count":     len(extra),
        "jd_skill_count":  len(jd_set),
        "coverage":        coverage      # % of JD skills the candidate covers
    }


#  Generate a simple text feedback for candidate

def generate_feedback(gap_report: dict, match_percentage: float) -> str:
    coverage  = gap_report["coverage"]
    matched   = gap_report["matched_count"]
    missing   = gap_report["missing_count"]
    feedback  = []

    # overall verdict
    if match_percentage >= 75:
        feedback.append("Strong Match — This candidate is a great fit for the role.")
    elif match_percentage >= 50:
        feedback.append("Moderate Match — Candidate meets core requirements with some gaps.")
    else:
        feedback.append("Weak Match — Candidate is missing several key requirements.")

    # skill coverage line
    feedback.append(
        f"   Covers {matched} of {gap_report['jd_skill_count']} required skills ({coverage}% coverage)."
    )

    # missing skills callout
    if gap_report["missing_skills"]:
        top_missing = ", ".join(gap_report["missing_skills"][:5])
        if missing > 5:
            top_missing += f" and {missing - 5} more"
        feedback.append(f"   Key gaps: {top_missing}.")

    # bonus skills
    if gap_report["extra_skills"]:
        top_extra = ", ".join(gap_report["extra_skills"][:4])
        feedback.append(f"   Bonus skills: {top_extra}.")

    return "\n".join(feedback)


#  Run full gap analysis for a single candidate

def run_gap_analysis(match_result: dict, jd_text: str, skills_path: str = "data/skills_list.json") -> dict:
    jd_skills        = extract_jd_skills(jd_text, skills_path)
    candidate_skills = match_result.get("skills", [])

    gap = analyze_gap(candidate_skills, jd_skills)
    feedback = generate_feedback(gap, match_result.get("percentage", 0.0))

    return {
        "name":            match_result.get("name", "Unknown"),
        "email":           match_result.get("email", "Not found"),
        "match_score":     match_result.get("percentage", 0.0),
        "rank":            match_result.get("rank", "-"),
        "jd_skills":       jd_skills,
        "matched_skills":  gap["matched_skills"],
        "missing_skills":  gap["missing_skills"],
        "extra_skills":    gap["extra_skills"],
        "coverage":        gap["coverage"],
        "matched_count":   gap["matched_count"],
        "missing_count":   gap["missing_count"],
        "feedback":        feedback
    }


#  Run gap analysis for ALL ranked candidates

def run_gap_analysis_all(ranked_results: list, jd_text: str, skills_path: str = "data/skills_list.json") -> list:
    full_reports = []

    print(f"\n[INFO] Running skill gap analysis for {len(ranked_results)} candidate(s)...")

    for result in ranked_results:
        report = run_gap_analysis(result, jd_text, skills_path)
        full_reports.append(report)
        print(f"  → {report['name']:<25} Coverage: {report['coverage']}%  Missing: {report['missing_count']} skills")

    return full_reports


#  Pretty Print Gap Reports

def print_gap_reports(reports: list):
    print(f"\n{'='*60}")
    print(f"  SKILL GAP REPORT")
    print(f"{'='*60}")

    for r in reports:
        print(f"\n  Rank #{r['rank']}  —  {r['name']}")
        print(f"  Email          : {r['email']}")
        print(f"  Match Score    : {r['match_score']}%")
        print(f"  Skill Coverage : {r['coverage']}%")

        print(f"\n  Matched Skills ({r['matched_count']}):")
        if r["matched_skills"]:
            print("     " + ", ".join(r["matched_skills"]))
        else:
            print("     None")

        print(f"\n  Missing Skills ({r['missing_count']}):")
        if r["missing_skills"]:
            print("     " + ", ".join(r["missing_skills"]))
        else:
            print("     None — full coverage!")

        print(f"\n  Extra Skills ({len(r['extra_skills'])}):")
        if r["extra_skills"]:
            print("     " + ", ".join(r["extra_skills"][:6]))
        else:
            print("     None")

        print(f"\n  Feedback:\n{r['feedback']}")
        print(f"\n  {'-'*58}")

    print(f"\n{'='*60}")


#  Quick Test — run this file directly

if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from src.parser    import parse_multiple_resumes
    from src.extractor import extract_all
    from src.matcher   import match_multiple_resumes

    if len(sys.argv) < 3:
        print("Usage: python src/skill_gap.py <resumes_folder> <jd_text_file>")
        sys.exit(1)

    resumes_folder = sys.argv[1]
    jd_file        = sys.argv[2]

    with open(jd_file, "r") as f:
        jd_text = f.read()

    # pipeline — parse → extract → match → gap
    parsed_list = parse_multiple_resumes(resumes_folder)

    extracted_list = []
    for parsed in parsed_list:
        if not parsed.get("error"):
            info = extract_all(parsed["text"])
            info["text"]     = parsed["text"]
            info["filename"] = parsed["filename"]
            extracted_list.append(info)

    ranked   = match_multiple_resumes(extracted_list, jd_text)
    reports  = run_gap_analysis_all(ranked, jd_text)

    print_gap_reports(reports)