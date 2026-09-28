"""Agent LangGraph : à chaque tour, le modèle choisit un outil d'après les résultats obtenus,
puis rédige la réponse finale. Au plus quatre outils par question."""

import json
from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from juriscope.generate.providers import extract_json

MAX_STEPS = 4
PROMPT = """Tu es un agent qui répond à des questions de droit du travail français avec des \
outils.

Outils :
- recherche : trouve les articles pertinents et rédige une réponse citée. Entrée : une \
question précise.
- article : texte d'un article du Code du travail. Entrée : son numéro, par exemple L1234-1.
- conventions : requête SQL en lecture seule sur la table conventions(idcc, nom, titre, \
salaries, articles), qui décrit les 10 conventions collectives du corpus. Entrée : une requête \
SELECT.
- veille : articles ajoutés, supprimés ou modifiés depuis la version précédente du corpus. \
Entrée : vide.

Question : {question}

Étapes déjà faites :
{steps}

Choisis l'étape suivante. Si la question sort du droit du travail, refuse. Si tu as tout ce \
qu'il faut, termine.
Réponds uniquement en JSON, soit {{"outil": "recherche", "entree": "..."}} avec l'outil choisi, \
soit {{"outil": "fin", "refus": false, "reponse": "réponse finale en français, appuyée sur les \
étapes"}}"""


class State(TypedDict):
    question: str
    steps: list[dict]
    decision: dict


def render(steps: list[dict]) -> str:
    lines = []
    for i, step in enumerate(steps, 1):
        sortie = json.dumps(step["sortie"], ensure_ascii=False)[:1500]
        lines.append(f"{i}. {step['outil']}({step['entree']}) : {sortie}")
    return "\n".join(lines) or "aucune"


def llm_decide(complete: Callable, model: str) -> Callable:
    """Décision du modèle ; une réponse illisible termine la question par un refus."""

    def decide(question: str, steps: list[dict]) -> dict:
        answer = complete(PROMPT.format(question=question, steps=render(steps)), model)
        return extract_json(answer["output"]) or {"outil": "fin", "refus": True, "reponse": ""}

    return decide


def build_agent(decide: Callable, tools: dict[str, Callable]):
    def decide_node(state: State) -> dict:
        return {"decision": decide(state["question"], state["steps"])}

    def tool_node(name: str) -> Callable:
        def run(state: State) -> dict:
            entree = str(state["decision"].get("entree", ""))
            step = {"outil": name, "entree": entree, "sortie": tools[name](entree)}
            return {"steps": [*state["steps"], step]}

        return run

    def route(state: State) -> str:
        outil = state["decision"].get("outil")
        return outil if outil in tools and len(state["steps"]) < MAX_STEPS else END

    graph = StateGraph(State)
    graph.add_node("decide", decide_node)
    for name in tools:
        graph.add_node(name, tool_node(name))
        graph.add_edge(name, "decide")
    graph.add_edge(START, "decide")
    graph.add_conditional_edges("decide", route, [*tools, END])
    return graph.compile()


def run(agent, question: str) -> dict:
    """Réponse finale, outils utilisés et articles cités par les outils."""
    state = agent.invoke({"question": question, "steps": [], "decision": {}})
    decision, steps = state["decision"], state["steps"]
    citations = []
    for step in steps:
        sortie = step["sortie"]
        citations += [sortie["cid"]] if "cid" in sortie else sortie.get("citations", [])
    return {
        "outils": [s["outil"] for s in steps],
        "reponse": decision.get("reponse", "") if decision.get("outil") == "fin" else "",
        "refus": bool(decision.get("refus")),
        "citations": list(dict.fromkeys(citations)),
        "erreurs_outils": sum(1 for s in steps if "erreur" in s["sortie"]),
        "etapes": steps,
    }
