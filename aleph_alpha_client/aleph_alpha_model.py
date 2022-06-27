from aleph_alpha_client.aleph_alpha_client import AlephAlphaClient
from aleph_alpha_client.completion import CompletionRequest, CompletionResponse
from aleph_alpha_client.detokenization import DetokenizationRequest, DetokenizationResponse
from aleph_alpha_client.embedding import EmbeddingRequest, EmbeddingResponse
from aleph_alpha_client.evaluation import EvaluationRequest, EvaluationResponse
from aleph_alpha_client.qa import QaRequest, QaResponse
from aleph_alpha_client.tokenization import TokenizationRequest, TokenizationResponse


class AlephAlphaModel:

    def __init__(self, client: AlephAlphaClient, model_name: str, hosting: str = "cloud") -> None:
        self.client = client
        self.model_name = model_name
        self.hosting = hosting

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        response_json = self.client.complete(model = self.model_name, hosting=self.hosting, **request._asdict())
        return CompletionResponse.from_json(response_json)

    def tokenize(self, request: TokenizationRequest) -> TokenizationResponse:
        response_json = self.client.tokenize(model = self.model_name, **request._asdict())
        return TokenizationResponse.from_json(response_json)

    def detokenize(self, request: DetokenizationRequest) -> DetokenizationResponse:
        response_json = self.client.detokenize(model = self.model_name, **request._asdict())
        return DetokenizationResponse.from_json(response_json)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        response_json = self.client.embed(model = self.model_name, hosting=self.hosting, **request._asdict())
        return EmbeddingResponse.from_json(response_json)

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        response_json = self.client.evaluate(model = self.model_name, hosting=self.hosting, **request._asdict())
        return EvaluationResponse.from_json(response_json)

    def qa(self, request: QaRequest) -> QaResponse:
        response_json = self.client.qa(model = self.model_name, hosting=self.hosting, **request._asdict())
        return QaResponse.from_json(response_json)
