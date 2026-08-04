from time import perf_counter


class TestReport:
    def __init__(self):

        self.start = perf_counter()

    def finish(self, results):

        elapsed = perf_counter() - self.start

        updated = sum(1 for r in results if r.get("updated"))
        skipped = sum(1 for r in results if not r.get("updated"))
        errors = sum(1 for r in results if "error" in r)

        print("\n===== Test Summary =====")

        print(f"Processed : {len(results)}")
        print(f"Updated   : {updated}")
        print(f"Skipped   : {skipped}")
        print(f"Errors    : {errors}")
        print(f"Time      : {elapsed:.2f}s")
