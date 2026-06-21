"""Corporate buzzword grammar for the CBAG BS core.

An original buzzword lexicon and sentence-template set inspired by the classic
open-source *Corporate Bullshit Generator*. We author our own lists (no upstream
license to track). bs_core.generate fills these templates to produce syntactically
valid, semantically empty corporate sentences — the raw material the LLM refines.

Kept intentionally large so the seed varies (and the LLM doesn't keep echoing the
same few buzzwords).
"""

# Base-form transitive verbs (used after a subject or modal, e.g. "we VERB ...").
VERBS = [
    "leverage", "synergize", "incentivize", "streamline", "monetize",
    "operationalize", "evangelize", "repurpose", "harness", "orchestrate",
    "unlock", "productize", "ideate", "disrupt", "scale", "optimize",
    "transform", "empower", "architect", "future-proof", "benchmark",
    "integrate", "amplify", "accelerate", "actualize", "recontextualize",
    "democratize", "gamify", "rightsize", "pivot", "iterate", "incubate",
    "crowdsource", "reimagine", "supercharge", "catalyze", "unpack", "level-up",
    "socialize", "spearhead", "galvanize", "unbundle", "reengineer",
    "double-down on", "lean into", "right-shore", "dogfood", "moonshot",
    "value-engineer", "hypercharge", "future-cast", "platformize",
]

# Adjectives / modifiers.
ADJECTIVES = [
    "synergistic", "scalable", "value-added", "world-class", "best-of-breed",
    "cutting-edge", "next-generation", "holistic", "agile", "frictionless",
    "customer-centric", "data-driven", "cloud-native", "mission-critical",
    "disruptive", "robust", "seamless", "bleeding-edge", "turnkey",
    "results-driven", "hyper-scalable", "AI-powered", "outside-the-box",
    "end-to-end", "enterprise-grade", "future-ready", "omnichannel", "web-scale",
    "low-latency", "high-velocity", "purpose-built", "north-star", "granular",
    "actionable", "bespoke", "lean", "nimble", "plug-and-play", "best-in-class",
    "mission-driven", "intelligent", "autonomous", "composable", "zero-trust",
    "blockchain-enabled", "quantum-ready", "GenAI-native", "sustainable",
    "human-centered", "hyper-converged", "battle-tested", "self-healing",
    "value-accretive", "category-defining",
]

# Plural / mass nouns and noun phrases.
NOUNS = [
    "synergies", "paradigms", "deliverables", "mindshare", "bandwidth",
    "core competencies", "value propositions", "ecosystems", "verticals",
    "touchpoints", "KPIs", "growth hacks", "best practices", "low-hanging fruit",
    "action items", "stakeholders", "road maps", "north stars", "moonshots",
    "frameworks", "thought leadership", "wheelhouses", "deep dives",
    "circle-backs", "win-wins", "value streams", "learnings", "paradigm shifts",
    "blue-sky thinking", "game changers", "value-adds", "pain points",
    "quick wins", "table stakes", "sea changes", "force multipliers",
    "flywheels", "tailwinds", "swim lanes", "guardrails", "playbooks", "levers",
    "north-star metrics", "value chains", "moats", "unlocks", "optionality",
    "white space", "buy-in", "runway", "escape velocity", "synergy loops",
    "innovation pipelines", "digital transformations", "operating models",
    "growth levers", "value pools", "centers of excellence",
]

# Sentence templates. {V} -> verb, {N} -> noun phrase (may gain adjectives via
# density). Each is written so a base-form verb reads correctly.
TEMPLATES = [
    "we must {V} our {N}.",
    "our {N} will {V} the {N}.",
    "let's {V} {N} and {V} our {N}.",
    "to {V} {N}, we {V} {N}.",
    "moving forward, our {N} will {V} {N}.",
    "we {V} {N} to drive {N}.",
    "at scale, we {V} {N} across all {N}.",
    "the goal is to {V} {N} while we {V} {N}.",
    "we {V} {N} to maximize {N}.",
    "going forward, let's {V} {N} for {N}.",
    "in this new paradigm, we {V} {N} to unlock {N}.",
    "our north star is to {V} {N} through {N}.",
    "we double-click on {N} to {V} {N}.",
    "circling back, we {V} {N} and {V} {N}.",
]
