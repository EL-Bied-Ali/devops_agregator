import unittest

from marocannonces_fetch import extract_total_pages, parse_detail_page, parse_listing_page


LISTING_HTML = """
<ul class="cars-list">
  <li class="firstitem">
    <a title="Connexion" href="mes-favoris.html">
      <div class="holder">
        <h3>Connexion</h3>
        <span class="location">Casablanca</span>
      </div>
    </a>
    <div class="time"><em class="date"><span class="cnt-today">Aujourd'hui</span></em></div>
  </li>
  <li>
    <a title="Technicien support informatique" href="categorie/309/Offres-emploi/annonce/123456/Technicien-support-informatique.html">
      <div class="holder">
        <h3>Technicien support informatique</h3>
        <span class="location">Rabat</span>
      </div>
    </a>
    <div class="time"><em class="date"><span class="cnt-today">Aujourd'hui</span><br><span>10:42</span></em></div>
  </li>
</ul>
<a href="/maroc/offres-emploi-domaine-informatique-multimedia-internet-b309.html?f_3=Informatique+%2F+Multim%C3%A9dia+%2F+Internet&pge=1">2</a>
<a href="/maroc/offres-emploi-domaine-informatique-multimedia-internet-b309.html?f_3=Informatique+%2F+Multim%C3%A9dia+%2F+Internet&pge=2">3</a>
"""


DETAIL_HTML = """
<html>
  <head>
    <script type="application/ld+json">
    {
      "@context": "http://schema.org",
      "@type": "JobPosting",
      "url": "https://www.marocannonces.com/categorie/309/Offres-emploi/annonce/123456/Technicien-support-informatique.html",
      "title": "Technicien support informatique",
      "datePosted": "2026-04-16 10:42",
      "description": "<p>Support utilisateurs, maintenance du parc et gestion reseau.</p>",
      "industry": "Informatique / Multimédia / Internet",
      "employmentType": "CDI",
      "jobLocation": {
        "@type": "Place",
        "address": {
          "@type": "PostalAddress",
          "addressRegion": "Rabat",
          "addressLocality": "Rabat",
          "addressCountry": "Maroc"
        }
      },
      "hiringOrganization": {
        "@type": "Organization",
        "name": "Tech Maroc"
      }
    }
    </script>
  </head>
  <body>
    <h1>Technicien support informatique - Rabat</h1>
  </body>
</html>
"""

DETAIL_HTML_NO_JSONLD = """
<html>
  <body>
    <h1>Techniciens SI - Rabat</h1>
    <div class="block">
      <div class="box1"></div>
      Missions principales :<br />
      Assurer la maintenance et le support des systèmes et réseaux.<br />
      Participer à l’installation et à la configuration des infrastructures SI.<br />
      Diagnostiquer et résoudre les incidents techniques.
    </div>
    <!-- block -->
    <div class="parameter">
      <div id="extra_questions">
        <ul class='extraQuestionName' id='extraQuestionName'>
          <li>Domaine : <a>Informatique / Multimédia / Internet</a></li>
          <li>Contrat : <a>CDI</a></li>
          <li>Entreprise : <a>confidentiel</a></li>
          <li>Ville : Rabat</li>
        </ul>
      </div>
    </div>
  </body>
</html>
"""


class MarocAnnoncesParserTests(unittest.TestCase):
    def test_extract_total_pages(self):
        self.assertEqual(extract_total_pages(LISTING_HTML), 3)

    def test_parse_listing_page_filters_non_annonce_links(self):
        rows = parse_listing_page(LISTING_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Technicien support informatique")
        self.assertIn("/annonce/123456/", rows[0]["url"])
        self.assertEqual(rows[0]["location"], "Rabat")

    def test_parse_detail_page_uses_json_ld(self):
        row = parse_detail_page(
            DETAIL_HTML,
            "https://www.marocannonces.com/categorie/309/Offres-emploi/annonce/123456/Technicien-support-informatique.html",
        )
        self.assertEqual(row["title"], "Technicien support informatique")
        self.assertEqual(row["company"], "Tech Maroc")
        self.assertEqual(row["location"], "Rabat")
        self.assertEqual(row["created"], "2026-04-16")
        self.assertIn("Support utilisateurs", row["description"])
        self.assertEqual(row["contract_type"], "CDI")

    def test_parse_detail_page_falls_back_to_html_body(self):
        row = parse_detail_page(
            DETAIL_HTML_NO_JSONLD,
            "https://www.marocannonces.com/categorie/309/Offres-emploi/annonce/10284252/Techniciens-SI.html",
        )
        self.assertEqual(row["title"], "Techniciens SI - Rabat")
        self.assertEqual(row["company"], "confidentiel")
        self.assertEqual(row["location"], "Rabat")
        self.assertEqual(row["contract_type"], "CDI")
        self.assertIn("maintenance et le support des systèmes", row["description"].lower())


if __name__ == "__main__":
    unittest.main()
