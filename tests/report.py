from time import perf_counter


class TestReport:
    def __init__(self):

        self.start = perf_counter()

    def finish(self, results):

        elapsed = perf_counter() - self.start

        updated = sum(1 for r in results if r and r.get("updated"))

        # failed = sum(1 for r in results if r and "error" in r)

        skipped = sum(
            1 for r in results if r and not r.get("updated") and "error" not in r
        )

        errors = sum(len(r.get("errors", [])) for r in results if r)

        warnings = sum(len(r.get("warnings", [])) for r in results if r)

        print("\n===== Test Summary =====")

        print(f"Processed : {len(results)}")
        print(f"Updated   : {updated}")
        print(f"Skipped   : {skipped}")
        print(f"Errors    : {errors}")
        print(f"Warnings  : {warnings}")
        print(f"Time      : {elapsed:.2f}s")
