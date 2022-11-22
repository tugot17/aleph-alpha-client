from multiprocessing.sharedctypes import Value
from typing import List
import pytest
from aleph_alpha_client import AlephAlphaClient
from aleph_alpha_client.aleph_alpha_client import Client
from aleph_alpha_client.aleph_alpha_model import AlephAlphaModel
from aleph_alpha_client.evaluation import EvaluationRequest
from aleph_alpha_client.prompt import Prompt
from tests.common import sync_client, client, model_name, model, checkpoint_name


@pytest.mark.needs_api
def test_evaluate(sync_client: Client, model_name: str):

    request = EvaluationRequest(
        prompt=Prompt.from_text("hello"), completion_expected="world"
    )

    result = sync_client.evaluate(request, model=model_name)

    assert result.model_version is not None
    assert result.result is not None


@pytest.mark.needs_api
def test_evaluate_against_checkpoint(sync_client: Client, checkpoint_name: str):
    request = EvaluationRequest(
        prompt=Prompt.from_text("hello"), completion_expected="world"
    )

    result = sync_client.evaluate(request, checkpoint=checkpoint_name)

    assert result.model_version is not None
    assert result.result is not None


@pytest.mark.needs_api
def test_evaluate_with_client(client: AlephAlphaClient, model_name: str):
    result = client.evaluate(model_name, prompt="hello", completion_expected="world")

    assert result["model_version"] is not None
    assert result["result"] is not None


@pytest.mark.needs_api
def test_evaluate_with_client_against_checkpoint(
    client: AlephAlphaClient, checkpoint_name: str
):
    result = client.evaluate(
        model=None,
        prompt="hello",
        completion_expected="world",
        checkpoint=checkpoint_name,
    )

    assert result["model_version"] is not None
    assert result["result"] is not None
