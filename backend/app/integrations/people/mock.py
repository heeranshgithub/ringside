"""Seeded provider so the demo works with zero third-party credits.

Phones are intentionally absent, so nothing here can ever be dialled by accident."""

from __future__ import annotations

from app.integrations.people.base import PersonResult, SearchCriteria

_SEED: list[dict] = [
    {
        "name": "Ananya Iyer",
        "title": "Senior Frontend Engineer",
        "company": "Razorpay",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["react", "next.js", "typescript", "tailwind", "redux"],
        "yrs": 6,
    },
    {
        "name": "Rohan Mehta",
        "title": "Frontend Developer",
        "company": "Zepto",
        "loc": "Mumbai, Maharashtra, India",
        "skills": ["react", "javascript", "css", "vite"],
        "yrs": 3,
    },
    {
        "name": "Priya Nair",
        "title": "Full Stack Engineer",
        "company": "Freshworks",
        "loc": "Chennai, Tamil Nadu, India",
        "skills": ["node.js", "react", "postgres", "typescript", "aws"],
        "yrs": 5,
    },
    {
        "name": "Karthik Reddy",
        "title": "Backend Engineer",
        "company": "Swiggy",
        "loc": "Hyderabad, Telangana, India",
        "skills": ["python", "fastapi", "django", "postgres", "redis", "kafka"],
        "yrs": 4,
    },
    {
        "name": "Sneha Kulkarni",
        "title": "Senior Backend Engineer",
        "company": "PhonePe",
        "loc": "Pune, Maharashtra, India",
        "skills": ["java", "spring", "kafka", "mysql", "kubernetes"],
        "yrs": 7,
    },
    {
        "name": "Arjun Sharma",
        "title": "Python Developer",
        "company": "Meesho",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["python", "fastapi", "mongodb", "docker", "celery"],
        "yrs": 3,
    },
    {
        "name": "Divya Menon",
        "title": "DevOps Engineer",
        "company": "Zomato",
        "loc": "Gurugram, Haryana, India",
        "skills": ["aws", "terraform", "kubernetes", "github actions", "python"],
        "yrs": 5,
    },
    {
        "name": "Vikram Singh",
        "title": "Site Reliability Engineer",
        "company": "Flipkart",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["kubernetes", "prometheus", "go", "aws", "linux"],
        "yrs": 6,
    },
    {
        "name": "Meera Krishnan",
        "title": "Data Scientist",
        "company": "Cred",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["python", "pandas", "scikit-learn", "sql", "pytorch"],
        "yrs": 4,
    },
    {
        "name": "Aditya Verma",
        "title": "Machine Learning Engineer",
        "company": "Ola",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["python", "pytorch", "mlops", "aws", "docker"],
        "yrs": 5,
    },
    {
        "name": "Neha Gupta",
        "title": "Product Manager",
        "company": "Paytm",
        "loc": "Noida, Uttar Pradesh, India",
        "skills": ["product strategy", "sql", "analytics", "roadmapping"],
        "yrs": 6,
    },
    {
        "name": "Sameer Khan",
        "title": "Field Sales Executive",
        "company": "Bajaj Finserv",
        "loc": "Delhi, India",
        "skills": ["sales", "crm", "negotiation", "hindi", "english"],
        "yrs": 3,
    },
    {
        "name": "Pooja Desai",
        "title": "Sales Executive",
        "company": "HDFC Bank",
        "loc": "Ahmedabad, Gujarat, India",
        "skills": ["sales", "customer relations", "gujarati", "hindi"],
        "yrs": 2,
    },
    {
        "name": "Rahul Yadav",
        "title": "Warehouse Associate",
        "company": "Delhivery",
        "loc": "Lucknow, Uttar Pradesh, India",
        "skills": ["inventory", "forklift", "wms", "hindi"],
        "yrs": 2,
    },
    {
        "name": "Kavya Rao",
        "title": "Customer Support Executive",
        "company": "Urban Company",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["customer support", "zendesk", "kannada", "english", "hindi"],
        "yrs": 3,
    },
    {
        "name": "Manish Patel",
        "title": "Marketing Associate",
        "company": "Nykaa",
        "loc": "Mumbai, Maharashtra, India",
        "skills": ["seo", "content", "google ads", "analytics"],
        "yrs": 2,
    },
    {
        "name": "Ishita Bose",
        "title": "Digital Marketing Manager",
        "company": "Myntra",
        "loc": "Kolkata, West Bengal, India",
        "skills": ["performance marketing", "meta ads", "seo", "analytics"],
        "yrs": 5,
    },
    {
        "name": "Suresh Babu",
        "title": "Delivery Partner",
        "company": "Dunzo",
        "loc": "Chennai, Tamil Nadu, India",
        "skills": ["two-wheeler", "navigation", "tamil"],
        "yrs": 1,
    },
    {
        "name": "Farhan Ali",
        "title": "Store Manager",
        "company": "Reliance Retail",
        "loc": "Hyderabad, Telangana, India",
        "skills": ["retail operations", "team management", "pos", "telugu", "hindi"],
        "yrs": 6,
    },
    {
        "name": "Lakshmi Pillai",
        "title": "HR Executive",
        "company": "TCS",
        "loc": "Kochi, Kerala, India",
        "skills": ["recruitment", "onboarding", "hrms", "malayalam", "english"],
        "yrs": 3,
    },
    {
        "name": "Deepak Joshi",
        "title": "Senior React Developer",
        "company": "Groww",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["react", "typescript", "next.js", "graphql", "jest"],
        "yrs": 5,
    },
    {
        "name": "Tanvi Shah",
        "title": "UI Engineer",
        "company": "Postman",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["react", "design systems", "css", "storybook", "typescript"],
        "yrs": 4,
    },
    {
        "name": "Nikhil Agarwal",
        "title": "Backend Developer",
        "company": "Unacademy",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["python", "django", "postgres", "aws", "redis"],
        "yrs": 3,
    },
    {
        "name": "Ritu Chauhan",
        "title": "Engineering Manager",
        "company": "Atlassian",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["leadership", "python", "system design", "agile"],
        "yrs": 10,
    },
    {
        "name": "Harish Kumar",
        "title": "Node.js Developer",
        "company": "BYJU'S",
        "loc": "Chennai, Tamil Nadu, India",
        "skills": ["node.js", "express", "mongodb", "typescript", "docker"],
        "yrs": 4,
    },
    {
        "name": "Shreya Banerjee",
        "title": "Data Analyst",
        "company": "Swiggy",
        "loc": "Kolkata, West Bengal, India",
        "skills": ["sql", "python", "tableau", "excel"],
        "yrs": 2,
    },
    {
        "name": "Yash Malhotra",
        "title": "Cloud Engineer",
        "company": "Infosys",
        "loc": "Pune, Maharashtra, India",
        "skills": ["aws", "azure", "terraform", "python", "docker"],
        "yrs": 4,
    },
    {
        "name": "Bhavana Hegde",
        "title": "QA Engineer",
        "company": "Zeta",
        "loc": "Bengaluru, Karnataka, India",
        "skills": ["selenium", "playwright", "python", "api testing"],
        "yrs": 4,
    },
    {
        "name": "Omkar Deshpande",
        "title": "Android Developer",
        "company": "Dream11",
        "loc": "Mumbai, Maharashtra, India",
        "skills": ["kotlin", "android", "jetpack compose", "firebase"],
        "yrs": 5,
    },
    {
        "name": "Zara Sheikh",
        "title": "Telecaller",
        "company": "Policybazaar",
        "loc": "Gurugram, Haryana, India",
        "skills": ["telecalling", "hindi", "english", "crm"],
        "yrs": 2,
    },
]


def _tokens(*parts: str | None) -> set[str]:
    out: set[str] = set()
    for p in parts:
        if p:
            out.update(
                t for t in p.lower().replace("/", " ").replace(",", " ").split() if len(t) > 1
            )
    return out


class MockProvider:
    name = "mock"

    async def search(self, criteria: SearchCriteria) -> list[PersonResult]:
        scored: list[tuple[int, PersonResult]] = []
        want_titles = [t.lower() for t in criteria.titles]
        want_locs = _tokens(*criteria.locations)
        want_skills = {s.lower() for s in criteria.skills}
        want_kw = _tokens(criteria.keywords)
        for i, p in enumerate(_SEED):
            score = 0
            title = p["title"].lower()
            for t in want_titles:
                if t in title:
                    score += 5
                elif _tokens(t) & _tokens(title):
                    score += 2
            if want_locs & _tokens(p["loc"]):
                score += 2
            score += 2 * len(want_skills & set(p["skills"]))
            score += len(want_kw & (_tokens(title, p["company"]) | set(p["skills"])))
            if score == 0 and (want_titles or want_skills or want_kw):
                continue
            person = PersonResult(
                source="mock",
                source_ref=f"mock-{i:03d}",
                name=p["name"],
                first_name=p["name"].split()[0],
                last_name=p["name"].split()[-1],
                phone=None,
                email=f"{p['name'].split()[0].lower()}.{p['name'].split()[-1].lower()}@example.com",
                current_title=p["title"],
                current_company=p["company"],
                location=p["loc"],
                skills=p["skills"],
                linkedin_url=None,
                summary=f"{p['title']} at {p['company']} with {p['yrs']} years of experience.",
                years_experience=float(p["yrs"]),
            )
            scored.append((score, person))
        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored[: criteria.limit]]
