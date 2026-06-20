import json
import logging

from app.services.comparison import ComparisonService


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    _configure_logging()
    log = logging.getLogger("run_comparison")

    log.info("Starting 2x2 comparison (2 models x 2 strategies x 10 scenarios)")
    service = ComparisonService()
    result = service.run()

    print("\n=== 2x2 Comparison Summary (averages) ===")
    for row in result["summary"]:
        print(
            f"{row['model_name']:<28} {row['strategy']:<9} "
            f"fact={row['fact_recall']:<6} tone={row['tone_accuracy']:<6} "
            f"fluency={row['conciseness_fluency']:<6} overall={row['overall']}"
        )

    winner = result["winner"]
    if winner:
        print(
            f"\nWinner: {winner['model_name']} ({winner['strategy']}) "
            f"with overall {winner['overall']}"
        )

    if result.get("stopped_early"):
        log.warning(
            "Run stopped early on a daily token cap. Completed combos are cached and "
            "written. Re-run this command after the quota resets to finish the rest."
        )

    log.info("Results written to the results/ directory.")
    print("\nResults written to the results/ directory.")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
