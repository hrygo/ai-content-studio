"""引擎结果实体"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EngineResult:
    """引擎操作结果"""
    success: bool
    file_path: Path | None = None
    duration: float = 0.0
    engine_name: str = ""
    error_message: str | None = None

    @classmethod
    def ok(
        cls,
        file_path: Path,
        duration: float = 0.0,
        engine_name: str = "",
    ) -> "EngineResult":
        return cls(success=True, file_path=file_path, duration=duration, engine_name=engine_name)

    @classmethod
    def fail(cls, error_message: str, engine_name: str = "") -> "EngineResult":
        return cls(success=False, error_message=error_message, engine_name=engine_name)
