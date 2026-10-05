"""
CloudAdapter interface. Only this module's subclasses may import cloud SDKs
— nothing else in the codebase should contain gs://, s3://, azure, etc.
Checked by `make audit-src`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CloudAdapter(ABC):
    # --- used by this project ---
    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> None: ...

    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> None: ...

    @abstractmethod
    def push_image(self, local_tag: str, remote_tag: str) -> None: ...

    @abstractmethod
    def emit_metric(self, name: str, value: float, labels: dict[str, str]) -> None: ...

    @abstractmethod
    def teardown(self, labels: dict[str, str]) -> None: ...

    # --- not used by this project (batch-only, no online endpoint, no LLM) ---
    # Implemented as stubs that raise, per architecture.md section 3, so a
    # call to one of these is an obvious bug rather than a silent no-op.
    def submit_training(self, *a, **kw) -> Any:
        raise NotImplementedError("not used: training runs via `make train`")

    def wait_training(self, *a, **kw) -> Any:
        raise NotImplementedError("not used: training runs via `make train`")

    def register_model(self, *a, **kw) -> Any:
        raise NotImplementedError("not used: registration is handled by MLflow directly")

    def deploy(self, *a, **kw) -> Any:
        raise NotImplementedError("not used: no online endpoint, batch job only")

    def invoke(self, *a, **kw) -> Any:
        raise NotImplementedError("not used: no online endpoint, batch job only")

    def generate(self, *a, **kw) -> Any:
        raise NotImplementedError("not used: no LLM in this project")
