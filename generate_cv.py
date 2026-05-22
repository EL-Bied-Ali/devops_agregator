"""Generate a PDF CV from cv_data.py using Playwright (Chromium).

Usage:
    python generate_cv.py                        # generates Ali_EL_Bied_CV.pdf
    python generate_cv.py --output company.pdf   # custom filename
    python generate_cv.py --html                 # also saves .html for debugging
"""
import asyncio
import argparse
import base64
import os
import copy
from pathlib import Path
from playwright.async_api import async_playwright

from cv_data import CV


# ── helpers ────────────────────────────────────────────────────────────────────

def _photo_b64(path: str) -> str | None:
    if path and os.path.exists(path):
        ext = Path(path).suffix.lstrip('.').lower()
        if ext == 'jpg':
            ext = 'jpeg'
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/{ext};base64,{data}"
    return None


def _esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _bullets(items: list) -> str:
    return ''.join(f'<li>{_esc(b)}</li>' for b in items)


def _section(icon: str, title: str, body: str) -> str:
    return f"""
<div class="section">
  <div class="section-header">
    <div class="section-icon">{icon}</div>
    <h2>{title}</h2>
  </div>
  <div class="section-body">{body}</div>
</div>"""


def _experience_html(exps: list) -> str:
    out = ''
    for e in exps:
        out += f"""
<div class="exp-block">
  <div class="exp-top">
    <div>
      <div class="exp-company">{_esc(e['company'])}</div>
      <div class="exp-role">{_esc(e['role'])}</div>
    </div>
    <div class="exp-meta">{_esc(e['period'])} | {_esc(e['location'])}</div>
  </div>
  <ul>{_bullets(e['bullets'])}</ul>
</div>"""
    return out


def _skills_html(skills: list) -> str:
    return ''.join(
        f'<div class="skill-row"><span class="skill-cat">{_esc(cat)}</span> — {_esc(items)}</div>'
        for cat, items in skills
    )


def _languages_html(langs: list) -> str:
    return ''.join(
        f'<div class="lang-row"><span class="lang-name">{_esc(lang)}</span> — {_esc(level)}</div>'
        for lang, level in langs
    )


def _education_html(edus: list) -> str:
    out = ''
    for e in edus:
        out += f"""
<div class="edu-block">
  <div class="edu-degree">{_esc(e['degree'])}</div>
  <div class="edu-school">{_esc(e['school'])}</div>
  <div class="edu-period">{_esc(e['period'])} | {_esc(e['location'])}</div>
  <ul>{_bullets(e.get('bullets', []))}</ul>
</div>"""
    return out


def _certs_html(certs: list) -> str:
    out = ''
    for c in certs:
        out += '<div class="cert-block">'
        out += f'<div class="cert-name">{_esc(c["name"])}</div>'
        if c.get('issuer'):
            out += f'<div class="cert-issuer">{_esc(c["issuer"])}</div>'
        if c.get('detail'):
            out += f'<div class="cert-detail">{_esc(c["detail"])}</div>'
        out += '</div>'
    return out


def _projects_html(projs: list) -> str:
    out = ''
    for p in projs:
        out += f"""
<div class="proj-block">
  <div class="proj-name">{_esc(p['name'])}</div>
  <div class="proj-tech">{_esc(p['tech'])}</div>
  <ul>{_bullets(p['bullets'])}</ul>
</div>"""
    return out


# ── HTML builder ───────────────────────────────────────────────────────────────

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Segoe UI', Arial, sans-serif;
  font-size: 8.2pt;
  color: #1a1a2e;
  background: white;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

/* ── HEADER ── */
.header {
  background: #1b2333;
  color: white;
  padding: 18px 24px 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left { flex: 1; min-width: 0; }

h1 {
  font-size: 22pt;
  font-weight: 700;
  color: white;
  letter-spacing: 0.3px;
  line-height: 1.1;
}
.cv-title {
  font-size: 10pt;
  color: #94a3b8;
  margin-top: 3px;
  margin-bottom: 10px;
  font-weight: 400;
}
.contacts {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 14px;
  margin-top: 6px;
}
.contact-item {
  font-size: 7.8pt;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 4px;
}
.contact-icon { font-size: 9px; opacity: 0.8; }
a.contact-item { text-decoration: none; color: #cbd5e1; }

/* ── PHOTO ── */
.photo {
  width: 82px;
  height: 82px;
  border-radius: 50%;
  object-fit: cover;
  object-position: center top;
  border: 2.5px solid rgba(255,255,255,0.25);
  margin-left: 20px;
  flex-shrink: 0;
}
.photo-placeholder {
  width: 82px;
  height: 82px;
  border-radius: 50%;
  background: #2d3f5a;
  margin-left: 20px;
  flex-shrink: 0;
}

/* ── BODY ── */
.body {
  display: flex;
}
.col-left {
  flex: 0 0 54%;
  padding: 14px 16px 14px 20px;
  border-right: 1px solid #e8edf2;
}
.col-right {
  flex: 0 0 46%;
  padding: 14px 20px 14px 14px;
}

/* ── SECTIONS ── */
.section { margin-bottom: 13px; }
.section-header {
  display: flex;
  align-items: center;
  gap: 7px;
  padding-bottom: 4px;
  border-bottom: 1.5px solid #e2e8f0;
  margin-bottom: 7px;
}
.section-icon {
  width: 17px;
  height: 17px;
  background: #1b2333;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  flex-shrink: 0;
}
.section-header h2 {
  font-size: 8.5pt;
  font-weight: 700;
  letter-spacing: 0.9px;
  color: #1b2333;
  text-transform: uppercase;
}
.section-body {
  font-size: 8pt;
  line-height: 1.45;
}

p { margin-bottom: 0; }

ul { list-style: none; padding-left: 0; margin-top: 3px; }
ul li {
  padding-left: 11px;
  position: relative;
  margin-bottom: 2px;
}
ul li::before {
  content: "–";
  position: absolute;
  left: 0;
  color: #64748b;
}

/* ── EXPERIENCE ── */
.exp-block { margin-bottom: 9px; }
.exp-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2px;
}
.exp-company { font-weight: 700; font-size: 8.5pt; color: #1b2333; }
.exp-role { font-size: 7.8pt; color: #475569; margin-top: 1px; }
.exp-meta {
  font-size: 7.3pt;
  color: #64748b;
  text-align: right;
  white-space: nowrap;
  margin-left: 8px;
  margin-top: 1px;
  flex-shrink: 0;
}

/* ── SKILLS ── */
.skill-row { margin-bottom: 3px; }
.skill-cat { font-weight: 700; }

/* ── LANGUAGES ── */
.lang-row { margin-bottom: 2px; }
.lang-name { font-weight: 700; }

/* ── EDUCATION ── */
.edu-block { margin-bottom: 9px; }
.edu-degree { font-weight: 700; font-size: 8.5pt; color: #1b2333; }
.edu-school { font-size: 8pt; color: #475569; }
.edu-period { font-size: 7.3pt; color: #64748b; margin-bottom: 3px; }

/* ── CERTIFICATES ── */
.cert-block { margin-bottom: 7px; }
.cert-name { font-weight: 700; font-size: 8pt; color: #1b2333; }
.cert-issuer { font-size: 7.8pt; color: #475569; }
.cert-detail { font-size: 7.3pt; color: #64748b; }

/* ── PROJECTS ── */
.proj-block { margin-bottom: 9px; }
.proj-name { font-weight: 700; font-size: 8.5pt; color: #1b2333; }
.proj-tech { font-size: 7.3pt; color: #64748b; margin-bottom: 2px; }
"""


def build_html(cv: dict) -> str:
    photo_src = _photo_b64(cv.get('photo', ''))
    photo_tag = (
        f'<img class="photo" src="{photo_src}" alt="Photo">'
        if photo_src else
        '<div class="photo-placeholder"></div>'
    )

    contacts = [
        ('✉',  cv['email'],            f'mailto:{cv["email"]}'),
        ('📍', cv['location'],          None),
        ('🔗', cv.get('github', ''),    cv.get('github_url')),
        ('📞', cv['phone'],             f'tel:{cv["phone"]}'),
        ('in', cv.get('linkedin', ''),  cv.get('linkedin_url')),
    ]
    def _contact_item(icon, text, url):
        inner = f'<span class="contact-icon">{icon}</span>{_esc(text)}'
        if url:
            return f'<a class="contact-item" href="{url}" target="_blank">{inner}</a>'
        return f'<span class="contact-item">{inner}</span>'
    contacts_html = ''.join(
        _contact_item(icon, text, url)
        for icon, text, url in contacts if text
    )

    left = (
        _section('👤', 'Profile', f'<p>{_esc(cv["profile"])}</p>') +
        _section('💼', 'Experience', _experience_html(cv['experience'])) +
        _section('🔧', 'Skills', _skills_html(cv['skills'])) +
        _section('🌐', 'Languages', _languages_html(cv['languages']))
    )

    right = (
        _section('🎓', 'Education', _education_html(cv['education'])) +
        _section('📋', 'Certificates', _certs_html(cv['certificates'])) +
        _section('📁', 'Key Projects', _projects_html(cv['projects']))
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <h1>{_esc(cv['name'])}</h1>
    <div class="cv-title">{_esc(cv['title'])}</div>
    <div class="contacts">{contacts_html}</div>
  </div>
  {photo_tag}
</div>
<div class="body">
  <div class="col-left">{left}</div>
  <div class="col-right">{right}</div>
</div>
</body>
</html>"""


# ── Playwright renderer ─────────────────────────────────────────────────────────

async def render_pdf(html: str, output: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until='networkidle')
        await page.pdf(
            path=output,
            format='A4',
            print_background=True,
            margin={'top': '0mm', 'right': '0mm', 'bottom': '0mm', 'left': '0mm'},
        )
        await browser.close()


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Generate CV PDF')
    ap.add_argument('--output', '-o', default='Ali_EL_Bied_CV.pdf')
    ap.add_argument('--html', action='store_true', help='Also save HTML for inspection')
    args = ap.parse_args()

    html = build_html(CV)

    if args.html:
        html_path = args.output.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'HTML: {html_path}')

    asyncio.run(render_pdf(html, args.output))
    print(f'PDF: {args.output}')


if __name__ == '__main__':
    main()
