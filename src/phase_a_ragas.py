from __future__ import annotations

"""Phase A: RAGAS Production Evaluation — 50q, 3 distributions, cluster analysis."""

import json
import math
import os
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH, ANSWERS_PATH, ARTIFACTS_DIR
from src.experiment_support import write_json

Distribution = str  # "factual" | "multi_hop" | "adversarial"

DIAGNOSTIC_TREE = {
    "faithfulness":      ("LLM hallucinating", "Tighten system prompt, lower temperature"),
    "context_recall":    ("Missing relevant chunks", "Improve chunking or add BM25"),
    "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
    "answer_relevancy":  ("Answer doesn't match question", "Improve prompt template"),
}


@dataclass
class RagasResult:
    question_id: int
    distribution: Distribution
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    @property
    def avg_score(self) -> float:
        return (self.faithfulness + self.answer_relevancy +
                self.context_precision + self.context_recall) / 4

    @property
    def worst_metric(self) -> str:
        scores = {
            "faithfulness":      self.faithfulness,
            "answer_relevancy":  self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall":    self.context_recall,
        }
        return min(scores, key=scores.get)


# ─── Đã implement sẵn ────────────────────────────────────────────────────────

@dataclass
class RagasEvaluation:
    """Task 2 output: measured rows plus model identifiers reported by m4."""
    results: list[RagasResult]
    evaluator_models: list[str]

def load_test_set_50q(path: str = TEST_SET_PATH) -> list[dict]:
    """Load 50q test set với 3 distributions."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_answers(path: str = ANSWERS_PATH) -> list[dict]:
    """Load pre-generated answers từ setup_answers.py."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"answers_50q.json không tìm thấy tại {path}\n"
            "→ Chạy trước: python scripts/setup_answers.py --live"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict]) -> dict:
    """Provided exporter: preserve the student-produced Task 3 rows verbatim."""
    per_dist: dict[str, dict] = {}
    for dist in ["factual", "multi_hop", "adversarial"]:
        subset = [r for r in results if r.distribution == dist]
        if subset:
            per_dist[dist] = {
                "count": len(subset),
                "faithfulness":      sum(r.faithfulness for r in subset) / len(subset),
                "answer_relevancy":  sum(r.answer_relevancy for r in subset) / len(subset),
                "context_precision": sum(r.context_precision for r in subset) / len(subset),
                "context_recall":    sum(r.context_recall for r in subset) / len(subset),
                "avg_score":         sum(r.avg_score for r in subset) / len(subset),
            }

    report = {
        "total_questions": len(results),
        "per_question": [asdict(r) for r in results],
        "per_distribution": per_dist,
        "failure_clusters": clusters,
        "bottom_10": bottom,
    }
    return report


def save_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict],
                        path: str = os.path.join(ARTIFACTS_DIR, "ragas_50q.json")) -> None:
    write_json(path, build_phase_a_report(results, clusters, bottom))



# ─── Tasks 1-4: Sinh viên implement ──────────────────────────────────────────

DISTRIBUTIONS = ("factual", "multi_hop", "adversarial")
METRICS = tuple(DIAGNOSTIC_TREE)

# Gợi ý riêng cho từng distribution, ghép thêm vào chẩn đoán theo worst_metric.
DISTRIBUTION_HINTS = {
    "factual":     "câu tra cứu một tài liệu",
    "multi_hop":   "câu cần ghép thông tin từ nhiều tài liệu/điều khoản",
    "adversarial": "câu có bẫy phiên bản (v2023/v2024, v1/v2) hoặc phủ định",
}
DISTRIBUTION_FIXES = {
    "factual":     "kiểm tra chunk chứa con số/điều khoản có nằm trong top-3 sau rerank",
    "multi_hop":   "tăng top_k hoặc trả parent chunk để đủ các vế của câu hỏi",
    "adversarial": "ưu tiên tài liệu phiên bản mới qua metadata (version/effective date) "
                   "và yêu cầu prompt nêu rõ phiên bản đang hiệu lực, giữ phủ định",
}


def group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]:
    """Task 1: Nhóm 50 câu hỏi theo 3 distributions.

    Returns:
        {"factual": [...], "multi_hop": [...], "adversarial": [...]}
    """
    groups: dict[str, list[dict]] = {d: [] for d in DISTRIBUTIONS}
    for item in test_set:
        distribution = item["distribution"]
        if distribution not in groups:
            raise ValueError(f"Câu {item.get('id')}: distribution lạ '{distribution}'.")
        groups[distribution].append(item)
    return groups


def run_ragas_50q(answers: list[dict]) -> RagasEvaluation:
    """Task 2: Chạy RAGAS 4 metrics trên toàn bộ 50 câu hỏi.

    Gọi m4_eval.evaluate_ragas đúng một lần với 4 list cùng thứ tự; ghép kết quả
    theo vị trí (m4 giữ nguyên thứ tự) và lấy evaluator_models từ metadata m4.
    """
    try:
        from src.m4_eval import evaluate_ragas
    except ImportError as error:
        raise ValueError("Missing src/m4_eval.py; cannot evaluate or declare evaluator models") from error

    questions     = [a["question"]     for a in answers]
    ans_texts     = [a["answer"]       for a in answers]
    contexts      = [list(a["contexts"]) for a in answers]
    ground_truths = [a["ground_truth"] for a in answers]

    raw = evaluate_ragas(questions, ans_texts, contexts, ground_truths)
    per_q = list(raw.get("per_question", []))
    if len(per_q) != len(answers):
        raise ValueError(f"m4 trả {len(per_q)} kết quả cho {len(answers)} câu; không ghép âm thầm.")
    evaluator_models = raw.get("metadata", {}).get("evaluator_models")
    if not evaluator_models:
        raise ValueError("m4 phải trả metadata.evaluator_models; không dùng JUDGE_MODEL thay thế.")

    def metric(record, name: str, qid: int) -> float:
        value = record[name] if isinstance(record, dict) else getattr(record, name)
        value = float(value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"Câu {qid}: {name}={value} không hữu hạn trong [0, 1].")
        return value

    results = []
    for a, pq in zip(answers, per_q):
        results.append(RagasResult(
            question_id=a["id"], distribution=a["distribution"],
            question=a["question"], answer=a["answer"],
            contexts=a["contexts"], ground_truth=a["ground_truth"],
            **{name: metric(pq, name, a["id"]) for name in METRICS},
        ))
    return RagasEvaluation(results, list(evaluator_models))


REFUSAL_MARKERS = ("không tìm thấy", "không có thông tin", "không đủ thông tin")


def _is_refusal(answer: str) -> bool:
    return answer.strip().lower().startswith(REFUSAL_MARKERS)


def _diagnose(r: RagasResult) -> tuple[str, str]:
    """Chẩn đoán một câu từ điểm số và nội dung answer/contexts, không chỉ tra cây metric.

    faithfulness thấp có hai nghĩa khác nhau: answer bịa (có khẳng định không được context
    hỗ trợ) hoặc answer không có khẳng định nào (từ chối/cụt). Phân biệt bằng nội dung answer
    và context_recall để tách lỗi retrieval khỏi lỗi generation.
    """
    base_diag, base_fix = DIAGNOSTIC_TREE[r.worst_metric]
    worst_value = getattr(r, r.worst_metric)
    scores = (f"F={r.faithfulness:.2f}, AR={r.answer_relevancy:.2f}, "
              f"CP={r.context_precision:.2f}, CR={r.context_recall:.2f}")
    hint = DISTRIBUTION_HINTS[r.distribution]
    retrieval_ok = r.context_recall >= 0.5

    if not r.contexts:
        return (f"Retrieval không trả context nào ({scores}; {hint})",
                f"Kiểm tra index/BM25 cho câu này; {DISTRIBUTION_FIXES[r.distribution]}")
    if _is_refusal(r.answer):
        if retrieval_ok:
            return (f"Lỗi generation: answer từ chối 'Không tìm thấy' dù contexts chứa phần lớn "
                    f"đáp án ({scores}; {hint}). Không phải hallucination: faithfulness=0 vì answer "
                    f"không có khẳng định nào; AR thấp vì RAGAS coi câu từ chối là noncommittal",
                    f"Sửa prompt generation: cho phép tổng hợp/tính từ nhiều context và chỉ trả "
                    f"'Không tìm thấy' khi không context nào liên quan; {DISTRIBUTION_FIXES[r.distribution]}; "
                    f"đo lại tỷ lệ refusal trên 50 câu sau khi sửa")
        return (f"Lỗi retrieval dẫn tới từ chối: thiếu context đúng nên answer 'Không tìm thấy' "
                f"({scores}; {hint})",
                f"{DIAGNOSTIC_TREE['context_recall'][1]}; {DISTRIBUTION_FIXES[r.distribution]}")
    if len(r.answer.strip()) < 12:
        return (f"Lỗi generation: answer bị cụt/thoái hoá '{r.answer.strip()}' dù context có đáp án "
                f"({scores}; {hint})",
                "Kiểm tra finish_reason và retry khi answer quá ngắn; đặt temperature=0 và "
                "kiểm tra độ dài tối thiểu trước khi trả lời")

    diagnosis = f"{base_diag}: {r.worst_metric}={worst_value:.2f} ({scores}; {hint})"
    if r.worst_metric == "faithfulness" and retrieval_ok:
        diagnosis += "; context đủ nên phần thêm/sai nằm ở generation"
    elif not retrieval_ok:
        diagnosis += "; context_recall thấp nên retrieval là nguyên nhân gốc"
    return diagnosis, f"{base_fix}; {DISTRIBUTION_FIXES[r.distribution]}"


def bottom_10(results: list[RagasResult]) -> list[dict]:
    """Task 3: Lấy 10 câu hỏi có avg_score thấp nhất.

    Returns:
        [{"rank": 1, "question_id": ..., "distribution": ...,
          "question": ..., "avg_score": ..., "worst_metric": ...,
          "diagnosis": ..., "suggested_fix": ...}, ...]
    """
    # Sắp ổn định theo (avg_score, question_id) để kết quả lặp lại được khi bằng điểm.
    ordered = sorted(results, key=lambda r: (r.avg_score, r.question_id))[:10]
    output = []
    for rank, r in enumerate(ordered, 1):
        diagnosis, suggested_fix = _diagnose(r)
        output.append({
            "rank": rank,
            "question_id": r.question_id,
            "distribution": r.distribution,
            "question": r.question,
            "avg_score": r.avg_score,
            "worst_metric": r.worst_metric,
            "worst_metric_score": getattr(r, r.worst_metric),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    return output


def cluster_analysis(results: list[RagasResult]) -> dict:
    """Task 4: Phân tích failure clusters theo (worst_metric × distribution).

    Matrix thống kê worst_metric của mọi câu, không coi mọi câu là một failure.
    Nhóm yếu nhất = distribution có avg_score trung bình thấp nhất (bỏ nhóm rỗng).
    Tổng matrix theo cột chỉ là kích thước nhóm 20/20/10, không đo chất lượng.
    """
    matrix = {metric: {d: 0 for d in DISTRIBUTIONS} for metric in METRICS}
    for r in results:
        matrix[r.worst_metric][r.distribution] += 1

    # Nhóm rỗng bị loại khỏi phép chia, không gán 0 điểm.
    means = {}
    for d in DISTRIBUTIONS:
        subset = [r.avg_score for r in results if r.distribution == d]
        if subset:
            means[d] = sum(subset) / len(subset)
    if not means:
        return {"matrix": matrix, "distribution_avg_scores": {},
                "dominant_failure_distribution": None, "dominant_failure_metric": None,
                "insight": "Không có kết quả để phân tích."}

    dominant_dist = min(means, key=means.get)  # chất lượng thấp nhất, KHÔNG phải nhóm đông nhất
    totals = {m: sum(matrix[m].values()) for m in METRICS}
    dominant_metric = max(METRICS, key=lambda m: totals[m])
    metric_means = {m: sum(getattr(r, m) for r in results) / len(results) for m in METRICS}
    in_weakest = matrix[dominant_metric].get(dominant_dist, 0)
    weakest_size = sum(r.distribution == dominant_dist for r in results)

    ranking = ", ".join(f"{d}={means[d]:.3f}" for d in sorted(means, key=means.get))
    insight = (
        f"Mean avg_score theo distribution (thấp→cao): {ranking}; nhóm yếu nhất là "
        f"'{dominant_dist}'. Metric thấp nhất xuất hiện nhiều nhất là '{dominant_metric}' "
        f"({totals[dominant_metric]}/{len(results)} câu, trong đó {in_weakest}/{weakest_size} "
        f"câu thuộc '{dominant_dist}'); mean toàn bộ của metric này là "
        f"{metric_means[dominant_metric]:.3f}. Chẩn đoán: {DIAGNOSTIC_TREE[dominant_metric][0]}. "
        f"Đề xuất: {DIAGNOSTIC_TREE[dominant_metric][1]}; với '{dominant_dist}': "
        f"{DISTRIBUTION_FIXES[dominant_dist]}. Matrix chỉ đếm worst_metric của mọi câu, "
        f"không phải số câu lỗi."
    )
    refusals = {d: sum(1 for r in results if r.distribution == d and _is_refusal(r.answer))
                for d in DISTRIBUTIONS}
    if any(refusals.values()):
        refusal_ok = sum(1 for r in results if _is_refusal(r.answer) and r.context_recall >= 0.5)
        insight += (f" Answer 'Không tìm thấy': {sum(refusals.values())}/{len(results)} câu "
                    f"({', '.join(f'{d}={n}' for d, n in refusals.items())}), trong đó {refusal_ok} câu "
                    f"có context_recall>=0.5 → lỗi generation từ chối nhầm, làm faithfulness và "
                    f"answer_relevancy về 0 chứ không phải hallucination.")
    if "adversarial" in means and "factual" in means:
        gap = means["factual"] - means["adversarial"]
        insight += (f" Adversarial {'thấp' if gap > 0 else 'không thấp'} hơn factual "
                    f"{abs(gap):.3f} điểm; điều này chưa chứng minh pipeline nhận ra bẫy phiên bản.")

    return {"matrix": matrix, "distribution_avg_scores": means,
            "metric_means": metric_means, "worst_metric_totals": totals,
            "dominant_failure_distribution": dominant_dist,
            "dominant_failure_metric": dominant_metric, "insight": insight}


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "a", *sys.argv[1:]]))
