import unittest

from emploi_ma_fetch import extract_total_pages, html_to_text, parse_detail_page, parse_listing_cards


class EmploiMaParserTests(unittest.TestCase):
    def test_extract_total_pages_uses_zero_based_page_links(self):
        html = """
        <div class="pagination">
          <a href="/recherche-jobs-maroc?f%5B0%5D=im_field_offre_metiers%3A31&page=1">2</a>
          <a href="/recherche-jobs-maroc?f%5B0%5D=im_field_offre_metiers%3A31&page=2">3</a>
        </div>
        """
        self.assertEqual(extract_total_pages(html), 3)

    def test_parse_listing_cards_extracts_core_fields(self):
        html = """
        <div class="card card-job featured" data-href="https://www.emploi.ma/offre-emploi-maroc/devops-engineer-casablanca-123">
          <div class="card-job-detail">
            <h3><a href="/offre-emploi-maroc/devops-engineer-casablanca-123" title="DevOps Engineer - Casablanca">DevOps Engineer - Casablanca</a></h3>
            <a href="/recruteur/42" class="card-job-company company-name">ACME TECH</a>
            <div class="card-job-description"><p>Automatisation CI/CD et infrastructure cloud.</p><a href="#">+plus</a></div>
            <ul>
              <li>Niveau d'expérience : <strong>Débutant &lt; 2 ans</strong></li>
              <li>Contrat proposé : <strong>CDI</strong></li>
              <li>Région de : <strong>Casablanca-Mohammedia</strong></li>
            </ul>
            <time datetime="2026-04-16">16.04.2026</time>
          </div>
        </div>
        """
        rows = parse_listing_cards(html)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["title"], "DevOps Engineer - Casablanca")
        self.assertEqual(row["company"], "ACME TECH")
        self.assertEqual(row["location"], "Casablanca-Mohammedia")
        self.assertEqual(row["created"], "2026-04-16")
        self.assertEqual(row["contract_type"], "CDI")
        self.assertIn("CI/CD", row["description"])
        self.assertTrue(row["url"].endswith("/offre-emploi-maroc/devops-engineer-casablanca-123"))

    def test_parse_detail_page_extracts_sections(self):
        html = """
        <html>
          <head>
            <meta property="og:title" content="[ACME TECH] DevOps Engineer - Casablanca" />
            <link rel="canonical" href="https://www.emploi.ma/offre-emploi-maroc/devops-engineer-casablanca-123" />
          </head>
          <body>
            <h1 class="text-center">DevOps Engineer - Casablanca</h1>
            <div class="page-application-details"><p>Publiée le 16.04.2026</p></div>
            <li class="withicon location-dot"><span>Casablanca-Mohammedia</span></li>
            <li class="withicon chart"><span>Débutant &lt; 2 ans</span></li>
            <li class="withicon graduation-cap"><span>Bac+5</span></li>
            <li class="withicon file-signature"><span>CDI</span></li>
            <div class="job-description"><p>Déployer des pipelines CI/CD.</p><ul><li>Terraform</li></ul></div>
            <div class="job-qualifications"><p>Une première expérience cloud est souhaitée.</p></div>
            <ul class="arrow-list"><li><strong>Langues exigées</strong> : <span>français</span></li></ul>
          </body>
        </html>
        """
        row = parse_detail_page(html, "https://www.emploi.ma/offre-emploi-maroc/devops-engineer-casablanca-123")
        self.assertEqual(row["title"], "DevOps Engineer - Casablanca")
        self.assertEqual(row["company"], "ACME TECH")
        self.assertEqual(row["location"], "Casablanca-Mohammedia")
        self.assertEqual(row["created"], "2026-04-16")
        self.assertEqual(row["contract_type"], "CDI")
        self.assertIn("Déployer des pipelines CI/CD.", row["description"])
        self.assertIn("Une première expérience cloud est souhaitée.", row["description"])
        self.assertNotIn("Langues exigées", row["description"])

    def test_html_to_text_preserves_block_boundaries(self):
        raw = "<div><p>Bonjour&nbsp;monde</p><ul><li>ligne 1</li><li>ligne 2</li></ul></div>"
        self.assertEqual(html_to_text(raw), "Bonjour monde\nligne 1\nligne 2")


if __name__ == "__main__":
    unittest.main()
