"""@package partsmith.gui.image_loader
@brief Coalesces bounded source-image decoding outside the wx event thread.
@details Only the newest selection is returned; original source assets remain
on disk, independent of the disposable decoded display cache.
"""

from io import BytesIO
from threading import Condition, Thread


class ImageLoader:
    """@brief Owns one worker and at most one pending display image request.
    @details Does not allocate wx resources or mutate engineering state.
    """

    def __init__(self, publish):
        """@brief Starts an idle decoding worker with a result dispatch sink.
        @param publish Thread-safe callback receiving binding, result and
        error.
        @return None.
        @details Closing releases pending work and the retained callback.
        """
        self.publish = publish
        self.condition = Condition()
        self.pending = None
        self.closed = False
        self.worker = Thread(
            target=self.run, name="PartSmith source image", daemon=True
        )
        self.worker.start()

    def request(self, binding, session, reference, size, budget):
        """@brief Replaces the pending source-image decode request.
        @param binding Immutable session/selection binding.
        @param session Source CAS owner retained for this request only.
        @param reference Exact content-addressed PNG reference.
        @param size Declared source-image dimensions.
        @param budget Maximum decoded RGB display bytes.
        @return None.
        @details Newer requests replace pending work without an unbounded
        queue.
        """
        with self.condition:
            self.pending = (binding, session, reference, size, budget)
            self.condition.notify()

    def close(self):
        """@brief Releases pending work and stops after the current decode.
        @return None.
        @details Never joins a worker on the GUI thread.
        """
        with self.condition:
            self.closed = True
            self.pending = None
            self.condition.notify()

    def run(self):
        """@brief Decodes one bounded original source image at a time.
        @return None.
        @details Validates declared and actual pixel allocations before decode.
        """
        from PIL import Image

        while True:
            with self.condition:
                self.condition.wait_for(
                    lambda: self.pending is not None or self.closed
                )
                if self.closed:
                    self.publish = None
                    return
                binding, session, reference, size, budget = self.pending
                self.pending = None
            result, error = None, None
            try:
                width, height = map(int, size)
                if width * height * 4 > int(budget):
                    raise ValueError(
                        "Source image exceeds display-cache budget; "
                        "use lower DPI"
                    )
                with Image.open(BytesIO(session.get(reference))) as image:
                    if image.size != (width, height):
                        raise ValueError(
                            "Source image dimensions differ from "
                            "retained metadata"
                        )
                    with image.convert("RGB") as decoded:
                        result = (width, height, decoded.tobytes())
            except Exception as exception:
                error = str(exception)
            with self.condition:
                if not self.closed and self.pending is None:
                    self.publish(binding, result, error)
