import re


STOP_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "you", "your",
    "are", "our", "will", "have", "has", "job", "role", "work", "years",
    "year", "experience", "required", "preferred", "skills", "ability",
    "strong", "good", "looking", "team", "using", "use", "including",
}


def _terms(value):
    return {
        token.casefold()
        for token in re.findall(r"[a-zA-Z0-9+#.]{2,}", value or "")
        if token.casefold() not in STOP_WORDS
    }


def description_keywords(value):
    return ", ".join(sorted(_terms(value))[:12])


def score_job(alert, job):
    """Return an explainable 0-100 relevance score and matching reasons."""
    title = (job.get("title") or "").casefold()
    content = " ".join(
        (job.get(key) or "") for key in ("title", "snippet", "company", "location", "type")
    ).casefold()
    reasons = []

    role_terms = _terms(alert.role_title)
    title_hits = role_terms.intersection(_terms(title))
    if title_hits:
        reasons.append("Role title match")

    skills = [item.strip() for item in re.split(r"[,;\n]", alert.skills) if item.strip()]
    skill_hits = [skill for skill in skills if skill.casefold() in content]
    if skill_hits:
        reasons.append("Skills: " + ", ".join(skill_hits[:5]))

    if alert.employment_type:
        requested_type = (
            alert.get_employment_type_display().casefold().replace("-", "").replace(" ", "")
        )
        returned_type = (job.get("type") or "").casefold().replace("-", "").replace(" ", "")
        if requested_type in returned_type:
            reasons.append("Employment type")

    description_terms = _terms(alert.role_description)
    description_hits = description_terms.intersection(_terms(content))
    if description_hits:
        reasons.append("Role details overlap")

    if alert.location and alert.location.casefold() in (job.get("location") or "").casefold():
        reasons.append("Location match")
    elif alert.remote_only and "remote" in content:
        reasons.append("Remote role")

    score = 0
    if role_terms:
        score += round(35 * len(title_hits) / len(role_terms))
    if skills:
        score += round(45 * len(skill_hits) / len(skills))
    if description_terms:
        score += round(10 * len(description_hits) / len(description_terms))
    if alert.location and alert.location.casefold() in (job.get("location") or "").casefold():
        score += 10
    elif alert.remote_only and "remote" in content:
        score += 10

    return min(score, 100), reasons
