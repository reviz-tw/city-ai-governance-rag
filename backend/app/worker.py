import threading
from app.services import store, jobs


def serve(stop=None):
    stop = stop or threading.Event()
    store.initialize()
    while not stop.is_set():
        try:
            jobs.poll_once()
            jobs.purge_expired()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('worker_poll_failed kind=%s',type(exc).__name__)
        stop.wait(1)

if __name__ == '__main__':
    serve()
