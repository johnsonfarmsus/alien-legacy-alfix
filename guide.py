#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
guide.py -- build a browsable Alien Legacy campaign guide (research tree, story-critical
technologies, cinematic triggers) from your own copy of the game (TECH.DAT and
TECHTXT.DAT; identical in v1.01 and v1.10).

Usage:  python3 guide.py [GAME_DIR] [OUT.html]
        GAME_DIR defaults to the folder this script is in; OUT defaults to guide.html
        in the current directory.

No game text is distributed with this script: the page is built locally from the
game files you already have. File formats: see README.md, "Campaign guide".
"""
import json, os, struct, sys


def table(path):
    """Read an Alien Legacy *TXT.DAT string table: u16 count, u16 4, (count+1) u32 offsets, strings."""
    d = open(path, "rb").read()
    n = struct.unpack_from("<H", d, 0)[0]
    offs = struct.unpack_from(f"<{n + 1}I", d, 4)
    base = 4 + 4 * (n + 1)
    return [d[base + offs[i]:base + offs[i + 1]].split(b"\0")[0].decode("latin1") for i in range(n)]


def decode(gamedir):
    """TECH.DAT: 25-byte records. [0] kind, [1] ?, [2:9] science levels, [9:12] prerequisite
    records (0x63 = none), [12] research cost, [13:25] six u16 indexes into TECHTXT.DAT:
    effect, 'still needed' message, progress report, completion report, first encyclopedia
    entry, encyclopedia entry."""
    def find(name):
        for n in (name, name.lower()):
            p = os.path.join(gamedir, n)
            if os.path.exists(p):
                return p
        sys.exit(f"{name} not found in {gamedir}. Pass the Alien Legacy folder as the first argument.")
    txt = table(find("TECHTXT.DAT"))
    t = open(find("TECH.DAT"), "rb").read()
    if len(t) % 25:
        sys.exit(f"TECH.DAT has an unexpected size ({len(t)} bytes)")
    rows = []
    for r in range(len(t) // 25):
        b = t[r * 25:r * 25 + 25]
        if not any(b[:9]) and not any(b[12:]):
            continue                                  # unused slot
        idx = struct.unpack_from("<6H", b, 13)
        rows.append(dict(rec=r, type=b[0], sci=list(b[2:9]),
                         prereq=[x for x in b[9:12] if x != 0x63], cost=b[12],
                         effect=txt[idx[0]], progress=txt[idx[2]], done=txt[idx[3]],
                         ency=txt[idx[5]], blank=[txt[idx[1]], txt[idx[4]]]))
    return rows



# Names aren't stored as text in the game files; these come from each encyclopedia entry.
NAMES = {
    0: "Delton Ore Refiner", 1: "Tiptow Blood Filter", 2: "Eco-Scope", 6: "Trionide Solenoid",
    7: "Super-Dense Micro-Ceramic", 12: "Ramikin Engine", 13: "Delstar Force Generator",
    14: "Shiitake Meat Synthesizer", 15: "Reduplication Theory", 16: "Sarconi Sensor",
    18: "Self-Malleable Die-Casting", 19: "Mass Driver", 20: "Antigen Inhibitor",
    21: "Bi-Focaline Crystal", 22: "Micro-Black Hole Generator", 23: "Bi-Polar Metal Alloy (Bipoma)",
    24: "Tagawa Gyroscope", 25: "Ferro-Sensometer", 26: "Translation Constant", 27: "Electron Damper",
    30: "Solar Collector", 31: "Energy Pulsor", 32: "Quantum Absorber Metal", 33: "McGuffey's Theorem",
    34: "Quark Burner", 35: "Gluon Converter", 36: "Black Hole Furnace", 37: "Sub-Warp Radio",
    38: "Transponder Muffler", 39: "Furgess Supermetal", 40: "Leibowitz Fuel Nozzle",
    42: "Doppler Engine", 43: "Spritzer Quartz", 44: "Bio-Synth Converter", 45: "Smythe Vapor Screen",
    48: "Banos Superconductor", 49: "Tri-Focaline Crystal", 50: "Neusch Focalizer", 51: "Rampal Engine",
    52: "Mintronic Brain", 54: "Feldman Accelerator", 55: "Bio-Plasticene", 56: "Bio-Cene Plastic Metal",
    57: "Monofilament Structure Theory", 60: "Tien-Shou Battery", 61: "Quark Fuser",
    62: "Anti-Matter Fuser", 66: "Shindra Auto-Processor", 67: "Inverse Fusion Reactor",
    68: "Inverse Clone Theory", 72: "Vincenzo Quark Cage", 73: "Alpha Enhancer",
    74: "Humpbert Magnetic Cage", 75: "Unified Field Theory", 78: "Tri-Warp Engine",
    79: "Theta Wave Scrambler", 80: "Telekinetic Amplifier", 84: "Stinson Replicator",
    85: "MacroStructure Stabilizer", 90: "Specter Engine",
}
gamedir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
out = sys.argv[2] if len(sys.argv) > 2 else "guide.html"
rows = decode(gamedir)

data = []
for r in rows:
    data.append(dict(
        rec=r["rec"], name=NAMES.get(r["rec"], f"Technology #{r['rec']}"), type=r["type"], sci=r["sci"], cost=r["cost"],
        pre=r["prereq"], effect=r["effect"].strip(), progress=r["progress"].strip(),
        done=r["done"].strip(),
        # components keep a first encyclopedia entry in slot 5 and a later one in slot 6;
        # upgrades with prerequisites keep their "still needed" message in slot 2
        ency=(r["ency"] or r["blank"][1]).replace("\t", " ").strip(),
        ency_alt=r["blank"][1].strip() if r["ency"] else "",
        needs=r["blank"][0].strip(),
    ))
blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<title>Alien Legacy Campaign Guide</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a research-lab console sheet. Narrow intro column, recipe strip, then a two-column catalogue of tech cards. */
:root {
  --bg: #eef1f4;
  --panel: #f8fafb;
  --ink: #142231;
  --muted: #566577;
  --line: #ccd4dd;
  --accent: #0f6a86;
  --accent-soft: #d6e8ee;
  --heat: 15, 106, 134;
  --t1: #8a3b2e; --t2: #0f6a86; --t3: #6b4f9c; --t4: #5d6b2a;
  --display: "Chakra Petch", "Segoe UI", system-ui, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #0d151d; --panel: #14202b; --ink: #dde6ee; --muted: #93a3b4; --line: #26384a;
    --accent: #5cc0dc; --accent-soft: #173a48; --heat: 92, 192, 220;
    --t1: #e39482; --t2: #5cc0dc; --t3: #b49be0; --t4: #b5c46e;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0d151d; --panel: #14202b; --ink: #dde6ee; --muted: #93a3b4; --line: #26384a;
  --accent: #5cc0dc; --accent-soft: #173a48; --heat: 92, 192, 220;
  --t1: #e39482; --t2: #5cc0dc; --t3: #b49be0; --t4: #b5c46e;
}
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body); }
.wrap { max-width: 1120px; margin: 0 auto; padding-inline: 20px; padding-block: 36px 64px; display: grid; gap: 40px; }
h1, h2, h3 { font-family: var(--display); text-wrap: balance; margin: 0; }
h1 { font-size: clamp(30px, 5vw, 46px); font-weight: 700; letter-spacing: .01em; line-height: 1.05; }
h2 { font-size: 22px; font-weight: 600; }
.eyebrow { font: 500 12px/1 var(--mono); letter-spacing: .14em; text-transform: uppercase; color: var(--accent); }
header { display: grid; gap: 14px; max-width: 68ch; }
header p { margin: 0; color: var(--muted); }
.stats { display: flex; flex-wrap: wrap; gap: 8px 22px; font: 13px var(--mono); color: var(--muted); }
.stats b { color: var(--ink); font-weight: 500; }
section { display: grid; gap: 16px; }
.lede { margin: 0; color: var(--muted); max-width: 68ch; }

.groups { display: grid; gap: 22px; }
.group { display: grid; gap: 8px; }
.group h3 { font-size: 15px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; display: flex; gap: 8px; align-items: baseline; }
.group h3 span { font: 12px var(--mono); color: var(--muted); letter-spacing: 0; }
.group > p { margin: 0; color: var(--muted); font-size: 14px; }
.recipes { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap: 10px; }
.recipe .note { font-size: 13px; color: var(--muted); font-style: italic; }
.fix { margin: 0; font-size: 13px; color: var(--muted); border-left: 2px solid var(--accent); padding-left: 10px; }
.story-line { margin: 0; font-size: 13px; }
.story-line b { font-family: var(--mono); font-weight: 500; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--t3); margin-right: 6px; }
h3.sub { font-size: 16px; font-weight: 600; margin-top: 8px; }
.story-techs { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); gap: 10px; }
.story-tech { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; display: grid; gap: 4px; font-size: 14px; }
.story-tech .tn { font-family: var(--display); font-weight: 600; font-size: 16px; }
.story-tech .fl { font: 12px var(--mono); color: var(--muted); }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); }
table.films { border-collapse: collapse; width: 100%; min-width: 640px; font-size: 14px; }
.films th, .films td { text-align: left; vertical-align: top; padding: 8px 12px; border-bottom: 1px solid var(--line); }
.films th { font: 500 11px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.films tr:last-child td { border-bottom: 0; }
.films td.n { font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
.films td.src { font: 12px var(--mono); color: var(--muted); }
.films tr.quiet td { color: var(--muted); }
.conf { display: inline-block; font: 500 10px var(--mono); letter-spacing: .06em; text-transform: uppercase; padding: 1px 6px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); margin-left: 6px; }
.recipe { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; display: grid; gap: 6px; }
.recipe .in { display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; font-size: 14px; }
.recipe .plus { color: var(--muted); font-family: var(--mono); }
.recipe .out { font-family: var(--display); font-weight: 600; font-size: 16px; color: var(--accent); }
.recipe .out::before { content: "\2192\00a0"; color: var(--muted); font-family: var(--mono); font-weight: 400; }
a.tl { color: inherit; text-decoration: none; border-bottom: 1px dotted var(--muted); }
a.tl:hover, a.tl:focus-visible { color: var(--accent); border-bottom-color: var(--accent); outline: none; }

.controls { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center; position: sticky; top: env(safe-area-inset-top, 0px); z-index: 2; background: var(--bg); padding-block: 10px; border-bottom: 1px solid var(--line); }
.controls input[type=search] { flex: 1 1 220px; min-width: 0; font: 15px var(--body); color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; }
.controls select { font: 14px var(--body); color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 7px 8px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font: 500 13px var(--body); color: var(--muted); background: transparent; border: 1px solid var(--line); border-radius: 999px; padding: 5px 11px; cursor: pointer; }
.chip[aria-pressed="true"] { color: var(--ink); border-color: var(--ink); }
.chip .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.count { font: 13px var(--mono); color: var(--muted); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 500px), 1fr)); gap: 12px; align-items: start; }
.card { background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--tc); border-radius: 6px; padding: 14px 16px; display: grid; gap: 10px; scroll-margin-top: 80px; }
.card:target { box-shadow: 0 0 0 2px var(--accent); }
.head { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
.head h3 { font-size: 18px; font-weight: 600; }
.meta { font: 12px var(--mono); color: var(--muted); white-space: nowrap; }
.type { font: 500 11px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--tc); }
.effect { margin: 0; font-weight: 500; }
.sci { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)) auto; gap: 3px; font-family: var(--mono); font-variant-numeric: tabular-nums; }
.sci div { text-align: center; border-radius: 3px; padding: 3px 0 2px; font-size: 13px; }
.sci small { display: block; font-size: 10px; letter-spacing: .06em; color: var(--muted); }
.sci .cost { padding-inline: 10px; border: 1px solid var(--line); }
.links { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 13px; color: var(--muted); }
.links span b { font-weight: 500; color: var(--ink); }
details { font-size: 14px; }
summary { cursor: pointer; color: var(--accent); font-weight: 500; }
details p { margin: 8px 0 0; max-width: 70ch; }
details p em { font-style: normal; font: 500 11px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); display: block; }
.empty { color: var(--muted); font-style: italic; }
.notes { max-width: 72ch; color: var(--muted); font-size: 14px; }
.notes li { margin-bottom: 6px; }
.notes code { font-family: var(--mono); font-size: 13px; color: var(--ink); }
@media (prefers-reduced-motion: no-preference) { .card:target { transition: box-shadow .2s; } }
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Alien Legacy · CALYPSO mission records</div>
    <h1>Campaign Guide</h1>
    <p>The research tree and the story of the Beta Caeli campaign, decoded from the game itself (versions 1.01 and 1.10). It covers which technologies the plot depends on, when each of the 27 cinematics plays, and every technology the colonists can research, with the lab reports and encyclopedia text from the game.</p>
    <div class="stats" id="stats"></div>
  </header>

  <section aria-labelledby="h-chains">
    <h2 id="h-chains">Breakthroughs</h2>
    <p class="lede">Most technologies only need enough science. These are the ones the game also gates on earlier discoveries: research everything on the left before the lab can start on the right.</p>
    <div class="groups" id="recipes"></div>
  </section>

  <section aria-labelledby="h-story">
    <h2 id="h-story">Story and cinematics</h2>
    <p class="lede">The plot runs on about 80 small event scripts (the <code>RESOURCE.0xx</code> files), each compiled code that the game loads and calls. They check technologies, start crises, queue advisor messages and play the <code>CINEMA.0xx</code> films. These technologies are the ones the crises turn on.</p>
    <div class="story-techs" id="story"></div>
    <h3 class="sub">When each cinematic plays</h3>
    <div class="table-wrap"><table class="films">
      <thead><tr><th scope="col">Film</th><th scope="col">Shows</th><th scope="col">Plays when</th><th scope="col">Triggered by</th></tr></thead>
      <tbody id="films"></tbody>
    </table></div>
    <p class="lede">Other video files: <code>INTRO.DVF</code> is the opening; <code>VIDEO.000</code>–<code>.040</code> are the advisors' talking heads, chosen by which advisor is speaking; <code>ANIM.*</code> are animations used on the planet and space screens.</p>
  </section>

  <section aria-labelledby="h-cat">
    <h2 id="h-cat">All technologies</h2>
    <div class="controls">
      <input type="search" id="q" placeholder="Search names and text, e.g. mushroom" aria-label="Search technologies">
      <div class="chips" id="types" role="group" aria-label="Filter by kind"></div>
      <select id="sort" aria-label="Sort order">
        <option value="rec">Game order</option>
        <option value="cost">Research cost</option>
        <option value="total">Total science</option>
        <option value="name">Name</option>
      </select>
      <span class="count" id="count" aria-live="polite"></span>
    </div>
    <div class="grid" id="grid"></div>
  </section>

  <section aria-labelledby="h-notes">
    <h2 id="h-notes">About the data</h2>
    <ul class="notes">
      <li><b>Source.</b> <code>TECH.DAT</code> holds 96 slots of 25 bytes; 60 are used. Each record has a kind, seven science requirements, up to three prerequisite technologies (<code>0x63</code> = none), a research cost and six indexes into <code>TECHTXT.DAT</code>.</li>
      <li><b>Names</b> aren't stored as text anywhere in the game files (the menus draw them from elsewhere), so each name here is taken from the opening of the technology's encyclopedia entry.</li>
      <li><b>Sciences.</b> The order Astronomy, Geology, Electronics, Chemistry, Biology, Mathematics, Physics is inferred from which column each technology leans on (the plague and the mushroom synthesizer on Biology, the Translation Constant on Mathematics, the black-hole and orbital devices on Astronomy). The game has exactly these seven science text files.</li>
      <li><b>Kinds</b> are the record's first byte. The labels are inferred from the effect lines: <i>Upgrade</i> improves factories, power plants, spacecraft or sensors; <i>Component</i> is a theory or material that "may help improve" later upgrades; <i>Special</i> is a story device; <i>Weapon</i> is the single missile technology.</li>
      <li><b>Unlocked levels</b> come from the game code, not the data files. When research completes, <code>AL.EXE</code> raises the factory level for the Delton Ore Refiner, Self-Malleable Die-Casting, Black Hole Furnace, Shindra Auto-Processor and Stinson Replicator (levels 2 to 6), and the power-plant level for the Trionide Solenoid, Solar Collector, Banos Superconductor, Tien-Shou Battery and Vincenzo Quark Cage. The Shindra Auto-Processor's effect line in the game is wrong: it upgrades factories.</li>
      <li><b>Research cost</b> is the raw value from the record. Its unit isn't documented; it grows steadily through the tree.</li>
      <li><b>Story and cinematics</b> come from the event scripts. Each <code>RESOURCE.0xx</code> file is a small compiled module that calls back into the game through a table of about 150 functions. One of them, which stores a number and has the game play <code>?:cinema.NNN</code> on its next tick, is how the scripts play films; the game itself plays films 7, 17, 18 and 19 after combat. Films marked probable are where the branch was read from the code but what it tests (an Energy Pulsor count; which of two back-to-back films shows what) is inferred. Films 4, 6, 10, 21 and 27 aren't played by any event; they are probably reached only from the PDA library, whose entries carry their own film numbers.</li>
      <li>Prerequisites shown are only those the record enforces. The encyclopedia often mentions other parts too (the Electron Damper "uses the unique properties of the Bi-Focaline Crystal"), but the game doesn't require them.</li>
    </ul>
  </section>
</div>

<script>
const T = __DATA__;
const SCI = [["As","Astronomy"],["Ge","Geology"],["El","Electronics"],["Ch","Chemistry"],["Bi","Biology"],["Ma","Mathematics"],["Ph","Physics"]];
const KIND = {1:["Weapon","--t1"],2:["Upgrade","--t2"],3:["Special","--t3"],4:["Component","--t4"]};
const byRec = Object.fromEntries(T.map(t => [t.rec, t]));
const leadsTo = {};
T.forEach(t => t.pre.forEach(p => (leadsTo[p] ||= []).push(t.rec)));
const maxSci = Math.max(...T.flatMap(t => t.sci));
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const link = r => `<a class="tl" href="#t${r}">${esc(byRec[r].name)}</a>`;
const total = t => t.sci.reduce((a, b) => a + b, 0);

const kinds = [2,4,3,1];
document.getElementById("stats").innerHTML =
  `<span><b>${T.length}</b> technologies</span>` +
  kinds.map(k => `<span><b>${T.filter(t => t.type === k).length}</b> ${KIND[k][0].toLowerCase()}${k===1?"":"s"}</span>`).join("") +
  `<span><b>${T.filter(t => t.pre.length).length}</b> with prerequisites</span>`;

// Installation levels set when research completes: the switch on the technology
// record at obj1 0x307D3 in AL.EXE v1.10 writes the factory level (obj2 0x35D28)
// and the power-plant level (obj2 0x35D1C).
const LEVELS = {0: ["Factory", 2], 18: ["Factory", 3], 36: ["Factory", 4], 66: ["Factory", 5], 84: ["Factory", 6],
                6: ["Power plant", 2], 30: ["Power plant", 3], 48: ["Power plant", 4], 60: ["Power plant", 5], 72: ["Power plant", 6]};
// Breakthroughs grouped by what they improve: the level they set where the code says, else their effect line.
const GROUPS = [
  ["Vehicles", "Spacecraft engines and CALYPSO itself.", t => !LEVELS[t.rec] && /spacecraft|CALYPSO/i.test(t.effect)],
  ["Factories", "Factory productivity.", t => LEVELS[t.rec] ? LEVELS[t.rec][0] === "Factory" : /factor/i.test(t.effect)],
  ["Power plants", "Power-plant energy output.", t => LEVELS[t.rec] ? LEVELS[t.rec][0] === "Power plant" : /power plant/i.test(t.effect)],
  ["Other", "Story devices.", t => true],
];
// Story roles, from the event scripts (RESOURCE.0xx) that test each technology: [role, films].
const STORY = {
  1: ["Without it the crew dies of accelerated aging from the cryo trip; Dr. Tiptow needs a research lab on CALYPSO early on.", [1]],
  2: ["Needed to find habitable sectors; the opening objectives use it to place the second colony on Gaea.", []],
  13: ["Shields Gaea colonies from the hostile biota. Colonies lost to the biota end in the attack film.", [7]],
  31: ["Protects colonies from meteor strikes: with one online the meteor is destroyed, without one the colony is hit.", [16, 24]],
  26: ["Translates the alien messages found on the Gamma 1 sporeship and leads to the Transponder Muffler.", []],
  38: ["Muffles the Gamma 1 signal that destroys robots, vehicles and eventually CALYPSO's hull.", [11, 14]],
  40: ["Missiles: the way to destroy the Gamma 1 sporeship's weak spot and to fight the Empiant fleets.", [5, 13, 17, 18, 19]],
  67: ["Destroys the sporeship, or, after it dives into Beta Caeli, is sent into the star to stop it going critical.", [13, 2]],
  61: ["Its armor insulates the Inverse Fusion Reactor; without it the IFR fails in Beta Caeli's corona.", [2, 25, 3]],
  73: ["Lets the colonists understand the telepathic Empiants.", []],
  79: ["Delivered to Cronus, it ends the war with the Empiants and leads to the alliance.", [9]],
  85: ["The four stabilizers on the Empiant superstructure that CALYPSO is sent through.", []],
  90: ["Faster-than-light travel: the winning ending. A failed attempt can rupture CALYPSO's engines.", [22, 14]],
};
// The CINEMA.0xx films: [number, shows, plays when, triggered by, confidence].
const FILMS = [
  [1, "Command taken from you", "Game over by mutiny: neglecting Gaea's habitats, missing the first colony objectives, the crew riot after the cryo disaster, running out of energy a second time, the Tiptow aging, or massacring civilians in the Fanatic crisis", "RESOURCE.000, 001, 005, 008, 030, 087", "confirmed"],
  [2, "The IFR launched into Beta Caeli", "Final crisis: the Inverse Fusion Reactor is sent into the star, by ship or teleported by the Empiants; the outcome follows", "RESOURCE.065", "confirmed"],
  [3, "Beta Caeli goes critical (part 2)", "The losing end of the final crisis, straight after film 25", "RESOURCE.065", "probable"],
  [4, "", "Not played by any event", "", "none"],
  [5, "The sporeship dives into Beta Caeli", "Time runs out before Gamma 1 is destroyed; starts the final crisis", "RESOURCE.063", "confirmed"],
  [6, "", "Not played by any event", "", "none"],
  [7, "Gaea's lifeforms overrun a colony", "The biota destroy a colony on Gaea", "RESOURCE.051, game", "confirmed"],
  [8, "Cryo-chamber explosion", "A power surge in CALYPSO's cryo-chambers kills sleepers and destroys resources", "RESOURCE.006", "confirmed"],
  [9, "Peace with the Empiants", "The Theta Wave Scrambler is delivered to Cronus", "RESOURCE.070", "confirmed"],
  [10, "", "Not played by any event", "", "none"],
  [11, "A vehicle explodes", "A ship blows up in transit or orbit, robots near Gamma 1 fail under the signal, or the hull-examination team is lost", "RESOURCE.023, 061, 062, 064, 066", "confirmed"],
  [12, "Gamma 1 revealed as a sporeship", "A power flux in the Beta asteroids after the signal source is found", "RESOURCE.063", "confirmed"],
  [13, "The sporeship destroyed", "Missiles hit its weak spot, or the Inverse Fusion Reactor detonates", "RESOURCE.063", "confirmed"],
  [14, "CALYPSO destroyed", "Game over: the Gamma 1 signal tears the hull, the sporeship's explosion catches CALYPSO, or a fusion-engine containment breach during the FTL attempt", "RESOURCE.062, 063, 083", "confirmed"],
  [15, "A comet hits CALYPSO", "Random hazard: hull breach near the ore and energy stores", "RESOURCE.100", "confirmed"],
  [16, "An Energy Pulsor destroys a meteor", "Meteor event at a colony with an Energy Pulsor online", "RESOURCE.021", "probable"],
  [17, "Empiant attack", "Empiant ships emerge from Cronus to attack CALYPSO or a colony, and later Empiant fleet raids", "RESOURCE.070, game", "confirmed"],
  [18, "Empiants defeat the defenders", "An Empiant raid where the defending ships lose", "game", "confirmed"],
  [19, "Defenders destroy the Empiants", "An Empiant raid where the defending ships win", "game", "confirmed"],
  [20, "Memory device recovered on Gamma 1", "The asteroid's memory device is retrieved; the clip is added to the PDA library", "RESOURCE.060", "confirmed"],
  [21, "", "Not played by any event", "", "none"],
  [22, "Victory", "Alliance with the Empiants and faster-than-light travel", "RESOURCE.080", "confirmed"],
  [23, "Habitat explosion on Gaea", "Random hazard: an environmental-control explosion in a Gaea habitat", "RESOURCE.102", "confirmed"],
  [24, "A meteor storm hits a colony", "Meteor event at a colony without a working Energy Pulsor", "RESOURCE.021", "probable"],
  [25, "Beta Caeli goes critical (part 1)", "The sporeship has burrowed into the star and nothing has stopped it (\"CAPTAIN! LOOK!\")", "RESOURCE.065", "probable"],
  [26, "Power-plant explosion on Gaea", "Random hazard: a Gaea power plant explodes and energy is lost", "RESOURCE.101", "confirmed"],
  [27, "", "Not played by any event", "", "none"],
];
const NOTE = {66:"The game's effect line says power plants, but completing it raises the factory level to 5 and leaves power plants alone. Its lab and encyclopedia text describe factory robots."};
const recipe = t =>
  `<div class="recipe"><div class="in">${t.pre.map(link).join('<span class="plus">+</span>')}</div>` +
  `<div class="out"><a class="tl" href="#t${t.rec}">${esc(t.name)}</a></div>` +
  (NOTE[t.rec] ? `<div class="note">${esc(NOTE[t.rec])}</div>` : "") + `</div>`;
let left = T.filter(t => t.pre.length);
document.getElementById("recipes").innerHTML = GROUPS.map(([name, blurb, test]) => {
  const mine = left.filter(test); left = left.filter(t => !mine.includes(t));
  return mine.length ? `<div class="group"><h3>${name} <span>${mine.length}</span></h3><p>${blurb}</p>` +
    `<div class="recipes">${mine.map(recipe).join("")}</div></div>` : "";
}).join("");

const filmRef = n => `<a class="tl" href="#film${n}">${n}</a>`;
document.getElementById("story").innerHTML = Object.entries(STORY).map(([rec, [role, films]]) =>
  `<div class="story-tech"><div class="tn">${byRec[rec] ? link(+rec) : "#" + rec}</div><div>${esc(role)}</div>` +
  (films.length ? `<div class="fl">Films ${films.map(filmRef).join(", ")}</div>` : "") + `</div>`).join("");
const CONF = {confirmed: "", probable: '<span class="conf">probable</span>', none: ""};
document.getElementById("films").innerHTML = FILMS.map(([n, shows, when, src, conf]) =>
  `<tr id="film${n}" class="${conf === "none" ? "quiet" : ""}"><td class="n">CINEMA.${String(n).padStart(3, "0")}</td>` +
  `<td>${esc(shows) || "—"}${CONF[conf]}</td><td>${esc(when)}</td><td class="src">${esc(src)}</td></tr>`).join("");

const active = new Set(kinds);
document.getElementById("types").innerHTML = kinds.map(k =>
  `<button class="chip" type="button" id="k${k}" data-k="${k}" aria-pressed="true"><span class="dot" style="background:var(${KIND[k][1]})"></span>${KIND[k][0]}</button>`).join("");

function card(t) {
  const [kname, kvar] = KIND[t.type];
  const cells = t.sci.map((v, i) => {
    const a = v ? (0.12 + 0.75 * Math.sqrt(v / maxSci)).toFixed(2) : 0;
    const fg = v && a > 0.5 ? "var(--panel)" : "var(--ink)";
    return `<div title="${SCI[i][1]}: ${v}" style="background:rgba(var(--heat),${a});color:${v ? fg : "var(--muted)"}"><small>${SCI[i][0]}</small>${v || "·"}</div>`;
  }).join("");
  const lt = leadsTo[t.rec] || [];
  const links = [
    LEVELS[t.rec] ? `<span><b>Unlocks</b> ${LEVELS[t.rec][0]} level ${LEVELS[t.rec][1]}</span>` : "",
    t.pre.length ? `<span><b>Requires</b> ${t.pre.map(link).join(", ")}</span>` : "",
    lt.length ? `<span><b>Leads to</b> ${lt.map(link).join(", ")}</span>` : "",
  ].join("");
  const para = (label, s) => s ? `<p><em>${label}</em>${esc(s)}</p>` : "";
  return `<article class="card" id="t${t.rec}" style="--tc:var(${kvar})">
    <div class="head"><div><div class="type">${kname}</div><h3>${esc(t.name)}</h3></div><span class="meta">#${t.rec}</span></div>
    <p class="effect">${esc(t.effect)}</p>
    ${STORY[t.rec] ? `<p class="story-line"><b>Story</b>${esc(STORY[t.rec][0])}</p>` : ""}
    ${NOTE[t.rec] ? `<p class="fix">${esc(NOTE[t.rec])}</p>` : ""}
    <div class="sci">${cells}<div class="cost" title="Research cost"><small>Cost</small>${t.cost}</div></div>
    ${links ? `<div class="links">${links}</div>` : ""}
    <details><summary>Lab reports and encyclopedia</summary>
      ${para("While researching", t.progress)}${para("Still needed", t.needs)}${para("Completed", t.done)}
      ${para("Encyclopedia", t.ency)}${para("Encyclopedia, earlier entry", t.ency_alt)}
    </details></article>`;
}

const q = document.getElementById("q"), sortSel = document.getElementById("sort");
function render() {
  const s = q.value.trim().toLowerCase();
  const key = sortSel.value;
  const list = T.filter(t => active.has(t.type) && (!s ||
      [t.name, t.effect, t.progress, t.done, t.ency, t.ency_alt, t.needs].join(" ").toLowerCase().includes(s)))
    .sort((a, b) => key === "name" ? a.name.localeCompare(b.name)
                  : key === "cost" ? a.cost - b.cost || a.rec - b.rec
                  : key === "total" ? total(a) - total(b) || a.rec - b.rec : a.rec - b.rec);
  document.getElementById("grid").innerHTML = list.length ? list.map(card).join("")
    : `<p class="empty">No technology matches "${esc(q.value)}". Clear the search or turn a kind back on.</p>`;
  document.getElementById("count").textContent = `${list.length} of ${T.length}`;
}
document.getElementById("types").addEventListener("click", e => {
  const b = e.target.closest(".chip"); if (!b) return;
  const k = +b.dataset.k, on = b.getAttribute("aria-pressed") !== "true";
  b.setAttribute("aria-pressed", on); on ? active.add(k) : active.delete(k); render();
});
q.addEventListener("input", render); sortSel.addEventListener("change", render);
document.addEventListener("click", e => {
  const a = e.target.closest("a.tl"); if (!a) return;
  const id = a.getAttribute("href").slice(1);
  if (!document.getElementById(id)) { q.value = ""; active.clear(); kinds.forEach(k => { active.add(k); document.getElementById("k"+k).setAttribute("aria-pressed","true"); }); render(); }
});
render();
</script>
"""
open(out, "w", encoding="utf-8").write(HTML.replace("__DATA__", blob))
print(f"wrote {out}: {len(data)} technologies")
