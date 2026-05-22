import os

# API keys are loaded from config_secrets.py (not tracked) or environment variables.
try:
    from config_secrets import ADZUNA_APP_ID, ADZUNA_APP_KEY, JOOBLE_API_KEY  # type: ignore
except ImportError:
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
    JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")

# Keep provider credentials optional at import time.
# Some markets rely on HTML providers instead of Adzuna/Jooble.
if JOOBLE_API_KEY is None:
    JOOBLE_API_KEY = ""


def has_adzuna_credentials() -> bool:
    return bool(ADZUNA_APP_ID and ADZUNA_APP_KEY)


def require_adzuna_credentials():
    if not has_adzuna_credentials():
        raise RuntimeError("Missing Adzuna API credentials. Set env vars or config_secrets.py")


def has_jooble_credentials() -> bool:
    return bool(JOOBLE_API_KEY)


def require_jooble_credentials():
    if not has_jooble_credentials():
        raise RuntimeError("Missing Jooble API credentials. Set env vars or config_secrets.py")

# Supported market modes
DEFAULT_MARKET = "be"
SUPPORTED_MARKETS = ("be", "ch", "ma", "nl", "de", "fr", "gb", "ie", "ae")
DEFAULT_CH_FOCUS = "all"
SUPPORTED_CH_FOCUS = ("all", "romandie")
DEFAULT_FILTER_MODE = "strict"
SUPPORTED_FILTER_MODES = ("strict", "broad", "both")
DEFAULT_JOB_MODE = "strict"
SUPPORTED_JOB_MODES = ("strict", "speed")

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

# Termes de recherche pour recuperer large cote API
# --> orientes Cloud / SysAdmin / DevOps junior-friendly
SEARCH_TERMS = [
    "devops",
    "junior devops",
    "cloud engineer",
    "junior cloud engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "systems engineer",
    "system engineer",
    "systems administrator",
    "system administrator",
    "linux system administrator",
    "junior linux administrator",
    "windows system administrator",
    "endpoint administrator",
    "intune administrator",
    "infrastructure engineer",
    "it operations engineer",
    "operations engineer",
    "production support engineer",
    "application support engineer",
    "cloud support engineer",
    "ci/cd",
    "release engineer",
    "build engineer",
    "terraform",
    "ansible",
    "kubernetes",
    "docker",
    "azure",
    "azure administrator",
    "azure engineer",
    "test automation engineer",
    "qa automation engineer",
    # Titres métiers en pénurie BE/FR (liste officielle Actiris + arrêté FR 2025)
    "administrateur systemes",
    "administrateur systèmes",
    "administrateur reseau",
    "administrateur réseau",
    "gestionnaire exploitation informatique",
    "technicien exploitation informatique",
    "ingenieur exploitation informatique",
    "ingenieur production informatique",
    "technicien systemes reseaux",
    "technicien systèmes réseaux",
    "technicien reseau",
    "ingenieur systemes reseaux",
    "gestionnaire reseau",
    "chargé exploitation informatique",
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
BE_ALLOWED_LOCATIONS_KEYWORDS = [
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

# Suisse: inclut les cantons/villes FR + hubs nationaux + remote.
CH_ALLOWED_LOCATIONS_KEYWORDS = [
    "Switzerland",
    "Suisse",
    "Schweiz",
    "Svizzera",
    "Geneva",
    "Geneve",
    "Vaud",
    "Lausanne",
    "Neuchatel",
    "Jura",
    "Fribourg",
    "Freiburg",
    "Valais",
    "Wallis",
    "Sion",
    "Nyon",
    "Montreux",
    "Yverdon",
    "Biel",
    "Bienne",
    "Bern",
    "Berne",
    "Basel",
    "Bale",
    "Zurich",
    "Luzern",
    "Lucerne",
    "Zug",
    "Winterthur",
    "Lugano",
    "Remote",
    "Teletravail",
    "Telework",
    "Work from home",
]

CH_ROMANDIE_ALLOWED_LOCATIONS_KEYWORDS = [
    "Switzerland",
    "Suisse",
    "Schweiz",
    "Geneva",
    "Geneve",
    "Genf",
    "Vaud",
    "Waadt",
    "Lausanne",
    "Neuchatel",
    "Neuenburg",
    "Jura",
    "Jura bernois",
    "Berner Jura",
    "Fribourg",
    "Freiburg",
    "Valais",
    "Wallis",
    "Sion",
    "Nyon",
    "Montreux",
    "Yverdon",
    "Bienne",
    "Le Mont-sur-Lausanne",
    "Morges",
    "Gland",
    "Renens",
    "Prilly",
    "Ecublens",
    "Écublens",
    "Chavannes-pres-Renens",
    "Chavannes-près-Renens",
    "Preverenges",
    "Préverenges",
    "Carouge",
    "Lancy",
    "Versoix",
    "Meyrin",
    "Aclens",
    "Ouest Lausannois",
    "Riviera-Pays-d'Enhaut",
    "Saane",
    "Gros-de-Vaud",
    "Lavaux-Oron",
    "Broye-Vully",
    "Glane",
    "Veveyse",
    "Jura-Nord vaudois",
    "Aigle",
    "Villars-sur-Glane",
    "Villars-sur-Glâne",
    "Granges-Paccot",
    "Franches-Montagnes",
    "Delemont",
    "Delémont",
    "Martigny",
    "Monthey",
    "Conthey",
    "Herens",
    "Remote",
    "Teletravail",
    "Telework",
    "Work from home",
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

    # contracting & consulting senior roles
    "freelance",
    "independent consultant",
    "consultant senior",
    "consulting lead",

    # red flags de seniorite / ownership
    "end-to-end responsibility",
    "strategic mindset",
    "make architectural decisions",
    "design scalable systems",
    "design cloud solutions",

    # signaux de postes infra seniors / data center (hors experience explicite)
    "experience in data center",
    "experience en data center",
    "data center europeen",
    "migration des infrastructures",
    "migrate infrastructure",

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

    # hors scope embarque / video / test logiciel pur
    "embedded",
    "embedded software",
    "firmware",
    "hardware",
    "video engineer",
    "software test engineer",
    "rail traffic data",
    # Non-IT physical infrastructure (Veolia-type environmental/waste roles)
    "landfill",
    "wastewater treatment",
    "sewage treatment",
    "waste water treatment",
    # Companies with no EU offices posting on EU job boards (Air Apps: Lisbon+SF only)
    # These remote jobs won't lead to a DE/NL/FR/GB work visa
    "lisbon and san francisco",
    "offices in both lisbon",
    # US defense contractors (Booz Allen Hamilton type) — require US gov clearance
    "u.s. federal government",
    "us federal government",
    "cross domain solution",
    "cross domain solutions",
    "government clearance",
]

# Experience is handled separately from EXCLUDE_KEYWORDS to avoid over-blocking.
EXPERIENCE_SOFT_BLOCK_PHRASES = [
    "2+ years",
    "2 years experience",
    "min 2 years",
    "minimum 2 years",
    "at least 2 years",
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
    "au moins 2 ans",
    "au moins 3 ans",
    "au moins 4 ans",
    "min. 2 ans",
    "min. 3 ans",
    "min. 4 ans",
    "minimum 2 ans d'experience",
    "minimum 3 ans d'experience",
    "minimum 4 ans d'experience",
    "experience confirmee",
    "experience significative",
    "experience solide",
    "profil confirme",
    "3 a 5 ans",
    "3-5 years",
    "strong experience",
    "solide experience",
    "advanced knowledge",
    "in-depth knowledge",
    "deep knowledge",
    "broad experience",
]

EXPERIENCE_HARD_BLOCK_PHRASES = [
    "5+ years",
    "5 years experience",
    "min 5 years",
    "minimum 5 years",
    "at least 5 years",
    "6+ years",
    "7+ years",
    "8+ years",
    "10+ years",
    "au moins 5 ans",
    "min. 5 ans",
    "minimum 5 ans d'experience",
    "5 ans",
    "5 years",
    "experience approfondie",
    "profil senior",
    "expert level",
    "senior only",
    "many years of experience",
    "extensive experience",
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
    # "graduate program" removed — too generic (matches Picnic Analytics, finance grad programs, etc.)
    # training_program_relevant() handles this with IT-content verification
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
    # Graduate programs non-IT
    "java graduate",
    "java academy",
    "analytics graduate",
    "business analytics graduate",
    "supply chain graduate",
    "supply chain engineering",
    # Mid-level explicit (senior déguisé)
    "as a mid level",
    "as a mid-level",
    "as a midlevel",
    "mid-level engineer",
    "mid level engineer",
    "seeking a mid",
    "we need a mid",
    "looking for a mid",
    "confirmed engineer",
    "ingenieur confirme",
    # Consumer electronics / power tools (ex: TTI/Milwaukee Tool)
    "power tools",
    "cordless technology",
    "floorcare",
    # Coding bootcamps / training programs (not DevOps roles)
    "coding trainee",
    "programming trainee",
    "coding apprentice",
    "bootcamp trainee",
    # Non-IT graduate roles that slip through keyword matching
    "ecologist",
    "hotel management",
    "aquatic",
    "health, safety",
    "health safety",
    "wellbeing graduate",
    "management graduate programme",
    # Java developer / Java QA (not DevOps)
    "java automation",
    "java automation engineer",
    # Pay-to-train schemes ("job guaranteed" = you pay for training then they place you)
    "job guaranteed",
    "launch your cyber security career",
    "career programme",

    # QA fonctionnel, testeur non infra

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

# Optional widening mode for faster job search throughput.
SPEED_ROLE_TARGETS = [
    "system administrator",
    "systems administrator",
    "system admin",
    "sysadmin",
    "junior sysadmin",
    "cloud support",
    "cloud support engineer",
    "platform support",
    "platform support engineer",
    "application support",
    "application support engineer",
    "release engineer",
    "build engineer",
    "test automation",
    "test automation engineer",
    "qa automation",
    "qa automation engineer",
    "endpoint administrator",
    "endpoint admin",
    "intune",
    "entra",
    "m365",
    "microsoft 365",
]

BE_BLOCKED_LANGUAGE_CODES = ["nl", "de"]
BE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS = [
    "dutch required",
    "dutch mandatory",
    "native dutch",
    "native level dutch",
    "near-native dutch",
    "near native dutch",
    "native level or near-native level dutch",
    "fluent dutch",
    "excellent dutch",
    "must speak dutch",
    "only open to native",
    "native level or near-native",
    "proficient in dutch",
    "excellent proficiency in both dutch",
    "proficiency in both dutch",
    "native and dutch",
    "nederlands vereist",
    "nederlands verplicht",
    "moedertaal nederlands",
    "goede kennis nederlands",
    "perfect nederlands",
    "neerlandais obligatoire",
    "neerlandais requis",
    "german required",
    "german mandatory",
    "must speak german",
    "deutsch erforderlich",
    "german english speaking",
    "german & english speaking",
    "allemand obligatoire",
    "allemand requis",
]

CH_BLOCKED_LANGUAGE_CODES = ["de", "it", "nl"]
CH_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS = BE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS + [
    "german required",
    "german mandatory",
    "native german",
    "fluent german",
    "excellent german",
    "must speak german",
    "italian required",
    "italian mandatory",
    "native italian",
    "fluent italian",
    "excellent italian",
    "must speak italian",
    "allemand obligatoire",
    "allemand requis",
    "allemand courant",
    "italien obligatoire",
    "italien requis",
    "italien courant",
    "deutsch erforderlich",
    "deutschkenntnisse erforderlich",
    "fliessend deutsch",
    "verhandlungssicher deutsch",
    "schweizerdeutsch",
    "german & english",
    "german and english",
    "must have german",
    "deutsch und englisch",
    "deutsch & englisch",
    "german speaker",
    "italienisch erforderlich",
    "italienischkenntnisse erforderlich",
    "tedesco obbligatorio",
    "tedesco richiesto",
]

# Suisse: strategie "find job fast" pour profil junior/entry infra-cloud.
CH_SEARCH_TERMS = [
    "junior system administrator",
    "system administrator",
    "linux system administrator",
    "systems administrator",
    "network administrator",
    "network engineer",
    "administrateur systeme",
    "administrateur reseau",
    "ingenieur systeme",
    "ingenieur reseau",
    "it support",
    "it support specialist",
    "technical support engineer",
    "support informatique",
    "technicien support",
    "helpdesk it",
    "service desk",
    "service desk engineer",
    "application support engineer",
    "test automation engineer",
    "qa automation engineer",
    "build engineer",
    "release engineer",
    "ict system engineer",
    "it infrastructure specialist",
    "infrastructure support",
    "platform support engineer",
    "cloud support",
    "cloud support engineer",
    "cloud operations",
    "it operations",
    "operations engineer",
    "junior cloud engineer",
    "cloud engineer",
    "devops",
    "devops engineer",
    "junior devops",
    "site reliability engineer",
    "sre",
    "it trainee",
    "it intern",
    "stage informatique",
    "it graduate program",
    "graduate programme digital and it",
    "technology graduate program",
    "entry level it support",
    "junior it support",
]

MA_SEARCH_TERMS = [
    "devops",
    "devops engineer",
    "cloud engineer",
    "platform engineer",
    "system administrator",
    "systems administrator",
    "linux administrator",
    "linux system administrator",
    "infrastructure engineer",
    "systems engineer",
    "system engineer",
    "network engineer",
    "network administrator",
    "it support",
    "technical support",
    "application support",
    "operations engineer",
    "it operations",
    "cloud support",
    "automation engineer",
    "administrateur systeme",
    "administrateur systèmes",
    "administrateur reseau",
    "administrateur réseau",
    "ingenieur systeme",
    "ingénieur système",
    "ingenieur infrastructure",
    "ingénieur infrastructure",
    "support informatique",
    "technicien support",
]

MA_ROLE_REQUIRED_KEYWORDS = [
    "devops",
    "devops engineer",
    "cloud engineer",
    "cloud support",
    "cloud support engineer",
    "cloud operations",
    "platform engineer",
    "system administrator",
    "systems administrator",
    "linux system administrator",
    "linux administrator",
    "system engineer",
    "systems engineer",
    "infrastructure engineer",
    "network engineer",
    "network administrator",
    "support informatique",
    "it support",
    "technical support",
    "support technique",
    "service desk",
    "helpdesk",
    "help desk",
    "application support",
    "technicien support",
    "technicien it",
    "technicien informatique",
    "technicien en informatique",
    "technicien support informatique",
    "technicien reseau informatique",
    "technicien en reseaux informatiques",
    "technicien si",
    "techniciens si",
    "technicien informaticien",
    "informaticien",
    "it support specialist",
    "ingenieur systemes d information",
    "systemes d information",
    "software engineer",
    "software developer",
    "full stack",
    "fullstack",
    "backend developer",
    "backend engineer",
    "frontend developer",
    "web developer",
    "developpeur full stack",
    "developpeur backend",
    "developpeur frontend",
    "concepteur developpeur",
    "java developer",
    "python developer",
    "dotnet developer",
    ".net developer",
    "data engineer",
    "data analyst",
    "business intelligence",
    "bi developer",
    "power bi",
    "data scientist",
    "machine learning",
    "ai engineer",
    "ingenieur ia",
    "qa engineer",
    "qa tester",
    "test engineer",
    "test analyst",
    "test automation",
    "automation qa",
]

MA_ROLE_FORBIDDEN_KEYWORDS = ROLE_FORBIDDEN_KEYWORDS + [
    "ingenieur commercial",
    "commercial it",
    "avant-vente",
    "avant vente",
    "proxy product owner",
    "product owner",
    "support applicatif",
    "application support analyst",
    "conseiller de clientele",
    "customer care",
    "customer service",
    "charge d'affaires",
    "assistante administrative",
    "administrative et commerciale",
    "administration et data analyse",
    "data analyse",
    "responsable paie",
    "testeur informatique",
    "test analyst",
    "qa tester",
    "qa analyst",
    "qos analyst",
    "test automatise",
]

CH_ROLE_REQUIRED_KEYWORDS = [
    "devops",
    "devops engineer",
    "junior devops",
    "cloud engineer",
    "junior cloud engineer",
    "cloud support",
    "cloud support engineer",
    "cloud operations",
    "platform engineer",
    "site reliability engineer",
    "sre",
    "system administrator",
    "systems administrator",
    "network administrator",
    "administrateur reseau",
    "network engineer",
    "ingenieur reseau",
    "linux system administrator",
    "linux administrator",
    "linux admin",
    "infrastructure engineer",
    "infrastructure support",
    "it operations",
    "operations engineer",
    "it support",
    "test automation engineer",
    "qa automation engineer",
    "build engineer",
    "release engineer",
    "ict system engineer",
    "it infrastructure specialist",
    "technical support engineer",
    "support engineer",
    "support informatique",
    "helpdesk",
    "service desk",
    "application support",
    "platform support",
    "network support",
    "it trainee",
    "it intern",
    "stage informatique",
    "it specialist",
    "computer scientist",
    "application support engineer",
    "network operations engineer",
    "security operations engineer",
]

CH_ROLE_FORBIDDEN_KEYWORDS = [
    "global mobility",
    "audit",
    "financial accounting",
    "civil infrastructure",
    "planificateur",
    "dessinateur",
    "applied ai",
    "ai platform",
    "electrical reference",
    "relocation to sofia",
    "bulgaria",
    "developpeur web",
    "developpeuse web",
    "developpeur full stack",
    "developpeuse full stack",
    "developpeur fullstack",
    "developpeuse fullstack",
    "developpeur frontend",
    "developpeuse frontend",
    "developpeur front end",
    "developpeuse front end",
    "developpeur backend",
    "developpeuse backend",
    "integrateur web",
]

CH_EXCLUDE_KEYWORDS = [
    "civil infrastructure",
    "planificateur",
    "dessinateur",
    "developpeur web",
    "developpeuse web",
    "developpeur full stack",
    "developpeuse full stack",
    "developpeur fullstack",
    "developpeuse fullstack",
    "integrateur web",
    "apprenticeship",
    "apprentissage",
    "apprenti",
    "cfc",
    "formateur",
    "trainer",
]

CH_EXTRA_BAD_TITLE_KEYWORDS = [
    "sr ",
    " sr ",
]

CH_BLOCKED_LOCATION_KEYWORDS = [
    "zurich",
    "zuerich",
    "zug",
    "bern",
    "berne",
    "basel",
    "bale",
    "luzern",
    "lucerne",
    "winterthur",
    "st. gallen",
    "sankt gallen",
]

CH_FOREIGN_LOCATION_KEYWORDS = [
    "germany",
    "deutschland",
    "france",
    "belgium",
    "belgique",
    "netherlands",
    "nederland",
    "austria",
    "osterreich",
    "italy",
    "italia",
    "spain",
    "portugal",
    "poland",
    "romania",
    "bulgaria",
    "united kingdom",
    "uk",
    "england",
    "usa",
    "united states",
    "canada",
]

MA_ALLOWED_LOCATIONS_KEYWORDS = [
    "Morocco",
    "Maroc",
    "Casablanca",
    "Casablanca-Mohammedia",
    "Rabat",
    "Rabat-Sale-Kenitra",
    "Rabat-Salé-Kénitra",
    "Marrakech",
    "Marrakech-Safi",
    "Agadir",
    "Souss-Massa",
    "Tanger",
    "Tangier",
    "Tanger-Tetouan-Al Hoceima",
    "Tanger-Tétouan-Al Hoceïma",
    "Tetouan",
    "Tétouan",
    "Kenitra",
    "Kénitra",
    "Fes",
    "Fès",
    "Fès-Meknès",
    "Meknes",
    "Meknès",
    "Oujda",
    "Oriental",
    "El Jadida",
    "Settat",
    "Mohammedia",
    "Bouskoura",
    "Benguerir",
    "Temara",
    "Témara",
    "Salé",
    "Nador",
    "Remote",
    "Teletravail",
    "Télétravail",
    "Hybrid",
]

# Netherlands: grandes villes + remote
NL_ALLOWED_LOCATIONS_KEYWORDS = [
    "Netherlands",
    "Nederland",
    "Amsterdam",
    "Rotterdam",
    "The Hague",
    "Den Haag",
    "Utrecht",
    "Eindhoven",
    "Tilburg",
    "Groningen",
    "Almere",
    "Breda",
    "Nijmegen",
    "Enschede",
    "Apeldoorn",
    "Haarlem",
    "Leiden",
    "Delft",
    "Maastricht",
    "Arnhem",
    "Remote",
    "Hybrid",
    "Work from home",
]

# Germany: hubs tech principaux + remote
DE_ALLOWED_LOCATIONS_KEYWORDS = [
    "Germany",
    "Deutschland",
    "Berlin",
    "Munich",
    "München",
    "Frankfurt",
    "Hamburg",
    "Cologne",
    "Köln",
    "Stuttgart",
    "Düsseldorf",
    "Dusseldorf",
    "Leipzig",
    "Dortmund",
    "Nuremberg",
    "Nürnberg",
    "Hannover",
    "Bremen",
    "Dresden",
    "Bonn",
    "Mannheim",
    "Karlsruhe",
    "Freiburg",
    "Remote",
    "Hybrid",
    "Work from home",
    "Home office",
]

# Netherlands: termes de recherche — postes cloud/devops anglophones
NL_SEARCH_TERMS = [
    "devops engineer",
    "devops",
    "junior devops",
    "cloud engineer",
    "junior cloud engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "system administrator",
    "linux system administrator",
    "infrastructure engineer",
    "it operations engineer",
    "cloud support engineer",
    "cloud operations",
    "automation engineer",
    "build engineer",
    "release engineer",
    "kubernetes engineer",
    "azure engineer",
    "azure administrator",
    "cloud graduate",
    "it graduate",
    "graduate program",
]

# Germany: termes de recherche — postes cloud/devops anglophones, EU Blue Card friendly
DE_SEARCH_TERMS = [
    "devops engineer",
    "devops",
    "junior devops",
    "cloud engineer",
    "junior cloud engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "system administrator",
    "linux system administrator",
    "infrastructure engineer",
    "it operations engineer",
    "cloud support engineer",
    "cloud operations engineer",
    "automation engineer",
    "build engineer",
    "release engineer",
    "kubernetes engineer",
    "azure engineer",
    "azure administrator",
    "cloud graduate",
    "it graduate",
    "graduate program",
]

# Netherlands: filtre langue — bloquer les annonces exigeant le neerlandais
NL_BLOCKED_LANGUAGE_CODES = ["nl", "de"]
NL_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS = BE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS

# Germany: filtre langue — bloquer les annonces exigeant l'allemand
DE_BLOCKED_LANGUAGE_CODES = ["de"]
DE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS = [
    "german required",
    "german mandatory",
    "must speak german",
    "native german",
    "fluent german",
    "excellent german",
    "german speaker",
    "german and english",
    "german & english",
    "must have german",
    "deutsch erforderlich",
    "deutschkenntnisse erforderlich",
    "fliessend deutsch",
    "verhandlungssicher deutsch",
    "muttersprachliche deutschkenntnisse",
    "c1 deutsch",
    "c2 deutsch",
    "alemand obligatoire",
    "allemand requis",
    "allemand obligatoire",
    "allemand courant",
]

# Signaux de sponsorship dans les offres
SPONSORSHIP_POSITIVE_PHRASES = [
    "visa sponsorship",
    "sponsorship provided",
    "we sponsor",
    "will sponsor",
    "work permit sponsorship",
    "relocation package",
    "relocation support",
    "relocation assistance",
    "relocation budget",
    "relocation provided",
    "we support relocation",
    "international candidates welcome",
    "international candidates encouraged",
    "open to candidates from abroad",
    "open to international",
    "global talent",
    "employer sponsorship",
    "permit sponsorship",
    "we provide sponsorship",
    "happy to sponsor",
    "sponsoring the visa",
    "work authorization supported",
]

SPONSORSHIP_NEGATIVE_PHRASES = [
    "no sponsorship",
    "no visa sponsorship",
    "cannot sponsor",
    "cannot offer visa sponsorship",
    "role cannot offer visa sponsorship",
    "this role cannot offer",
    "unable to sponsor",
    "unable to offer sponsorship",
    "not in a position to sponsor",
    "not providing sponsorship",
    "not providing relocation sponsorship",
    "not able to provide sponsorship",
    "not offering sponsorship",
    "we cannot offer",
    "sponsorship not available",
    "no work permit",
    "eu passport required",
    "eu citizenship required",
    "eu citizens only",
    "eu residents only",
    "must have right to work",
    "already authorized to work",
    "must be authorized to work",
    "no relocation assistance",
    "no relocation support",
    "no relocation budget",
    # UK-specific
    "uk national",
    "must be a uk national",
    "must be uk based",
    "must live within",
    # Work authorization (no sponsorship implied)
    "existing work authorization",
    "existing eu work authorization",
    "existing netherlands work authorization",
    "right to work in",
    "work authorization required",
    "only candidates with existing",
    # Typo variants common in job descriptions
    "sponsership is not provided",
    "sponsership not provided",
    "no sponsership",
    "sponsorship is not provided",
    "sponsoring is not provided",
]

# =============================================================
# FRANCE — Passeport Talent (>1,5x SMIC, ~€2700/mois)
# =============================================================
FR_ALLOWED_LOCATIONS_KEYWORDS = [
    "France",
    "Paris",
    "Lyon",
    "Bordeaux",
    "Toulouse",
    "Marseille",
    "Nantes",
    "Strasbourg",
    "Montpellier",
    "Lille",
    "Grenoble",
    "Nice",
    "Rennes",
    "Sophia-Antipolis",
    "Sophia Antipolis",
    "Île-de-France",
    "Ile-de-France",
    "La Défense",
    "La Defense",
    "Massy",
    "Vélizy",
    "Velizy",
    "Meudon",
    "Puteaux",
    "Neuilly",
    "Levallois",
    "Courbevoie",
    "Boulogne",
    "Issy",
    "Clichy",
    "Aix-en-Provence",
    "Aix en Provence",
    "Sophia",
    "Remote",
    "Teletravail",
    "Télétravail",
    "Hybrid",
    "Hybride",
]

FR_SEARCH_TERMS = [
    # English terms (indexed on French boards too)
    "devops engineer",
    "devops",
    "junior devops",
    "cloud engineer",
    "junior cloud engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "system administrator",
    "linux system administrator",
    "infrastructure engineer",
    "cloud support engineer",
    "cloud operations",
    "automation engineer",
    "build engineer",
    "release engineer",
    "azure engineer",
    "azure administrator",
    # French terms
    "ingenieur devops",
    "ingenieur cloud",
    "ingenieur infrastructure",
    "administrateur systeme",
    "administrateur systemes",
    "ingenieur systeme",
    "ingenieur systemes",
    "administrateur linux",
    "ingenieur devops junior",
    "ingenieur cloud junior",
    "stagiaire devops",
    "alternant devops",
    "technicien systeme",
    "technicien infrastructure",
    # Titres pénurie officiels FR (arrêté mai 2025)
    "gestionnaire exploitation informatique",
    "technicien exploitation informatique",
    "ingenieur production informatique",
    "administrateur reseau",
    "gestionnaire reseau",
    "ingenieur systemes reseaux",
    "technicien systemes reseaux",
]

# Pour la France: pas de blocage de langue — il parle français
# Bloquer seulement habilitation défense (clearances FR)
FR_EXCLUDE_KEYWORDS = list(EXCLUDE_KEYWORDS) + [
    # Contrats étudiants — le candidat a déjà un Master, pas étudiant
    "alternance",
    "alternant",
    "stage de fin d'etudes",
    "stage de fin d etudes",
    "stage fin d'etudes",
    "stage - ",   # titres commençant par "Stage - "
    "bts sio",
    "bts informatique",
    "master 1",
    "master 2",
    "bac+3",
    "bac+4",
    "bac+5",
    # Habilitations défense (clearances FR)
    "habilitation securite",
    "habilitation de securite",
    "secret defense",
    "secret défense",
    "diffusion restreinte",
    "confidentiel defense",
    "confidentiel défense",
    "ts/sci",
]

# =============================================================
# UK (GB) — Skilled Worker Visa (employeur Home Office agréé)
# =============================================================
GB_ALLOWED_LOCATIONS_KEYWORDS = [
    "United Kingdom",
    "UK",
    "England",
    "London",
    "Manchester",
    "Edinburgh",
    "Birmingham",
    "Bristol",
    "Leeds",
    "Cambridge",
    "Oxford",
    "Sheffield",
    "Liverpool",
    "Newcastle",
    "Nottingham",
    "Reading",
    "Guildford",
    "Slough",
    "Staines",
    "Coventry",
    "Glasgow",
    "Cardiff",
    "Belfast",
    "Remote",
    "Hybrid",
    "Work from home",
]

GB_SEARCH_TERMS = [
    "devops engineer",
    "devops",
    "junior devops",
    "cloud engineer",
    "junior cloud engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "system administrator",
    "linux system administrator",
    "infrastructure engineer",
    "cloud support engineer",
    "cloud operations engineer",
    "automation engineer",
    "build engineer",
    "release engineer",
    "azure engineer",
    "azure administrator",
    "kubernetes engineer",
    "cloud graduate",
    "graduate program",
    "it graduate",
]

GB_BLOCKED_LANGUAGE_CODES = ["nl", "de"]
GB_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS = BE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS

# =============================================================
# IRELAND (IE) — Critical Skills Employment Permit
# Google, Meta, Microsoft, Amazon, Stripe EU HQ à Dublin
# =============================================================
IE_ALLOWED_LOCATIONS_KEYWORDS = [
    "Ireland",
    "Dublin",
    "Cork",
    "Galway",
    "Limerick",
    "Waterford",
    "Belfast",
    "Remote",
    "Hybrid",
]

IE_SEARCH_TERMS = GB_SEARCH_TERMS  # Même termes EN

# =============================================================
# UAE (AE) — Employment Visa (0 complexité, employeur donne le visa)
# Dubai tech scene en explosion, 0 taxes, bcp de Marocains
# =============================================================
AE_ALLOWED_LOCATIONS_KEYWORDS = [
    "United Arab Emirates",
    "UAE",
    "Dubai",
    "Abu Dhabi",
    "Sharjah",
    "Ajman",
    "Remote",
    "Hybrid",
]

AE_SEARCH_TERMS = [
    "devops engineer",
    "devops",
    "cloud engineer",
    "site reliability engineer",
    "sre",
    "platform engineer",
    "system administrator",
    "linux administrator",
    "infrastructure engineer",
    "cloud support engineer",
    "cloud operations",
    "azure engineer",
    "azure administrator",
    "kubernetes engineer",
    "automation engineer",
]

MARKET_PROFILES = {
    "be": {
        "adzuna_country": "be",
        "jooble_location": "",
        "supports_adzuna": True,
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": BE_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": BE_BLOCKED_LANGUAGE_CODES,
        "blocked_language_requirement_keywords": BE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS,
        "search_terms": SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
    "ch": {
        "adzuna_country": "ch",
        "jooble_location": "Switzerland",
        "supports_adzuna": True,
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": CH_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": CH_BLOCKED_LOCATION_KEYWORDS,
        "foreign_location_keywords": CH_FOREIGN_LOCATION_KEYWORDS,
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": CH_BLOCKED_LANGUAGE_CODES,
        "blocked_language_requirement_keywords": CH_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS,
        "search_terms": CH_SEARCH_TERMS,
        "role_required_keywords": CH_ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS + CH_ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS + CH_EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": CH_EXTRA_BAD_TITLE_KEYWORDS,
    },
    "ma": {
        "adzuna_country": "ma",
        "jooble_location": "Morocco",
        "supports_adzuna": False,
        "supports_jooble": False,
        "supports_emploi_ma": True,
        "supports_rekrute": True,
        "supports_marocannonces": True,
        "enforce_location_filter": True,
        "allowed_location_keywords": MA_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        "allowed_language_codes": ["fr", "en", "ar"],
        "blocked_language_codes": [],
        "blocked_language_requirement_keywords": [],
        "search_terms": MA_SEARCH_TERMS,
        "role_required_keywords": MA_ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": MA_ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
    "nl": {
        "adzuna_country": "nl",
        "jooble_location": "Netherlands",
        "supports_adzuna": True,
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "supports_marocannonces": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": NL_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": NL_BLOCKED_LANGUAGE_CODES,
        "blocked_language_requirement_keywords": NL_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS,
        "search_terms": NL_SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
    "de": {
        "adzuna_country": "de",
        "jooble_location": "Germany",
        "supports_adzuna": True,
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "supports_marocannonces": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": DE_ALLOWED_LOCATIONS_KEYWORDS,
        # Explicitly block jobs listed in foreign cities common on adzuna.de
        # (nearshore offices in Romania, Poland, etc. — not eligible for German visa)
        "blocked_location_keywords": [
            "Cluj", "Bucharest", "Warsaw", "Krakow", "Kraków", "Wroclaw", "Wrocław",
            "Timisoara", "Iași", "Poznań", "Poznan", "Gdansk", "Gdańsk",
            "Katowice", "Lodz", "Łódź", "Sofia", "Bratislava", "Prague",
            "Budapest", "Kyiv", "Kiev", "Belgrade", "Sarajevo",
        ],
        "foreign_location_keywords": [],
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": DE_BLOCKED_LANGUAGE_CODES,
        "blocked_language_requirement_keywords": DE_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS,
        "search_terms": DE_SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
    "fr": {
        "adzuna_country": "fr",
        "jooble_location": "France",
        "supports_adzuna": True,
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "supports_marocannonces": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": FR_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        # Français OK pour lui — pas de blocage langue
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": [],
        "blocked_language_requirement_keywords": [],
        "search_terms": FR_SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": FR_EXCLUDE_KEYWORDS,
        # "Confirmé" = intermediate/mid-level in French consulting (SSII/ESN)
        # "Expert(e)" alone in title (not "Junior Expert") = senior consultant
        "extra_bad_title_keywords": ["confirmé", "confirme", "confirmée"],
    },
    "gb": {
        "adzuna_country": "gb",
        "jooble_location": "United Kingdom",
        "supports_adzuna": True,
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "supports_marocannonces": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": GB_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": GB_BLOCKED_LANGUAGE_CODES,
        "blocked_language_requirement_keywords": GB_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS,
        "search_terms": GB_SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
    "ie": {
        "adzuna_country": "ie",
        "jooble_location": "Ireland",
        "supports_adzuna": False,  # Adzuna ne couvre pas IE — jobs Dublin inclus dans GB
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "supports_marocannonces": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": IE_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        "allowed_language_codes": ["fr", "en"],
        "blocked_language_codes": GB_BLOCKED_LANGUAGE_CODES,
        "blocked_language_requirement_keywords": GB_BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS,
        "search_terms": IE_SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
    "ae": {
        "adzuna_country": "ae",
        "jooble_location": "Dubai",
        "supports_adzuna": False,  # Adzuna ne couvre pas UAE — utiliser Bayt.com ou LinkedIn
        "supports_jooble": True,
        "supports_emploi_ma": False,
        "supports_rekrute": False,
        "supports_marocannonces": False,
        "enforce_location_filter": False,
        "allowed_location_keywords": AE_ALLOWED_LOCATIONS_KEYWORDS,
        "blocked_location_keywords": [],
        "foreign_location_keywords": [],
        # UAE: anglais dominant en tech, pas de blocage de langue
        "allowed_language_codes": ["fr", "en", "ar"],
        "blocked_language_codes": [],
        "blocked_language_requirement_keywords": [],
        "search_terms": AE_SEARCH_TERMS,
        "role_required_keywords": ROLE_REQUIRED_KEYWORDS,
        "role_forbidden_keywords": ROLE_FORBIDDEN_KEYWORDS,
        "exclude_keywords": EXCLUDE_KEYWORDS,
        "extra_bad_title_keywords": [],
    },
}


def resolve_market(market: str = "") -> str:
    raw = (market or os.getenv("JOB_MARKET") or DEFAULT_MARKET).strip().lower()
    if raw not in SUPPORTED_MARKETS:
        supported = ", ".join(SUPPORTED_MARKETS)
        raise ValueError(f"Unsupported market '{raw}'. Supported values: {supported}")
    return raw


def resolve_ch_focus(ch_focus: str = "") -> str:
    raw = (ch_focus or os.getenv("JOB_CH_FOCUS") or DEFAULT_CH_FOCUS).strip().lower()
    if raw not in SUPPORTED_CH_FOCUS:
        supported = ", ".join(SUPPORTED_CH_FOCUS)
        raise ValueError(f"Unsupported ch_focus '{raw}'. Supported values: {supported}")
    return raw


def resolve_filter_mode(filter_mode: str = "", allow_both: bool = False) -> str:
    raw = (filter_mode or os.getenv("JOB_FILTER_MODE") or DEFAULT_FILTER_MODE).strip().lower()
    allowed = SUPPORTED_FILTER_MODES if allow_both else SUPPORTED_FILTER_MODES[:2]
    if raw not in allowed:
        supported = ", ".join(allowed)
        raise ValueError(f"Unsupported filter_mode '{raw}'. Supported values: {supported}")
    return raw


def resolve_job_mode(job_mode: str = "") -> str:
    raw = (job_mode or os.getenv("JOB_MODE") or DEFAULT_JOB_MODE).strip().lower()
    if raw not in SUPPORTED_JOB_MODES:
        supported = ", ".join(SUPPORTED_JOB_MODES)
        raise ValueError(f"Unsupported job_mode '{raw}'. Supported values: {supported}")
    return raw


def get_market_profile(market: str = "", ch_focus: str = "") -> dict:
    resolved = resolve_market(market)
    resolved_ch_focus = resolve_ch_focus(ch_focus) if resolved == "ch" else "all"
    profile = MARKET_PROFILES[resolved]

    allowed_locations = list(profile["allowed_location_keywords"])
    blocked_locations = list(profile["blocked_location_keywords"])
    enforce_location_filter = bool(profile["enforce_location_filter"])
    if resolved == "ch" and resolved_ch_focus == "romandie":
        allowed_locations = list(CH_ROMANDIE_ALLOWED_LOCATIONS_KEYWORDS)
        blocked_locations = []
        enforce_location_filter = True

    return {
        "market": resolved,
        "ch_focus": resolved_ch_focus,
        "adzuna_country": profile["adzuna_country"],
        "jooble_location": profile["jooble_location"],
        "supports_adzuna": bool(profile.get("supports_adzuna", True)),
        "supports_jooble": bool(profile.get("supports_jooble", True)),
        "supports_emploi_ma": bool(profile.get("supports_emploi_ma", False)),
        "supports_rekrute": bool(profile.get("supports_rekrute", False)),
        "supports_marocannonces": bool(profile.get("supports_marocannonces", False)),
        "enforce_location_filter": enforce_location_filter,
        "allowed_location_keywords": allowed_locations,
        "blocked_location_keywords": blocked_locations,
        "foreign_location_keywords": list(profile["foreign_location_keywords"]),
        "allowed_language_codes": list(profile["allowed_language_codes"]),
        "blocked_language_codes": list(profile["blocked_language_codes"]),
        "blocked_language_requirement_keywords": list(profile["blocked_language_requirement_keywords"]),
        "search_terms": list(profile["search_terms"]),
        "role_required_keywords": list(profile["role_required_keywords"]),
        "role_forbidden_keywords": list(profile["role_forbidden_keywords"]),
        "exclude_keywords": list(profile["exclude_keywords"]),
        "extra_bad_title_keywords": list(profile["extra_bad_title_keywords"]),
    }


def get_output_paths(market: str = "") -> dict:
    resolved = resolve_market(market)
    if resolved == DEFAULT_MARKET:
        return {
            "adzuna_raw_csv": "data/adzuna_jobs_raw.csv",
            "adzuna_filtered_csv": "data/adzuna_jobs_filtered.csv",
            "adzuna_filtered_strict_csv": "data/adzuna_jobs_filtered_strict.csv",
            "adzuna_filtered_broad_csv": "data/adzuna_jobs_filtered_broad.csv",
            "emploi_ma_raw_csv": "data/emploi_ma_jobs_raw.csv",
            "emploi_ma_filtered_csv": "data/emploi_ma_jobs_filtered.csv",
            "emploi_ma_filtered_strict_csv": "data/emploi_ma_jobs_filtered_strict.csv",
            "emploi_ma_filtered_broad_csv": "data/emploi_ma_jobs_filtered_broad.csv",
            "rekrute_raw_csv": "data/rekrute_jobs_raw.csv",
            "rekrute_filtered_csv": "data/rekrute_jobs_filtered.csv",
            "rekrute_filtered_strict_csv": "data/rekrute_jobs_filtered_strict.csv",
            "rekrute_filtered_broad_csv": "data/rekrute_jobs_filtered_broad.csv",
            "marocannonces_raw_csv": "data/marocannonces_jobs_raw.csv",
            "marocannonces_filtered_csv": "data/marocannonces_jobs_filtered.csv",
            "marocannonces_filtered_strict_csv": "data/marocannonces_jobs_filtered_strict.csv",
            "marocannonces_filtered_broad_csv": "data/marocannonces_jobs_filtered_broad.csv",
            "jooble_raw_csv": "data/jooble_jobs_raw.csv",
            "jooble_filtered_csv": "data/jooble_jobs_filtered.csv",
            "jooble_filtered_strict_csv": "data/jooble_jobs_filtered_strict.csv",
            "jooble_filtered_broad_csv": "data/jooble_jobs_filtered_broad.csv",
            "merged_csv": "data/all_jobs_merged.csv",
            "merged_raw_csv": "data/all_jobs_merged_raw.csv",
            "merged_filtered_csv": "data/all_jobs_merged_filtered.csv",
            "merged_filtered_strict_csv": "data/all_jobs_merged_filtered_strict.csv",
            "merged_filtered_broad_csv": "data/all_jobs_merged_filtered_broad.csv",
            "apply_queue_csv": "data/apply_queue.csv",
            "applications_tracker_csv": "data/applications_tracker.csv",
            "daily_alert_state_json": "data/daily_alert_state.json",
            "near_miss_csv": "data/near_miss_jobs.csv",
            "term_performance_csv": "data/term_performance.csv",
        }

    prefix = f"{resolved}_"
    return {
        "adzuna_raw_csv": f"data/{prefix}adzuna_jobs_raw.csv",
        "adzuna_filtered_csv": f"data/{prefix}adzuna_jobs_filtered.csv",
        "adzuna_filtered_strict_csv": f"data/{prefix}adzuna_jobs_filtered_strict.csv",
        "adzuna_filtered_broad_csv": f"data/{prefix}adzuna_jobs_filtered_broad.csv",
        "emploi_ma_raw_csv": f"data/{prefix}emploi_ma_jobs_raw.csv",
        "emploi_ma_filtered_csv": f"data/{prefix}emploi_ma_jobs_filtered.csv",
        "emploi_ma_filtered_strict_csv": f"data/{prefix}emploi_ma_jobs_filtered_strict.csv",
        "emploi_ma_filtered_broad_csv": f"data/{prefix}emploi_ma_jobs_filtered_broad.csv",
        "rekrute_raw_csv": f"data/{prefix}rekrute_jobs_raw.csv",
        "rekrute_filtered_csv": f"data/{prefix}rekrute_jobs_filtered.csv",
        "rekrute_filtered_strict_csv": f"data/{prefix}rekrute_jobs_filtered_strict.csv",
        "rekrute_filtered_broad_csv": f"data/{prefix}rekrute_jobs_filtered_broad.csv",
        "marocannonces_raw_csv": f"data/{prefix}marocannonces_jobs_raw.csv",
        "marocannonces_filtered_csv": f"data/{prefix}marocannonces_jobs_filtered.csv",
        "marocannonces_filtered_strict_csv": f"data/{prefix}marocannonces_jobs_filtered_strict.csv",
        "marocannonces_filtered_broad_csv": f"data/{prefix}marocannonces_jobs_filtered_broad.csv",
        "jooble_raw_csv": f"data/{prefix}jooble_jobs_raw.csv",
        "jooble_filtered_csv": f"data/{prefix}jooble_jobs_filtered.csv",
        "jooble_filtered_strict_csv": f"data/{prefix}jooble_jobs_filtered_strict.csv",
        "jooble_filtered_broad_csv": f"data/{prefix}jooble_jobs_filtered_broad.csv",
        "merged_csv": f"data/{prefix}all_jobs_merged.csv",
        "merged_raw_csv": f"data/{prefix}all_jobs_merged_raw.csv",
        "merged_filtered_csv": f"data/{prefix}all_jobs_merged_filtered.csv",
        "merged_filtered_strict_csv": f"data/{prefix}all_jobs_merged_filtered_strict.csv",
        "merged_filtered_broad_csv": f"data/{prefix}all_jobs_merged_filtered_broad.csv",
        "apply_queue_csv": f"data/{prefix}apply_queue.csv",
        "applications_tracker_csv": f"data/{prefix}applications_tracker.csv",
        "daily_alert_state_json": f"data/{prefix}daily_alert_state.json",
        "near_miss_csv": f"data/{prefix}near_miss_jobs.csv",
        "term_performance_csv": f"data/{prefix}term_performance.csv",
    }


ACTIVE_MARKET_PROFILE = get_market_profile()
CH_FOCUS = ACTIVE_MARKET_PROFILE["ch_focus"]
COUNTRY = ACTIVE_MARKET_PROFILE["adzuna_country"]
JOOBLE_LOCATION = ACTIVE_MARKET_PROFILE["jooble_location"]
ALLOWED_LOCATIONS_KEYWORDS = ACTIVE_MARKET_PROFILE["allowed_location_keywords"]
ALLOWED_LANGUAGE_CODES = ACTIVE_MARKET_PROFILE["allowed_language_codes"]
BLOCKED_LANGUAGE_CODES = ACTIVE_MARKET_PROFILE["blocked_language_codes"]
BLOCKED_LANGUAGE_REQUIREMENT_KEYWORDS = ACTIVE_MARKET_PROFILE["blocked_language_requirement_keywords"]
BLOCKED_LOCATION_KEYWORDS = ACTIVE_MARKET_PROFILE["blocked_location_keywords"]
FOREIGN_LOCATION_KEYWORDS = ACTIVE_MARKET_PROFILE["foreign_location_keywords"]
SEARCH_TERMS = ACTIVE_MARKET_PROFILE["search_terms"]
ROLE_REQUIRED_KEYWORDS = ACTIVE_MARKET_PROFILE["role_required_keywords"]
ROLE_FORBIDDEN_KEYWORDS = ACTIVE_MARKET_PROFILE["role_forbidden_keywords"]
EXCLUDE_KEYWORDS = ACTIVE_MARKET_PROFILE["exclude_keywords"]
EXTRA_BAD_TITLE_KEYWORDS = ACTIVE_MARKET_PROFILE["extra_bad_title_keywords"]

ACTIVE_OUTPUT_PATHS = get_output_paths()
ADZUNA_RAW_CSV = ACTIVE_OUTPUT_PATHS["adzuna_raw_csv"]
ADZUNA_FILTERED_CSV = ACTIVE_OUTPUT_PATHS["adzuna_filtered_csv"]
ADZUNA_FILTERED_STRICT_CSV = ACTIVE_OUTPUT_PATHS["adzuna_filtered_strict_csv"]
ADZUNA_FILTERED_BROAD_CSV = ACTIVE_OUTPUT_PATHS["adzuna_filtered_broad_csv"]
JOOBLE_RAW_CSV = ACTIVE_OUTPUT_PATHS["jooble_raw_csv"]
JOOBLE_FILTERED_CSV = ACTIVE_OUTPUT_PATHS["jooble_filtered_csv"]
JOOBLE_FILTERED_STRICT_CSV = ACTIVE_OUTPUT_PATHS["jooble_filtered_strict_csv"]
JOOBLE_FILTERED_BROAD_CSV = ACTIVE_OUTPUT_PATHS["jooble_filtered_broad_csv"]
MERGED_CSV = ACTIVE_OUTPUT_PATHS["merged_csv"]
MERGED_RAW_CSV = ACTIVE_OUTPUT_PATHS["merged_raw_csv"]
MERGED_FILTERED_CSV = ACTIVE_OUTPUT_PATHS["merged_filtered_csv"]
MERGED_FILTERED_STRICT_CSV = ACTIVE_OUTPUT_PATHS["merged_filtered_strict_csv"]
MERGED_FILTERED_BROAD_CSV = ACTIVE_OUTPUT_PATHS["merged_filtered_broad_csv"]
APPLY_QUEUE_CSV = ACTIVE_OUTPUT_PATHS["apply_queue_csv"]
APPLICATIONS_TRACKER_CSV = ACTIVE_OUTPUT_PATHS["applications_tracker_csv"]
DAILY_ALERT_STATE_JSON = ACTIVE_OUTPUT_PATHS["daily_alert_state_json"]
NEAR_MISS_CSV = ACTIVE_OUTPUT_PATHS["near_miss_csv"]
TERM_PERFORMANCE_CSV = ACTIVE_OUTPUT_PATHS["term_performance_csv"]
JOB_MODE = resolve_job_mode()
