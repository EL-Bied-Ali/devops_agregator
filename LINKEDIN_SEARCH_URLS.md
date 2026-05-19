# LinkedIn Search URLs — DevOps/Cloud (NL, DE, FR, GB, IE, AE)

Check these every morning. Posted last 24h, entry-level, English-friendly companies.

---

## Netherlands (Pays-Bas) — Kennismigrant Visa Target

### DevOps / Platform / Cloud — Entry to Mid
https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Netherlands&f_TPR=r86400&f_EXP=1%2C2&f_JT=F

### Cloud Engineer — Entry Level
https://www.linkedin.com/jobs/search/?keywords=cloud+engineer&location=Netherlands&f_TPR=r86400&f_EXP=1%2C2&f_JT=F

### SRE / Platform / Infrastructure Engineer
https://www.linkedin.com/jobs/search/?keywords=site+reliability+engineer+OR+platform+engineer+OR+infrastructure+engineer&location=Netherlands&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

### Remote DevOps — Netherlands timezone
https://www.linkedin.com/jobs/search/?keywords=devops&location=Netherlands&f_TPR=r86400&f_WT=2%2C3&f_JT=F

### System Administrator / Linux Admin
https://www.linkedin.com/jobs/search/?keywords=system+administrator+OR+linux+administrator&location=Netherlands&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

---

## Germany (Allemagne) — EU Blue Card Target

### DevOps / Cloud — English language jobs in DE
https://www.linkedin.com/jobs/search/?keywords=devops+engineer&location=Germany&f_TPR=r86400&f_EXP=1%2C2&f_JT=F

### Cloud / Azure / AWS Engineer
https://www.linkedin.com/jobs/search/?keywords=cloud+engineer+azure+OR+aws&location=Germany&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

### Platform / SRE / Infrastructure
https://www.linkedin.com/jobs/search/?keywords=platform+engineer+OR+sre+OR+infrastructure+engineer&location=Germany&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

### Berlin (startup scene, most English-speaking)
https://www.linkedin.com/jobs/search/?keywords=devops+cloud&location=Berlin%2C+Germany&f_TPR=r86400&f_JT=F

### Munich (big tech, SAP, Microsoft, BMW IT)
https://www.linkedin.com/jobs/search/?keywords=devops+cloud&location=Munich%2C+Germany&f_TPR=r86400&f_JT=F

---

## France — Passeport Talent (> 1,5x SMIC, ~€2700/mois)

### DevOps / Cloud / Infra — Paris et Île-de-France
https://www.linkedin.com/jobs/search/?keywords=ingenieur+devops+OR+cloud+engineer+OR+devops+engineer&location=Paris%2C+France&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

### DevOps anglophone — toute France
https://www.linkedin.com/jobs/search/?keywords=devops+engineer+cloud&location=France&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

---

## UK — Skilled Worker Visa

### DevOps / Cloud — Londres (plus grand marché Adzuna)
https://www.linkedin.com/jobs/search/?keywords=devops+engineer+OR+cloud+engineer&location=London%2C+United+Kingdom&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

### Platform / SRE / Infrastructure — UK-wide
https://www.linkedin.com/jobs/search/?keywords=platform+engineer+OR+sre+OR+infrastructure+engineer&location=United+Kingdom&f_TPR=r86400&f_EXP=1%2C2%2C3&f_JT=F

---

## Ireland — Critical Skills Employment Permit

### DevOps / Cloud — Dublin (siège EU de Google, Meta, Microsoft, Amazon, Stripe)
https://www.linkedin.com/jobs/search/?keywords=devops+cloud+engineer&location=Dublin%2C+Ireland&f_TPR=r86400&f_JT=F

---

## UAE / Dubai — Employment Visa (0 complication, employeur donne le visa)

### DevOps / Cloud — Dubai
https://www.linkedin.com/jobs/search/?keywords=devops+engineer+OR+cloud+engineer&location=Dubai%2C+United+Arab+Emirates&f_TPR=r86400&f_JT=F

### Infrastructure / SysAdmin — UAE-wide
https://www.linkedin.com/jobs/search/?keywords=devops+cloud+infrastructure&location=United+Arab+Emirates&f_TPR=r86400&f_JT=F

---

## Grandes boites qui sponsorisent — chercher directement

Ces companies ont des programmes de sponsorship établis. Cherche leur page carrières directement :

| Company | Pays | Page carrières |
|---------|------|----------------|
| ASML | NL (Eindhoven) | https://www.asml.com/en/careers/find-your-job |
| Booking.com | NL (Amsterdam) | https://careers.booking.com |
| Adyen | NL (Amsterdam) | https://www.adyen.com/careers |
| Capgemini NL | NL | https://www.capgemini.com/nl-en/careers |
| Microsoft NL | NL (Amsterdam) | https://careers.microsoft.com |
| SAP | DE (Walldorf) | https://jobs.sap.com |
| Zalando | DE (Berlin) | https://jobs.zalando.com |
| Capgemini DE | DE | https://www.capgemini.com/de-de/karriere |
| Capgemini FR | FR (Paris) | https://www.capgemini.com/fr-fr/carrieres |
| Atos | FR (Paris) | https://atos.net/en/careers |
| Sopra Steria | FR (Paris) | https://www.soprasteria.com/careers |
| Google Ireland | IE (Dublin) | https://careers.google.com |
| Stripe | IE (Dublin) | https://stripe.com/jobs |
| Microsoft IE | IE (Dublin) | https://careers.microsoft.com |
| Capgemini UK | GB (London) | https://www.capgemini.com/gb-en/careers |
| Accenture UK | GB (London) | https://www.accenture.com/gb-en/careers |
| Amazon | AE (Dubai) | https://amazon.jobs |
| Microsoft AE | AE (Dubai) | https://careers.microsoft.com |

---

## Mots-clés à ajouter dans les recherches pour le sponsorship

Dans LinkedIn, après la recherche, utilise le filtre "Sponsored by employer" si disponible, OU cherche ces phrases dans le texte de l'offre :
- `visa sponsorship`
- `relocation package`
- `work permit`
- `international candidates`
- `willing to relocate`

---

## Routine recommandée (15 min/matin)

**Pipeline automatique (depuis le terminal) :**
```bash
# Priorité 1 : marchés avec sponsorship le plus accessible
python daily_alerts.py --market nl   # NL — Kennismigrant, 2-4 sem
python daily_alerts.py --market de   # DE — EU Blue Card, Master suffisant
python daily_alerts.py --market ae   # UAE — visa auto, 0 complexité

# Priorité 2 : marchés avec visa plus long mais gros volume
python daily_alerts.py --market gb   # UK — Skilled Worker
python daily_alerts.py --market ie   # IE — Critical Skills (Google/Meta/Stripe)
python daily_alerts.py --market fr   # FR — Passeport Talent, il parle français
```

**Manuel LinkedIn (5 min) :**
1. Parcourir 2-3 des URLs ci-dessus (filtrées "last 24h")
2. Postuler en priorité sur les offres avec `company_signal >= 3`
3. Mentionner dans la lettre : "Open to relocation, will require work permit sponsorship"

**Ce que tu n'as PAS besoin de faire :**
- NE PAS postuler sur des offres avec `sponsorship_score = -10` (EU only, no sponsorship)
- NE PAS contacter des PME locales sans présence internationale

---

*Dernière mise à jour : 2026-05-18*
