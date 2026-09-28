"""Affine multilingual-e5-small sur des paires question-article tirées hors du jeu d'évaluation.

1. Haiku 4.5 écrit deux questions pour chacun de 1 000 articles jamais utilisés par le jeu.
2. BM25 donne à chaque question un négatif difficile, entre les rangs 10 et 50.
3. Une boucle contrastive courte entraîne le modèle : chaque question doit être plus proche de
   son article que des autres articles du lot et de son négatif.
"""

import json
import random
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from juriscope.corpus import load_corpus, read_jsonl
from juriscope.evalset.generate_questions import eligible
from juriscope.generate.providers import anthropic_complete, extract_json
from juriscope.paths import DATA, ROOT
from juriscope.retrieve.bm25 import BM25
from juriscope.retrieve.dense import MODEL, passages

MODEL_OUT = DATA / "models" / "e5-small-ft"
PAIRS = DATA / "finetune" / "pairs.jsonl"
REPORT = ROOT / "results" / "finetune" / "entrainement.json"
GENERATOR = "claude-haiku-4-5-20251001"
N_ARTICLES, SEED = 1000, 2026
BATCH, EPOCHS, LEARNING_RATE, SCALE = 32, 1, 2e-5, 20.0
PROMPT = """Voici un article de droit du travail français.

{title}
{text}

Écris deux questions qu'un salarié ou un employeur pourrait poser, dont la réponse se trouve \
dans cet article : la première avec les termes du texte, la seconde avec des mots courants, \
sans jargon juridique. Chaque question se comprend sans avoir lu l'article.

Réponds uniquement en JSON : {{"questions": ["...", "..."]}}"""


def excluded_cids() -> set[str]:
    """Articles sources du jeu d'évaluation : ni positifs ni négatifs, pour éviter toute fuite."""
    generated = read_jsonl(DATA / "questions" / "generated.jsonl")
    return {source["cid"] for row in generated for source in row["sources"]}


def training_articles(corpus: list[dict], excluded: set[str], n: int, seed: int) -> list[dict]:
    candidates = [a for a in corpus if a["cid"] not in excluded and eligible(a)]
    return random.Random(seed).sample(candidates, n)


def write_questions(article: dict, complete: Callable = anthropic_complete) -> list[str]:
    answer = complete(PROMPT.format(title=article["title"], text=article["text"]), GENERATOR)
    questions = (extract_json(answer["output"]) or {}).get("questions", [])
    return [q for q in questions if isinstance(q, str) and q.strip()]


def generate_pairs(articles: list[dict], write: Callable = write_questions) -> list[dict]:
    """Paires question-article ; trois requêtes à la fois, sous la limite de débit de l'API."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        questions = list(pool.map(write, articles))
    return [
        {"cid": article["cid"], "question": question}
        for article, found in zip(articles, questions, strict=True)
        for question in found
    ]


def mine_negatives(pairs: list[dict], search: Callable, excluded: set, seed: int) -> list[dict]:
    """Ajoute à chaque paire un négatif difficile, tiré entre les rangs 10 et 50 de BM25.

    Les premiers rangs contiennent souvent des articles qui répondent aussi : les prendre comme
    négatifs apprendrait au modèle à écarter de bonnes réponses.
    """
    rng = random.Random(seed)
    triplets = []
    for pair in pairs:
        candidates = [
            c for c in search(pair["question"], 50)[10:] if c not in excluded | {pair["cid"]}
        ]
        if candidates:
            triplets.append(pair | {"negative": rng.choice(candidates)})
    return triplets


def train(triplets: list[dict], articles: dict) -> list[float]:
    """Entraîne et enregistre le modèle ; renvoie la perte de chaque lot."""
    # torch n'est installé que dans le workflow finetune
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    def embed(texts: list[str]):
        batch = tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors="pt")
        hidden = model(**batch).last_hidden_state
        mask = batch["attention_mask"].unsqueeze(-1)
        return torch.nn.functional.normalize((hidden * mask).sum(1) / mask.sum(1), dim=-1)

    def passage(cid: str) -> str:
        return f"passage: {passages(articles[cid])[0]}"

    losses = []
    model.train()
    rng = random.Random(SEED)
    for _ in range(EPOCHS):
        rng.shuffle(triplets)
        for start in range(0, len(triplets), BATCH):
            batch = triplets[start : start + BATCH]
            queries = embed([f"query: {t['question']}" for t in batch])
            docs = embed(
                [passage(t["cid"]) for t in batch] + [passage(t["negative"]) for t in batch]
            )
            # le bon document de la question i est le document i ; tous les autres sont négatifs
            scores = SCALE * queries @ docs.T
            loss = torch.nn.functional.cross_entropy(scores, torch.arange(len(batch)))
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            losses.append(loss.item())
    model.save_pretrained(MODEL_OUT)
    tokenizer.save_pretrained(MODEL_OUT)
    return losses


def main() -> None:
    corpus = load_corpus()
    excluded = excluded_cids()
    if not PAIRS.exists():
        pairs = generate_pairs(training_articles(corpus, excluded, N_ARTICLES, SEED))
        PAIRS.parent.mkdir(parents=True, exist_ok=True)
        PAIRS.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs))
    pairs = read_jsonl(PAIRS)
    triplets = mine_negatives(pairs, BM25(corpus).search, excluded, SEED)
    losses = train(triplets, {a["cid"]: a for a in corpus})
    report = {
        "paires": len(pairs),
        "triplets": len(triplets),
        "lots": len(losses),
        "perte_10_premiers_lots": sum(losses[:10]) / 10,
        "perte_10_derniers_lots": sum(losses[-10:]) / 10,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
