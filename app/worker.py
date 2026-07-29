import queue
import threading

from flask import current_app

task_queue = queue.Queue()


def worker_loop(app):
    """Background worker that runs bulk tasks"""
    with app.app_context():
        while True:
            func, args, kwargs = task_queue.get()
            try:
                print(f"Worker started: running {func}")
                func(*args, **kwargs)
            except Exception as e:
                state = current_app.bulk_state  # type: ignore
                state.update(message=f"Worker error: {e}", done=False)
                current_app.logger.error(f" >> Func error: {str(e)}")
                state.run_lock.release()
            finally:
                task_queue.task_done()
                print(f"Worker completed: func : {func}")


def start_worker(app):
    t = threading.Thread(target=worker_loop, args=(app,), daemon=True)
    t.start()
