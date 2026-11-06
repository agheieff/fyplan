#!/usr/bin/env python3
"""Typeset the 15th Five-Year Plan Outline into Chinese / English / bilingual PDFs."""
import json, os, re, subprocess, sys, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)

TITLE_ZH = '中华人民共和国国民经济和社会发展第十五个五年规划纲要'
TITLE_EN = 'Outline of the 15th Five-Year Plan for National Economic and Social Development of the People’s Republic of China (2026–2030)'
TITLE_EN_SHORT = 'China’s 15th Five-Year Plan (2026–2030)'

# ---------------------------------------------------------------- data

def load_source():
    return json.load(open(os.path.join(ROOT, 'work/source.json')))

def norm_en(v):
    v = v.replace("'", '’')
    v = re.sub(r'(\d)\s*(?:percent|per cent)\b', r'\1%', v)
    v = re.sub(r'[ \t]{2,}', ' ', v)
    return v.strip()


def _en(v):
    """box text and titles skip norm_en; the bilingual edition still wants curly apostrophes"""
    return (v or '').replace("'", '’')


def load_translations(body_ids):
    tr = {}
    d = os.path.join(ROOT, 'work/en')
    for f in sorted(os.listdir(d)):
        m = re.match(r'part-(\d+)\.json$', f)
        if not m:
            continue
        data = json.load(open(os.path.join(d, f)))
        for k, v in data.get('translations', {}).items():
            tr[k] = norm_en(v) if k in body_ids else v
    return tr

def load_boxes():
    d = os.path.join(ROOT, 'work/boxes')
    boxes = {}
    for f in sorted(os.listdir(d)):
        m = re.match(r'box-(\d+)\.json$', f)
        if not m:
            continue
        try:
            data = json.load(open(os.path.join(d, f)))
        except Exception as e:
            print('  !! bad box file', f, e, file=sys.stderr)
            continue
        boxes[int(m.group(1))] = data
    return boxes

# ---------------------------------------------------------------- escaping

SPECIAL = [('\\', r'\textbackslash{}'), ('&', r'\&'), ('%', r'\%'), ('$', r'\$'),
           ('#', r'\#'), ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
           ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}')]

def esc(s):
    for a, b in SPECIAL:
        s = s.replace(a, b)
    return s

SUBRE = re.compile(r'\{sub\}(.*?)\{\}')

def texify(s):
    """escape LaTeX specials, turning {sub}2.5{} into a real subscript"""
    if s is None:
        return ''
    out, pos = [], 0
    for m in SUBRE.finditer(s):
        out.append(esc(s[pos:m.start()]))
        out.append(r'\textsubscript{' + esc(m.group(1)) + '}')
        pos = m.end()
    out.append(esc(s[pos:]))
    return ''.join(out)

def typo(s):
    """English typographic polish applied after escaping"""
    s = re.sub(r'(?<=\d)-(?=\d)', '–', s)          # 2026-2030 -> en dash
    s = re.sub(r'(\d)%', r'\1\\%', s) if False else s
    return s

# ---------------------------------------------------------------- counts

CN_DIG = '零一二三四五六七八九'
def cn_num(n):
    if n <= 10:
        return ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'][n]
    if n < 20:
        return '十' + CN_DIG[n - 10]
    t, u = divmod(n, 10)
    return CN_DIG[t] + '十' + (CN_DIG[u] if u else '')

# ---------------------------------------------------------------- preamble

PREAMBLE_COMMON = r"""
\usepackage{xeCJK}
\xeCJKDeclareCharClass{CJK}{"2160->"2183,"2460->"24FF,"3007}
\xeCJKDeclareCharClass{Default}{"2018,"2019}
\usepackage{fontspec}
\setmainfont{Noto Serif}
\setsansfont{Noto Sans}
\setmonofont{Noto Sans Mono}
\setCJKmainfont{NotoSerifCJK-Regular.ttc}[Path=/usr/share/fonts/noto-cjk/,FontIndex=2,
  BoldFont=NotoSerifCJK-Bold.ttc,BoldFeatures={FontIndex=2}]
\setCJKsansfont{NotoSansCJK-Regular.ttc}[Path=/usr/share/fonts/noto-cjk/,FontIndex=2,
  BoldFont=NotoSansCJK-Bold.ttc,BoldFeatures={FontIndex=2}]
\usepackage{xcolor}
\definecolor{ink}{HTML}{1B1B1B}
\definecolor{accent}{HTML}{8C2F27}
\definecolor{midgray}{HTML}{585858}
\definecolor{lightgray}{HTML}{9A9A9A}
\definecolor{hairline}{HTML}{C9C2B2}
\definecolor{boxbg}{HTML}{F7F4EC}
\definecolor{boxframe}{HTML}{CFC5AC}
\definecolor{boxbar}{HTML}{8C2F27}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage{needspace}
\usepackage{eso-pic}
\usepackage[hidelinks,unicode,bookmarksnumbered,bookmarksopen]{hyperref}
\usepackage[english]{babel}
\usepackage{microtype}
\hyphenpenalty=80
\tolerance=1200
\emergencystretch=2em
\raggedbottom
\usepackage{tcolorbox}
\tcbuselibrary{breakable,skins}
\usepackage{titlesec}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
"""

# Paired columns. The bilingual edition does not use side-by-side minipages: each
# column is set on its own, then the two are zipped line by line into full-width rows.
# Every row is exactly \biLead tall and carries its own piece of the rule, so
#   - both columns share one baseline grid, and no two lines can sit closer than \biLead;
#   - a page can break between any two rows, so paragraphs never need artificial splits;
#   - rows are ordinary vertical material, so all of this also works inside a breakable box.
# Text in a \biPair must not change colour: its lines end up interleaved with the other
# column's, and an open colour would leak across. Black-only makes that a non-issue.
BI_PREAMBLE = r"""
\linespread{1}
\AtBeginDocument{\fontsize{9.5}{13.2}\selectfont}
\setlength{\parindent}{0pt}
\newcommand{\bodyfont}{\fontsize{9.5}{13.2}\selectfont}
\lineskip=0pt
\lineskiplimit=0pt
% Solid black only. A mono printer turns any grey or tint into a halftone, which breaks up
% small type and hairlines, so hierarchy is carried by size and weight instead.
\definecolor{ink}{gray}{0}
\definecolor{accent}{gray}{0}
\definecolor{midgray}{gray}{0}
\definecolor{lightgray}{gray}{0}
\definecolor{hairline}{gray}{0}
% Regular Song strokes are thin next to Noto Serif: Medium evens out the two columns and
% holds up through a mono printer or a photocopy.
\setCJKmainfont{NotoSerifCJK-Medium.ttc}[Path=/usr/share/fonts/noto-cjk/,FontIndex=2,
  BoldFont=NotoSerifCJK-Bold.ttc,BoldFeatures={FontIndex=2}]
\hypersetup{bookmarksopenlevel=1}
\xeCJKsetup{CheckSingle=true}
\makeatletter
\newdimen\biLead  \biLead=13.2pt
\newdimen\biAsc   \biAsc=9.7pt
\newdimen\biDesc  \biDesc=\dimexpr\biLead-\biAsc\relax
\newdimen\biParGap \biParGap=0.72\biLead
\newdimen\biRuleW \biRuleW=0.35pt
\newdimen\biGut   \biGut=20pt
\newdimen\biHalf  \biHalf=\dimexpr(\biGut-\biRuleW)/2\relax
\newdimen\biWz    \biWz=148pt
\newdimen\biWe
\AtBeginDocument{\biWe=\dimexpr\textwidth-\biGut-\biWz\relax}
\newdimen\biPad   \biPad=7pt
\newdimen\biFrame \biFrame=0.5pt
\newbox\biCz \newbox\biCe \newbox\biLz \newbox\biLe \newbox\biRow
\newcount\biN \newcount\biPen
\newcount\biKeep \biKeep=0
\newif\ifbiMore
% The English column keeps its quotes, dashes and ellipses in the Latin font; xeCJK would
% otherwise claim them as full-width CJK punctuation.
\def\biEnglish{\XeTeXcharclass"201C=0 \XeTeXcharclass"201D=0 \XeTeXcharclass"2014=0
  \XeTeXcharclass"2013=0 \XeTeXcharclass"2026=0 \XeTeXcharclass"00B7=0
  \frenchspacing\hyphenpenalty=400 \doublehyphendemerits=60000 \finalhyphendemerits=60000 }
% #1 box  #2 width  #3 setup  #4 text.  The empty first box is split off at once so that
% every line, the first included, comes out of \vsplit on the same footing.
\def\biSet#1#2#3#4{%
  \setbox#1\vbox{\hbox{}\penalty-\@M
    \hsize#2\relax\linewidth\hsize\parindent\z@\parskip\z@
    \bodyfont\lineskip\z@\lineskiplimit-\maxdimen #3\noindent#4\par}%
  \setbox\z@\vsplit#1 to\z@}
\def\biTake#1#2{\ifvoid#1\setbox#2\box\voidb@x\else
  \setbox#2\vsplit#1 to\splittopskip
  \setbox#2\vbox{\unvbox#2}\fi}
% Rule pieces overhang their row by a hair (the box dimensions stay nominal): edges that
% merely abut show as faint seams once rasterised.
\def\biRowBox{\hbox to\linewidth{%
  \hbox to\biWz{\ifvoid\biLz\else\box\biLz\fi\hss}\hskip\biHalf
  \vrule width\biRuleW height\dimexpr\biAsc+.4pt\relax depth\dimexpr\biDesc+.4pt\relax
  \hskip\biHalf\hbox to\biWe{\ifvoid\biLe\else\box\biLe\fi\hss}\hss}}
\def\biTail#1{\ifvoid#1\else\ifdim\dimexpr\ht#1+\dp#1\relax<1.5\biLead\biPen\@M\fi\fi}
% Break control after row \biN: never strand a first or last line of either column, and
% keep \biKeep rows with the heading above.
\newcommand{\biPair}[2]{%
  \par\begingroup
  \splittopskip\biAsc\splitmaxdepth\maxdimen\vbadness\@M\vfuzz\maxdimen
  \biSet\biCz\biWz{}{#1}\biSet\biCe\biWe\biEnglish{#2}%
  \biN\z@
  \loop
    \advance\biN\@ne
    \biTake\biCz\biLz\biTake\biCe\biLe
    \setbox\biRow\biRowBox\ht\biRow\biAsc\dp\biRow\biDesc
    \nointerlineskip\box\biRow
    \biMorefalse
    \ifvoid\biCz\else\biMoretrue\fi
    \ifvoid\biCe\else\biMoretrue\fi
    \ifbiMore
      \biPen\z@
      \ifnum\biN<\biKeep\biPen\@M\fi
      \ifnum\biN=\@ne\biPen\@M\fi
      \biTail\biCz\biTail\biCe
      \penalty\biPen
  \repeat
  \endgroup\global\biKeep\z@}
% A heading pair: one unbreakable row of any height, glued to what follows.
\newcommand{\biHead}[2]{%
  \par\begingroup
  \setbox\biCz\vtop{\hsize\biWz\linewidth\hsize\parindent\z@\raggedright#1\par}%
  \setbox\biCe\vtop{\hsize\biWe\linewidth\hsize\parindent\z@\raggedright\biEnglish#2\par}%
  \dimen@\ht\biCz\ifdim\ht\biCe>\dimen@\dimen@\ht\biCe\fi
  \dimen2\dp\biCz\ifdim\dp\biCe>\dimen2\dimen2\dp\biCe\fi
  \setbox\biRow\hbox to\linewidth{\hbox to\biWz{\box\biCz\hss}\hskip\biHalf
    \vrule width\biRuleW height\dimexpr\dimen@+.4pt\relax depth\dimexpr\dimen2+.4pt\relax
    \hskip\biHalf\hbox to\biWe{\box\biCe\hss}\hss}%
  \ht\biRow\dimen@\dp\biRow\dimen2
  \nointerlineskip\box\biRow
  \endgroup\nobreak\global\biKeep=3\relax}
% Space that carries the rule. Glue, so it disappears at a page break and leaves no stub.
% \cleaders, because plain \leaders drops a tile that does not fit its alignment grid.
\newcommand{\biBridge}[1]{%
  \par\begingroup\dimen@=#1\relax
  \cleaders\hbox to\linewidth{\hskip\dimexpr\biWz+\biHalf\relax
    \vrule width\biRuleW height\dimen@ depth\z@\hss}\vskip\dimen@
  \endgroup}
\newcommand{\biLabel}{\sffamily\bfseries\fontsize{8.5}{11}\selectfont}
\newcommand{\biChapter}[4]{\biHead
  {{\biLabel#1\par}\vspace{2pt}{\sffamily\bfseries\fontsize{13}{17.5}\selectfont#2\par}}%
  {{\biLabel#3\par}\vspace{2pt}{\sffamily\bfseries\fontsize{12}{16.5}\selectfont#4\par}}}
\newcommand{\biSection}[2]{\biHead
  {{\sffamily\bfseries\fontsize{9.5}{13.2}\selectfont#1\par}}%
  {{\sffamily\bfseries\fontsize{9.5}{13.2}\selectfont#2\par}}}
% Boxes: frame only, no fill. Columns are narrowed so the rule stays at the page's position
% and can run straight through the box.
\newtcolorbox{bibox}{breakable,enhanced,sharp corners,colback=white,colframe=black,
  boxrule=\biFrame,left=\biPad,right=\biPad,top=0pt,bottom=0pt,boxsep=0pt,
  before skip=0pt,after skip=0pt,lines before break=6,
  before upper={\advance\biWz by-\dimexpr\biPad+\biFrame\relax
                \advance\biWe by-\dimexpr\biPad+\biFrame\relax}}
\newcommand{\biBoxTitle}[4]{%
  \biBridge{5pt}\nobreak
  \biHead{{\biLabel#1\par}\vspace{1pt}{\sffamily\bfseries\fontsize{10.5}{14}\selectfont#2\par}}%
          {{\biLabel#3\par}\vspace{1pt}{\sffamily\bfseries\fontsize{10}{13.5}\selectfont#4\par}}%
  \biBridge{4.5pt}\nobreak\nointerlineskip
  \moveleft\biPad\vbox{\hrule width\dimexpr\linewidth+2\biPad\relax height\biFrame}\nobreak
  \biBridge{6.5pt}\nobreak}
\newcommand{\biBoxHead}[3]{\biHead
  {\sffamily\bfseries\fontsize{9.2}{12.6}\selectfont\hangindent=1.75em\hangafter=1
   \makebox[1.75em][l]{#1}#2\par}%
  {\sffamily\bfseries\fontsize{9.2}{12.6}\selectfont\hangindent=1.75em\hangafter=1
   \makebox[1.75em][l]{#1}#3\par}}
\newcommand{\biBoxSub}[2]{\biHead
  {\sffamily\bfseries\fontsize{8.8}{12}\selectfont#1\par}%
  {\sffamily\bfseries\fontsize{8.8}{12}\selectfont#2\par}}
\makeatother
"""


def preamble(mode, duplex=False):
    if mode == 'zh':
        geo = r'\usepackage[a4paper,top=2.5cm,bottom=2.5cm,left=2.7cm,right=2.7cm,headsep=14pt,footskip=20pt]{geometry}'
        body = r"""
\linespread{1}
\AtBeginDocument{\fontsize{11}{18.6}\selectfont}
\setlength{\parindent}{2em}
\newcommand{\bodyfont}{\fontsize{11}{18.6}\selectfont}
"""
    elif mode == 'en':
        geo = r'\usepackage[a4paper,top=2.5cm,bottom=2.5cm,left=2.6cm,right=2.6cm,headsep=14pt,footskip=20pt]{geometry}'
        body = r"""
\linespread{1}
\AtBeginDocument{\fontsize{10.8}{15.4}\selectfont}
\setlength{\parskip}{0.52em}
\setlength{\parindent}{0pt}
\newcommand{\bodyfont}{\fontsize{10.8}{15.4}\selectfont}
"""
    else:
        geo = r'\usepackage[a4paper,top=2.2cm,bottom=2.2cm,left=1.9cm,right=1.9cm,headsep=12pt,footskip=18pt]{geometry}'
        body = BI_PREAMBLE
    hs = r'\footnotesize\sffamily\color{midgray}'
    part = hs + r'\nouppercase{\leftmark}'
    chap = r'\rightmark' if mode == 'bi' else ''
    if duplex:
        # Long-edge duplex: the page number and chapter sit on the outer edge of each page, the part
        # title on the inner edge. PREAMBLE_COMMON's \raggedbottom undoes twoside's \flushbottom.
        heads = ('\\fancyhead[LO,RE]{' + part + '}\n'
                 '\\fancyhead[RO]{' + hs + (chap + r'\hspace{1.6em}' if chap else '') + r'\thepage}' + '\n'
                 '\\fancyhead[LE]{' + hs + r'\thepage' + (r'\hspace{1.6em}' + chap if chap else '') + '}')
    else:
        heads = ('\\fancyhead[L]{' + part + '}\n'
                 '\\fancyhead[R]{' + hs + (chap + r'\hspace{1.6em}' if chap else '') + r'\thepage}')
    return r"""
\documentclass[11pt,a4paper""" + (',twoside' if duplex else '') + r"""]{article}
""" + geo + PREAMBLE_COMMON + body + r"""
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0.25pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{hairline}\leaders\hrule height \headrulewidth\hfill}}
""" + heads + r"""
\fancypagestyle{plain}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}%
  \fancyfoot[C]{\footnotesize\sffamily\color{midgray}\thepage}}
\newcommand{\fvmark}[1]{\markboth{#1}{}}
"""

# ---------------------------------------------------------------- front matter

def cover(mode):
    if mode == 'zh':
        kicker = r'{\sffamily\fontsize{9}{12}\selectfont\color{midgray}新华社\hspace{1em}·\hspace{1em} 2026 年 3 月 14 日}'
        title = (r'{\sffamily\fontsize{24}{37}\selectfont\color{ink}'
                 r'中华人民共和国国民经济和社会发展\par 第十五个五年规划纲要\par}')
        sub = r'{\sffamily\fontsize{15}{20}\selectfont\color{accent}（2026—2030 年）\par}'
        tag = r'{\sffamily\fontsize{9.5}{13}\selectfont\color{midgray}中\hspace{1em} 文\hspace{1em} 版\par}'
        align_open, align_close = r'\begin{center}', r'\end{center}'
    elif mode == 'en':
        kicker = r'{\sffamily\fontsize{9}{12}\selectfont\color{midgray}\MakeUppercase{Xinhua News Agency}\hspace{1em}·\hspace{1em} 14 March 2026}'
        title = (r'{\sffamily\fontsize{21}{31}\selectfont\color{ink}'
                 r'Outline of the 15th Five-Year Plan\par for National Economic and Social Development\par '
                 r'of the People’s Republic of China\par}')
        sub = r'{\sffamily\fontsize{15}{20}\selectfont\color{accent}2026–2030\par}'
        tag = r'{\sffamily\fontsize{9.5}{13}\selectfont\color{midgray}E N G L I S H\hspace{1em} E D I T I O N\par}'
        align_open, align_close = r'{\raggedright', r'}'
    else:
        kicker = r'{\sffamily\fontsize{9}{12}\selectfont\color{midgray}\MakeUppercase{Xinhua News Agency}\hspace{1em}·\hspace{1em} 14 March 2026}'
        title = (r'{\sffamily\fontsize{19}{28}\selectfont\color{ink}'
                 r'中华人民共和国国民经济和社会发展\par 第十五个五年规划纲要\par}')
        sub = (r'{\sffamily\fontsize{11.5}{16}\selectfont\color{midgray}'
               r'Outline of the 15th Five-Year Plan for National Economic and Social\par '
               r'Development of the People’s Republic of China\par}')
        tag = (r'{\sffamily\fontsize{9.5}{13}\selectfont\color{accent}\biEnglish 2026–2030\hspace{1em}·\hspace{1em}'
               r'中 英 对 照 版\hspace{1em}·\hspace{1em} B I L I N G U A L\hspace{1em} E D I T I O N\par}')
        align_open, align_close = r'\begin{center}', r'\end{center}'
    out = [r'\begin{titlepage}', r'\thispagestyle{empty}', r'\vspace*{0.145\textheight}',
           r'{\color{accent}\rule{1.1cm}{2.6pt}}\par\vspace{1.1em}',
           align_open, kicker, r'\par', r'\vspace{2.5em}', title, r'\vspace{1.05em}',
           r'{\color{hairline}\rule{0.34\textwidth}{0.6pt}}\par', r'\vspace{1.15em}',
           sub, r'\vspace{0.85em}', tag, align_close,
           r'\vfill',
           r'{\footnotesize\sffamily\color{lightgray}'
           r'Typeset from the official text published by Xinhua News Agency, 14 March 2026\par{}'
           r'Source: www.locpg.gov.cn\hspace{1em}·\hspace{1em} retrieved 6 November 2026\par}',
           r'\end{titlepage}']
    return '\n'.join(out)


# In the duplex editions the contents and page 1 open on a right-hand page, so the counter's
# parity matches the sheet side; the page this may add before each is left blank.
BLANK_VERSO = r'\clearpage\ifodd\value{page}\else\thispagestyle{empty}\null\clearpage\fi'


def frontmatter(mode, duplex=False):
    out = [r'\clearpage'] + ([BLANK_VERSO] if duplex else []) + [r'\pagenumbering{roman}', r'\setcounter{page}{1}']
    out.append(r'{\sffamily\fontsize{20}{26}\selectfont\color{ink}'
               + ('目　录' if mode == 'zh' else ('Contents' if mode == 'en' else 'Contents\\hspace{1em} 目　录'))
               + r'\par}')
    out.append(r'\vspace{0.55em}{\color{accent}\rule{\textwidth}{1.1pt}}')
    out.append(r'\vspace{1.2em}')
    out.append(r'\renewcommand{\contentsname}{}')
    out.append(r'\vspace{-2.2em}')
    out.append(r'\tableofcontents')
    out.append(BLANK_VERSO if duplex else r'\clearpage')
    return '\n'.join(out)

# ---------------------------------------------------------------- headings

def short_mark(txt, limit=52):
    txt = re.sub(r'\s+', ' ', txt.replace(r'\par ', ' ')).strip()
    if len(txt) <= limit:
        return txt
    cut = txt[:limit]
    if ' ' in cut:
        cut = cut[:cut.rfind(' ')]
    return cut.rstrip(',;:') + '…'


def _split_title_zh(t):
    cl = [c for c in re.split(r'[\u3000 ]+', t) if c]
    if len(cl) >= 2 and len(cl[0]) > 3:
        return cl
    return [t]


def _split_title_en(t):
    if len(t) > 46 and ' and ' in t:
        i = t.index(' and ')
        return [t[:i], 'and ' + t[i + 5:]]
    return [t]


def part_block(mode, b, en):
    zt, et = b['zh'], en or ''
    zm = re.match(r'^第([一二三四五六七八九十]+)篇\u3000(.*)$', zt)
    numeral, ztitle_raw = (zm.group(1), zm.group(2)) if zm else ('', zt)
    zlines = _split_title_zh(ztitle_raw)
    ztitle_plain = '\u3000'.join(zlines)

    enm = re.match(r'^Part\s+(\d+)\s+(.*)$', et)
    enum_ = enm.group(1) if enm else ''
    elines = _split_title_en(enm.group(2) if enm else et)
    etitle_plain = ' '.join(elines)
    if mode == 'bi' and len(elines[0]) < 16:
        elines = [etitle_plain]

    # a part opener is a page of running text, so in the bilingual edition it keeps its number
    # A part opens a new page, unless that would leave the last page of the previous part
    # holding only a few lines; then it shares that page.
    lines = ([r'\Needspace{0.72\textheight}', r'\thispagestyle{plain}'] if mode == 'bi' else
             [r'\clearpage', r'\thispagestyle{empty}'])
    lines += [r'\vspace*{0.06\textheight}', r'\begin{flushleft}']

    if mode in ('zh', 'bi'):
        lab = '第%s篇' % numeral
        lines.append(r'{\sffamily\fontsize{12}{15}\selectfont\color{accent}' + esc(lab) + r'\par}')
        lines.append(r'\vspace{0.85em}')
        size = ('27', '40') if mode == 'zh' else ('19', '28')
        body = (r'\par ').join(texify(c) for c in zlines)
        lines.append(r'{\sffamily\fontsize{%s}{%s}\selectfont\color{ink}' % size + body + r'\par}')
    if mode in ('en', 'bi'):
        if mode == 'en':
            lines.append(r'\vspace{1.0em}')
            lines.append(r'{\sffamily\fontsize{11}{14}\selectfont\color{accent}PART ' + enum_ + r'\par}')
            lines.append(r'\vspace{0.85em}')
            size = ('21', '31')
        else:
            lines.append(r'\vspace{0.5em}')
            lines.append(r'{\sffamily\fontsize{9.5}{12}\selectfont\color{accent}PART ' + enum_ + r'\par}')
            lines.append(r'\vspace{0.4em}')
            size = ('13.5', '19')
        body = (r'\par ').join(texify(c) for c in elines)
        if mode == 'bi':
            body = r'\biEnglish ' + body
        lines.append(r'{\sffamily\fontsize{%s}{%s}\selectfont\color{ink}' % size + body + r'\par}')
    lines += [r'\vspace{2.2em}', r'{\color{accent}\rule{3.4cm}{1.1pt}}', r'\end{flushleft}', r'\vspace{1.9em}']

    if mode == 'en':
        mark = 'Part ' + enum_ + '\u2003' + short_mark(etitle_plain)
    else:
        mark = '第%s篇\u3000' % numeral + ztitle_plain
    lines.append(r'\fvmark{' + esc(mark) + '}')
    lines.append(r'\addcontentsline{toc}{docpart}{' + toc_part(mode, zt, et, numeral) + '}')
    return '\n'.join(lines)


def toc_part(mode, zt, et, numeral):
    if mode == 'zh':
        return r'\textbf{' + esc(re.sub(r'^第\S+篇　', '第' + numeral + '篇 ', zt)) + '}'
    if mode == 'en':
        m = re.match(r'^Part\s+(\d+)\s+(.*)$', et or '')
        return r'\textbf{' + ('Part ' + m.group(1) + ' ' + esc(m.group(2)) if m else esc(et or '')) + '}'
    zm = re.sub(r'^第\S+篇　', '第' + numeral + '篇 ', zt)
    m = re.match(r'^Part\s+(\d+)\s+(.*)$', et or '')
    ent = ('Part ' + m.group(1) + ' ' + m.group(2)) if m else (et or '')
    return (r'\texorpdfstring{\textbf{' + esc(zm) + r'}\\{\footnotesize\protect\biEnglish ' + esc(_en(ent)) + r'}}{'
            + esc(zm) + ' / ' + esc(_en(ent)) + '}')

def chapter_block(mode, b, en):
    zt = b['zh']
    zm = re.match(r'^第([一二三四五六七八九十]+)章　(.*)$', zt)
    numeral, ztitle = (zm.group(1), zm.group(2)) if zm else ('', zt)
    em = re.match(r'^Chapter\s+(\d+)\s+(.*)$', en or '')
    etitle = em.group(2) if em else (en or '')
    etitle = re.sub(r'\s{2,}', ' ', etitle)
    if mode == 'bi':
        n = em.group(1) if em else ''
        plain = '第' + numeral + '章 ' + ztitle + ' / Chapter ' + n + ' ' + _en(etitle)
        toc = (r'\texorpdfstring{\textbf{' + esc('第' + numeral + '章 ' + ztitle) +
               r'}\hspace{1em}{\footnotesize\protect\biEnglish Chapter ' + n + ' ' + esc(_en(etitle)) + r'}}{' + esc(plain) + '}')
        return '\n'.join([
            r'\phantomsection\addcontentsline{toc}{docchapter}{' + toc + '}',
            r'\markright{第' + numeral + r'章\hspace{0.5em}·\hspace{0.5em}Chapter ' + n + '}',
            r'\biChapter{第' + numeral + '章}{' + texify(ztitle) + '}{CHAPTER ' + n + '}{' + texify(_en(etitle)) + '}'])
    lines = [r'\needspace{7\baselineskip}', r'\par\vspace{2.1em}\noindent']
    if mode == 'zh':
        lines.append(r'{\sffamily\fontsize{10.5}{14}\selectfont\color{accent}第' + numeral + r'章\par}')
        lines.append(r'\vspace{0.4em}')
        lines.append(r'{\sffamily\fontsize{18}{26}\selectfont\color{ink}' + texify(ztitle) + r'\par}')
        lines.append(r'\vspace{0.75em}{\color{accent}\rule{2.2cm}{0.9pt}}')
    elif mode == 'en':
        lines.append(r'{\sffamily\fontsize{9.5}{12}\selectfont\color{accent}CHAPTER ' + (em.group(1) if em else '') + r'\par}')
        lines.append(r'\vspace{0.45em}')
        lines.append(r'{\sffamily\fontsize{16.5}{22}\selectfont\color{ink}' + texify(etitle) + r'\par}')
        lines.append(r'\vspace{0.75em}{\color{accent}\rule{2.2cm}{0.9pt}}')
    lines.append(r'\par\vspace{0.9em}')
    if mode == 'zh':
        toc = r'\textbf{' + esc('第' + numeral + '章 ' + ztitle) + '}'
    else:
        toc = r'\textbf{Chapter ' + (em.group(1) if em else '') + ' ' + esc(etitle) + '}'
    lines.append(r'\addcontentsline{toc}{docchapter}{' + toc + '}')
    return '\n'.join(lines)

def section_block(mode, b, en):
    zt = b['zh']
    zm = re.match(r'^第([一二三四五六七八九十]+)节　(.*)$', zt)
    numeral, ztitle = (zm.group(1), zm.group(2)) if zm else ('', zt)
    em = re.match(r'^Section\s+(\d+)\s+(.*)$', en or '')
    etitle = em.group(2) if em else (en or '')
    n = em.group(1) if em else ''
    if mode == 'bi':
        return '\n'.join([
            r'\pdfbookmark[2]{' + esc(ztitle + ' / ' + _en(etitle)) + '}{sec' + b['id'] + '}',
            r'\biSection{第' + numeral + '节　' + texify(ztitle) + r'}{Section ' + n + r'\hspace{0.55em}' +
            texify(_en(etitle)) + '}'])
    lines = [r'\needspace{2\baselineskip}', r'\par\vspace{1.15em}\noindent']
    if mode == 'zh':
        lines.append(r'{\sffamily\fontsize{12}{17}\selectfont\color{ink}第' + numeral + r'节　' +
                     texify(ztitle) + r'\par}')
    else:
        lines.append(r'{\sffamily\fontsize{11.4}{16}\selectfont\color{ink}Section ' + n + r' ' +
                     texify(etitle) + r'\par}')
    lines.append(r'\par\vspace{0.55em}')
    lines.append(r'\pdfbookmark[2]{' + esc((ztitle if mode != 'en' else etitle)) + '}{sec' + b['id'] + '}')
    return '\n'.join(lines)

def doctitle_block(mode, zh, en):
    if mode == 'zh':
        return (r'\par\vspace{0.2em}\begin{center}{\sffamily\fontsize{15}{22}\selectfont\color{ink}'
                + texify(zh) + r'\par}\vspace{0.5em}{\color{accent}\rule{2.4cm}{0.9pt}}\end{center}\vspace{1.4em}')
    if mode == 'en':
        return (r'\par\vspace{0.2em}\begin{center}{\sffamily\fontsize{13.5}{19}\selectfont\color{ink}'
                + texify(en) + r'\par}\vspace{0.5em}{\color{accent}\rule{2.4cm}{0.9pt}}\end{center}\vspace{1.4em}')
    return (r'\par\vspace{0.2em}\begin{center}'
            r'{\sffamily\fontsize{12}{17}\selectfont\color{ink}' + texify(zh) + r'\par}'
            r'\vspace{0.3em}{\sffamily\fontsize{10}{14}\selectfont\color{midgray}' + texify(en) + r'\par}'
            r'\vspace{0.5em}{\color{accent}\rule{2.4cm}{0.9pt}}\end{center}\vspace{1.2em}')


def para_block(mode, b, en):
    zh = texify(b['zh'])
    en_ = texify(en or '')
    if b['zh'].strip() == TITLE_ZH:
        return doctitle_block(mode, b['zh'], en or '')
    if mode == 'zh':
        return r'\par\bodyfont ' + zh + r'\par'
    if mode == 'en':
        return r'\par\noindent\bodyfont ' + en_ + r'\par'
    return r'\biPair{' + zh + '}{' + en_ + '}'

def item_block(mode, b, en):
    zh = re.sub(r'^——\s*', '', b['zh'])
    en_ = re.sub(r'^\s*(—|--|-)\s*', '', en or '')
    zh, en_ = texify(zh), texify(en_)
    if mode == 'zh':
        return (r'\par\noindent\bodyfont\hangindent=2em\hangafter=1 '
                r'\makebox[2em][l]{——}' + zh + r'\par')
    if mode == 'en':
        return (r'\par\noindent\bodyfont\hangindent=1.35em\hangafter=1 '
                r'\makebox[1.35em][l]{\textemdash}' + en_ + r'\par')
    return (r'\biPair{\hangindent=2.3em\hangafter=1 \makebox[2.3em][l]{——}' + zh + '}'
            r'{\hangindent=1.35em\hangafter=1 \makebox[1.35em][l]{\textemdash}' + en_ + '}')

# ---------------------------------------------------------------- boxes

def _colspec(spec, mode='zh'):
    cols = spec.get('cols', [])
    rows = spec.get('rows', [])
    ncol = len(cols)
    if not ncol:
        return None, []
    tw = 15.0                      # usable cm inside the box
    req = []
    key = 'en' if mode == 'en' else 'zh'
    for i in range(ncol):
        cells = [c[i] for c in rows if len(c) > i]
        lens = [len(c.get(key) or '') for c in cells] or [1]
        hl = len(cols[i].get(key) or '')
        need = max(hl, 0.80 * max(lens), 0.95 * (sum(lens) / len(lens)), 3.0)
        req.append(need * (0.235 if mode == 'en' else 0.345) + 0.45)
    lo, hi = 1.62, tw * 0.33
    a = [min(max(r, lo), hi) for r in req]
    for _ in range(60):
        ssum = sum(a)
        diff = tw - ssum
        if abs(diff) < 0.01:
            break
        if diff > 0:               # spare room: give it to columns still below hi
            pool = [i for i in range(ncol) if a[i] < hi - 1e-6]
            if not pool:
                break
            share = diff / len(pool)
            for i in pool:
                a[i] = min(a[i] + share, hi)
        else:                      # too wide: take it from columns above lo
            pool = [i for i in range(ncol) if a[i] > lo + 1e-6]
            if not pool:
                break
            share = (-diff) / len(pool)
            for i in pool:
                a[i] = max(a[i] - share, lo)
    tot = sum(a)
    frac = [x / tot for x in a]
    return ''.join(r'>{\raggedright\arraybackslash}p{\dimexpr%.4f\linewidth-2\tabcolsep\relax}' % f
                   for f in frac), cols


def _cell(mode, c):
    def wrap(t):
        if not t:
            return ''
        return r'{\sffamily\bfseries ' + t + '}' if c.get('b') else t
    if mode == 'zh':
        return wrap(texify(c.get('zh', '')))
    return wrap(texify(c.get('en', '')))


def table_box(mode, spec):
    """A 专栏/图 that is a whole table -> coloured band + longtable (page-breakable)."""
    num = spec.get('number')
    tzh, ten = spec.get('title_zh', ''), spec.get('title_en', '')
    tblk = next((b for b in spec.get('blocks', []) if b.get('t') == 'table'), None)
    if not tblk:
        return box_rendered_plain(mode, spec)
    if mode == 'bi':
        return bi_table_box(spec, tblk)
    if mode == 'zh':
        band = r'{\sffamily\bfseries 专栏 ' + str(num) + r'\hspace{1em} ' + texify(tzh) + '}'
    else:
        band = r'{\sffamily\bfseries Box ' + str(num) + r'\hspace{1em} ' + texify(ten) + '}'
    out = [r'\par\vspace{1.1em}',
           r'\noindent{\colorbox{boxbar}{\parbox{\dimexpr\linewidth-2\fboxsep\relax}{'
           r'\color{white}' + band + r'}}}',
           r'\par\vspace{0.5em}']

    def one(m):
        colspec, cols = _colspec(tblk, m)
        if not colspec:
            return ''
        body = [r'{\small\renewcommand{\arraystretch}{1.30}',
                r'\begin{longtable}{@{}' + colspec + r'@{}}',
                r'\toprule',
                ' & '.join(r'{\sffamily\bfseries\footnotesize ' + _cell(m, c) + '}' for c in cols) +
                r' \\ \midrule\endfirsthead',
                r'\toprule',
                ' & '.join(r'{\sffamily\bfseries\footnotesize ' + _cell(m, c) + '}' for c in cols) +
                r' \\ \midrule\endhead',
                r'\midrule\multicolumn{%d}{r}{\footnotesize\color{midgray}\itshape continued}\endfoot' % len(cols),
                r'\bottomrule\endlastfoot']
        prev0 = None
        for r_ in tblk.get('rows', []):
            cells = list(r_)
            if cells:
                z0 = (cells[0].get('zh') or '').strip()
                if z0 and z0 == prev0 and len(cells) > 1:
                    cells[0] = {'zh': '', 'en': ''}
                else:
                    prev0 = z0
                    cells[0] = {'zh': cells[0].get('zh') or '', 'en': cells[0].get('en') or '', 'b': True}
            body.append(' & '.join(_cell(m, c) for c in cells) + r' \\')
        body.append(r'\end{longtable}}')
        return '\n'.join(body)

    out.append(one(mode))
    notes = tblk.get('notes') or []
    if notes:
        out.append(r'\par\vspace{0.45em}{\footnotesize\color{midgray}')
        for nn in notes:
            out.append(texify(nn.get('zh' if mode == 'zh' else 'en', '')) + r'\par')
        out.append(r'}')
    out.append(r'\par\vspace{0.9em}')
    return '\n'.join(out)


def box_table(mode, spec):
    cols = spec.get('cols', [])
    rows = spec.get('rows', [])
    notes = spec.get('notes', []) or []
    ncol = len(cols)
    if not ncol:
        return ''
    total = r'\linewidth'
    # column widths: first col narrower, numeric cols narrower
    widths, frac = [], []
    for i, c in enumerate(cols):
        lab = (c.get('zh') if mode != 'en' else c.get('en')) or ''
        if i == 0:
            frac.append(0.16)
        elif len(lab) <= 6:
            frac.append(0.13)
        else:
            frac.append(0.0)
    rest = 1.0 - sum(frac)
    big = [i for i, f in enumerate(frac) if f == 0.0]
    if big:
        for i in big:
            frac[i] = rest / len(big)
    else:
        s = sum(frac)
        frac = [f / s for f in frac]
    spec_ = ''.join(r'>{\raggedright\arraybackslash}p{\dimexpr%.4f\linewidth-2\tabcolsep\relax}' % f
                    for f in frac)
    def cell(c):
        if mode == 'zh':
            return texify(c.get('zh', ''))
        if mode == 'en':
            return texify(c.get('en', ''))
        zh = texify(c.get('zh', ''))
        en = texify(c.get('en', ''))
        if not en:
            return zh
        return zh + r'\newline{\footnotesize ' + en + '}'
    out = [r'\par\vspace{0.45em}', r'{\small', r'\renewcommand{\arraystretch}{1.28}',
           r'\noindent\begin{tabular}{@{}' + spec_ + r'@{}}', r'\toprule']
    hdr = ' & '.join(r'{\sffamily\bfseries\footnotesize ' + cell(c) + '}' for c in cols)
    out.append(hdr + r' \\ \midrule')
    prev = [None] * ncol
    for r in rows:
        out.append(' & '.join(cell(c) for c in r) + r' \\')
    out.append(r'\bottomrule')
    out.append(r'\end{tabular}}')
    if notes:
        out.append(r'\par\vspace{0.35em}{\footnotesize\color{midgray}')
        for n in notes:
            if mode == 'zh':
                out.append(texify(n.get('zh', '')) + r'\par')
            elif mode == 'en':
                out.append(texify(n.get('en', '')) + r'\par')
            else:
                out.append(texify(n.get('zh', '')) + r'\par{\color{lightgray}' + texify(n.get('en', '')) + r'}\par')
        out.append(r'}')
    return '\n'.join(out)

def box_rendered_plain(mode, spec):
    return ''


def box_rendered(mode, n, spec):
    if spec is None:
        return (r'\par\vspace{0.8em}{\colorbox{boxbg}{\parbox{0.94\linewidth}{\centering\color{midgray}'
                r'\sffamily [ 专栏 / 图 ' + str(n) + r' — transcription pending ]}}}\par\vspace{0.8em}')
    kind = spec.get('kind', 'box')
    num = spec.get('number')
    if kind == 'table':
        return table_box(mode, spec)
    tzh, ten = spec.get('title_zh', ''), spec.get('title_en', '')
    if kind == 'figure':
        img = bi_map(n) if mode == 'bi' else os.path.join(ROOT, 'src', 'img', '%02d.jpg' % n)
        out = [r'\par\vspace{0.9em}', r'\begin{center}',
               r'\includegraphics[width=\linewidth,height=0.78\textheight,keepaspectratio]{' + img + r'}']
        cap = []
        if mode == 'en':
            cap.append(r'{\footnotesize\sffamily Figure ' + str(num) + r'\hspace{0.6em}'
                       + texify(ten) + r'}')
        elif mode == 'bi':
            cap.append(r'{\footnotesize\sffamily\biEnglish Figure ' + str(num) + r'\hspace{0.6em}'
                       + texify(_en(ten)) + r'}')
        if cap:
            out.append(r'\\[0.5em]' + cap[0])
        _note_zh = '注：图件依原刊复制，采用彩色编码。'
        _note_en = 'Note: reproduced as published; the map uses colour coding.'
        if mode == 'zh':
            out.append(r'\\[0.25em]{\footnotesize\color{midgray}' + texify(_note_zh) + r'}')
        elif mode == 'en':
            out.append(r'\\[0.25em]{\footnotesize\itshape\color{midgray}' + texify(_note_en) + r'}')
        else:
            out.append(r'\\[0.25em]{\footnotesize 注：图件据原刊复制，已调浅以便印刷；图中以颜色区分类别，黑白打印时无法显示。}')
            out.append(r'\\{\footnotesize\itshape Note: published colour map, lightened for print; its colour '
                       r'coding is lost in black and white.}')
        out.append(r'\end{center}')
        if mode == 'bi':
            # a run-in legend, and map to legend in one piece: a stacked legend overran the
            # page on the tallest map and left its last line alone on the next
            leg = [b for b in spec.get('blocks', []) if b.get('t') in ('subhead', 'p', 'bullet') and b.get('en')]
            title = next((b['en'] for b in leg if b.get('t') == 'subhead'), 'Legend')
            items = [texify(_en(b['en'])) for b in leg if b.get('t') != 'subhead']
            items = [r'\mbox{' + i + '}' if len(i) < 24 else i for i in items]     # keeps "Scale 1:27,500,000" whole
            out.append(r'{\centering\footnotesize\biEnglish{\sffamily\bfseries ' + texify(title) + r'}\hspace{0.7em}'
                       + r'~·\ '.join(items) + r'\par}')
            return r'\par\noindent\begin{minipage}{\linewidth}' + '\n'.join(out[1:]) + r'\end{minipage}\par'
        if mode == 'en':
            leg = [b for b in spec.get('blocks', []) if b.get('t') in ('subhead', 'p', 'bullet')]
            if leg:
                out.append(r'\par\vspace{0.2em}{\centering\footnotesize\color{midgray}')
                for b2 in leg:
                    txt = b2.get('en') or ''
                    if not txt:
                        continue
                    if b2.get('t') == 'subhead':
                        out.append(r'\par{\sffamily\bfseries ' + texify(txt) + r'}\par\vspace{0.15em}')
                    else:
                        out.append(r'\par ' + texify(txt) + r'\par')
                out.append(r'}\par')
        out.append(r'\par\vspace{0.9em}')
        return '\n'.join(out)
    if kind == 'missing':
        note = spec.get('note_zh', '') if mode != 'en' else spec.get('note_en', '')
        return (r'\par\vspace{0.8em}\begin{tcolorbox}[colback=boxbg,colframe=boxframe,boxrule=0.3pt,arc=1pt,'
                r'left=6pt,right=6pt,top=5pt,bottom=5pt]{\footnotesize\sffamily\color{midgray}'
                + texify(note) + r'}\end{tcolorbox}\par\vspace{0.8em}')
    if mode == 'bi':
        return bi_box(spec)
    # title band text
    if mode == 'zh':
        band = r'{\sffamily\bfseries 专栏 ' + str(num) + r'\hspace{1em} ' + texify(tzh) + '}'
    else:
        band = r'{\sffamily\bfseries Box ' + str(num) + r'\hspace{1em} ' + texify(ten) + '}'
    body = []
    for blkd in spec.get('blocks', []):
        t = blkd.get('t')
        z = blkd.get('zh' if mode == 'zh' else 'en', '')
        if t == 'table':
            body.append(box_table(mode, blkd))
        elif t == 'head':
            body.append(r'\par\vspace{0.35em}\noindent{\sffamily\bfseries\footnotesize\color{accent}'
                        + texify(blkd.get('num', '')) + r'}\hspace{1em}{\sffamily\bfseries ' + texify(z) + r'}\par\nobreak\vspace{0.1em}')
        elif t == 'subhead':
            body.append(r'\par\vspace{0.3em}\noindent{\sffamily\bfseries\footnotesize ' + texify(z) + r'}\par\vspace{0.1em}')
        elif t == 'bullet':
            body.append(r'\par\noindent\hangindent=1.2em ' + texify(z) + r'\par')
        else:
            body.append(r'\par\noindent ' + texify(z) + r'\par')
    inner = '\n'.join(body)
    return (r'\par\vspace{1.0em}\begin{tcolorbox}[breakable,colback=boxbg,colframe=boxframe,boxrule=0.35pt,'
            r'arc=1.2pt,left=8pt,right=8pt,top=6pt,bottom=7pt,'
            r'title={' + band + r'},fonttitle=\normalsize,'
            r'colbacktitle=boxbar,coltitle=white,bottomtitle=3pt,toptitle=3pt,'
            r'before skip=0pt,after skip=0pt]' + '\n' + inner + '\n' + r'\end{tcolorbox}\par\vspace{0.6em}')


def bi_map(n):
    '''The source maps are pale pastels; a mono printer screens those into an even speckle
    that buries the labels. Lift the tones so the background falls to paper white while
    labels, boundaries and flows stay dark. Hue and geometry are untouched, and the
    published image stays as it is in src/ and in the other two editions.'''
    from PIL import Image
    import numpy as np
    im = Image.open(os.path.join(ROOT, 'src', 'img', '%02d.jpg' % n)).convert('RGB')
    a = np.asarray(im).astype(float) / 255
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    target = np.clip((lum - 0.12) / (0.88 - 0.12), 0, 1) ** 0.75
    out = np.clip(a * ((target + 1e-4) / (lum + 1e-4))[..., None], 0, 1)
    im = Image.fromarray((out * 255 + 0.5).astype('uint8'))
    # the sources are ~150 dpi at this size: enlarge so print edges are smooth, not blocky
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    path = os.path.join(OUT, 'map-%02d.jpg' % n)
    im.save(path, quality=90)
    return path


def bi_box(spec):
    num, out, prev = spec.get('number'), [], None
    out.append(r'\biBoxTitle{专栏 %s}{%s}{BOX %s}{%s}' % (num, texify(spec.get('title_zh', '')), num,
                                                          texify(_en(spec.get('title_en', '')))))
    for blk in spec.get('blocks', []):
        t = blk.get('t')
        zh, en = texify(blk.get('zh', '')), texify(_en(blk.get('en', '')))
        if prev == 'p':
            out.append(r'\biBridge{%s}' % (r'\biParGap' if t == 'p' else r'0.95\biLead'))
        elif prev is not None:
            out.append(r'\biBridge{0.22\biLead}')
        if t == 'head':
            out.append(r'\biBoxHead{%s}{%s}{%s}' % (texify(blk.get('num', '')), zh, en))
        elif t == 'subhead':
            out.append(r'\biBoxSub{%s}{%s}' % (zh, en))
        else:
            out.append(r'\biPair{%s}{%s}' % (zh, en))
        prev = t
    out.append(r'\biBridge{6.5pt}')
    return r'\begin{bibox}' + '\n' + '\n'.join(out) + '\n' + r'\end{bibox}'


def bi_table_box(spec, tblk):
    '''One table for both languages: zh and en stacked in each cell, so a figure is read
    against its own label, instead of two tables a page apart.'''
    num, rows = spec.get('number'), tblk.get('rows', [])
    fracs = (0.15, 0.355, 0.085, 0.085, 0.195, 0.13)
    colspec = ''.join(r'>{\raggedright\arraybackslash}p{\dimexpr%.4f\linewidth-2\tabcolsep\relax}' % f
                      for f in fracs)

    def stack(c, bold=False):
        zh, en = (c.get('zh') or '').strip(), _en(c.get('en') or '').strip()
        cell = texify(zh)
        if en and en != zh and not zh.startswith(en):       # 5 / 5, 2025年 / 2025
            cell += r'\newline{\biEnglish ' + texify(en).replace('/', r'/\allowbreak ') + '}'
        return (r'{\sffamily\bfseries ' + cell + '}') if bold else cell

    head = ' & '.join(stack(c, True) for c in tblk.get('cols', [])) + r' \\'
    out = [r'\Needspace{12\biLead}\par',
           r'{\sffamily\bfseries\noindent{\biLabel 专栏 %s\hspace{1em}BOX %s}\par\vspace{1pt}' % (num, num),
           r'{\fontsize{10.5}{14}\selectfont ' + texify(spec.get('title_zh', '')) + r'\par}',
           r'{\fontsize{10}{13.5}\selectfont ' + texify(_en(spec.get('title_en', ''))) + r'\par}}\nobreak\vspace{3pt}\nobreak',
           r'{\fontsize{8.7}{11.2}\selectfont\hyphenpenalty=10000 \renewcommand{\arraystretch}{1.08}\setlength{\tabcolsep}{4pt}',
           r'\setlength{\LTpre}{0pt}\setlength{\LTpost}{0pt}\setlength{\LTleft}{0pt}\setlength{\LTright}{0pt}',
           r'\begin{longtable}{@{}' + colspec + r'@{}}',
           r'\toprule', head, r'\midrule\endfirsthead',
           r'\toprule', head, r'\midrule\endhead',
           r'\multicolumn{6}{r}{\itshape continued}\endfoot',
           r'\bottomrule\endlastfoot']
    prev0 = None
    for i, r_ in enumerate(rows):
        cells = list(r_)
        z0 = (cells[0].get('zh') or '').strip()
        new_group = z0 != prev0
        if new_group and i:
            out.append(r'\midrule')
        first = stack(cells[0], True) if new_group else ''
        prev0 = z0
        out.append(' & '.join([first] + [stack(c) for c in cells[1:]]) + r' \\')
        # a category label is two or three lines: its first rows stay on one page
        out.append(r'\noalign{\nobreak}' if new_group else r'\noalign{\vskip 1.5pt}')
    out.append(r'\end{longtable}}')
    notes = tblk.get('notes') or []
    if notes:
        out.append(r'\par\vspace{4pt}{\fontsize{8.5}{11.2}\selectfont')
        for nn in notes:
            out.append(texify(nn.get('zh', '')) + r'\par\vspace{1pt}{\biEnglish ' + texify(_en(nn.get('en', ''))) + r'\par}')
        out.append(r'}')
    return '\n'.join(out)

# ---------------------------------------------------------------- assemble

def _bi_paired(b, boxes):
    '''Set in the two columns, so the rule can carry on through it?'''
    if b['type'] in ('chapter', 'section', 'item'):
        return True
    if b['type'] == 'para':
        return b['zh'].strip() != TITLE_ZH
    return b['type'] == 'img' and (boxes.get(b['n']) or {}).get('kind') == 'box'


def bi_gap(prev, cur, boxes):
    '''The space between two blocks. Between paired blocks it carries the rule, so the rule
    only ever stops at genuinely full-width material.'''
    t0, t1 = prev['type'], cur['type']
    if t0 == 'part' or (t0 == 'para' and prev['zh'].strip() == TITLE_ZH):
        return ''                       # these end with their own space
    if t1 == 'chapter':
        g = r'2.6\biLead'
    elif t1 == 'section':
        g = r'1.5\biLead'
    elif t0 == 'chapter':
        g = r'0.5\biLead'
    elif t0 == 'section':
        g = r'0.25\biLead'
    elif t0 == 'img' or t1 == 'img':
        g = r'1.1\biLead'
    elif t0 == t1 == 'item':
        g = r'0.4\biLead'
    else:
        g = r'\biParGap'
    if _bi_paired(prev, boxes) and _bi_paired(cur, boxes):
        # the box title must not be stranded; tested before the gap so a moved box leaves
        # no stub of rule behind
        need = r'\Needspace{9\biLead}' if t1 == 'img' else ''
        return need + r'\biBridge{' + g + '}'
    return r'\par\vspace{' + g + '}'


def build_body(mode, doc, tr, boxes):
    out, prev = [], None
    for b in doc['blocks']:
        t = b['type']
        en = tr.get(b.get('id', ''))
        if mode == 'bi' and prev is not None and t != 'part':
            out.append(bi_gap(prev, b, boxes))
        if t == 'part':
            out.append(part_block(mode, b, en))
        elif t == 'chapter':
            out.append(chapter_block(mode, b, en))
        elif t == 'section':
            out.append(section_block(mode, b, en))
        elif t == 'para':
            out.append(para_block(mode, b, en))
        elif t == 'item':
            out.append(item_block(mode, b, en))
        elif t == 'img':
            out.append(box_rendered(mode, b['n'], boxes.get(b['n'])))
        prev = b
    return '\n'.join(out)

def colophon(mode):
    zh_body = [
        r'The Chinese text reproduced here is the official \emph{Outline of the 15th Five-Year Plan for '
        r'National Economic and Social Development of the People’s Republic of China (2026–2030)}, '
        r'published by Xinhua News Agency on 14 March 2026 and retrieved from the website of the Liaison '
        r'Office of the Central People’s Government in the Hong Kong SAR (www.locpg.gov.cn).',
        r'The English translation was prepared for this edition so that the document can be read alongside '
        r'the original. It aims to be faithful and complete; where the wording is ambiguous, the Chinese '
        r'text is authoritative. The twenty-three \emph{zhuanlan} (policy boxes) and three maps that appear '
        r'as images in the source have been transcribed and translated into set text, so that the whole '
        r'document is searchable.',
        r'Chinese is set in Noto Serif CJK SC, English in Noto Serif; headings are in the Noto Sans family.',
    ]
    zh_zh = [
        r'本文件正文依据新华社 2026 年 3 月 14 日播发的《中华人民共和国国民经济和社会发展第十五个五年规划纲要》，'
        r'取自中央人民政府驻香港特别行政区联络办公室网站（www.locpg.gov.cn）。',
        r'文中二十三幅「专栏」与三幅示意图，原文均为图片，本版已逐条转录排为文字，以便检索与对照。',
        r'排版沿用原件的篇、章、节结构；中文正文用思源宋体（Noto Serif CJK SC），标题用思源黑体。',
    ]
    if mode == 'zh':
        title = r'\sffamily\fontsize{12}{16}\selectfont\color{ink}版\quad 本\quad 说\quad 明'
        body = zh_zh
        note = r'{\footnotesize\color{midgray}中文版 · A4 · 11 pt}'
    elif mode == 'en':
        title = r'\sffamily\fontsize{12}{16}\selectfont\color{ink}About this edition'
        body = zh_body
        note = r'{\footnotesize\color{midgray}English edition · A4 · 10.8 pt}'
    else:
        title = r'\sffamily\fontsize{12}{16}\selectfont\color{ink}About this edition\hspace{1.6em}版\quad 本\quad 说\quad 明'
        body = zh_body + zh_zh[1:]
        note = r'{\footnotesize\color{midgray}Bilingual edition · A4 · 9.5 pt · two columns, Chinese left / English right}'
    out = [r'\clearpage', r'\thispagestyle{empty}', r'\vspace*{0.10\textheight}',
           r'\begin{flushleft}', title, r'\par\vspace{0.55em}',
           r'{\color{accent}\rule{2.6cm}{0.9pt}}', r'\par\vspace{1.4em}',
           r'\begin{minipage}{0.82\textwidth}', r'\footnotesize\color{midgray}\linespread{1.25}\selectfont']
    for p in body:
        if mode == 'bi' and p in zh_body:
            p = r'{\biEnglish ' + p + r'\par}'
        out.append(p + r'\par\vspace{0.8em}')
    out += [note, r'\end{minipage}', r'\end{flushleft}', r'\vfill', r'\null']
    return '\n'.join(out)


def toc_format(mode):
    levels = r'\makeatletter\def\toclevel@docpart{0}\def\toclevel@docchapter{1}\makeatother' if mode == 'bi' else ''
    return levels + r"""
\makeatletter
\renewcommand{\@pnumwidth}{2.5em}
\renewcommand{\@tocrmarg}{2.5em}
\newcommand{\l@docpart}[2]{%
  \addvspace{1.15em}\par\noindent{\raggedright\bfseries\sffamily #1\par}\vspace{0.24em}}
\newcommand{\l@docchapter}[2]{%
  \@dottedtocline{1}{2.2em}{2.6em}{#1}{#2}}
\makeatother
\setcounter{tocdepth}{2}
"""

META = {
    'zh': ('中华人民共和国国民经济和社会发展第十五个五年规划纲要', 'Chinese edition'),
    'en': ('Outline of the 15th Five-Year Plan for National Economic and Social Development of the People’s Republic of China (2026–2030)', 'English edition'),
    'bi': ('十五五规划纲要 / Outline of the 15th Five-Year Plan (2026–2030)', 'Bilingual edition'),
}


def make_tex(mode, doc, tr, boxes, duplex=False):
    mt = META[mode]
    meta = (r'\hypersetup{pdftitle={' + mt[0] + r'},'
            r'pdfsubject={The 15th Five-Year Plan Outline, Xinhua, 14 March 2026 — ' + mt[1] + r'},'
            r'pdfauthor={Typeset edition},'
            r'pdfkeywords={15th Five-Year Plan, China, 2026-2030, bilingual}}')
    parts = [preamble(mode, duplex), toc_format(mode), meta, r'\begin{document}', cover(mode), frontmatter(mode, duplex),
             r'\pagenumbering{arabic}\setcounter{page}{1}']
    parts.append(build_body(mode, doc, tr, boxes))
    parts.append(colophon(mode))
    parts.append(r'\end{document}')
    return '\n'.join(parts)

def compile_tex(name, tex, passes=2):
    path = os.path.join(OUT, name + '.tex')
    open(path, 'w').write(tex)
    ok = True
    for i in range(passes):
        r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error', '-file-line-error',
                            name + '.tex'], cwd=OUT, capture_output=True, text=True)
        if r.returncode != 0:
            ok = False
            tail = r.stdout[-4000:]
            print(tail, file=sys.stderr)
            break
    return ok

def main():
    modes = sys.argv[1:] or ['zh', 'en', 'bi', 'zh-duplex', 'en-duplex', 'bi-duplex']
    doc = load_source()
    body_ids = {b['id'] for b in doc['blocks']
                if b.get('type') in ('para', 'item') and 'id' in b}
    tr = load_translations(body_ids)
    boxes = load_boxes()
    need = sum(1 for b in doc['blocks'] if 'id' in b)
    print('translations: %d / %d blocks (%.0f%%)' % (len(tr), need, 100.0 * len(tr) / need))
    miss_boxes = [n for n in range(1, 27) if n not in boxes]
    print('boxes: %d / 26  missing: %s' % (len(boxes), miss_boxes))
    for name in modes:
        # 'bi-duplex' etc.: the same edition with headers mirrored for long-edge double-sided printing
        mode, _, variant = name.partition('-')
        assert mode in ('zh', 'en', 'bi') and variant in ('', 'duplex'), name
        tex = make_tex(mode, doc, tr, boxes, duplex=variant == 'duplex')
        ok = compile_tex(name, tex, passes=2)
        pdf = os.path.join(OUT, name + '.pdf')
        pages = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
        pg = re.search(r'Pages:\s+(\d+)', pages)
        print('%-9s %s  %s pages' % (name, 'OK ' if ok else 'FAIL', pg.group(1) if pg else '?'))

if __name__ == '__main__':
    main()
