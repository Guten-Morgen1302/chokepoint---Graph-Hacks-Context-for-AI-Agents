import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# .env at the repo root (never committed). Real environment variables win.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    falkordb_host: str = field(default_factory=lambda: _env("FALKORDB_HOST", "localhost"))
    falkordb_port: int = field(default_factory=lambda: int(_env("FALKORDB_PORT", "6379")))
    falkordb_username: str | None = field(default_factory=lambda: _env("FALKORDB_USERNAME"))
    falkordb_password: str | None = field(default_factory=lambda: _env("FALKORDB_PASSWORD"))
    secret: str = field(default_factory=lambda: _env("CHOKEPOINT_SECRET", "dev-only-change-me"))
    llm_provider: str = field(default_factory=lambda: (_env("LLM_PROVIDER", "gemini") or "gemini").lower())
    gemini_api_key: str | None = field(default_factory=lambda: _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _env("GEMINI_MODEL", "gemini-3.5-flash"))
    anthropic_api_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-opus-5-5"))
    max_visitor_graphs: int = field(default_factory=lambda: int(_env("CHOKEPOINT_MAX_GRAPHS", "50")))
    per_ip_graphs_per_hour: int = field(default_factory=lambda: int(_env("CHOKEPOINT_IP_GRAPHS_PER_HOUR", "5")))
    llm_runs_per_visitor_hour: int = field(default_factory=lambda: int(_env("CHOKEPOINT_RUNS_PER_HOUR", "10")))
    llm_runs_per_day: int = field(default_factory=lambda: int(_env("CHOKEPOINT_RUNS_PER_DAY", "300")))
    admin_token: str | None = field(default_factory=lambda: _env("CHOKEPOINT_ADMIN_TOKEN"))

    @property
    def model(self) -> str:
        return self.anthropic_model if self.llm_provider == "anthropic" else self.gemini_model


settings = Settings()
