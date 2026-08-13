import time

import requests

BASE_URL = "http://127.0.0.1:59001"

USERNAME = "demo"
PASSWORD = "demo"

session = requests.Session()


def main():
    # --------------------------------------------------------------
    # Login
    # --------------------------------------------------------------

    response = session.post(
        f"{BASE_URL}/login",
        data={
            "username": USERNAME,
            "password": PASSWORD,
        },
    )

    response.raise_for_status()

    print("Logged in.")

    # --------------------------------------------------------------
    # Start synchronization
    # --------------------------------------------------------------

    job = {
        "novels": [1, 5, 17],
        "source": "local",
        "mode": "fill_missing",
        "fields": [
            "name",
            "author",
            "description",
        ],
        "dry_run": True,
        "force": False,
    }

    response = session.post(
        f"{BASE_URL}/api/v1/sync",
        json=job,
    )

    print("\nStart response:")
    print(response.status_code)
    print(response.json())

    response.raise_for_status()

    data = response.json()
    job_id = data["job_id"]

    print(f"\nJob ID: {job_id}")

    print("\nConnecting to event stream...")

    with session.get(
        f"{BASE_URL}/api/v1/sync/{job_id}/events",
        stream=True,
    ) as response:
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            print(f"EVENT: {line}")

            if line == "event: done":
                print("Synchronization stream finished.")
                break

    # --------------------------------------------------------------
    # Monitor execution
    # --------------------------------------------------------------

    while True:
        response = session.get(
            f"{BASE_URL}/api/v1/sync/{job_id}",
        )

        response.raise_for_status()

        data = response.json()
        execution = data["execution"]

        print(f"status={execution['status']} done={execution['done']}")

        if execution["done"]:
            print("\nFinal result:")
            print(execution)

            break

        time.sleep(0.5)


if __name__ == "__main__":
    main()
