ADZUNA_APP_ID = "026d8627"
ADZUNA_APP_KEY = "883990e03a21c61e376492c7e2ccf2ed"

JOOBLE_API_KEY = "TON_API_KEY_JOOBLE"

# Pagination et taille de page
# PAGES_PER_TERM : dict facultatif pour surcharger le nombre de pages par terme
PAGES_PER_TERM = {
    # "devops": 3,
    # "cloud": 2,
}
DEFAULT_PAGES = 2
RESULTS_PER_PAGE = 50

# Description minimale
REQUIRE_DESCRIPTION = True
MIN_DESCRIPTION_CHARS = 120

COUNTRY = "be"

# Termes de recherche pour récupérer large côté API
# --> orientés Cloud / SysAdmin / DevOps junior-friendly
SEARCH_TERMS = [
    # cœur DevOps / Cloud
    "devops",
    "devops engineer",
    "junior devops",
    "cloud",
    "cloud engineer",
    "junior cloud engineer",
    "cloud operations",
    "cloud operations engineer",
    "cloud support",
    "cloud support engineer",
    "platform engineer",
    "site reliability engineer",
    "sre",
    "linux engineer",
    "linux system engineer",
    "linux system administrator",
    "system administrator",
    "systems administrator",
    "systems engineer",
    "infrastructure engineer",
    "infrastructure specialist",
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
    "kubernetes",
    "docker",
]

# pondération des termes pour le scoring
PRIORITY_TERMS = {
    "cloud support": 6,             # priorité max pour toi
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

# annonces pas plus vieilles que 15 jours
MAX_DAYS_OLD = 15

# on élargit à toute la Belgique, mais filtrée par grandes villes
ALLOWED_LOCATIONS_KEYWORDS = [
    "Brussels",
    "Bruxelles",
    "Wallonia",
    "Wallonie",
    "Liege",
    "Liège",
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
    "Mechelen",
    "Malines",
    "Kortrijk",
]

# on filtre ce qu'on ne veut PAS:
# - postes trop seniors
# - jobs où le néerlandais est clairement exigé
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

    # FR - années d'expérience
    "au moins 3 ans",
    "au moins 4 ans",
    "au moins 5 ans",
    "min. 3 ans",
    "min. 4 ans",
    "min. 5 ans",
    "minimum 3 ans d'expérience",
    "minimum 4 ans d'expérience",
    "minimum 5 ans d'expérience",
    "plusieurs années d'expérience",

    # FR - profils confirmés / seniors
    "expérience confirmée",
    "expérience significative",
    "expérience solide",
    "expérience approfondie",
    "profil confirmé",
    "profil senior",

    # contracting & consulting senior roles
    "freelance",
    "independent consultant",
    "consultant senior",
    "consulting lead",

    # red flags de séniorité / ownership
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
    "expérience en data center",
    "data center européen",
    "migration des infrastructures",
    "migrate infrastructure",
    "strong experience",
    "solide experience",
    "3 à 5 ans",
    "3-5 years",
    "5 ans",
    "5 years",
    "advanced knowledge",
    "in-depth knowledge",
    "deep knowledge",
    "broad experience",

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
    "zeer goede connaissance du néerlandais",
    "zeer goede connaissance du neerlandais",
    "zeer goede kennis nederlands",
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

    # hors scope embarqué / vidéo / test logiciel pur
    "embedded",
    "embedded software",
    "firmware",
    "hardware",
    "video engineer",
    "software test engineer",
    "rail traffic data",
]

# ==== filtres de type de rôle (optimisés pour ton profil) ====

# Rôles qu'on considère pertinents pour toi après DevOps + AZ-400 + Master ULB
ROLE_REQUIRED_KEYWORDS = [
    # cœur Cloud / Infra / DevOps
    "devops",
    "devops engineer",
    "cloud engineer",
    "cloud support",
    "cloud support engineer",
    "cloud operations",
    "cloud operations engineer",
    "cloud operations specialist",
    "platform engineer",
    "site reliability engineer",
    "sre",

    # Linux / systèmes
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

    # Observabilité / pipelines / automation
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

    # DevSecOps / sécurité liée à l’infra (facultatif mais OK)
    "devsecops",
    "security operations",
]

# Rôles à exclure : non-tech, commerciaux, data/ML/AI, dev pur, automation industrielle
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

    # qualité/systèmes non infra
    "quality & systems",
    "ingénieur qualité",

    # sécurité très pointue
    "cyber security specialist",
    "mergers & acquisitions",
    "m&a",

    # L3 / niveaux élevés
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

    # rôles support / coord / qualité (non tech)
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

    # développement pur (pas DevOps/System)
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
