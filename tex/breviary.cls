% breviary.cls -- typesetting class for the 1967 Dominican Breviary in English
%
% The book is set in two colours. Black is the text that you say. Red is the
% rubric that tells you how and when to say it. The two mix inside a single
% sentence, so the rubric commands must work inline as well as in a block.
%
% The default trim is 104 x 165 mm. That is not a guess. It is the measured
% size of the original page, taken from the flatbed scans, where the scanner
% glass gives a true physical scale.
%
% Compile with lualatex.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{breviary}[2026/08/16 Dominican Breviary]

\newlength{\brevwidth}\setlength{\brevwidth}{104mm}
\newlength{\brevheight}\setlength{\brevheight}{165mm}
% Print on demand services want a stock size. This is the nearest one.
\DeclareOption{pod}{\setlength{\brevwidth}{4.25in}\setlength{\brevheight}{6.875in}}
% A larger sheet for proof reading on screen, where 7.5pt is tiring.
\DeclareOption{proof}{\setlength{\brevwidth}{5.5in}\setlength{\brevheight}{8.5in}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{book}}
\ProcessOptions\relax

\LoadClass[10pt,twoside]{book}

\RequirePackage{geometry}
% Every value below is measured from the scans, not chosen by eye. The text
% block is 77.5 mm wide, in two columns of 37.6 mm with a 2.2 mm gutter.
% The inner margin is 1 mm wider than the original, to allow for the binding.
\geometry{paperwidth=\brevwidth,paperheight=\brevheight,
          inner=10mm,outer=16.5mm,top=10mm,bottom=14mm,
          headsep=4pt,footskip=10pt}

\RequirePackage{fontspec}
\RequirePackage{xcolor}
\RequirePackage{multicol}
\RequirePackage{lettrine}
\RequirePackage{needspace}
\RequirePackage{graphicx}
\RequirePackage{fancyhdr}
\RequirePackage{microtype}
\RequirePackage{longtable}

% Only three installed faces carry the versicle and response marks at U+2123
% and U+211F. Of those, STIX Two Text is much the closest to the original: it
% is Times-like, sturdy and wide-set, where EB Garamond is narrow and light.
\setmainfont{STIX Two Text}

% A warm vermilion, closer to the ink of the original than a pure red.
\definecolor{rubric}{RGB}{178,34,34}

% ------------------------------------------------------------- type sizes
% The book class offers 10, 11 and 12 point only. A breviary column is about
% 40 mm wide, so it needs much smaller type. We set every size by hand.
% The leading, 9.12pt, is measured from the scans and is reliable: the spacing
% of the lines survives blur. It gives 41 lines to a column, as the original.
%
% The body size was set by comparing renders against the scan at 300dpi, at
% true physical size. Two other methods were tried and both mislead:
%   - characters per line, because the original is justified in a narrow
%     measure with very loose word spacing;
%   - x-height read off the scan, because printed ink spreads and a fresh
%     render is crisp, so the same measurement is not comparable across the
%     two. That method disagreed by about 8 per cent.
\renewcommand\normalsize{%
  \@setfontsize\normalsize{9}{9.12}%
  \abovedisplayskip 4\p@ \@plus2\p@ \@minus2\p@
  \belowdisplayskip \abovedisplayskip
  \abovedisplayshortskip \z@ \@plus2\p@
  \belowdisplayshortskip \abovedisplayskip}
\renewcommand\small{\@setfontsize\small{7.5}{8.6}}
\renewcommand\footnotesize{\@setfontsize\footnotesize{6.6}{7.8}}
\renewcommand\scriptsize{\@setfontsize\scriptsize{5.8}{6.8}}
\renewcommand\large{\@setfontsize\large{10}{11.5}}
\renewcommand\Large{\@setfontsize\Large{12}{13.5}}
\normalsize

% 2.2 mm, as measured.
\setlength{\columnsep}{6.2pt}
\setlength{\columnseprule}{0pt}
\setlength{\parindent}{0.9em}
\setlength{\parskip}{0pt}
\raggedbottom

% A 40 mm column breaks badly under normal settings. Let TeX stretch harder
% and hyphenate more freely than it would in a wide measure.
\emergencystretch=3em
\hyphenpenalty=50
\tolerance=4000
\hbadness=4000

% ---------------------------------------------------------------- rubrics
% \rubric works inline, so a rubric may interrupt a sentence and hand it back.
\newcommand{\rubric}[1]{\textcolor{rubric}{#1}}
% A rubric that stands alone between paragraphs.
\newenvironment{rubricpar}{\par\color{rubric}\ignorespaces}{\par}

% ------------------------------------------------------- versicle, response
% The book always sets these with a following point, and the point is red too,
% so it belongs in the command and not in every line of the transcription.
\newcommand{\vers}{\textcolor{rubric}{\char"2123.}\nobreakspace}
\newcommand{\resp}{\textcolor{rubric}{\char"211F.}\nobreakspace}
% The mediant star divides a psalm verse at the pause. A plain asterisk sits
% too small and too high against 7.5pt text, so we enlarge and drop it.
\newcommand{\med}{\nobreakspace\raisebox{-0.16ex}{\scalebox{1.4}{\textasteriskcentered}}\nobreakspace}

% ------------------------------------------------------------- structure
\newcommand{\hour}[1]{\par\medskip{\centering\large\scshape #1\par}\smallskip}
\newcommand{\heading}[1]{\par\smallskip{\centering\scshape\textcolor{rubric}{#1}\par}\nopagebreak\smallskip}
% Some headings are black and bold rather than red, such as the name of a
% nocturn or the kind of office. They are structure, not matter to be said.
\newcommand{\bheading}[1]{\par\smallskip{\centering\bfseries #1\par}\nopagebreak\smallskip}
\newcommand{\psalmhead}[1]{\par\smallskip{\centering\textcolor{rubric}{Psalm #1}\par}\nopagebreak}
\newcommand{\ant}[1]{\rubric{Ant.\nobreakspace#1}\nobreakspace}
\newcommand{\lesson}[1]{\par\smallskip{\centering\textcolor{rubric}{Lesson #1}\par}\nopagebreak}

% Psalms and canticles open with a drop cap of two lines. A drop cap stranded
% at the foot of a column is a real fault, so demand room for it first.
% The initial is often red rather than black, so the colour is an argument.
\newcommand{\opening}[3][black]{%
  \needspace{3\baselineskip}%
  \lettrine[lines=2,findent=2pt,nindent=0pt]{\textcolor{#1}{#2}}{#3}}

% Matter that spans the full measure, above or between the columns: the
% display title of a part, and the opening rubric that introduces it.
\newcommand{\displaytitle}[1]{%
  \par\vspace{1.6\baselineskip}{\centering\Large #1\par}\vspace{0.5\baselineskip}}
% The rule under a display title is black, unlike the red rules in the text.
\newcommand{\blackrule}{%
  \par\smallskip{\centering\rule{0.30\textwidth}{0.5pt}\par}\smallskip}

% A word that the transcriber could not read. It must stay visible, so that a
% proof-reader can find it against the scan. Never let it print silently.
\newcommand{\unclear}{\textcolor{rubric}{\textbf{[?]}}}

% A thin rule divides one block of matter from the next.
\newcommand{\brevrule}{\par\smallskip{\centering\textcolor{rubric}{\rule{0.35\columnwidth}{0.4pt}}\par}\smallskip}

% ---------------------------------------------------------------- running heads
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyhead[LE]{\footnotesize\thepage}
\fancyhead[RO]{\footnotesize\thepage}
\fancyhead[RE,LO]{\footnotesize\textcolor{rubric}{\nouppercase{\leftmark}}}
\newcommand{\office}[1]{\markboth{#1}{#1}}

% The body of the book runs in two columns.
\newenvironment{brevbody}{\begin{multicols}{2}}{\end{multicols}}

% The book sets a few pages as a grid: the calendar of the year, and the table
% of the movable feasts. A grid spans the measure, so it stands outside the two
% column body, and the width of each column arrives as a fraction of the
% measure, taken from the page it was read off. The printed table then keeps
% the shape the 1967 compositor gave it.
% A `tabular` cannot break across a page, and the calendar of this book runs
% to 45 rows on a leaf 165 mm high. Set as a `tabular` it fills the leaf or
% falls off it, and the whole 24 page calendar could not print. `longtable`
% breaks between rows and carries on overleaf, which is what a calendar wants.
\newenvironment{brevtable}[1]{%
  \par\smallskip\footnotesize
  \setlength{\tabcolsep}{2pt}%
  \setlength{\LTpre}{0pt}\setlength{\LTpost}{0pt}%
  \renewcommand{\arraystretch}{1.04}%
  \begin{longtable}{@{}#1@{}}%
}{%
  \end{longtable}\par\smallskip}
