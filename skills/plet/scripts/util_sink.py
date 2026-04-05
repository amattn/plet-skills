"""Event sink abstraction for orchestrator output.

Replaces the output_ndjson bool pattern. The orchestrator emits events
and text through a sink object instead of printing directly.

Production sinks: NdjsonSink (NDJSON to stdout), TextSink (human text to stdout)
Testing sink: CaptureSink (captures events/messages in memory)
Persistence sink: FileSink (writes NDJSON to a file)
Composition: MultiplexSink (combines multiple sinks)
"""

import json
import sys

from util_cli import now_iso


class EventSink:
    """Base class for orchestrator event output."""

    def event(self, data):
        """Emit a structured event."""
        pass

    def text(self, msg):
        """Emit a human-readable text message."""
        pass


class NdjsonSink(EventSink):
    """Production: NDJSON events to stdout, text suppressed."""

    def event(self, data):
        data["timestamp"] = now_iso()
        print(json.dumps(data, separators=(",", ":")))
        sys.stdout.flush()

    def text(self, msg):
        pass  # suppressed in NDJSON mode


class TextSink(EventSink):
    """Production: human-readable text to stdout, events suppressed."""

    def event(self, data):
        pass  # suppressed in text mode

    def text(self, msg):
        print(msg)
        sys.stdout.flush()


class CaptureSink(EventSink):
    """Testing: capture everything in memory."""

    def __init__(self):
        self.events = []
        self.messages = []

    def event(self, data):
        data["timestamp"] = now_iso()
        self.events.append(dict(data))

    def text(self, msg):
        self.messages.append(msg)


class FileSink(EventSink):
    """Persistence: write NDJSON events to a file. Text suppressed."""

    def __init__(self, path):
        self.path = path

    def event(self, data):
        data["timestamp"] = now_iso()
        with open(self.path, "a") as f:
            f.write(json.dumps(data) + "\n")

    def text(self, msg):
        pass


class MultiplexSink(EventSink):
    """Combine multiple sinks. Events/text go to all."""

    def __init__(self, *sinks):
        self.sinks = sinks

    def event(self, data):
        for s in self.sinks:
            s.event(dict(data))  # copy so one sink's mutations don't affect others

    def text(self, msg):
        for s in self.sinks:
            s.text(msg)
