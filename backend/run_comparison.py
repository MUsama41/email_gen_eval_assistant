import json

from app.services.comparison import ComparisonService


def main() -> None:
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

    print("\nResults written to the results/ directory.")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
