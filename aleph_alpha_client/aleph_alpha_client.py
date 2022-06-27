from socket import timeout
from typing import List, Optional, Dict, Sequence, Union

import requests
import logging
import aleph_alpha_client
from aleph_alpha_client.document import Document
from aleph_alpha_client.explanation import ExplanationRequest
from aleph_alpha_client.image import ImagePrompt
from aleph_alpha_client.prompt import _to_prompt_item, _to_serializable_prompt

POOLING_OPTIONS = ["mean", "max", "last_token", "abs_max"]


class QuotaError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AlephAlphaClient:
    def __init__(self, host, token=None, email=None, password=None):
        if host[-1] != "/":
            host += "/"
        self.host = host

        # check server version
        expect_release = "1"
        version = self.get_version()
        if not version.startswith(expect_release):
            logging.warning(
                f"Expected API version {expect_release}.x.x, got {version}. Please update client."
            )

        assert token is not None or (email is not None and password is not None)
        self.token = token or self.get_token(email, password)

    def get_version(self):
        response = requests.get(self.host + "version")
        response.raise_for_status()
        return response.text

    def get_token(self, email, password):
        response = requests.post(
            self.host + "get_token", json={"email": email, "password": password}
        )
        if response.status_code == 200:
            response_json = response.json()
            return response_json["token"]
        else:
            raise ValueError("cannot get token")

    @property
    def request_headers(self):
        return {
            "Authorization": "Bearer " + self.token,
            "User-Agent": "Aleph-Alpha-Python-Client-" + aleph_alpha_client.__version__,
        }

    def available_models(self):
        """
        Queries all models which are currently available.
        """
        response = requests.get(
            self.host + "models_available", headers=self.request_headers
        )
        return self._translate_errors(response)

    def tokenize(
        self, model: str, prompt: str, tokens: bool = True, token_ids: bool = True
    ):
        """
        Tokenizes the given prompt for the given model.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "tokens": tokens,
            "token_ids": token_ids,
        }
        response = requests.post(
            self.host + "tokenize",
            headers=self.request_headers,
            json=payload,
            timeout=None,
        )
        return self._translate_errors(response)

    def detokenize(self, model: str, token_ids: List[int]):
        """
        Detokenizes the given tokens.
        """
        payload = {"model": model, "token_ids": token_ids}
        response = requests.post(
            self.host + "detokenize",
            headers=self.request_headers,
            json=payload,
            timeout=None,
        )
        return self._translate_errors(response)

    def complete(
        self,
        model: str,
        prompt: Union[str, List[Union[str, ImagePrompt]]] = "",
        hosting: str = "cloud",
        maximum_tokens: Optional[int] = 64,
        temperature: Optional[float] = 0.0,
        top_k: Optional[int] = 0,
        top_p: Optional[float] = 0.0,
        presence_penalty: Optional[float] = 0.0,
        frequency_penalty: Optional[float] = 0.0,
        repetition_penalties_include_prompt: Optional[bool] = False,
        use_multiplicative_presence_penalty: Optional[bool] = False,
        best_of: Optional[int] = None,
        n: Optional[int] = 1,
        logit_bias: Optional[Dict[int, float]] = None,
        log_probs: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        tokens: Optional[bool] = False,
        disable_optimizations: Optional[bool] = False,
    ):
        """
        Generates samples from a prompt.

        Parameters:
            model (str, required):
                Name of model to use. A model name refers to a model architecture (number of parameters among others). Always the latest version of model is used. The model output contains information as to the model version.

            prompt (str, optional, default ""):
                The text to be completed. Unconditional completion can be started with an empty string (default). The prompt may contain a zero shot or few shot task.

            hosting (str, optional, default "cloud"):
                Specifies where the computation will take place. This defaults to "cloud", meaning that it can be
                executed on any of our servers. An error will be returned if the specified hosting is not available.
                Check available_models() for available hostings.

            maximum_tokens (int, optional, default 64):
                The maximum number of tokens to be generated. Completion will terminate after the maximum number of tokens is reached. Increase this value to generate longer texts. A text is split into tokens. Usually there are more tokens than words. The summed number of tokens of prompt and maximum_tokens depends on the model (for luminous-base, it may not exceed 2048 tokens).

            temperature (float, optional, default 0.0)
                A higher sampling temperature encourages the model to produce less probable outputs ("be more creative"). Values are expected in a range from 0.0 to 1.0. Try high values (e.g. 0.9) for a more "creative" response and the default 0.0 for a well defined and repeatable answer.

                It is recommended to use either temperature, top_k or top_p and not all at the same time. If a combination of temperature, top_k or top_p is used rescaling of logits with temperature will be performed first. Then top_k is applied. Top_p follows last.

            top_k (int, optional, default 0)
                Introduces random sampling from generated tokens by randomly selecting the next token from the k most likely options. A value larger than 1 encourages the model to be more creative. Set to 0 if repeatable output is to be produced.
                It is recommended to use either temperature, top_k or top_p and not all at the same time. If a combination of temperature, top_k or top_p is used rescaling of logits with temperature will be performed first. Then top_k is applied. Top_p follows last.

            top_p (float, optional, default 0.0)
                Introduces random sampling for generated tokens by randomly selecting the next token from the smallest possible set of tokens whose cumulative probability exceeds the probability top_p. Set to 0.0 if repeatable output is to be produced.
                It is recommended to use either temperature, top_k or top_p and not all at the same time. If a combination of temperature, top_k or top_p is used rescaling of logits with temperature will be performed first. Then top_k is applied. Top_p follows last.

            presence_penalty (float, optional, default 0.0)
                The presence penalty reduces the likelihood of generating tokens that are already present in the text. Presence penalty is independent of the number of occurences. Increase the value to produce text that is not repeating the input.

            frequency_penalty (float, optional, default 0.0)
                The frequency penalty reduces the likelihood of generating tokens that are already present in the text. Presence penalty is dependent on the number of occurences of a token.

            repetition_penalties_include_prompt (bool, optional, default False)
                Flag deciding whether presence penalty or frequency penalty are applied to the prompt and completion (True) or only the completion (False)

            use_multiplicative_presence_penalty (bool, optional, default True)
                Flag deciding whether presence penalty is applied multiplicatively (True) or additively (False). This changes the formula stated for presence and frequency penalty.

            best_of (int, optional, default None)
                Generates best_of completions server-side and returns the "best" (the one with the highest log probability per token). Results cannot be streamed.
                When used with n, best_of controls the number of candidate completions and n specifies how many to return – best_of must be greater than n.

            n (int, optional, default 1)
                How many completions to generate for each prompt.

            logit_bias (dict mapping token ids to score, optional, default None)
                The logit bias allows to influence the likelihood of generating tokens. A dictionary mapping token ids (int) to a bias (float) can be provided. Such bias is added to the logits as generated by the model.

            log_probs (int, optional, default None)
                Number of top log probabilities to be returned for each generated token. Log probabilities may be used in downstream tasks or to assess the model's certainty when producing tokens.

            stop_sequences (List(str), optional, default None)
                List of strings which will stop generation if they're generated. Stop sequences may be helpful in structured texts.

                Example: In a question answering scenario a text may consist of lines starting with either "Question: " or "Answer: " (alternating). After producing an answer, the model will be likely to generate "Question: ". "Question: " may therfore be used as stop sequence in order not to have the model generate more questions but rather restrict text generation to the answers.

            tokens (bool, optional, default False)
                return tokens of completion

            disable_optimizations  (bool, optional, default False)
                We continually research optimal ways to work with our models. By default, we apply these optimizations to both your prompt and  completion for you.

                Our goal is to improve your results while using our API. But you can always pass disable_optimizations: true and we will leave your prompt and completion untouched.
        """

        # validate data types
        if not isinstance(model, str):
            raise ValueError("model must be a string")

        if isinstance(temperature, int):
            temperature = float(temperature)
        if isinstance(top_p, int):
            top_p = float(top_p)
        if isinstance(presence_penalty, int):
            presence_penalty = float(presence_penalty)
        if isinstance(frequency_penalty, int):
            frequency_penalty = float(frequency_penalty)

        payload = {
            "model": model,
            "prompt": _to_serializable_prompt(prompt=prompt),
            "hosting": hosting,
            "maximum_tokens": maximum_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "best_of": best_of,
            "n": n,
            "logit_bias": logit_bias,
            "log_probs": log_probs,
            "repetition_penalties_include_prompt": repetition_penalties_include_prompt,
            "use_multiplicative_presence_penalty": use_multiplicative_presence_penalty,
            "stop_sequences": stop_sequences,
            "tokens": tokens,
            "disable_optimizations": disable_optimizations,
        }

        response = requests.post(
            self.host + "complete",
            headers=self.request_headers,
            json=payload,
            timeout=None,
        )
        response_json = self._translate_errors(response)
        if response_json.get("optimized_prompt") is not None:
            # Return a message to the user that we optimized their prompt
            print(
                'We optimized your prompt before sending it to the model. The optimized prompt is available at result["optimized_prompt"]. If you do not want these optimizations applied, you can pass the disable_optimizations flag to your request.'
            )
        return response_json

    def embed(
        self,
        model,
        prompt: Union[str, Sequence[Union[str, ImagePrompt]]],
        pooling: List[str],
        layers: List[int],
        hosting: str = "cloud",
        tokens: Optional[bool] = False,
        type: Optional[str] = None,
    ):
        """
        Embeds a text and returns vectors that can be used for downstream tasks (e.g. semantic similarity) and models (e.g. classifiers).

        Parameters:
            model (str, required):
                Name of model to use. A model name refers to a model architecture (number of parameters among others). Always the latest version of model is used. The model output contains information as to the model version.

            prompt (str, required):
               The text to be embedded.

            layers (List[int], required):
               A list of layer indices from which to return embeddings.
                    * Index 0 corresponds to the word embeddings used as input to the first transformer layer
                    * Index 1 corresponds to the hidden state as output by the first transformer layer, index 2 to the output of the second layer etc.
                    * Index -1 corresponds to the last transformer layer (not the language modelling head), index -2 to the second last layer etc.

            pooling (List[str])
                Pooling operation to use.
                Pooling operations include:
                    * mean: aggregate token embeddings across the sequence dimension using an average
                    * max: aggregate token embeddings across the sequence dimension using a maximum
                    * last_token: just use the last token
                    * abs_max: aggregate token embeddings across the sequence dimension using a maximum of absolute values

            hosting (str, optional, default "cloud"):
                Specifies where the computation will take place. This defaults to "cloud", meaning that it can be
                executed on any of our servers. An error will be returned if the specified hosting is not available.
                Check available_models() for available hostings.

            tokens (bool, optional, default False)
                Flag indicating whether the tokenized prompt is to be returned (True) or not (False)

            type
                Type of the embedding (e.g. symmetric or asymmetric)

        """

        serializable_prompt = _to_serializable_prompt(
            prompt=prompt, at_least_one_token=True
        )

        if tokens is None:
            tokens = False

        payload = {
            "model": model,
            "prompt": serializable_prompt,
            "hosting": hosting,
            "layers": layers,
            "tokens": tokens,
            "pooling": pooling,
            "type": type,
        }
        response = requests.post(
            self.host + "embed", headers=self.request_headers, json=payload
        )
        return self._translate_errors(response)

    def evaluate(
        self,
        model,
        completion_expected,
        hosting: str = "cloud",
        prompt: Union[str, List[Union[str, ImagePrompt]]] = "",
    ):
        """
        Evaluates the model's likelihood to produce a completion given a prompt.

        Parameters:
            model (str, required):
                Name of model to use. A model name refers to a model architecture (number of parameters among others). Always the latest version of model is used. The model output contains information as to the model version.

            completion_expected (str, required):
                The ground truth completion expected to be produced given the prompt.

            hosting (str, optional, default "cloud"):
                Specifies where the computation will take place. This defaults to "cloud", meaning that it can be
                executed on any of our servers. An error will be returned if the specified hosting is not available.
                Check available_models() for available hostings.

            prompt (str, optional, default ""):
                The text to be completed. Unconditional completion can be used with an empty string (default). The prompt may contain a zero shot or few shot task.
        """

        serializable_prompt = _to_serializable_prompt(prompt=prompt)

        payload = {
            "model": model,
            "prompt": serializable_prompt,
            "hosting": hosting,
            "completion_expected": completion_expected,
        }
        response = requests.post(
            self.host + "evaluate", headers=self.request_headers, json=payload
        )
        return self._translate_errors(response)

    def qa(
        self,
        model: str,
        query: str,
        documents: List[Document],
        maximum_tokens: int = 64,
        max_chunk_size: int = 175,
        disable_optimizations: bool = False,
        max_answers: int = 0,
        min_score: float = 0.0,
        hosting: str = "cloud",
    ):
        """
        Answers a question about a prompt.

        Parameters:
            model (str, required):
                Name of model to use. A model name refers to a model architecture (number of parameters among others). Always the latest version of model is used. The model output contains information as to the model version.

            query (str, required):
                The question to be answered about the documents by the model.

            documents (List[Document], required):
                A list of documents. This can be either docx documents or text/image prompts.

            maximum_tokens (int, default 64):
                The maximum number of tokens to be generated. Completion will terminate after the maximum number of tokens is reached.

                Increase this value to generate longer texts. A text is split into tokens. Usually there are more tokens than words. The summed number of tokens of prompt and maximum_tokens depends on the model (for luminous-base, it may not exceed 2048 tokens).

            max_chunk_size (int, default 175):
                Long documents will be split into chunks if they exceed max_chunk_size.
                The splitting will be done along the following boundaries until all chunks are shorter than max_chunk_size or all splitting criteria have been exhausted.
                The splitting boundaries are, in the given order:
                1. Split first by double newline
                (assumed to mark the boundary between 2 paragraphs).
                2. Split paragraphs that are still too long by their median sentence as long as we can still find multiple sentences in the paragraph.
                3. Split each remaining chunk of a paragraph or sentence further along white spaces until each chunk is smaller than max_chunk_size or until no whitespace can be found anymore.

            disable_optimizations  (bool, default False)
                We continually research optimal ways to work with our models. By default, we apply these optimizations to both your query, documents, and answers for you.
                Our goal is to improve your results while using our API. But you can always pass `disable_optimizations: true` and we will leave your query, documents, and answers untouched.

            max_answers (int, default 0):
                The upper limit of maximum number of answers.

            min_score (float, default 0.0):
                The lower limit of minimum score for every answer.

            hosting (str, default "cloud"):
                Specifies where the computation will take place. This defaults to "cloud", meaning that it can be
                executed on any of our servers. An error will be returned if the specified hosting is not available.
                Check available_models() for available hostings.
        """

        payload = {
            "model": model,
            "query": query,
            "documents": [document._to_serializable_document() for document in documents],
            "maximum_tokens": maximum_tokens,
            "max_answers": max_answers,
            "min_score": min_score,
            "max_chunk_size": max_chunk_size,
            "disable_optimizations": disable_optimizations,
            "hosting": hosting,
        }

        response = requests.post(
            self.host + "qa",
            headers=self.request_headers,
            json=payload,
            timeout=None,
        )
        response_json = self._translate_errors(response)
        return response_json

    def _explain(self, model: str, request: ExplanationRequest, hosting: Optional[str] = None):
        body = request.render_as_body(model, hosting)
        response = requests.post(f"{self.host}explain", headers=self.request_headers, json=body)
        response_dict = self._translate_errors(response)
        return response_dict
        

    @staticmethod
    def _translate_errors(response):
        if response.status_code == 200:
            return response.json()
        else:
            if response.status_code == 400:
                raise ValueError(response.status_code, response.json())
            elif response.status_code == 401:
                raise PermissionError(response.status_code, response.json())
            elif response.status_code == 402:
                raise QuotaError(response.status_code, response.json())
            elif response.status_code == 408:
                raise TimeoutError(response.status_code, response.json())
            else:
                raise RuntimeError(response.status_code, response.json())
