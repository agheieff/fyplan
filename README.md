# 十五五规划纲要 · China's 15th Five-Year Plan (2026–2030)

Print editions of the *Outline of the 15th Five-Year Plan for National Economic and Social
Development of the People's Republic of China (2026–2030)*
(《中华人民共和国国民经济和社会发展第十五个五年规划纲要》), typeset from the official text
published by Xinhua News Agency on 14 March 2026, in Chinese, in English, and side by side.

## Download

| Edition | One-sided | Double-sided |
|---|---|---|
| Chinese (简体中文), 11 pt | [PDF](deliverables/15th-Five-Year-Plan_Chinese.pdf), 101 pages | [PDF](deliverables/15th-Five-Year-Plan_Chinese_Duplex.pdf), 103 pages |
| English, 10.8 pt | [PDF](deliverables/15th-Five-Year-Plan_English.pdf), 157 pages | [PDF](deliverables/15th-Five-Year-Plan_English_Duplex.pdf), 158 pages |
| Bilingual, 9.5 pt | [PDF](deliverables/15th-Five-Year-Plan_Bilingual.pdf), 143 pages | [PDF](deliverables/15th-Five-Year-Plan_Bilingual_Duplex.pdf), 144 pages |

All are A4. The one-sided PDFs are for reading on screen or printing on one side. The double-sided
PDFs are for printing on both sides with a long-edge flip: page numbers sit on the outer edge, and
the contents and page 1 start on a right-hand page. The text and page numbers are otherwise the same.

The bilingual edition sets Chinese on the left and English on the right, paragraph by paragraph,
with the two columns on one baseline grid so that lines run straight across the page.

## What is in it

- The full text: 18 parts (篇), 62 chapters (章) and 171 sections (节), about 57,500 Chinese
  characters and 43,000 English words, with contents, PDF bookmarks and running heads.
- All 23 policy boxes (专栏), including Box 1, the table of 20 main indicators. In the original
  they are images; here they are transcribed and translated, so the whole document is searchable.
  Box 23 is a broken image on the official page and was taken from another copy of the same
  document.
- The three maps, as images, with translated captions and legends.

## Source

Xinhua News Agency, 14 March 2026, as published by the Liaison Office of the Central People's
Government in the Hong Kong SAR:
<https://www.locpg.gov.cn/20260314/4cab36f71ce14e90957ccd9cebbaf60c/c.html>. The page as retrieved
on 6 November 2026 is kept in `src/simp.html`. The Chinese text is authoritative.

## Translation

The English is a machine translation by DeepSeek (V4.1 Flash), made against a shared glossary of
official renderings ([`work/GLOSSARY.md`](work/GLOSSARY.md)): for example 新质生产力 is *new
quality productive forces* and 全过程人民民主 is *whole-process people's democracy*. Every
paragraph was checked to be translated exactly once, with nothing missing or added. It has not
been read through by a human translator.

Numbers and units are kept exactly as in the original, and "percent" is written as `%` throughout.
A few terms have no established rendering and were coined, among them 自主开放 (*self-initiated
opening up*), 数智化 (*digital and intelligent*) and 城市体检 (*city health checks*).

## Printing in black and white

The bilingual edition is designed for it: all text and rules are solid black, with hierarchy from
size and weight rather than colour or tints. Its maps are lightened so the pastel source images
do not print as speckle; place names stay legible, but the colour coding (such as the site classes
on Figure 2) cannot survive in black and white. For those, print pages 23, 81 and 116 in colour.

The Chinese and English editions use a dark red accent and tinted boxes, and show the maps as
published.

## Limitations

- Simplified Chinese only.
- The 60-entry index on Figure 2 (World Heritage Sites) is part of the image and is not
  translated.
- The three editions are paginated independently.

## Building

Requirements: XeLaTeX (TeX Live with `xeCJK`, `fancyhdr`, `tcolorbox`, `titlesec`, `needspace`,
`eso-pic`), the Noto Serif, Noto Sans and Noto CJK fonts (the CJK fonts are read from
`/usr/share/fonts/noto-cjk/`), Python 3 with Pillow and NumPy, and `pdfinfo` (Poppler).

```bash
python3 build.py                # all six editions
python3 build.py bi bi-duplex   # one edition, one-sided and double-sided
```

The editions are `zh`, `en` and `bi`, each with a `-duplex` variant. The LaTeX and PDFs are
written to `out/`; the PDFs in `deliverables/` are copies of these.

| Path | Contents |
|---|---|
| `build.py` | Builds the LaTeX for each edition and compiles it |
| `work/source.json` | The Chinese text as ordered blocks (parts, chapters, sections, paragraphs, images) |
| `work/en/` | The English translation, one file per part, keyed by block |
| `work/boxes/` | The 23 policy boxes and 3 maps, transcribed and translated |
| `work/GLOSSARY.md` | The glossary and style rules the translation follows |
| `src/img/` | The original box and map images |
| `src/simp.html` | The source page |

## Credits

Translation and typesetting by DeepSeek (V4.1 Flash), with Claude on the typesetting DeepSeek
couldn't handle.
