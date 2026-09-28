"""Compare deux résultats de run_eval sur les mêmes questions : gain et intervalle apparié.

python -m juriscope.eval.compare results/eval-dev/dense.json results/eval-dev/dense-ft.json
"""

import json
import sys
from pathlib import Path

from juriscope.eval.metrics import paired_gain_ci


def main() -> None:
    before, after = (json.loads(Path(p).read_text())["details"] for p in sys.argv[1:3])
    after_by_id = {row["id"]: row for row in after}
    print(f"| Mesure | {Path(sys.argv[1]).stem} | {Path(sys.argv[2]).stem} | gain [IC95] |")
    print("|---|---:|---:|---|")
    for metric in ("rappel@10", "mrr@10", "ndcg@10"):
        old = [row[metric] for row in before]
        new = [after_by_id[row["id"]][metric] for row in before]
        gain, low, high = paired_gain_ci(old, new)
        interval = f"{gain:+.3f} [{low:+.3f}, {high:+.3f}]"
        print(f"| {metric} | {sum(old) / len(old):.3f} | {sum(new) / len(new):.3f} | {interval} |")


if __name__ == "__main__":
    main()
