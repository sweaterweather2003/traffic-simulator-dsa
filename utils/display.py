def comparison(results):
    print("\nController              AvgWait   MaxQueue   Throughput   Stops")
    print("-"*65)
    for r in results:print(f"{r.controller:<24}{r.average_wait:>8.2f}{r.max_queue:>11}{r.throughput:>13}{r.stops:>8}")
