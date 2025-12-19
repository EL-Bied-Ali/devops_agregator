import os

# API keys are loaded from config_secrets.py (not tracked) or environment variables.
try:
    from config_secrets import ADZUNA_APP_ID, ADZUNA_APP_KEY, JOOBLE_API_KEY  # type: ignore
except ImportError:
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
    JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")

# Validation: stop early if Adzuna keys are missing
if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    raise RuntimeError("Missing Adzuna API credentials. Set env vars or config_secrets.py")
# Jooble key can stay empty if you don't use Jooble
if JOOBLE_API_KEY is None:
    JOOBLE_API_KEY = ""

# Laisser vide pour ne pas restreindre l'API Jooble (filtrage fait ensuite)
JOOBLE_LOCATION = ""

# Pagination et taille de page
# PAGES_PER_TERM : dict facultatif pour surcharger le nombre de pages par terme
PAGES_PER_TERM = {
    "devops": 4,
    "devops engineer": 4,
    "devops intern": 3,
    "devops graduate": 3,
    "graduate devops": 3,
    "graduate program": 2,
    "young graduate": 2,
    "cloud support": 4,
    "cloud support engineer": 4,
    "cloud support intern": 3,
    "cloud engineer": 3,
    "cloud graduate": 3,
    "cloud engineer intern": 3,
    "junior cloud engineer": 3,
    "cloud intern": 3,
    "system administrator": 3,
    "system administrator intern": 3,
    "linux system administrator": 3,
    "linux system administrator intern": 3,
    "platform engineer": 3,
    "platform engineer intern": 3,
    "site reliability engineer": 3,
    "sre": 3,
    "operations engineer": 3,
    "it operations": 3,
    "it intern": 3,
    "it trainee": 3,
    "stagiaire devops": 3,
    "stagiaire cloud": 3,
    "kubernetes": 2,
    "docker": 2,
}
DEFAULT_PAGES = 2
RESULTS_PER_PAGE = 50

# Description minimale (plus souple pour garder les offres courtes)
REQUIRE_DESCRIPTION = True
MIN_DESCRIPTION_CHARS = 60

COUNTRY = "be"

# Termes de recherche pour recuperer large cote API
# --> orientes Cloud / SysAdmin / DevOps junior-friendly
SEARCH_TERMS = [
    # coeur DevOps / Cloud
    "devops",
    "devops engineer",
    "junior devops",
    "devops graduate",
    "graduate devops",
    "graduate program",
    "young graduate",
    "system administrator",
    "linux system administrator",
    "linux system engineer",
    "systems administrator",
    "systems engineer",
    "sysadmin",
    "it operations",
    "operations engineer",
    "platform engineer",
    "cloud engineer",
    "junior cloud engineer",
    "cloud intern",
    "devops intern",
    "cloud engineer intern",
    "cloud support intern",
    "system administrator intern",
    "linux system administrator intern",
    "platform engineer intern",
    "it intern",
    "it trainee",
    "stagiaire devops",
    "stagiaire cloud",
    "alternance devops",
    "cloud operations",
    "cloud operations engineer",
    "cloud support",
    "cloud support engineer",
    "cloud support specialist",
    "site reliability engineer",
    "sre",
    "infrastructure engineer",
    "build engineer",
    "release engineer",

    # techno typiques DevOps / Cloud
    "azure devops",
    "azure engineer",
    "aws engineer",
    "gcp engineer",
    "cicd",
    "ci/cd",
    "automation engineer",
    "automation & mechanical",
    "ot ",
    "operational technology",
    "waterwastewater",
    "water wastewater",
    "wastewater",
    "formula one",
    "f1 ",
    "kubernetes",
    "docker",
    "monitoring engineer",
    "observability",
]

# ponderation des termes pour le scoring
PRIORITY_TERMS = {
    "cloud support": 6,             # priorite max pour toi
    "cloud operations": 6,
    "cloud engineer": 5,
    "junior cloud engineer": 5,
    "system administrator": 5,
    "linux system administrator": 5,
    "devops engineer": 4,
    "devops": 4,
    "site reliability engineer": 4,
    "platform engineer": 3,
}

# annonces pas plus vieilles que 45 jours (moins strict pour garder plus d'offres)
MAX_DAYS_OLD = 45

# on elargit a toute la Belgique, mais filtree par grandes villes
ALLOWED_LOCATIONS_KEYWORDS = [
    "Brussels",
    "Bruxelles",
    "Belgium",
    "Belgique",
    "Flanders",
    "Vlaanderen",
    "Flemish",
    "Wallonia",
    "Wallonie",
    "Flemish Brabant",
    "Brabant Flamand",
    "Brabant Wallon",
    "Walloon Brabant",
    "Hainaut",
    "Liege",
    "Liege Province",
    "Charleroi",
    "Namur",
    "Mons",
    "Louvain-la-Neuve",
    "Leuven",
    "Louvain",
    "Antwerp",
    "Anvers",
    "Ghent",
    "Gent",
    "East Flanders",
    "West Flanders",
    "Mechelen",
    "Malines",
    "Kortrijk",
    "Limbourg",
    "Limburg",
    "Arlon",
    "Luxembourg",
    "Remote",
    "Teletravail",
    "Telework",
]

# on filtre ce qu'on ne veut PAS:
# - postes trop seniors
# - jobs ou le neerlandais est clairement exige
EXCLUDE_KEYWORDS = [
    # seniority
    "senior",
    "medior",
    "expert",
    "principal",
    "architect",
    "lead",
    "team lead",
    "tech lead",
    "chapter lead",
    "manager",
    "head of",
    "director",
    "staff engineer",

    # experience requirements EN
    "3+ years",
    "3 years experience",
    "min 3 years",
    "minimum 3 years",
    "at least 3 years",

    "4+ years",
    "4 years experience",
    "min 4 years",
    "minimum 4 years",
    "at least 4 years",

    "5+ years",
    "5 years experience",
    "min 5 years",
    "minimum 5 years",
    "at least 5 years",

    "6+ years",
    "7+ years",
    "8+ years",
    "10+ years",

    # FR - annees d'experience
    "au moins 3 ans",
    "au moins 4 ans",
    "au moins 5 ans",
    "min. 3 ans",
    "min. 4 ans",
    "min. 5 ans",
    "minimum 3 ans d'experience",
    "minimum 4 ans d'experience",
    "minimum 5 ans d'experience",
    "plusieurs annees d'experience",

    # FR - profils confirmes / seniors
    "experience confirmee",
    "experience significative",
    "experience solide",
    "experience approfondie",
    "profil confirme",
    "profil senior",

    # contracting & consulting senior roles
    "freelance",
    "independent consultant",
    "consultant senior",
    "consulting lead",

    # red flags de seniorite / ownership
    "ownership",
    "take ownership",
    "autonomous",
    "work autonomously",
    "take the lead",
    "drive initiatives",
    "ability to mentor",
    "mentor",
    "mentor junior",
    "coaching",
    "lead improvements",
    "end-to-end responsibility",
    "strategic mindset",
    "make architectural decisions",
    "design scalable systems",
    "design cloud solutions",

    # signaux de postes infra seniors / data center
    "experience in data center",
    "experience en data center",
    "data center europeen",
    "migration des infrastructures",
    "migrate infrastructure",
    "strong experience",
    "solide experience",
    "3 a 5 ans",
    "3-5 years",
    "5 ans",
    "5 years",
    "advanced knowledge",
    "in-depth knowledge",
    "deep knowledge",
    "broad experience",

    # clearances / consulting exigeant
    "security clearance",
    "clearance",
    "secret clearance",
    "top secret",
    "nato",
    "cosmic",
    "defense",
    "defence",
    "military",
    "classified",
    "consultant",
    "consulting",
    "contractor",

    # language - dutch
    "dutch required",
    "dutch mandatory",
    "native dutch",
    "fluent dutch",
    "perfect dutch",
    "excellent dutch",
    "good dutch",
    "nederlands vereist",
    "nederlands verplicht",
    "moedertaal nederlands",
    "zeer goede connaissance du neerlandais",
    "zeer goede connaissance du neerlandais",
    "zeer goede connaissance du neerlandais",
    "goede kennis nederlands",
    "perfect nederlands",

    # roles not entry-level
    "architectuur",
    "enterprise architect",
    "solution architect",

    # hors scope data / ML / AI / data consulting
    "data consultant",
    "consultant data",
    "cloud & data",
    "data engineer",
    "data analyst",
    "business intelligence",
    "bi consultant",
    "machine learning",
    "ml engineer",
    "nlp",
    "ai engineer",
    "artificial intelligence",
    "python engineer",

    # hors scope embarque / video / test logiciel pur
    "embedded",
    "embedded software",
    "firmware",
    "hardware",
    "video engineer",
    "software test engineer",
    "rail traffic data",
]

# ==== filtres de type de role (optimises pour ton profil) ====

# Roles qu'on considere pertinents pour toi apres DevOps + AZ-400 + Master ULB
ROLE_REQUIRED_KEYWORDS = [
    # coeur Cloud / Infra / DevOps
    "devops",
    "devops engineer",
    "devops intern",
    "devops internship",
    "devops graduate",
    "graduate devops",
    "graduate program",
    "young graduate",
    "cloud intern",
    "cloud engineer intern",
    "cloud support intern",
    "stagiaire devops",
    "stagiaire cloud",
    "trainee devops",
    "cloud engineer",
    "cloud support",
    "cloud support engineer",
    "cloud operations",
    "cloud operations engineer",
    "cloud operations specialist",
    "platform engineer",
    "site reliability engineer",
    "sre",

    # Linux / systemes
    "linux system administrator",
    "linux administrator",
    "linux admin",
    "linux engineer",
    "system administrator",
    "systems administrator",
    "system engineer",
    "systems engineer",
    "infrastructure engineer",
    "infra engineer",

    # Observabilite / pipelines / automation
    "observability",
    "monitoring engineer",
    "monitoring specialist",
    "automation engineer",
    "cicd",
    "ci/cd",
    "build engineer",
    "release engineer",
    "pipeline engineer",
    "reliability engineer",

    # DevSecOps / securite liee a l'infra (facultatif mais OK)
    "devsecops",
    "security operations",
]

# Roles a exclure : non-tech, commerciaux, data/ML/AI, dev pur, automation industrielle
ROLE_FORBIDDEN_KEYWORDS = [
    "sql database administrator",
    "database administrator",
    " dba ",
    "keycloak",
    "observability engineer",
    "ict observability engineer",

    # hors scope management / C-level
    "coo",
    "chief operating officer",

    # qualite/systemes non infra
    "quality & systems",
    "ingenieur qualite",

    # securite tres pointue
    "cyber security specialist",
    "mergers & acquisitions",
    "m&a",

    # L3 / niveaux eleves
    " l3 ",

    # non-tech / sales
    "sales",
    "account executive",
    "account manager",
    "vendeur",
    "vendeuse",
    "commercial",
    "business developer",
    "business development",
    "inside sales",
    "customer success",
    "store",
    "shop",
    "cashier",
    "receptionist",
    "hostess",
    "host",

    # logistique / conduite
    "chauff",
    "driver",
    "delivery",
    "livreur",
    "magasinier",

    # marketing
    "marketing",
    "product marketer",
    "digital marketer",
    "seo ",
    "sea ",
    "sem ",

    # roles support / coord / qualite (non tech)
    "quality coordinator",
    "quality officer",
    "project coordinator",
    "office assistant",
    "administrative assistant",

    # data / ml / ai
    "data scientist",
    "data analyst",
    "business intelligence",
    "bi consultant",
    "power bi",
    "tableau developer",
    "machine learning",
    "ml engineer",
    "nlp",
    "ai engineer",
    "artificial intelligence",
    "consultant data",
    "data engineer",

    # developpement pur (pas DevOps/System)
    "frontend developer",
    "front end developer",
    "front-end developer",
    "fullstack",
    "full stack",
    "full-stack",
    "backend developer",
    "back-end developer",
    "back end developer",
    "java developer",
    "javascript developer",
    "react developer",
    ".net developer",
    "php developer",
    "web developer",
    "software engineer",
    "software developer",
    "content moderator",

    # QA fonctionnel, testeur non infra
    "manual tester",
    "functional tester",
    "test analyst",
    "qa analyst",
    "quality assurance analyst",

    # automation industrielle (PLC, SCADA…)
    "plc",
    "delta v",
    "deltav",
    "scada",
    "dcs ",
    "ladder logic",
    "automation system",
    "rockwell",
    "siemens tia portal",
    "siemens step7",
    "allen-bradley",
    "automate industriel",
]

ADZUNA_RAW_CSV = "data/adzuna_jobs_raw.csv"
ADZUNA_FILTERED_CSV = "data/adzuna_jobs_filtered.csv"
JOOBLE_RAW_CSV = "data/jooble_jobs_raw.csv"
JOOBLE_FILTERED_CSV = "data/jooble_jobs_filtered.csv"
MERGED_CSV = "data/all_jobs_merged.csv"
MERGED_RAW_CSV = "data/all_jobs_merged_raw.csv"
MERGED_FILTERED_CSV = "data/all_jobs_merged_filtered.csv"
