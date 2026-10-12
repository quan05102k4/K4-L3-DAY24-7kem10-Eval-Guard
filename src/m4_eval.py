from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

# Cây chẩn đoán: chỉ số thấp nhất → (nguyên nhân, hướng xử lý)
DIAGNOSTIC_TREE = {
    "faithfulness": ("LLM tự bịa câu trả lời ngoài tài liệu",
                     "Thắt chặt system prompt, giảm temperature về 0"),
    "context_recall": ("Hệ thống tìm kiếm bỏ sót đoạn văn đúng",
                       "Cải thiện bước cắt đoạn hoặc bổ sung từ khóa BM25"),
    "context_precision": ("Đoạn văn không liên quan bị xếp lên đầu",
                          "Bổ sung tầng Cross-Encoder reranking hoặc lọc theo metadata"),
    "answer_relevancy": ("Câu trả lời bị lệch trọng tâm câu hỏi",
                         "Viết lại prompt hướng dẫn mô hình trả lời trực tiếp hơn"),
}


# Evaluator models cho lượt RAGAS (OpenAI). Tách khỏi GENERATION_MODEL/JUDGE_MODEL của lab.
EVALUATOR_LLM_MODEL = os.getenv("EVALUATOR_LLM_MODEL", "gpt-4o-mini")
EVALUATOR_EMBEDDING_MODEL = os.getenv("EVALUATOR_EMBEDDING_MODEL", "text-embedding-3-small")
NAN_RETRY_ROUNDS = 3


def _run_ragas(questions, answers, contexts, ground_truths, llm, embeddings):
    """Một lượt ragas.evaluate; trả list dict 4 metric theo đúng thứ tự đầu vào (có thể NaN)."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.run_config import RunConfig
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

    dataset = Dataset.from_dict({
        "question": questions, "answer": answers,
        "contexts": contexts, "ground_truth": ground_truths,
    })
    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy,
                                        context_precision, context_recall],
                      llm=llm, embeddings=embeddings, raise_exceptions=False,
                      run_config=RunConfig(max_workers=8, max_retries=6, timeout=120))
    df = result.to_pandas()
    if len(df) != len(questions):
        raise ValueError(f"RAGAS trả {len(df)} dòng cho {len(questions)} câu hỏi.")
    return [{m: float(row[m]) for m in METRICS} for _, row in df.iterrows()]


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation với OpenAI LLM + embedding.

    Không thay NaN bằng điểm giả: câu nào ra NaN (thường do LLM trả JSON lỗi) được chấm
    lại tối đa NAN_RETRY_ROUNDS lượt; còn NaN thì báo lỗi. Thứ tự per_question giữ
    nguyên thứ tự đầu vào. metadata.evaluator_models ghi model thực sự được gọi.
    """
    import math
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    n = len(questions)
    if not (len(answers) == len(contexts) == len(ground_truths) == n):
        raise ValueError("questions/answers/contexts/ground_truths phải cùng độ dài.")

    llm = ChatOpenAI(model=EVALUATOR_LLM_MODEL, temperature=0)
    embeddings = OpenAIEmbeddings(model=EVALUATOR_EMBEDDING_MODEL)

    scores = _run_ragas(questions, answers, contexts, ground_truths, llm, embeddings)
    for round_no in range(1, NAN_RETRY_ROUNDS + 1):
        pending = [i for i, s in enumerate(scores) if not all(math.isfinite(v) for v in s.values())]
        if not pending:
            break
        print(f"  ⚠️  {len(pending)} câu có metric NaN, chấm lại lượt {round_no}...")
        retry = _run_ragas([questions[i] for i in pending], [answers[i] for i in pending],
                           [contexts[i] for i in pending], [ground_truths[i] for i in pending],
                           llm, embeddings)
        for i, fresh in zip(pending, retry):
            # Chỉ thay metric còn NaN; metric đã hữu hạn giữ nguyên.
            scores[i] = {m: scores[i][m] if math.isfinite(scores[i][m]) else fresh[m] for m in METRICS}
    missing = [(i, m) for i, s in enumerate(scores) for m in METRICS if not math.isfinite(s[m])]
    if missing:
        raise ValueError(f"RAGAS vẫn còn NaN sau {NAN_RETRY_ROUNDS} lượt chấm lại: {missing[:10]}")

    per_question = [EvalResult(question=q, answer=a, contexts=list(c), ground_truth=g, **s)
                    for q, a, c, g, s in zip(questions, answers, contexts, ground_truths, scores)]
    aggregate = {m: sum(getattr(r, m) for r in per_question) / n if n else 0.0 for m in METRICS}
    return {**aggregate, "per_question": per_question,
            "metadata": {"evaluator_models": [EVALUATOR_LLM_MODEL, EVALUATOR_EMBEDDING_MODEL]}}


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    scored = []
    for r in eval_results:
        scores = {m: getattr(r, m) for m in METRICS}
        avg = sum(scores.values()) / len(METRICS)
        worst_metric = min(scores, key=scores.get)
        diagnosis, suggested_fix = DIAGNOSTIC_TREE[worst_metric]
        scored.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "worst_metric": worst_metric,
            "score": avg,
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    scored.sort(key=lambda x: x["score"])
    return scored[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
