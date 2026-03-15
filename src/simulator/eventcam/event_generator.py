from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class EventBatch:
    events: np.ndarray
    event_image: np.ndarray


class EventGenerator:
    """Simple frame-difference event simulator.

    Event format: Nx4 array -> [x, y, timestamp_us, polarity]
    """

    def __init__(
        self,
        width: int,
        height: int,
        tol: float = 0.2,
        max_events_per_pixel: int = 5,
        max_total_events_per_frame: int = 250_000,
    ) -> None:
        self.width = width
        self.height = height
        self.tol = tol
        self.max_events_per_pixel = max_events_per_pixel
        self.max_total_events_per_frame = max_total_events_per_frame
        self.prev_log_gray: np.ndarray | None = None
        self.prev_ts_us: int | None = None

    def _prepare_gray(self, image_rgb: np.ndarray) -> np.ndarray:
        if image_rgb.shape[:2] != (self.height, self.width):
            image_rgb = cv2.resize(image_rgb, (self.width, self.height), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        log_gray = np.log(gray / 255.0 + 1e-3)
        return log_gray

    def image_callback(self, image_rgb: np.ndarray, timestamp_us: int) -> EventBatch:
        curr_log = self._prepare_gray(image_rgb)

        if self.prev_log_gray is None or self.prev_ts_us is None:
            self.prev_log_gray = curr_log
            self.prev_ts_us = timestamp_us
            empty = np.zeros((0, 4), dtype=np.int64)
            return EventBatch(events=empty, event_image=np.zeros((self.height, self.width), dtype=np.int8))

        dt_us = max(1, timestamp_us - self.prev_ts_us)
        delta = curr_log - self.prev_log_gray

        n_events = np.floor(np.abs(delta) / self.tol).astype(np.int32)
        n_events = np.clip(n_events, 0, self.max_events_per_pixel)
        ys, xs = np.nonzero(n_events > 0)

        rows: list[list[int]] = []
        event_image = np.zeros((self.height, self.width), dtype=np.int8)

        for y, x in zip(ys.tolist(), xs.tolist()):
            n = int(n_events[y, x])
            if n <= 0:
                continue

            pol = 1 if delta[y, x] >= 0 else -1
            event_image[y, x] = pol

            for k in range(n):
                t = self.prev_ts_us + int(((k + 1) * dt_us) / n)
                rows.append([x, y, t, pol])
                if len(rows) >= self.max_total_events_per_frame:
                    break

            if len(rows) >= self.max_total_events_per_frame:
                break

        if rows:
            events = np.asarray(rows, dtype=np.int64)
            order = np.argsort(events[:, 2], kind="stable")
            events = events[order]
        else:
            events = np.zeros((0, 4), dtype=np.int64)

        self.prev_log_gray = curr_log
        self.prev_ts_us = timestamp_us
        return EventBatch(events=events, event_image=event_image)
