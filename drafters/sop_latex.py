"""SOP LaTeX drafter, Columbia-style personal statement layout.

Style choices, matched to the user's Columbia SOP:
  - Title: "Personal Statement, [Degree] in [Field], [University]"
  - Fancyhdr header on every page with portfolio URL right, page label left
  - Compact leading, no visible section numbers, bold subheads
  - Body encourages **bold** on specifics: medal names, project names, metrics, faculty names

Also compiles the .tex to PDF using pdflatex if available.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path


TEMPLATE = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{parskip}
\usepackage{fancyhdr}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage{lmodern}
\usepackage[dvipsnames]{xcolor}
\hypersetup{colorlinks=true, urlcolor=MidnightBlue, linkcolor=black}

\pagestyle{fancy}
\fancyhf{}
\lhead{\small <<HEADER_LEFT>>}
\rhead{\small \href{https://i-ninte.github.io/portfolio/}{https://i-ninte.github.io/portfolio/}}
\renewcommand{\headrulewidth}{0pt}
\setlength{\headheight}{14pt}

\titleformat{\section}{\normalfont\bfseries\large}{}{0em}{}
\titlespacing*{\section}{0pt}{10pt}{4pt}

\begin{document}

\begin{center}
{\large \textbf{<<TITLE>>}}
\end{center}

<<OPENING>>

<<VISION_PARAGRAPH>>

\section*{<<T1_HEAD>>}
<<T1_BODY>>

\section*{<<T2_HEAD>>}
<<T2_BODY>>

\section*{<<T3_HEAD>>}
<<T3_BODY>>

\section*{Why <<UNIV_SHORT>>}
<<WHY_UNIV>>

\section*{Teaching and Mentorship}
<<TEACHING>>

\section*{Long Term Vision}
<<LONG_TERM>>

\end{document}
"""


def _compile(tex_path: Path) -> Path | None:
    """Compile .tex to .pdf if pdflatex is available. Returns pdf path or None."""
    if not shutil.which("pdflatex"):
        return None
    cwd = tex_path.parent
    # run twice for TOC / fancyhdr stability
    for _ in range(2):
        r = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=cwd, capture_output=True, text=True, timeout=90,
        )
        if r.returncode != 0:
            # write log for debugging then abort
            (cwd / "compile_error.log").write_text(r.stdout + "\n---\n" + r.stderr)
            return None
    pdf = tex_path.with_suffix(".pdf")
    return pdf if pdf.exists() else None


def build(
    university: str,
    university_short: str,
    degree_line: str,
    header_left: str,
    opening: str,
    vision_paragraph: str,
    t1_head: str, t1_body: str,
    t2_head: str, t2_body: str,
    t3_head: str, t3_body: str,
    why_university: str,
    teaching: str,
    long_term: str,
    out_dir: str,
) -> dict:
    title = f"Personal Statement, {degree_line}, {university}"
    tex = (
        TEMPLATE
        .replace("<<TITLE>>", title)
        .replace("<<HEADER_LEFT>>", header_left)
        .replace("<<UNIV_SHORT>>", university_short)
        .replace("<<OPENING>>", opening)
        .replace("<<VISION_PARAGRAPH>>", vision_paragraph)
        .replace("<<T1_HEAD>>", t1_head).replace("<<T1_BODY>>", t1_body)
        .replace("<<T2_HEAD>>", t2_head).replace("<<T2_BODY>>", t2_body)
        .replace("<<T3_HEAD>>", t3_head).replace("<<T3_BODY>>", t3_body)
        .replace("<<WHY_UNIV>>", why_university)
        .replace("<<TEACHING>>", teaching)
        .replace("<<LONG_TERM>>", long_term)
    )
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    tex_path = p / "sop.tex"
    tex_path.write_text(tex)
    pdf_path = _compile(tex_path)
    return {"tex": str(tex_path), "pdf": str(pdf_path) if pdf_path else None}
