# Task for Claude Code — "O projekte" page

## What to do
- Create the **"O projekte"** subpage and wire it to the existing navbar link (a nav entry for it already exists — hook this page up to it; add the entry only if it's missing).
- The page content is the exact Slovak text in the **Page content** section below. **Use it verbatim** — do not rewrite, translate, or reword it.
- Handle only the **formatting and visual layout**. Keep it consistent with the rest of the site and lean **minimalistic**.
- Contact email is included in the text (lubomir.rajter@gmail.com).
- Use `https://github.com/wRajter/spravomat` for the `[odkaz]` GitHub link.

## Section structure
1. Intro (no heading)
2. **Ako to funguje**
3. **Plány do budúcna** (three labelled items)
4. **O mne**

---

## Implementation plan

### 1. Route (`spravomat/web/routes/__init__.py`)
Add one route below `home()`. No DB, no logic — pure static render:
```python
@bp.route("/o-projekte")
def about():
    """Render the static 'O projekte' page."""
    return render_template("about.html")
```
- Slug: `/o-projekte` (Slovak, matches the site language).

### 2. Navbar (`templates/navbar.html`)
Change the placeholder link only:
```html
<a href="{{ url_for('web.about') }}">O projekte</a>
```
Leaves "Kategórie" as `#`, untouched.

### 3. Template (`templates/about.html`)
New file extending `base.html`. Structure per the section list, text verbatim:
- One wrapper `<div class="about">` (readable narrower column).
- Intro: 4 paragraphs, no heading.
- `<h3>Ako to funguje</h3>` + paragraph + GitHub line, where `[odkaz]`
  becomes a real link to `https://github.com/wRajter/spravomat`
  (`target="_blank" rel="noopener"`).
- `<h3>Plány do budúcna</h3>` + intro line + 3 items. Each labelled item is a
  `<p>` with the bold label in `<strong>`.
- `<h3>O mne</h3>` + paragraph, email as a `mailto:` link.

### 4. CSS (`static/css/main.css`)
Append a small `/* About page */` block, reusing existing `h3`, `p`, `a`:
- `.about { max-width: 70rem; }` — comfortable reading line length.
- `.about h3 { margin-top: 3rem; }` — section spacing.
- Links inside `.about` use the green accent on hover (consistent with site).

---

## Page content (use verbatim)

Tento projekt vznikol, aby som vyriešil svoj problém ako ostať up-to-date s meniacim sa news cyclom. Nebavilo ma otvárať množstvo novín na desiatkach tabov a orientovať sa, kto čo napísal a o čom. Chcel som mať všetko pekne štruktúrované po témach a podľa toho, o čom sa píše najčastejšie. Ale nechcel som používať agregátor správ, lebo tam často chýbajú odkazy na originálne správy.

Chcel som rozcestník, v ktorom by som videl témy, zhrnutie, kontext a odkazy. A vedel by som naskočiť aj na už rozbehnutú tému, ktorú som síce nezachytil od začiatku, ale mám tam zhrnutie, ktoré ma dá do obrazu za pár sekúnd. Keď ma niečo zaujme, hupnem na odkazy a hltavo čítam originálne zdroje.

Preto som vytvoril Spravomat. Keď ho otvorím, mám tu pekný prierez o tom, o čom sa najviac píše naprieč rôznymi novinami. Mám tu rýchle zhrnutie, na základe ktorého viem zhodnotiť, či si chcem danú tému skúmať ďalej. Ak áno, mám tu rovno prelinky na originálne články. A ak v téme nie som doma, mám tu aj kontext, aby som vedel, o čo ide, než sa na články vrhnem.

To, čo nechcem robiť, je nahrádzať alebo konkurovať originálnemu spravodajstvu. Oni vytvárajú skutočnú hodnotu. Nechcem robiť ani typický agregát správ. Samotné noviny sú samy o sebe agregátory (vyberajú správy, ktoré publikujú), takže robiť agregát agregátov nedáva veľký zmysel. Chcel by som, aby bol Spravomat iba jednoduchým miestom, na ktoré prídem, odpijem z rannej kávy, a mám pripravený celý svet správ na objavovanie.

### Ako to funguje

Spravomat v prvom kroku zbiera správy z rôznych novín. Potom zoskupí správy, ktoré píšu o tej istej udalosti. Takže namiesto desiatok samostatných článkov vznikne jedna téma a pod ňou všetky médiá, čo o nej píšu. Nakoniec sa automaticky vyberú a zobrazia tie témy, o ktorých sa píše najviac a sú najaktuálnejšie.

Viac technických detailov je na GitHube: [odkaz]

### Plány do budúcna

Spravomat je stále rozpracovaný a rád by som ho postupne posúval ďalej. Pár vecí, ktoré mám najbližšie v pláne:

**Kontext k správam:** po kliknutí na tému sa k nej objaví kontext. Nešlo by o prerozprávanie správ zo zdrojov, ale skôr o akúsi mini-wiki k danej téme, aby mal človek ešte pred čítaním širší obraz o tom, o čo ide, a lepšie tak pochopil samotné správy.

**Kategórie:** momentálne témy nie sú rozdelené do kategórií. Rád by som ich rozčlenil na: udalosti, geopolitiku, IT, financie, politiku a šport.

**Viac zdrojov:** pridávať ďalšie noviny, domáce aj zahraničné, nech je pokrytie širšie.

### O mne

Volám sa Ľubomír Rajter. Pracujem ako developer a vo voľnom čase rád vytváram rôzne malé projekty, ktoré pridávajú hodnotu do spoločnosti a pomáhajú ľuďom. Ak sa vám tento projekt páči alebo máte akýkoľvek feedback, neváhajte mi napísať: lubomir.rajter@gmail.com