"""Tests use a fake transport or HTTPX MockTransport, never a live model."""

import io
import json
from pathlib import Path

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, load_settings
from app.core.exceptions import ConfigurationError, ModelCallError, StructuredOutputError
from app.core.logging import configure_logging, log_event
from app.schemas.common import Contract, NonEmptyText
from app.services.llm import LLMClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Answer(Contract):
    message: NonEmptyText


def settings(**overrides):
    values = dict(
        _env_file=None,
        llm_model="test-model",
        llm_api_key=SecretStr("synthetic-key"),
        llm_base_url=None,
        llm_structured_method="function_calling",
    )
    values.update(overrides)
    return Settings(**values)


class FakeModel:
    def __init__(self, response=None, error=None):
        self.response, self.error = response, error
        self.calls = 0

    def bind_tools(self, tools, **kwargs):
        self.schema, self.options = tools[0], kwargs
        return self

    def with_structured_output(self, schema, **kwargs):
        self.schema, self.options = schema, kwargs
        return self

    def invoke(self, messages):
        self.calls += 1
        self.messages = messages
        if self.error:
            raise self.error
        return self.response


def test_missing_credentials_fail_before_model_creation():
    with pytest.raises(ConfigurationError, match="LLM_MODEL.*LLM_API_KEY"):
        LLMClient(settings(llm_model="", llm_api_key=SecretStr("")))


def test_invalid_config_values():
    for values in (
        {"max_jobs": 0},
        {"max_jobs": 2},
        {"max_repair_attempts": 3},
        {"request_timeout_seconds": 0},
        {"llm_base_url": "not-a-url"},
    ):
        with pytest.raises(ValidationError):
            settings(**values)


def test_shipped_env_example_loads_with_project_defaults(tmp_path, monkeypatch):
    """The template and the local .env must both satisfy the single-JD contract.

    A stale MAX_JOBS value here is invisible to the rest of the suite because every
    other test constructs Settings explicitly; only a real load_settings() call fails.
    """
    for env_name in (".env", ".env.example"):
        env_path = PROJECT_ROOT / env_name
        if not env_path.is_file():
            continue
        for key in ("LLM_MODEL", "LLM_API_KEY", "MAX_JOBS", "MAX_REPAIR_ATTEMPTS"):
            monkeypatch.delenv(key, raising=False)
        config = Settings(_env_file=env_path)
        assert config.max_jobs == 1, f"{env_name} must keep MAX_JOBS within the single-JD bound"


def test_settings_load_env_file_and_hide_secret(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("LLM_MODEL=local-test\nLLM_API_KEY=private-value\n", encoding="utf-8")
    config = Settings(_env_file=env)
    assert config.llm_model == "local-test"
    assert "private-value" not in repr(config)
    assert "private-value" not in config.model_dump_json()


def test_load_settings_redacts_invalid_value(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "secret-invalid-endpoint")
    with pytest.raises(ConfigurationError) as error:
        load_settings()
    assert "llm_base_url" in str(error.value)
    assert "secret-invalid-endpoint" not in str(error.value)


def test_logging_allowlist_and_idempotence():
    stream = io.StringIO()
    configure_logging(stream=stream)
    logger = configure_logging(stream=stream)
    log_event(
        logger,
        "test.event",
        request_id="one",
        node="test",
        resume_text="private-resume",
        api_key="private-key",
        status="success",
    )
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["request_id"] == "one"
    assert "private-" not in lines[0]


def test_logging_timestamp_uses_configured_timezone(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_TIMEZONE", "Asia/Shanghai")
    logger = configure_logging(log_dir=tmp_path)
    log_event(logger, "timezone.check")
    payload = json.loads((tmp_path / "jobpilot.log").read_text(encoding="utf-8").splitlines()[-1])
    assert payload["timestamp"].endswith("+08:00")


def test_structured_success_and_usage_logged_without_prompt():
    stream = io.StringIO()
    configure_logging(stream=stream)
    fake = FakeModel(
        response=AIMessage(
            content="private-output",
            tool_calls=[
                {
                    "name": "Answer",
                    "args": {"message": "ok"},
                    "id": "call_test",
                    "type": "tool_call",
                }
            ],
            usage_metadata={
                "input_tokens": 3,
                "output_tokens": 2,
                "total_tokens": 5,
            },
        )
    )
    result = LLMClient(settings(), model=fake).structured(
        Answer,
        instruction="Extract only",
        text="private-resume",
        request_id="test",
    )
    assert result.message == "ok"
    assert fake.options == {"tool_choice": "auto"}
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert events[-1]["total_tokens"] == 5
    assert "private-" not in stream.getvalue()


@pytest.mark.parametrize(
    "response",
    [
        None,
        {"parsed": None},
        {"parsed": {"wrong": "field"}},
        {"parsed": {"message": "ok"}, "parsing_error": ValueError("private-payload")},
    ],
)
def test_invalid_structured_output_is_safe(response):
    with pytest.raises(StructuredOutputError) as error:
        LLMClient(settings(), model=FakeModel(response=response)).structured(
            Answer,
            instruction="Extract",
            text="private-resume",
            request_id="test",
        )
    assert "private" not in str(error.value)


def test_provider_failure_is_redacted_and_not_retried_by_wrapper():
    fake = FakeModel(error=RuntimeError("private-key private-resume"))
    with pytest.raises(ModelCallError) as error:
        LLMClient(settings(), model=fake).structured(
            Answer,
            instruction="Extract",
            text="private-resume",
            request_id="test",
        )
    assert "private" not in str(error.value)
    assert fake.calls == 1


def test_real_adapter_with_mock_http_transport():
    """Exercise installed LangChain/OpenAI serialization without a network."""
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_test",
                                    "type": "function",
                                    "function": {
                                        "name": "Answer",
                                        "arguments": '{"message":"ok"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        model = ChatOpenAI(
            model="test-model",
            api_key="synthetic-key",
            http_client=http,
            base_url="https://example.invalid/v1",
            max_retries=0,
        )
        result = LLMClient(settings(), model=model).structured(
            Answer,
            instruction="Return a message",
            text="test",
            request_id="test",
        )
    assert result.message == "ok"
    assert requests[0]["tool_choice"] == "auto"
    assert requests[0]["tools"][0]["function"]["name"] == "Answer"


def test_local_retrieval_model_paths_are_configurable(tmp_path):
    config = settings(
        embedding_model_path=tmp_path / "embedding",
        embedding_device="cpu",
        reranker_model_path=tmp_path / "reranker",
    )
    assert config.embedding_model_path == tmp_path / "embedding"
    assert config.embedding_device == "cpu"
    assert config.reranker_model_path == tmp_path / "reranker"
