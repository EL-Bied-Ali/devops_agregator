import unittest

from rekrute_fetch import clean_text, parse_detail_page, parse_listing_page


class RekruteParserTests(unittest.TestCase):
    def test_parse_listing_page_extracts_card(self):
        html = """
        <ul class="job-list job-list2" id="post-data">
          <li class="post-id" id="181835">
            <div>
              <div class="col-sm-2 col-xs-12">
                <a href="/confidentiel-emploi-recrutement-42.html">
                  <img class="photo" alt="CONFIDENTIEL" title="CONFIDENTIEL" />
                </a>
              </div>
              <div class="col-sm-10 col-xs-12">
                <div class="section">
                  <h2><a class='titreJob' href="/offre-emploi-junior-infra-recrutement-confidentiel-casablanca-181835.html">Junior infra | Casablanca (Maroc)</a></h2>
                  <div class="holder">
                    <div class="info">
                      <span style="color: #5b5b5b;line-height: 18px;">Support technique, serveurs et postes de travail.</span>
                    </div>
                    <em class="date">Publication : du <span>16/04/2026</span> au <span>16/06/2026</span></em>
                    <div class="info">
                      <ul><li>Type de contrat : CDI</li><li>Expérience requise : Débutant (-1 an)</li></ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </li>
        </ul>
        <a class="next" href="/offres.html?p=2&s=1&o=1"></a>
        """
        rows, next_url = parse_listing_page(html, "https://www.rekrute.com/offres-emploi-metiers-de-l-it.html")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["title"], "Junior infra | Casablanca (Maroc)")
        self.assertEqual(row["company"], "CONFIDENTIEL")
        self.assertEqual(row["created"], "2026-04-16")
        self.assertIn("Support technique", row["description"])
        self.assertEqual(next_url, "https://www.rekrute.com/offres.html?p=2&s=1&o=1")

    def test_parse_detail_page_extracts_sections(self):
        html = """
        <html>
          <head>
            <meta property="og:title" content="[CONFIDENTIEL] Junior infra - Casablanca" />
            <meta property="og:url" content="https://www.rekrute.com/offre-emploi-junior-infra-recrutement-confidentiel-casablanca-181835.html" />
            <meta property="og:description" content="Support infra, postes de travail et serveurs." />
          </head>
          <body>
            <h1>Junior infra - Casablanca</h1>
            <ul class="featureInfo">
              <li title="Expérience requise">Débutant (-1 an)</li>
              <li title="Région"><b>1</b> poste(s) sur Casablanca et région - Maroc</li>
            </ul>
            <span class="tagContrat" title="Type de contrat">CDI</span>
            <div class="col-md-12 blc"><h2>Missions</h2><p>Assurer le support N1/N2 et la maintenance système.</p></div>
            <div class="col-md-12 blc"><h2>Profil recherché :</h2><p>Bac+5 en informatique avec 1 an d'expérience.</p></div>
          </body>
        </html>
        """
        row = parse_detail_page(html, "https://www.rekrute.com/offre-emploi-junior-infra-recrutement-confidentiel-casablanca-181835.html")
        self.assertEqual(row["title"], "Junior infra - Casablanca")
        self.assertEqual(row["company"], "CONFIDENTIEL")
        self.assertEqual(row["experience_hint"], "Débutant (-1 an)")
        self.assertEqual(row["contract_type"], "CDI")
        self.assertIn("support N1/N2", row["description"])
        self.assertIn("Bac+5 en informatique", row["description"])

    def test_clean_text_collapses_entities_and_spaces(self):
        self.assertEqual(clean_text("  CONFIDENTIEL&nbsp;  "), "CONFIDENTIEL")


if __name__ == "__main__":
    unittest.main()
