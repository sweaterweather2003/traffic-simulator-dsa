def comparison(results):
    print("\nController              AvgWait   MaxQueue   Throughput   Stops")
    print("-" * 65)
    for result in results:
        print(
            f"{result.controller:<24}{result.average_wait:>8.2f}"
            f"{result.max_queue:>11}{result.throughput:>13}{result.stops:>8}"
        )
