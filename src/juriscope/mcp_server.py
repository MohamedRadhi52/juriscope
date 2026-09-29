"""Serveur MCP : expose la recherche et la lecture d'articles à un client MCP (assistant de
bureau, éditeur de code). Lancer avec python -m juriscope.mcp_server, sur l'entrée standard."""

from mcp.server.mcpserver import MCPServer

from juriscope.agent.tools import find_article
from juriscope.corpus import load_corpus
from juriscope.retrieve.bm25 import BM25


def create_server(articles: list[dict]) -> MCPServer:
    bm25 = BM25(articles)
    by_cid = {a["cid"]: a for a in articles}
    code = {a["num"]: a for a in articles if not a["idcc"]}
    server = MCPServer(
        "juriscope",
        instructions="Code du travail en vigueur et dix conventions collectives nationales.",
    )

    @server.tool()
    def rechercher(question: str, k: int = 5) -> list[dict]:
        """Articles les plus proches d'une question : identifiant, titre et début du texte."""
        return [
            {"cid": cid, "titre": by_cid[cid]["title"], "extrait": by_cid[cid]["text"][:500]}
            for cid in bm25.search(question, k)
        ]

    @server.tool()
    def lire_article(numero: str) -> dict:
        """Texte d'un article du Code du travail désigné par son numéro, par exemple L1234-1."""
        return find_article(numero, code)

    return server


if __name__ == "__main__":
    create_server(load_corpus()).run()
