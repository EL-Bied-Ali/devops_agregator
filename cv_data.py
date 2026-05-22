"""CV content — edit this to update your resume."""

CV = {
    "name": "Ali EL Bied",
    "title": "DevOps Engineer — Linux · CI/CD · Cloud · Automation",
    "email": "Ali.el.bied9898@gmail.com",
    "phone": "+32 470 24 10 80",
    "location": "Brussels, Belgium",
    "github": "github.com/EL-Bied-Ali",
    "github_url": "https://github.com/EL-Bied-Ali",
    "linkedin": "LinkedIn",
    "linkedin_url": "https://www.linkedin.com/in/ali-el-bied-5a93a1226/",
    "photo": "data/photo.jpg",

    "profile": (
        "DevOps Engineer with hands-on experience in Linux, CI/CD, cloud infrastructure, automation, "
        "and containerized environments. Built practical projects using Azure, Terraform, Bicep, Ansible, "
        "Docker, Jenkins, and Git-based workflows. Holder of the Microsoft AZ-400 certification. "
        "Completed an intensive DevOps training program at Bruxelles Formation, open to sponsorship."
    ),

    "experience": [
        {
            "company": "Zeliq",
            "role": "QA Automation Intern (Remote)",
            "period": "01/2025 – 06/2025",
            "location": "Paris, France",
            "bullets": [
                "Built and maintained automated E2E test suites (Playwright) integrated into GitHub Actions CI pipelines and containerized for consistent execution.",
                "Integrated test execution into CI (GitHub Actions) and containerized runs for consistency.",
            ],
        },
        {
            "company": "Bruxelles Formation",
            "role": "DevOps Engineer Training Program",
            "period": "11/2025 – 05/2026",
            "location": "Brussels",
            "bullets": [
                "Intensive hands-on training focused on Linux administration, Azure cloud infrastructure, containerization, CI/CD pipelines, and infrastructure automation.",
                "Designed and deployed a secure Azure network baseline (VNet, public/private subnets, NSG) with controlled access and segmentation.",
                "Provisioned Linux VMs using Infrastructure as Code (Bicep / Terraform) and applied repeatable deployment patterns.",
                "Automated Linux configuration and Docker provisioning using Ansible roles and playbooks, ensuring secure and repeatable deployments.",
                "Set up a private container registry (Azure Container Registry) and deployed containerized apps in cloud environments.",
                "Implemented CI/CD workflows using Jenkins and Azure DevOps concepts for automated build and deployment pipelines.",
            ],
        },
    ],

    "skills": [
        ("Programming / Scripting", "Python, Bash"),
        ("CI/CD / Version Control", "Git, GitHub Actions, Jenkins, Azure DevOps"),
        ("Operating Systems / Infrastructure", "Linux (Debian/Ubuntu), systemd, networking fundamentals (TCP/IP, DNS, firewalling), VM-based environments"),
        ("Containers / Orchestration", "Docker, Docker Compose, Kubernetes (Kind)"),
        ("Cloud / IaC", "Azure, Azure CLI, Bicep, Terraform"),
        ("Automation", "Ansible"),
        ("Security / Hardening", "RBAC, Managed Identity, Key Vault integration, private networking (Private Endpoint / Private DNS), UFW, fail2ban, unattended upgrades"),
        ("Databases / Data Services", "PostgreSQL, SQLite"),
    ],

    "languages": [
        ("French", "Fluent"),
        ("English", "Professional working proficiency"),
        ("Arabic", "Fluent"),
    ],

    "education": [
        {
            "degree": "M.Sc. in Computer Science",
            "school": "Université libre de Bruxelles (ULB)",
            "period": "09/2019 – 08/2025",
            "location": "Brussels, Belgium",
            "bullets": [
                "Thesis: Neural Architecture Search with Reinforcement Learning (REINFORCE), early stopping (LSTM) and weight sharing. Applied experimentation, model optimization, and reproducible research workflows.",
            ],
        },
    ],

    "certificates": [
        {
            "name": "Microsoft Certified: DevOps Engineer Expert: AZ-400 (May 2026)",
            "issuer": None,
            "detail": "AZ-400: Designing and Implementing Microsoft DevOps Solutions",
        },
        {
            "name": "Professional Training Certificate — DevOps Engineer",
            "issuer": "Bruxelles Formation",
            "detail": None,
        },
    ],

    "projects": [
        {
            "name": "Azure Secure Infrastructure Baseline",
            "tech": "Bicep, Azure CLI",
            "bullets": [
                "Designed and deployed a modular Azure infrastructure baseline (network, compute, SQL) using environment-aware Bicep modules.",
                "Implemented secure-by-default controls: Managed Identity, RBAC, Key Vault secret access, and private SQL connectivity (Private Endpoint / Private DNS).",
            ],
        },
        {
            "name": "Azure Docker Platform Automation",
            "tech": "Ansible, Azure, Docker Compose",
            "bullets": [
                "Built role-based Ansible automation for Azure provisioning, OS hardening, Docker setup, and containerized application deployment.",
                "Used dynamic Azure inventory and post-deployment health checks to improve repeatability and operational reliability.",
            ],
        },
        {
            "name": "ChronoPlan: Planning & Project Control SaaS",
            "tech": "Streamlit, Python, SQLite",
            "bullets": [
                "Built a planning and project control web app for construction-style workflows (WBS, progress tracking, S-curves, Excel-driven inputs).",
                "Implemented product-oriented features including authentication, usage/premium logic, caching, and operational data handling.",
                "Focused on reliability, structured code organization, and operational considerations for ongoing commercialization.",
            ],
        },
        {
            "name": "Kubernetes Multi-Tier Platform on Kind",
            "tech": "Kubernetes, Kind, PostgreSQL, HPA",
            "bullets": [
                "Designed and deployed a multi-tier Kubernetes platform (frontend, backend, PostgreSQL, gateway) on Kind using modular manifests.",
                "Implemented persistent storage (PV/PVC), namespace separation, and autoscaling (HPA) for local integration testing.",
            ],
        },
        {
            "name": "Terraform Cloud Patterns with LocalStack",
            "tech": "Terraform, LocalStack, Docker Compose, AWS CLI",
            "bullets": [
                "Refactored Terraform assets into reusable blueprints/scenarios to improve maintainability and onboarding.",
                "Built LocalStack-based workflows for faster local Terraform testing.",
            ],
        },
    ],
}
