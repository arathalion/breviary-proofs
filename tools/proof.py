#!/usr/bin/env python3
"""Build a proof sheet: each column of the scan beside what the engine read.

Usage:
    proof.py <draft.json> ... -o proof.html   one file, images inside it
    proof.py <draft.json> ... -o proof-26/    a folder, images beside it

The draft is about 93 per cent correct, so it cannot be read as a text. It
must be checked. This sheet puts the colour original next to the reading and
marks every word the engine was unsure of, so a person checks a few marked
words instead of re-reading everything.

The sheet also records what the person finds. Click a word to correct it. The
sheet keeps the corrections in the browser and writes them out as JSON, and
`applyfix.py` puts them back into the drafts.

Two shapes of sheet, and the name you give `-o` chooses between them.

A file holds the images inside itself, so it opens anywhere and needs nothing
beside it. It also costs 4 MB a page, because a PNG becomes base64. Part 26 is
87 MB, and the big Propers cannot be built this way at all.

A folder holds the images beside the page, as WebP. The same part is 5 MB, and
every pixel of the scan is still there. Send a folder to another person, or
put it behind a web server. Send a file only if one file matters.
"""
import argparse
import base64
import collections
import hashlib
import html
import json
import re
from pathlib import Path

from PIL import Image

# The crops are 300 ppi PNG, about 1.8 MB each. WebP at this quality holds
# every pixel and costs about 112 KB. Measured on part 26: 65 MB of PNG became
# 5 MB, and the type is still sharp enough to judge a letter.
WEBP = {"quality": 72, "method": 4}

# Below this confidence a word is marked for a person to check. Tesseract
# reports 0 to 100. In this book most correct words score above 90.
CHECK = 80
BAD = 60          # marked more strongly: usually wrong, not merely doubtful

# No OCR engine reads the versicle and response marks at U+2123 and U+211F, so
# they always score badly, and `structure.py` recovers them by rule instead.
# Counting them as work to do would overstate the task and disagree with the
# audit, which leaves them out.
RE_MARKISH = re.compile(r"^[^A-Za-z0-9]{0,3}$")

# The book prints none of these characters on any page, so a token made only
# of them is stray ink or bleed through, and it must come out. Measured over
# all 2,386 pages: 34,713 tokens, about 15 a page. On the four pages Max read
# word by word, these were 79 of the 168 errors, which is 47 per cent of the
# work, and the sheet gave a person no cheap way to remove them.
RE_STRAY = re.compile(r"^[|\\{}~_=<>]{1,3}$")

LIGHT = """--bg:#FCFBF9;--ink:#17140F;--mute:#6E675E;--rule:#E1DBD2;
      --warn:#B03127;--warnbg:#F7E4E2;--bad:#8C1A12;--badbg:#F0C9C4;
      --good:#2E6B4C;--goodbg:#E2F0E7;--bar:#F4F1EC"""

# A page of this sheet stands beside a scan of white paper, and near black
# around a bright scan is hard to look at for an hour. So the dark ground is
# lifted well off black, and the type is softened off white: 12.4 to 1 rather
# than 14.5. Raise --bg to lift it further, and lower it to darken it.
DARK = """--bg:#232019;--ink:#E6E0D4;--mute:#B0A79A;--rule:#3C372E;
      --warn:#F09080;--warnbg:#46281F;--bad:#FFA895;--badbg:#5A2A20;
      --good:#8FD1A8;--goodbg:#223C2E;--bar:#2C2820"""

# Three rules, and the order matters. The browser's own setting comes first,
# and either word from the switch in the bar beats it.
CSS = ("""
:root{""" + LIGHT + """}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){""" + DARK + """}}
:root[data-theme="dark"]{""" + DARK + """}
:root[data-theme="light"]{""" + LIGHT + """}
""" + """
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);margin:0;padding:0 2rem 4rem;
     font:15px/1.5 ui-serif,Georgia,serif}
h1{font-size:1.5rem;font-weight:400;margin:0 0 .3rem}
.sub{color:var(--mute);margin:0 0 1rem;font-size:.9rem;max-width:46rem}
.head{padding-top:2rem}
.page{border-top:2px solid var(--ink);padding:1.2rem 0 2rem;margin-top:1.5rem}
.page h2{font-size:1rem;font-weight:400;color:var(--mute);margin:0 0 .6rem;
         font-family:ui-monospace,Menlo,monospace}
.cols{display:flex;gap:1.5rem;flex-wrap:wrap}
.col{display:flex;gap:1rem;flex:1 1 32rem;min-width:0;
     border:1px solid var(--rule);padding:1rem}
/* A column of this book is tall and narrow, and 17rem shows it at a size a
   person can read. A page not set in columns is nearly square, and the same
   17rem shrinks the whole leaf to a postage stamp. Give the wide ones room:
   the sheet holds one column on those pages, so the room is there. */
.col img.wide{max-width:min(40rem,100%)}
.thin{border:1px dashed var(--warn);color:var(--warn);border-radius:3px;
      padding:.5rem .7rem;font-size:.85rem;max-width:22rem;align-self:flex-start}
/* `width:100%` here stretched every crop to the full 17rem, whatever its own
   size. A crop 4 px wide then rendered 272 px wide and 114,716 px tall, and
   Max asked why the scan was so big to correct against. `width:auto` lets a
   crop keep its own size, and `max-width` still holds the big ones in. */
.col img{max-width:min(17rem,100%);width:auto;height:auto;align-self:flex-start;cursor:zoom-in;
         border:1px solid var(--rule);position:sticky;top:5rem}
/* 300 ppi of 9 pt type does not read at 17 rem. Click the scan to see it at
   the size it was scanned, which is the size a letter must be judged at. */
.col img.big{max-width:none;width:auto;position:static;cursor:zoom-out}
.col:has(img.big){flex-basis:100%}
.read{min-width:0;flex:1}
.read h3{font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;
         color:var(--mute);margin:0 0 .6rem;font-family:ui-monospace,Menlo,monospace}
.layer{margin-bottom:.5rem}
.layer p{margin:0;white-space:pre-wrap;font-size:.9rem}
.red p{color:var(--warn)}
w.g{color:var(--mute);opacity:.65}
w.s{color:var(--mute);opacity:.5;text-decoration:line-through}
w.s:hover{opacity:1}
w.s.ok{text-decoration:none;opacity:1}
w{padding:0 1px;border-radius:2px}
w.wit{border-bottom:2px dotted var(--good);cursor:help}
w.q{background:var(--warnbg);color:var(--warn);border-bottom:1px solid var(--warn)}
w.b{background:var(--badbg);color:var(--bad);border-bottom:2px solid var(--bad);font-weight:600}
w[data-i]{cursor:text}
w[data-i]:hover{box-shadow:0 0 0 2px var(--mute)}
w.g.fixed,w.g.ok{opacity:1}
w.ok{background:none;color:inherit;border-bottom:1px solid var(--rule);font-weight:400}
w.fixed{background:var(--goodbg);color:var(--good);border-bottom:2px solid var(--good);
        font-weight:600}
w.cut{text-decoration:line-through;opacity:.5;background:none;font-weight:400}
w.here{outline:2px solid var(--ink);outline-offset:1px}
w[contenteditable]{background:var(--bg);outline:2px solid var(--ink);outline-offset:1px}
.bar{position:sticky;top:0;z-index:9;background:var(--bar);border-bottom:1px solid var(--rule);
     margin:0 -2rem 0;padding:.6rem 2rem;display:flex;gap:1.4rem;align-items:center;
     flex-wrap:wrap;font:12px/1.4 ui-monospace,Menlo,monospace;color:var(--mute)}
.bar b{color:var(--ink);font-weight:600;font-size:14px}
.bar .sp{flex:1}
.bar a.back{color:var(--mute);text-decoration:none;white-space:nowrap;
     border-bottom:1px solid var(--rule);padding-bottom:1px}
.bar a.back:hover{color:var(--ink);border-bottom-color:var(--ink)}
.bar input{font:12px ui-monospace,Menlo,monospace;background:var(--bg);color:var(--ink);
     border:1px solid var(--rule);border-radius:3px;padding:.35rem .5rem}
button.mark{font-size:15px;line-height:1;padding:.25rem .55rem}
.alarm{background:var(--badbg);color:var(--bad);border-bottom:2px solid var(--bad);
       margin:0 -2rem;padding:.8rem 2rem;font:13px ui-monospace,Menlo,monospace}
button{font:12px ui-monospace,Menlo,monospace;color:var(--ink);background:var(--bg);
       border:1px solid var(--rule);border-radius:3px;padding:.35rem .7rem;cursor:pointer}
button:hover{border-color:var(--mute)}
.pagebar{display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin-bottom:1rem;
         font:12px ui-monospace,Menlo,monospace;color:var(--mute)}
.pagebar label{display:flex;gap:.4rem;align-items:center;cursor:pointer}
.pagebar input[type=text]{flex:1;min-width:14rem;font:12px ui-monospace,Menlo,monospace;
         background:var(--bg);color:var(--ink);border:1px solid var(--rule);
         border-radius:3px;padding:.35rem .5rem}
.pagebar.done{color:var(--good)}
.pagebar button.stray{color:var(--warn);border-color:var(--warn)}
.pagebar button.stray:disabled{color:var(--mute);border-color:var(--rule);
         cursor:default}
.keys{font:12px ui-monospace,Menlo,monospace;color:var(--mute);margin:0 0 1.5rem}
.keys kbd{border:1px solid var(--rule);border-bottom-width:2px;border-radius:3px;
          padding:0 .3rem;color:var(--ink)}
.stats{display:flex;gap:2rem;flex-wrap:wrap;font-size:.85rem;color:var(--mute);
       font-family:ui-monospace,Menlo,monospace;margin-bottom:.5rem}
.stats b{color:var(--ink);font-weight:600}
.struct{border-top:1px dashed var(--rule);margin-top:1.2rem;padding-top:1rem}
.struct h3{font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;
       color:var(--mute);margin:0 0 .7rem;font-family:ui-monospace,Menlo,monospace}
.sline{display:flex;gap:.8rem;align-items:baseline;padding:.08rem 0}
.stag{flex:0 0 7rem;text-align:right;color:var(--mute);
      font:11px ui-monospace,Menlo,monospace}
.stext{white-space:pre-wrap;font-size:.88rem}
.sline.rubric .stext{color:var(--warn)}
.sline.head{opacity:.55}
.sline.open .stag,.sline.heading .stag,.sline.bheading .stag{color:var(--good);
      font-weight:600}
.sline.rule .stext:before{content:"\2500\2500\2500\2500\2500\2500";color:var(--mute)}
.sline{position:relative}
.sline .stext{flex:1}
.sops{opacity:0;display:flex;gap:.2rem;flex:0 0 auto}
.sline:hover .sops,.sline:focus-within .sops,.sline.did .sops{opacity:1}
button.sop{font-size:12px;line-height:1;padding:.15rem .4rem;min-width:1.7rem}
button.sop.on{background:var(--goodbg);color:var(--good);border-color:var(--good)}
.sline.did{background:var(--goodbg)}
.sline.did .stag{color:var(--good);font-weight:600}
.shot{position:relative;display:inline-block;align-self:flex-start}
.guides{position:absolute;inset:0;pointer-events:none}
.col.setting .guides{pointer-events:auto;cursor:col-resize;
     background:linear-gradient(var(--warnbg),var(--warnbg));opacity:.85}
.guide{position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;
     background:var(--warn);pointer-events:auto;cursor:ew-resize;
     transform-origin:center}
.guide:hover{width:6px;margin-left:-3px}
.lean{position:absolute;right:.3rem;bottom:.3rem;pointer-events:auto;
     font:11px ui-monospace,Menlo,monospace;color:var(--warn);
     background:var(--bg);border:1px solid var(--warn);border-radius:3px;
     padding:.1rem .35rem}
.grid{width:100%;overflow-x:auto;margin-top:.6rem}
.grid table{border-collapse:collapse;width:100%}
.grid td{border:1px solid var(--rule);padding:.2rem .4rem;vertical-align:top;
     font-size:.85rem}
.grid tr:hover td{background:var(--bar)}
.col.tabley{flex-basis:100%}
.tagsum{font:11px ui-monospace,Menlo,monospace;color:var(--mute)}
.tagsum b{color:var(--ink);font-weight:600}
code{font-family:ui-monospace,Menlo,monospace;font-size:.9em}
""")

JS = r"""
const SHEET = "__SHEET__";
const INFO = __INFO__;
const STAMP = "__STAMP__";
const KEY = "proof:" + SHEET;

let state = {pages:{}};
try { state = JSON.parse(localStorage.getItem(KEY)) || {pages:{}}; } catch(e) {}

/* Some browsers refuse to keep anything for a page opened from a disk, and
   they refuse it quietly. A person would then proof for an hour and lose all
   of it on the first reload. Say so at the start instead. */
let keeps = true;
try {
  localStorage.setItem("proof:probe", "1");
  localStorage.removeItem("proof:probe");
} catch(e) { keeps = false; }

let held = true;   /* is everything on this sheet in a file yet */

function page(src){
  /* `cols` is left undefined on purpose. An empty list is a real answer — a
     person who takes every guide off a page means none — so it must be told
     apart from "nobody has said yet", which is what seeds the guides the book
     is being set from. Initialising it to [] here defeats that. */
  if(!state.pages[src]) state.pages[src] = {full:false, note:"", fix:{}, ok:{}, str:{}};
  /* Sheets held before the structure gestures existed have no `str`. */
  if(!state.pages[src].str) state.pages[src].str = {};
  return state.pages[src];
}
function save(){
  held = false;
  try{ localStorage.setItem(KEY, JSON.stringify(state)); }catch(e){}
}
addEventListener("beforeunload", e => { if(!held){ e.preventDefault(); e.returnValue = ""; } });

const words = [...document.querySelectorAll("w[data-i]")];
const srcOf = el => el.closest(".page").dataset.src;

/* Stray ink is not a word. It stays out of the word count, out of the error
   rate and out of the Tab pass, and the bar counts it on its own. The Tab
   pass then holds only the words the engine doubted, as it did before. */
const STRAY = {};
for(const el of document.querySelectorAll("w[data-s]")){
  const src = srcOf(el);
  (STRAY[src] = STRAY[src] || new Set()).add(el.dataset.i);
}
const isStray = (src, i) => !!(STRAY[src] && STRAY[src].has(i));

/* How much stray ink is still on this page, said on the button that removes
   it. A person who puts one mark back sees the number go up again. */
function strayCount(d){
  const b = d.querySelector("button.stray");
  if(!b) return;
  const p = page(d.dataset.src);
  let n = 0;
  for(const el of d.querySelectorAll("w[data-s]"))
    if(!p.fix[el.dataset.i] && !p.ok[el.dataset.i]) n++;
  b.textContent = n ? "delete the stray ink (" + n + ")" : "the stray ink is gone";
  b.disabled = !n;
}

/* One press takes every stray mark off the page. The book prints none of
   these characters, so this is safe, and a click on any one puts it back. */
document.addEventListener("click", e => {
  const b = e.target.closest("button.stray");
  if(!b) return;
  const d = b.closest(".page"), p = page(d.dataset.src);
  for(const el of d.querySelectorAll("w[data-s]")){
    const i = el.dataset.i;
    if(p.fix[i] || p.ok[i]) continue;
    p.fix[i] = {was: el.dataset.t, now: ""};
    /* Name the word that follows, as a single correction does. `applyfix.py`
       tests that word before it takes anything out, so it never cuts twice. */
    const near = [...el.parentElement.querySelectorAll("w[data-i]")];
    const nx = near[near.indexOf(el) + 1];
    if(nx) p.fix[i].after = nx.dataset.t;
    el.classList.remove("ok");
    el.classList.add("cut");
  }
  save(); strayCount(d); tally();
});

/* Paint whatever the store already holds. Reload loses nothing. */
function restore(){
  for(const el of words){
    const p = page(srcOf(el)), i = el.dataset.i;
    if(p.fix[i]){ el.textContent = p.fix[i].now || el.dataset.t; mark(el, p.fix[i].now); }
    else if(p.ok[i]){ el.classList.add("ok"); }
  }
  for(const d of document.querySelectorAll(".page")){
    const p = page(d.dataset.src);
    d.querySelector("input[type=checkbox]").checked = p.full;
    d.querySelector("input[type=text]").value = p.note;
    d.querySelector(".pagebar").classList.toggle("done", p.full);
    for(const line of d.querySelectorAll(".sline[data-b]"))
      paintLine(line, p.str[line.dataset.b]);
    for(const col of d.querySelectorAll(".col.tabley")){ drawGuides(col); buildGrid(col); }
    strayCount(d);
  }
  tally();
}

function mark(el, now){
  el.classList.remove("ok");
  el.classList.add(now === "" ? "cut" : "fixed");
}

/* No keyboard carries ℟ and ℣, and no engine reads them, so the forms a
   person can type become the true glyph here. The book uses these marks on a
   great many lines, so typing them must cost nothing.

   The book prints a full stop after the mark, so a person types `R/.` and not
   `R/`. The first rule here demanded that nothing follow the slash, and it
   refused every one of the 17 marks Max typed on 2026-08-17. Take the full
   stop on either side of the slash, and swallow it: `<R>` stands 2,718 times
   in the markup and `<R>.` stands nowhere, so the stop is not part of the
   mark. A slash must still be there, or a real `R.` would become a mark. */
function glyphs(s){
  return s.replace(/\bR\s*(?:\/\.|\.\/|\/)(?=\s|$)/gi, "℟")
          .replace(/\bV\s*(?:\/\.|\.\/|\/)(?=\s|$)/gi, "℣");
}

/* One word, checked. Same text means the engine was right. */
function commit(el){
  el.removeAttribute("contenteditable");
  const was = el.dataset.t;
  const now = glyphs(el.textContent.replace(/\s+/g," ").trim());
  const p = page(srcOf(el)), i = el.dataset.i;
  el.classList.remove("fixed","cut");
  if(now === was){
    delete p.fix[i]; p.ok[i] = 1;
    el.textContent = was;
    el.classList.add("ok");
  } else {
    delete p.ok[i]; p.fix[i] = {was:was, now:now};
    /* A deletion cannot be recognised once it is done, so name the word that
       follows it. `applyfix.py` tests that word before it takes anything out,
       and so it never deletes twice. */
    if(now === ""){
      const near = [...el.parentElement.querySelectorAll("w[data-i]")];
      const nx = near[near.indexOf(el) + 1];
      if(nx) p.fix[i].after = nx.dataset.t;
    }
    el.textContent = now === "" ? was : now;
    mark(el, now);
  }
  if(el.dataset.s) strayCount(el.closest(".page"));
  save(); tally();
}

function edit(el){
  document.querySelectorAll("w.here").forEach(w => w.classList.remove("here"));
  el.classList.add("here");
  el.contentEditable = "true";
  el.focus();
  const r = document.createRange(); r.selectNodeContents(el);
  const s = getSelection(); s.removeAllRanges(); s.addRange(r);
}

/* The next word the engine was unsure of, that nobody has looked at yet. */
function next(from){
  const start = from ? words.indexOf(from) + 1 : 0;
  for(let n = 0; n < words.length; n++){
    const el = words[(start + n) % words.length];
    if((el.dataset.f || el.dataset.w) && !el.classList.contains("ok")
       && !el.classList.contains("fixed")
       && !el.classList.contains("cut")) return el;
  }
  return null;
}
function go(el){
  if(!el){ alert("Every marked word on this sheet is checked."); return; }
  el.scrollIntoView({block:"center", behavior:"smooth"});
  edit(el);
}

document.addEventListener("click", e => {
  const el = e.target.closest("w[data-i]");
  if(el && !el.isContentEditable) edit(el);
  const im = e.target.closest(".col img");
  if(im) im.classList.toggle("big");
});

/* The two buttons put a mark into the word being edited. mousedown must not
   go through: the word would lose the focus, and the sheet would take that
   for the end of the edit. */
for(const b of document.querySelectorAll("button.mark")){
  b.addEventListener("mousedown", e => e.preventDefault());
  b.addEventListener("click", () => {
    const el = document.querySelector("w[contenteditable]");
    if(!el){ alert("Click the word first, then the mark."); return; }
    /* ℟ and ℣ stand instead of the word: the word is the mark, misread. The
       mediant stands beside one, so it goes in front of the word and the word
       stays. `applyfix.py` splits two words out of one at that address. */
    if(b.dataset.at === "start") getSelection().collapseToStart();
    document.execCommand("insertText", false, b.dataset.m);
  });
}
document.addEventListener("keydown", e => {
  const el = e.target.closest ? e.target.closest("w[contenteditable]") : null;
  if(el){
    if(e.key === "Enter"){ e.preventDefault(); commit(el); go(next(el)); }
    else if(e.key === "Escape"){ e.preventDefault(); el.textContent = el.dataset.t; commit(el); go(next(el)); }
    else if(e.key === "Tab"){ e.preventDefault(); commit(el); go(next(el)); }
    return;
  }
  if(e.key === "Tab" && !e.target.matches("input,button")){ e.preventDefault(); go(next(null)); }
});
document.addEventListener("blur", e => {
  const el = e.target.closest ? e.target.closest("w[contenteditable]") : null;
  if(el) commit(el);
}, true);

document.addEventListener("change", e => {
  const d = e.target.closest(".page"); if(!d) return;
  const p = page(d.dataset.src);
  if(e.target.type === "checkbox"){
    p.full = e.target.checked;
    d.querySelector(".pagebar").classList.toggle("done", p.full);
  }
  if(e.target.type === "text") p.note = e.target.value;
  save(); tally();
});

function tally(){
  let checked = 0, wrong = 0, stray = 0, fq = 0, fqw = 0,
      fullPages = 0, fullWords = 0, fullWrong = 0;
  for(const src in INFO){
    const p = state.pages[src]; if(!p) continue;
    /* A stray mark is not a word, and the word count leaves it out. Counting
       it as an error here would put it over a total that does not hold it,
       and the rate would disagree with the audit. Count it on its own. */
    let nfix = 0, nok = 0;
    for(const i in p.fix){ if(isStray(src, i)) stray++; else nfix++; }
    for(const i in p.ok) if(!isStray(src, i)) nok++;
    checked += nfix + nok; wrong += nfix;
    for(const i in p.fix) if(INFO[src].f[i]) fqw++;
    for(const i in p.ok)  if(INFO[src].f[i]) fq++;
    if(p.full){ fullPages++; fullWords += INFO[src].n; fullWrong += nfix; }
  }
  const pc = (a,b) => b ? (a/b*100).toFixed(1) + "%" : "--";
  document.getElementById("t-checked").textContent = checked;
  document.getElementById("t-wrong").textContent = wrong;
  document.getElementById("t-stray").textContent = stray;
  let moved = 0;
  for(const src in state.pages) moved += Object.keys(state.pages[src].str || {}).length;
  document.getElementById("t-struct").textContent = moved;
  document.getElementById("t-marked").textContent = pc(fqw, fq + fqw);
  document.getElementById("t-pages").textContent = fullPages;
  document.getElementById("t-rate").textContent = pc(fullWrong, fullWords);
}

/* Two people can proof the same part, so each correction file says who made
   it. Without a name both files are called the same thing, and one of them
   goes missing on the way back. */
const who = document.getElementById("who");
who.value = localStorage.getItem("proof:who") || "";
who.addEventListener("change", () => localStorage.setItem("proof:who", who.value.trim()));

/* A table is not two columns of prose and it is not a run of words. The book
   sets the calendar and a few other pages as a grid, and the reading comes
   back as one flat stream, which nobody can correct.

   The boundaries are on the page and a person can see them, so a person
   places them. Six attempts to find the shape of a page by measurement have
   failed on this book, and a seventh was tried on 2026-08-17: reading each
   column of the calendar on its own scored worse than reading them together,
   52 and 47 against 62. So this asks a person for four clicks instead.

   A guide is held as a fraction of the width of the scan, so it survives the
   image being shown at any size. */
/* The columns of this book do not always stand upright on the scan. The rows
   deskew to level and the columns still lean: on the calendar, up to 2.55
   degrees, which carries a column 51 px sideways from the top of the page to
   the bottom and drops a word into the cell next door.

   It is a shear, not a rotation, so deskew cannot see it. Nor can anything
   else: two searches for it were tried on 2026-08-17, one over the whole
   measure and one over the narrow columns alone, and the better of them
   agreed with the truth on 3 pages of 10. So a person leans the guides, and
   sees them lie along the printed rules while doing it.

   One page has one lean, and every guide on it shares it. A guide pivots
   about its own middle, so its fraction still means where it crosses the
   middle of the page. */
function leanOf(p, col){
  if(p.lean === undefined && col)
    p.lean = parseFloat(col.querySelector(".shot").dataset.lean || "0") || 0;
  return p.lean || 0;
}

function guidesOf(p, col){
  if(!p.cols && col){
    /* Nothing stored here yet, so open with whatever the book is being set
       from. An empty list is a real answer and is kept as one. */
    try { p.cols = JSON.parse(col.querySelector(".shot").dataset.cols || "[]"); }
    catch(e) { p.cols = []; }
  }
  return p.cols || (p.cols = []);
}

function drawGuides(col){
  const p = page(srcOf(col)), box = col.querySelector(".guides");
  if(!box) return;
  box.innerHTML = "";
  const lean = leanOf(p, col);
  for(const f of guidesOf(p, col)){
    const g = document.createElement("div");
    g.className = "guide";
    g.style.left = (f * 100) + "%";
    g.style.transform = "skewX(" + (-lean) + "deg)";
    g.dataset.f = f;
    box.appendChild(g);
  }
  if(guidesOf(p, col).length){
    const tag = document.createElement("div");
    tag.className = "lean";
    tag.textContent = "lean " + lean.toFixed(2) + "\u00b0";
    tag.title = "drag a guide to lean them all; click here to stand them up";
    box.appendChild(tag);
  }
}

/* Drag a guide and every guide on the page leans with it, because one page
   has one shear. The guide is made to pass through the pointer while staying
   where it is at the middle of the page. */
let leaning = null;
document.addEventListener("mousedown", e => {
  const g = e.target.closest(".col.setting .guide");
  if(!g) return;
  e.preventDefault();
  leaning = {col: g.closest(".col"), box: g.parentNode, f: +g.dataset.f,
             moved: false};
});
document.addEventListener("mousemove", e => {
  if(!leaning) return;
  const r = leaning.box.getBoundingClientRect();
  const midY = r.top + r.height / 2;
  const dy = midY - e.clientY;
  if(Math.abs(dy) < r.height * 0.08) return;   /* too near the pivot to aim */
  leaning.moved = true;
  const x0 = r.left + leaning.f * r.width;
  let deg = Math.atan2(e.clientX - x0, dy) * 180 / Math.PI;
  deg = Math.max(-6, Math.min(6, Math.round(deg * 100) / 100));
  const p = page(srcOf(leaning.col));
  p.lean = deg;
  drawGuides(leaning.col);
});
let dragged = false;
document.addEventListener("mouseup", () => {
  if(!leaning) return;
  const col = leaning.col;
  dragged = leaning.moved;
  leaning = null;
  if(dragged){ buildGrid(col); save(); }
});

/* Put the words where they sit on the page. A line of the page becomes a row
   unless it holds nothing but the last column, in which case it is the rest
   of the row above: on a calendar the day number stands once and the feast
   beside it runs on for three lines. */
function buildGrid(col){
  const p = page(srcOf(col)), grid = col.querySelector(".grid");
  if(!grid) return;
  const cuts = guidesOf(p, col);
  const words = [...col.querySelectorAll("w[data-x]")];
  if(!cuts.length || !words.length){
    for(const el of words) if(el._home) restoreWord(el);
    grid.hidden = true;
    col.querySelector(".read").hidden = false;
    return;
  }
  const nw = +col.querySelector(".shot").dataset.nw || 1;
  const cells = cuts.map(f => f * nw);
  /* Undo the lean before asking which cell a word is in. The guides are drawn
     leaning; the sum is the same either way, and this keeps the arithmetic in
     one place. `as_table` in `structure.py` must do the same. */
  const t = Math.tan(leanOf(p, col) * Math.PI / 180);
  const ys = words.map(el => +el.dataset.y);
  const midY = (Math.min(...ys) + Math.max(...ys)) / 2;
  const cellOf = el => {
    const mid = +el.dataset.x + (+el.dataset.w) / 2 - t * (midY - (+el.dataset.y));
    let c = 0;
    for(const x of cells) if(mid >= x) c++;
    return c;
  };
  const hs = words.map(el => +el.getAttribute("data-h") || 20).sort((a, b) => a - b);
  const med = hs[hs.length >> 1] || 20;
  const byY = [...words].sort((a, b) => (+a.dataset.y - +b.dataset.y)
                                        || (+a.dataset.x - +b.dataset.x));
  const lines = [];
  for(const el of byY){
    const last = lines[lines.length - 1];
    if(last && Math.abs(+el.dataset.y - (+last[0].dataset.y)) <= med * 0.6) last.push(el);
    else lines.push([el]);
  }
  /* One row of a table is not one line of the page. On a calendar the day
     number stands once and the feast beside it runs on for three lines. The
     widest column is the one that runs on, so a line that puts ink anywhere
     to the left of it opens a row, and a line that does not is the rest of
     the row above. */
  const n = cells.length + 1;
  const edges = [0].concat(cells, [nw]);
  let key = 0, widest = 0;
  for(let i = 0; i < n; i++){
    const w = edges[i + 1] - edges[i];
    if(w > widest){ widest = w; key = i; }
  }
  const rows = [];
  for(const ln of lines){
    const row = Array.from({length: n}, () => []);
    for(const el of ln) row[cellOf(el)].push(el);
    /* Anything outside the column that runs on opens a row. Looking only to
       its left collapsed the whole page into one row wherever the widest
       column came early, because the margin of the leaf is column 0 and
       nothing is ever in it. `as_table` in `structure.py` matches this. */
    const opens = row.some((c, i) => i !== key && c.length);
    if(opens || !rows.length) rows.push(row);
    else for(let i = 0; i < n; i++) rows[rows.length - 1][i].push(...row[i]);
  }
  /* A column empty on every row is not a column. At the fold it is the next
     leaf showing at the edge of the scan, which is what Max saw. `as_table`
     in `structure.py` drops it too, so the sheet and the book agree. */
  /* A column that is mostly stray ink is not a column. At the fold it is the
     next leaf showing at the edge of the scan, which is what Max saw on the
     calendar. `as_table` in `structure.py` uses the same test. */
  const live = [];
  for(let i = 0; i < n; i++){
    let all = 0, stray = 0;
    for(const r of rows) for(const el of r[i]){ all++; if(el.dataset.s) stray++; }
    if(all && stray * 2 <= all) live.push(i);
  }
  const shown = live.length && live.length < n
      ? rows.map(r => live.map(i => r[i])) : rows;

  const table = document.createElement("table");
  for(const row of shown){
    const tr = document.createElement("tr");
    for(const cell of row){
      const td = document.createElement("td");
      for(const el of cell){
        if(!el._home) el._home = {parent: el.parentNode, next: el.nextSibling};
        td.appendChild(el);
        td.appendChild(document.createTextNode(" "));
      }
      tr.appendChild(td);
    }
    table.appendChild(tr);
  }
  grid.innerHTML = "";
  grid.appendChild(table);
  grid.hidden = false;
  col.querySelector(".read").hidden = true;
}

function restoreWord(el){
  const h = el._home;
  h.parent.insertBefore(el, h.next);
  el._home = null;
}

document.addEventListener("click", e => {
  const btn = e.target.closest("button.cols");
  if(btn){
    for(const col of btn.closest(".page").querySelectorAll(".col.tabley"))
      col.classList.toggle("setting");
    const on = btn.closest(".page").querySelector(".col.tabley.setting");
    btn.textContent = on ? "done with the columns" : "set the columns";
    return;
  }
  const t = e.target.closest(".lean");
  if(t){
    const col = t.closest(".col"), p = page(srcOf(col));
    p.lean = 0; drawGuides(col); buildGrid(col); save(); return;
  }
  const g = e.target.closest(".guide");
  if(g){
    /* The click that ends a drag is not a click on the guide. */
    if(dragged){ dragged = false; return; }
    const col = g.closest(".col"), p = page(srcOf(col));
    p.cols = guidesOf(p, col).filter(f => f !== +g.dataset.f);
    drawGuides(col); buildGrid(col); save(); return;
  }
  const box = e.target.closest(".col.setting .guides");
  if(box){
    const col = box.closest(".col"), p = page(srcOf(col));
    const r = box.getBoundingClientRect();
    const f = Math.round((e.clientX - r.left) / r.width * 1000) / 1000;
    if(f > 0.01 && f < 0.99 && !guidesOf(p, col).includes(f)){
      p.cols = guidesOf(p, col).concat([f]).sort((a, b) => a - b);
      drawGuides(col); buildGrid(col); save();
    }
  }
});

/* What a person does to a block. The tag is not on offer: the ink colour
   decides it and the ink colour is right. These four say where a line
   belongs, and `open` says the line begins with a drop capital, which a word
   correction cannot record. Pressing the same one again takes it back. */
document.addEventListener("click", e => {
  const b = e.target.closest("button.sop");
  if(!b) return;
  const line = b.closest(".sline"), d = line.closest(".page");
  const p = page(d.dataset.src), i = line.dataset.b, op = b.dataset.op;
  if(p.str[i] && p.str[i].do === op) delete p.str[i];
  else p.str[i] = {do: op, was: line.dataset.t};
  paintLine(line, p.str[i]);
  save(); tally();
});

function paintLine(line, rec){
  line.classList.toggle("did", !!rec);
  for(const b of line.querySelectorAll("button.sop"))
    b.classList.toggle("on", !!rec && rec.do === b.dataset.op);
}

/* The structure stays out of the way until it is asked for. A person putting
   words right does not want it; a person asking why a heading came out cut in
   half does. It is read only for now, and it is here to show where the
   structural faults really are. */
const structBtn = document.getElementById("struct");
function paintStruct(on){
  for(const d of document.querySelectorAll(".struct")) d.hidden = !on;
  structBtn.textContent = on ? "hide the structure" : "show the structure";
}
let showStruct = localStorage.getItem("proof:struct") === "1";
paintStruct(showStruct);
structBtn.onclick = () => {
  showStruct = !showStruct;
  localStorage.setItem("proof:struct", showStruct ? "1" : "");
  paintStruct(showStruct);
};

/* A scan of white paper stands beside every column, and what suits one person
   at night tires another. The browser's own setting holds until a person says
   otherwise here, and then the choice holds over every sheet. */
const THEMES = ["", "light", "dark"];
const THEMEWORD = {"": "theme: browser", "light": "theme: light", "dark": "theme: dark"};
const themeBtn = document.getElementById("theme");
function paint(t){
  if(t) document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
  themeBtn.textContent = THEMEWORD[t];
}
paint(localStorage.getItem("proof:theme") || "");
themeBtn.onclick = () => {
  const now = localStorage.getItem("proof:theme") || "";
  const t = THEMES[(THEMES.indexOf(now) + 1) % THEMES.length];
  localStorage.setItem("proof:theme", t);
  paint(t);
};

function out(){
  const pages = {};
  for(const src in state.pages){
    const p = state.pages[src];
    if(p.full || p.note || Object.keys(p.fix).length || Object.keys(p.ok).length
       || Object.keys(p.str || {}).length || (p.cols || []).length)
      pages[src] = {full:p.full, note:p.note, fix:p.fix, str:p.str || {},
                    cols:p.cols || [], lean:p.lean || 0,
                    checked:Object.keys(p.ok).length};
  }
  return {sheet:SHEET, who:who.value.trim(), pages:pages};
}
/* Two ways to send the work back. The clipboard needs no file, no folder and
   no attachment: the corrections go straight into a message. A browser opens
   the clipboard only to a page at a web address, and not to a page on a disk,
   so the file stays here as the second way. */
function ready(){
  if(who.value.trim()) return true;
  who.focus();
  alert("Put your name in the box first.");
  return false;
}
document.getElementById("send").onclick = async () => {
  if(!ready()) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(out(), null, 1));
    held = true;
    alert("Your corrections are on the clipboard. Paste them into a message "
        + "to Max. They are text, so any message carries them.");
  } catch(e) {
    alert("This browser will not copy. Press download corrections instead.");
  }
};
document.getElementById("save").onclick = () => {
  if(!ready()) return;
  const tag = who.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const blob = new Blob([JSON.stringify(out(), null, 1)], {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "corrections-" + SHEET + "-" + tag + ".json";
  a.click();
  held = true;
};
document.getElementById("nextbtn").onclick = () => go(next(null));
document.getElementById("clear").onclick = () => {
  if(!confirm("Throw away every correction on this sheet?")) return;
  localStorage.removeItem(KEY); held = true; location.reload();
};
/* Was this sheet rebuilt under the work already stored for it? If it was,
   every address may point at a different word now, and going on would write
   corrections against words nobody looked at. */
if(state.stamp && state.stamp !== STAMP){
  const w = document.createElement("div");
  w.className = "alarm";
  w.innerHTML = "This sheet was built again after you last worked on it, and "
    + "the words have moved. What you see marked may sit on the wrong words. "
    + "Press <b>start again</b> before you go on, or send what you have first "
    + "and let Max decide.";
  document.querySelector(".bar").after(w);
}
state.stamp = STAMP;

if(!keeps){
  const w = document.createElement("div");
  w.className = "alarm";
  w.textContent = "This browser will not keep your work. Download the "
    + "corrections often, or open this sheet from a web address instead of a disk.";
  document.querySelector(".bar").after(w);
}
restore();
"""


def embed(path):
    if not path or not Path(path).exists():
        return None
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def convert(path, into):
    """Write one crop beside the page as WebP, and name it.

    A page read again gets a new crop, and the crop can change shape: a page
    named in `onecolumn.txt` goes from half the measure to all of it. Skipping
    a file that already existed left the sheet showing one column of the scan
    beside the text of the whole page, which is worse than showing nothing.
    So the crop wins whenever it is the newer file.
    """
    if not path or not Path(path).exists():
        return None
    out = into / "img" / (Path(path).stem + ".webp")
    if not out.exists() or out.stat().st_mtime < Path(path).stat().st_mtime:
        Image.open(path).convert("RGB").save(out, "WEBP", **WEBP)
    return f"img/{out.name}"


def read_structure(path):
    """The markup `structure.py` inferred for one page, as (tag, lines).

    A line opening with `.` or `#` names a block, and may carry its text on
    the same line. Every plain line after it belongs to that block.
    """
    if not path or not Path(path).exists():
        return []
    head, out = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        # Not `line[:1] in ".#"`: an empty string is a substring of every
        # string, so that form makes a block out of every blank line.
        #
        # The `#` lines that head a page are not blocks of it. `parse` in
        # `applystructure.py` holds them apart in the same way, and the two
        # must agree, because a correction names a block by its number.
        if line.startswith("#") and not out:
            head.append((line, []))
        elif line.startswith((".", "#")):
            tag, _, rest = line.partition(" ")
            out.append((tag, [rest] if rest.strip() else []))
        elif line.strip() and out:
            out[-1][1].append(line)
    return head, out


# What a person can do to a block, and what each one means. There is no way
# to change a tag to anything but `.open`: the tag comes from the ink colour,
# which is measured, and it is right about 99 times in 100. Measured over the
# book on 2026-08-17: of 2,255 blocks opening with a word this book sets in
# red, 21 came out as plain text. What is wrong is which block a line sits in,
# not what the block is called.
OPS = [("join", "\u2934", "join this to the block above"),
       ("up", "\u2191", "move it up"),
       ("down", "\u2193", "move it down"),
       ("open", "\u00b6", "this opens with a drop capital")]


def render_structure(head, blocks):
    """Show what the machine made of the page, and let a person mend it.

    A block carries its place on the page and the text the sheet saw. Both go
    back in the corrections, and `applystructure.py` refuses any change whose
    block no longer says what the sheet saw, exactly as `applyfix.py` does
    with a word.
    """
    rows = []
    for tag, lines in head:
        rows.append(f'<div class="sline head"><span class="stag">'
                    f'{html.escape(tag.split(" ")[0])}</span>'
                    f'<span class="stext">{html.escape(" ".join(tag.split(" ")[1:]))}'
                    f'</span></div>')
    for bi, (tag, lines) in enumerate(blocks):
        kind = tag.lstrip(".#") or "none"
        text = "\n".join(lines).strip()
        ops = "".join(f'<button class="sop" data-op="{o}" title="{t}">{g}</button>'
                      for o, g, t in OPS)
        bar = f'<span class="sops">{ops}</span>'
        rows.append(f'<div class="sline {html.escape(kind)}" data-b="{bi}" '
                    f'data-t="{html.escape(text)}">'
                    f'<span class="stag">{html.escape(tag) or "&nbsp;"}</span>'
                    f'<span class="stext">{html.escape(text)}</span>{bar}</div>')
    return "".join(rows)


def render_words(words, bi, place=False, says=None):
    """Lay the read words out, marking the ones that need a person.

    `data-i` is the address of the word in the draft file: the index of its
    block, then the index of the word in that block. `applyfix.py` writes the
    correction back at that address, so the two must agree.

    On a page that may be a table, each word also carries where it sits on the
    page. The sheet needs that to put it in a cell, and only those pages carry
    it, because four more attributes on 826,000 words is a sheet nobody can
    open.
    """
    out = []
    for wi, w in enumerate(words):
        t = html.escape(w["t"])
        c = w["conf"]
        # A mark keeps its address, so that the words in this sheet stand in
        # the same order as the words in the draft.
        at = (f' data-x="{w["x"]}" data-y="{w["y"]}" data-w="{w["w"]}"'
              f' data-h="{w["h"]}"' if place else "")
        if RE_MARKISH.match(w["t"]):
            # Stray ink the book cannot have printed. A person deletes it, and
            # the page bar deletes every one of them at one press.
            if RE_STRAY.match(w["t"]):
                out.append(f'<w class="s" data-i="{bi}.{wi}" data-t="{t}"{at} '
                           f'data-s="1" title="stray ink: the book prints no '
                           f'such mark. Click it to keep it.">{t}</w>')
                continue
            # A versicle or response mark. The rules in `structure.py` put
            # these back, not a person, so the sheet greys it and counts it
            # as no work.
            out.append(f'<w class="g" data-i="{bi}.{wi}" data-t="{t}"{at} '
                       f'title="a mark, recovered by rule">{t}</w>')
            continue
        cls, flag = "", ""
        if c < BAD:
            cls, flag = " b", ' data-f="1"'
        elif c < CHECK:
            cls, flag = " q", ' data-f="1"'
        # A word the book contradicts is reached by Tab like a marked word,
        # but it is not one of the engine's own doubts, so it is counted apart
        # and the measurements already taken stay comparable.
        w2 = (says or {}).get(f"{bi}.{wi}")
        if w2:
            cls += " wit"
            hint = (f' data-w="1" title="the book says {html.escape(w2["book"])} '
                    f'here {w2["seen"]} times over. Confidence {w2["conf"]}."')
        else:
            hint = f' title="confidence {c:.0f}"'
        out.append(f'<w class="{cls.strip()}" data-i="{bi}.{wi}" data-t="{t}"'
                   f'{at}{flag}{hint}>{t}</w>')
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--images", help="directory holding the colour column crops")
    ap.add_argument("--structured", default=str(Path(__file__).resolve().parent.parent
                                                / "structured"),
                    help="directory holding the markup structure.py inferred")
    ap.add_argument("--witness", default=str(Path(__file__).resolve().parent.parent
                                             / "witness.json"),
                    help="words the book contradicts elsewhere in itself")
    ap.add_argument("--structfix", default=str(Path(__file__).resolve().parent.parent
                                               / "structfix"),
                    help="directory holding what a person said about a page")
    args = ap.parse_args()

    # A name that ends in .html means one file. Anything else means a folder,
    # with the page in it and the images beside it.
    out = Path(args.out)
    folder = out.suffix.lower() != ".html"
    if folder:
        (out / "img").mkdir(parents=True, exist_ok=True)
        page_out = out / "index.html"
    else:
        page_out = out

    used = set()

    # Under this many pixels a crop holds no readable type. It happens where
    # the spread split leaves a strip of the facing leaf and the column finder
    # takes that strip for the page. The book chooses the number itself: of
    # 4,772 crops, 8 are 92 px or narrower and the next is 281. Nothing lies
    # between, so 150 catches every one of the 8 and cannot reach a real
    # column.
    THIN = 150

    # Above this ratio of width to height a crop is a page, not a column of
    # one. A column of this book runs about 0.30; a whole leaf runs 0.62 to
    # 0.75. Nothing in the book falls between.
    PAGEISH = 0.45

    def picture(src, n):
        """The image for one column, and whether it is a whole page."""
        if not args.images:
            return None, False
        crop = Path(args.images) / f"{src}-c{n}.png"
        if not crop.exists():
            return None, False
        w, h = Image.open(crop).size
        wide = h > 0 and w / h > PAGEISH
        picture.natural = w
        picture.thin = w < THIN
        if not folder:
            return embed(crop), wide
        name = convert(crop, out)
        if name:
            used.add(name)
        return name, wide

    # Where the book says something else in the same six words. See
    # `witness.py`. These carry no low confidence: the engine is sure of them,
    # and that is exactly why nothing else on this sheet can see them.
    witness = {}
    if Path(args.witness).exists():
        try:
            witness = json.loads(Path(args.witness).read_text(encoding="utf-8"))
        except ValueError:
            witness = {}

    body, total, flagged, strays, info = [], 0, 0, 0, {}
    alltags = collections.Counter()
    for d in args.drafts:
        data = json.loads(Path(d).read_text(encoding="utf-8"))
        src = data["src"]
        # Blocks arrive in reading order and alternate between the two ink
        # colours, so keep that order. Keying them by colour would collapse
        # every rubric on the page into one. Carry the index of each block, so
        # a correction can name the word it corrects.
        bycol = {}
        for bi, b in enumerate(data["blocks"]):
            bycol.setdefault(b["column"], []).append((bi, b))

        # Where the columns of a table already stand, the sheet opens with
        # them, so a person adjusts what the book is being set from rather
        # than starting again and wondering why the two disagree.
        held = Path(args.structfix) / f"{src}.json"
        setcols, setlean = [], 0.0
        if held.exists():
            try:
                rec = json.loads(held.read_text(encoding="utf-8"))
                setcols = rec.get("cols", [])
                setlean = float(rec.get("lean") or 0)
            except (ValueError, TypeError):
                setcols, setlean = [], 0.0

        pwords, pstray, pflags = 0, 0, {}
        cols_html = []
        anywide = False
        for n in sorted(bycol):
            img, wide = picture(src, n)
            iw = getattr(picture, "natural", 0)
            thin = getattr(picture, "thin", False)
            anywide = anywide or wide
            layers = [f'<h3>column {n}</h3>']
            for bi, b in bycol[n]:
                if not b["words"]:
                    continue
                for wi, w in enumerate(b["words"]):
                    if RE_MARKISH.match(w["t"]):
                        # Stray ink is not a word, so it stays out of the word
                        # count and out of the error rate. The rate then
                        # measures real words, and it agrees with the audit.
                        # It is still work, and the page bar counts it alone.
                        if RE_STRAY.match(w["t"]):
                            pstray += 1
                        continue
                    pwords += 1
                    if w["conf"] < CHECK:
                        pflags[f"{bi}.{wi}"] = 1
                layers.append(
                    f'<div class="layer {b["layer"]}">'
                    f'<p>{render_words(b["words"], bi, wide, witness.get(src))}'
                    f'</p></div>')
            if img and thin:
                # Showing it is worse than saying so: a person cannot check a
                # word against 4 px of paper, and blown up it fills the screen.
                imgtag = (f'<div class="thin">This column of the scan is '
                          f'{iw} px wide, so there is nothing here to check '
                          f'against. The page was split in the wrong place. '
                          f'Say so in the note box.</div>')
            else:
                imgtag = (f'<img class="{"wide" if wide else ""}" src="{img}" '
                          f'loading="lazy" alt="column {n} of the scan">'
                          if img else "")
            # A whole leaf is the shape a table comes on, so those pages get
            # the guides. The scan is wrapped, because a guide is drawn over
            # it and must move with it.
            wrap = (f'<div class="shot" data-nw="{iw}" '
                    f'data-cols="{html.escape(json.dumps(setcols))}" '
                    f'data-lean="{setlean:.3f}">{imgtag}'
                    f'<div class="guides"></div></div>') if wide else imgtag
            cols_html.append(
                f'<div class="col{" tabley" if wide else ""}">{wrap}'
                f'<div class="read">{"".join(layers)}</div>'
                + ('<div class="grid" hidden></div>' if wide else '')
                + '</div>')

        # What the machine made of the page, one stage further down. Every
        # structural fault a person reported lives here and nowhere else.
        shead, marks = read_structure(Path(args.structured) / f"{src}.md")
        tags = collections.Counter(t for t, _ in marks if t.startswith("."))
        for t in tags:
            alltags[t] += 1

        total += pwords
        flagged += len(pflags)
        strays += pstray
        info[src] = {"n": pwords, "f": pflags, "s": pstray}
        esc = html.escape(src)
        body.append(
            f'<div class="page" data-src="{esc}"><h2>{esc}</h2>'
            f'<div class="pagebar">'
            f'<label><input type="checkbox"> I read this page in full</label>'
            + (f'<button class="stray">delete the stray ink ({pstray})</button>'
               if pstray else '')
            + (f'<button class="cols">set the columns</button>' if anywide else '')
            + f'<input type="text" placeholder="a note on this page: a heading cut in half, '
            f'lines missing, the wrong order">'
            f'</div>'
            f'<div class="pagebar tagsum">' + (
                " ".join(f'{html.escape(t)} <b>{c}</b>'
                         for t, c in sorted(tags.items()))
                or "no structure inferred for this page")
            + f'</div>'
            f'<div class="cols">{"".join(cols_html)}</div>'
            + (f'<div class="struct" hidden><h3>what the machine made of this '
               f'page</h3>{render_structure(shead, marks)}</div>' if marks else '')
            + f'</div>')

    # Every correction names a word by its address, and a page read again
    # moves those addresses. A sheet rebuilt under a person's stored work then
    # paints their marks on to the wrong words, and nothing said so: Max lost
    # an afternoon of looking at that on 2026-08-17. Stamp the sheet with what
    # its addresses are, and let the sheet notice for itself.
    stamp = hashlib.sha256(
        "".join(f"{src}:{i['n']}:{len(i['f'])}" for src, i in sorted(info.items()))
        .encode()).hexdigest()[:12]

    pct = flagged / total * 100 if total else 0
    sheet = out.stem.replace("proof-", "")
    head = (
        f'<div class="bar">'
        f'<a class="back" href="../">&larr; all the parts</a>'
        f'<input id="who" placeholder="your name" size="10">'
        f'<span>checked <b id="t-checked">0</b></span>'
        f'<span>wrong <b id="t-wrong">0</b></span>'
        f'<span>stray marks gone <b id="t-stray">0</b></span>'
        f'<span>blocks mended <b id="t-struct">0</b></span>'
        f'<span>of the marked words <b id="t-marked">--</b></span>'
        f'<span>pages read in full <b id="t-pages">0</b></span>'
        f'<span>true error rate <b id="t-rate">--</b></span>'
        f'<span class="sp"></span>'
        f'<button class="mark" data-m="℟" title="response mark (or type R/)">'
        f'℟</button>'
        f'<button class="mark" data-m="℣" title="versicle mark (or type V/)">'
        f'℣</button>'
        f'<button class="mark" data-m="* " data-at="start" '
        f'title="the mediant: the star that divides a psalm verse. It goes in '
        f'front of the word you are on.">*</button>'
        f'<button id="nextbtn">next marked word</button>'
        f'<button id="send">send corrections</button>'
        f'<button id="save">download corrections</button>'
        f'<button id="struct">show the structure</button>'
        f'<button id="theme">theme</button>'
        f'<button id="clear">start again</button>'
        f'</div>'
        f'<div class="head"><h1>Proof sheet</h1>'
        f'<p class="sub">Check the marked words against the scan beside them. Click any '
        f'word to correct it. The sheet remembers what you do, so you can close it and '
        f'come back. Press <b>send corrections</b> when you stop. That puts your work '
        f'on the clipboard, and you paste it into a message.</p>'
        f'<p class="sub">Some marks are struck through. The book prints no such mark, '
        f'so they are stray ink. Press <b>delete the stray ink</b> on a page to take '
        f'them all off it, and click any one of them to keep it.</p>'
        f'<p class="keys"><kbd>Tab</kbd> go to the next marked word &nbsp; '
        f'<kbd>Enter</kbd> keep what you typed and go on &nbsp; '
        f'<kbd>Esc</kbd> the engine was right, go on &nbsp; '
        f'empty the word to delete it &nbsp; '
        f'type two words to add one &nbsp; '
        f'type <kbd>R/</kbd> or <kbd>V/</kbd> for ℟ and ℣</p>'
        f'<p class="keys">a missing character goes in with the word beside it: '
        f'click the word and type <kbd>* Praise</kbd> where the book has '
        f'<kbd>* Praise</kbd>. The <kbd>*</kbd> button does that for you. &nbsp; '
        f'a missing <b>drop capital</b> is not a word: press '
        f'<b>show the structure</b> and then <kbd>¶</kbd> on the line it opens.</p>'
        f'<div class="stats"><span>pages <b>{len(args.drafts)}</b></span>'
        f'<span>words <b>{total}</b></span>'
        f'<span>to check <b>{flagged}</b></span>'
        f'<span>that is <b>{pct:.1f}%</b></span>'
        f'<span>stray marks <b>{strays}</b></span>'
        f'<span>the book disagrees <b>{sum(len(witness.get(s, {})) for s in info)}</b></span>'
        f'<span>this build <b>{stamp}</b></span></div>'
        f'<p class="keys">the machine made of these pages: '
        + " &nbsp; ".join(f'<b>{html.escape(t)}</b> on {c} page{"s" if c > 1 else ""}'
                          for t, c in alltags.most_common(9))
        + '</p></div>')

    js = (JS.replace("__SHEET__", sheet)
            .replace("__INFO__", json.dumps(info, separators=(",", ":")))
            .replace("__STAMP__", stamp))
    page_out.write_text(
        f"<!doctype html><meta charset=utf-8><title>Proof sheet {html.escape(sheet)}</title>"
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<style>{CSS}</style>"
        f'<script>try{{var t=localStorage.getItem("proof:theme");'
        f'if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>'
        f"{head}{''.join(body)}"
        f"<script>{js}</script>", encoding="utf-8")

    # A page that loses a column leaves its old crop behind, and nothing points
    # at it any more. The folder is the sheet, so anything the sheet does not
    # name does not belong in it.
    dropped = 0
    if folder:
        for f in (out / "img").glob("*.webp"):
            if f"img/{f.name}" not in used:
                f.unlink()
                dropped += 1

    size = sum(f.stat().st_size for f in out.rglob("*")) if folder \
        else page_out.stat().st_size
    print(f"wrote {page_out}: {len(args.drafts)} pages, {total} words, "
          f"{flagged} to check ({pct:.1f}%), {size / 1e6:.1f} MB"
          + (f", {dropped} stale images removed" if folder and dropped else ""))


if __name__ == "__main__":
    main()
