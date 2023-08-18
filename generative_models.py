import threading
from abc import ABC, ABCMeta, abstractmethod
from json import load
from copy import deepcopy
import openai
import tiktoken
import asyncio

GPT35, GPT2 = 'GPT 3.5', 'GPT 2'

# Generative model infrastructure classes


class GenerativeModelMeta(ABCMeta):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs) -> 'GenerativeModel':
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class GenerativeModelFactory:
    _models = {}

    @classmethod
    def models(cls):
        return list(cls._models.keys())

    @classmethod
    def register_model(cls, name: str, value: 'GenerativeModel'):
        cls._models[name] = value

    @classmethod
    def get_model(cls, name: str, *args, **kwargs) -> 'GenerativeModel':
        if name not in cls._models:
            raise Exception(f'Model {name} is not registered!')
        return cls._models[name](name, *args, **kwargs)

# Generative models classes


class GenerativeModel(ABC, metaclass=GenerativeModelMeta):

    _settings_file = 'models_settings.json'
    _content_compressing_instruction = 'Briefly retell the text below retaining all the information:'

    def __init__(self, name: str, *args, **kwargs):
        self._settings = self._read_settings(name)
        self._encoding = tiktoken.encoding_for_model(self._settings['model'])

    @property
    def settings(self) -> dict:
        """
        model's settings should be included in models_settings.json
        settings required for any models:
            model: a name of the model. be sure that model's name is fit for using tiktoken
            context_window: a size of model's context window in tokens. int
            request_pause: a pause between two consequential requests in seconds. int
        :return dict of model's settings:
        """
        # used deepcopy to prohibit settings changing
        return deepcopy(self._settings)

    @property
    def content_compressing_instruction(self):
        return self._content_compressing_instruction

    @abstractmethod
    def send_message(self, message: str, max_tokens: int = None, top_p: float = None,
                     temperature: float = None, *args, **kwargs) -> 'CompletionResult':
        """
        sends a single message (prompt) to a model and returns its completion
        :param message: a prompt that is given to a model
        :param max_tokens: the limit of tokens within a model's completion
        :param top_p: a number from 0 to 1, in range which should be the sum of max probable generated tokens
        :param temperature: a number from 0 to 2 which makes probability distribution more or less peaked (creativity)
        :param args: any additional args
        :param kwargs: any additional kwargs
        :return: CompletionResult instance
        """
        pass

    def send_prompt(self, instruction: str, expectation: str, request: str,
                    examples: list[dict] = None,
                    **generation_parameters) -> 'CompletionResult':
        """
        send zero-shot, one-shot or a few-shot inference prompt to a model. relies on send_message() method
        one-shot prompt example:
        example[0]:
        Summarize this review: - instruction
        I love this movie! - example's request (examples[0]['request'])
        Sentiment: - expectation
        positive - example's response (examples[0]['response'])

        full request:
        Summarize this review: - instruction
        This movie is not so good - request
        Sentiment: - expectation

        :param instruction: an instruction that is given to the model. Look the example above
        :param expectation: an expectation of what should be returned as a completion. Look the example above
        :param request: a text which should be processed by the model. Look the example above
        :param examples: list of example for one-shot or a few-shot inference. Look the example above
        :param generation_parameters: generation parameters such as max_tokens, top_p and temperature
            look send_message()
        :return: CompletionResult instance
        """
        prompt = self._create_prompt(instruction, expectation, request, examples)
        return self.send_message(prompt, **generation_parameters)

    def send_content_with_overlap(self, content: str, compressing_instruction: str = None, overlap: int = 10,
                                  final_instruction: str = '', **generation_parameters) -> 'CompletionResult':
        """
        intended to send a content which is probably larger than a model's context window.
        uses overlap so the context wouldn't be lost by the model
        instructs model to compress the parts of the prompt until the result of compressing would be less in tokens
        than the size of context window. the uses the result of compressing as a final prompt
        relies on send_message(), asend_message(), _count_tokens(), settings["context_window"],
            settings["request_pause"]
        :param content: message text content
        :param compressing_instruction: an instruction how the model should compress parts of the prompt.
            uses content_compressing_instruction as a default value
        :param overlap: size of overlap in percents
        :param final_instruction: an instruction what a model should do with the final prompt
        :param generation_parameters: generation parameters such as max_tokens, top_p and temperature
            look send_message()
        :return: CompletionResult instance
        """
        # is refactoring needed?
        if compressing_instruction is None:
            compressing_instruction = self.content_compressing_instruction
        tokens, compressing_instruction_size = self._encode(content), len(self._encode(compressing_instruction))
        final_instruction_size = len(self._encode(final_instruction))
        check_result = self._check_instructions_size(tokens, compressing_instruction_size, final_instruction_size)
        if not check_result.success:
            return check_result
        # note: many cycles. should be optimized? refactoring maybe?
        while len(tokens) > self._settings['context_window'] - final_instruction_size:
            initial_length = len(tokens)
            tokens_list = self._split_tokens_with_overlap(tokens, self._settings['context_window'], overlap,
                                                          compressing_instruction_size)
            messages = [f'{compressing_instruction}\n{self._decode(token_set)}' for token_set in tokens_list]
            results = asyncio.run(self._asend_messages_set(messages, self._settings['request_pause'],
                                                           **generation_parameters))
            unif_result = self._unite_completions_results(results)
            if not unif_result['success']:
                # stop inference and return error if there is at least 1 failure. content should be fully processed
                return unif_result['result']
            content = unif_result['result']
            tokens = self._encode(content)
            if len(tokens) >= initial_length:
                # the model generated a completion larger than an initial prompt. so we should stop generating to avoid
                # possible infinite cycle
                # note: maybe iterations limit should be used with/instead of length check?
                return CompletionResult(success=False, error=Exception('The model generated an intermediate prompt '
                                                                       'longer than an initial one. Inference was '
                                                                       'stopped to avoid occurring an infinite cycle'))
        return self.send_message(f'{final_instruction}\n{content}', **generation_parameters)

    async def asend_message(self, message: str, max_tokens: int = None, top_p: float = None,
                            temperature: float = None, *args, **kwargs) -> 'CompletionResult':
        """
        asynchronous version of send_message(). relies on send_message()
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.send_message(message, max_tokens, top_p, temperature,
                                          *args, **kwargs))

    async def asend_prompt(self, instruction: str, expectation: str, request: str, examples: list[dict] = None,
                           **generation_parameters) -> 'CompletionResult':
        """
        asynchronous version of send_prompt(). relies on asend_message()
        """
        prompt = self._create_prompt(instruction, expectation, request, examples)
        return await self.asend_message(prompt, **generation_parameters)

    async def asend_content_with_overlap(self, content: str, compressing_instruction: str = None, overlap: int = 10,
                                         final_instruction: str = '', **generation_parameters) -> 'CompletionResult':
        """
        asynchronous version of send_content_with_overlap(). relies on send_prompt()
        """
        # should it be rewritten to optimize its performance and prevent potential issues?
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.send_content_with_overlap(content,
                                                                                       compressing_instruction,
                                                                                       overlap,
                                                                                       final_instruction,
                                                                                       **generation_parameters))

    @staticmethod
    def _create_prompt(instruction: str, expectation: str, request: str, examples: list[dict] = None):
        prompt = ''
        if examples is not None:
            prompt = '\n\n'.join([f'{instruction}:\n{example["request"]}\n{expectation}:\n{example["response"]}'
                                  for example in examples]) + '\n\n'
        prompt += f'{instruction}:\n{request}\n{expectation}:'
        return prompt

    def _check_instructions_size(self, tokens: list[int], compressing_instruction_size: int,
                                 final_instruction_size: int) -> 'CompletionResult':
        if len(tokens) > self._settings['context_window'] and \
                compressing_instruction_size >= self._settings['context_window']:
            return CompletionResult(success=False, error=Exception('Compressing instruction is larger than the '
                                                                   'context window'))
        if final_instruction_size >= self._settings['context_window']:
            return CompletionResult(success=False, error=Exception('Final instruction is larger than the '
                                                                   'context window'))
        return CompletionResult()

    @staticmethod
    def _unite_completions_results(results: list['CompletionResult']) -> dict:
        content = ''
        for result in results:
            if not result.success:
                return {'success': False, 'result': result}
            content += result.completion + '\n'
        return {'success': True, 'result': content}

    async def _asend_messages_set(self, messages: list[str], request_pause: int, **generation_parameters):
        coroutines, tasks = [self.asend_message(message, **generation_parameters) for message in messages], []
        for index, coroutine in enumerate(coroutines):
            tasks.append(asyncio.create_task(coroutine))
            if request_pause > 0 and index + 1 < len(coroutines):
                await asyncio.sleep(request_pause)
        return await asyncio.gather(*tasks)

    def _encode(self, text: str) -> list[int]:
        """
        encodes the text to the list of tokens
        use a proper tokenizer to implement this method in your subclass
        :param text: text of any length
        :return: list of tokens
        """
        return self._encoding.encode(text)

    def _decode(self, tokens: list[int]) -> str:
        """
        decodes the list of tokens to text
        use a proper tokenizer to implement this method in your subclass
        :param tokens: list of tokens
        :return: text
        """
        return self._encoding.decode(tokens)

    @staticmethod
    def _split_tokens_with_overlap(tokens: list[int], window_size: int, overlap: int,
                                   compressing_instruction_size: int) -> list[list[int]]:
        overlap_tokens, start, result = int(window_size * (overlap / 100)), 0, []
        while start < len(tokens):
            end = start + window_size - compressing_instruction_size
            result.append(tokens[start:end])
            start += end - overlap_tokens
        return result

    @classmethod
    def _read_settings(cls, name: str):
        with open(cls._settings_file, 'r') as settings_file:
            settings = load(settings_file)
        return settings[name]

    def _get_setting(self, name: str, value=None):
        if name not in self.settings:
            return None
        return value if value else self.settings[name]


class GPT35Model(GenerativeModel):

    @property
    def settings(self) -> dict:
        return {key: value for key, value in self._settings.items() if key != 'api_key'}

    def send_message(self, message: str, max_tokens: int = None, top_p: float = None,
                     temperature: float = None, *args, **kwargs) -> 'CompletionResult':
        """
        sends a single message (prompt) to a model and returns its completion as a CompletionResult
        :param message: a prompt that is given to a model
        :param max_tokens: the limit of tokens within a model's completion
        :param top_p: a number from 0 to 1, in range which should be the sum of max probable generated tokens
        :param temperature: a number from 0 to 2 which makes probability distribution more or less peaked (creativity)
        :param args: any additional args
        :param kwargs: any additional kwargs
        :return: CompletionResult instance
        """
        return self._send_message(message=message, max_tokens=max_tokens, top_p=top_p, temperature=temperature)

    def send_chat_message(self, dialogue: list[dict], max_tokens: int = None, top_p: float = None,
                          temperature: float = None, functions: list = None, *args, **kwargs) -> 'CompletionResult':
        """
        sends a single message (prompt) to a model and returns its completion as a CompletionResult
        :param dialogue: a prompt that is given to a model
        :param max_tokens: the limit of tokens within a model's completion
        :param top_p: a number from 0 to 1, in range which should be the sum of max probable generated tokens
        :param temperature: a number from 0 to 2 which makes probability distribution more or less peaked (creativity)
        :param functions: a list of functions to send to the model.
            look https://platform.openai.com/docs/guides/gpt/function-calling
        :param args: any additional args
        :param kwargs: any additional kwargs
        :return: CompletionResult instance
        """
        return self._send_message(max_tokens=max_tokens, top_p=top_p, temperature=temperature, dialogue=dialogue,
                                  functions=functions)

    def _send_message(self, message: str = None, max_tokens: int = None, top_p: float = None,
                      temperature: float = None, dialogue=None, functions=None, *args, **kwargs) -> 'CompletionResult':
        openai.api_key = self._settings['api_key']
        try:
            messages = dialogue if dialogue is not None else [{'role': 'user', 'content': message}]
            if functions is None:
                # a crutch to refactor when the default value of 'functions' will be found out
                response = openai.ChatCompletion.create(model=self.settings['model'], messages=messages,
                                                        max_tokens=self._get_setting('max_tokens', max_tokens),
                                                        top_p=self._get_setting('top_p', top_p),
                                                        temperature=self._get_setting('temperature', temperature))
            else:
                response = openai.ChatCompletion.create(model=self.settings['model'], messages=messages,
                                                        max_tokens=self._get_setting('max_tokens', max_tokens),
                                                        top_p=self._get_setting('top_p', top_p),
                                                        temperature=self._get_setting('temperature', temperature),
                                                        functions=functions)
        except openai.OpenAIError as openai_error:
            return CompletionResult(False, error=openai_error)
        except Exception as error:
            return CompletionResult(False, error=error)
        return CompletionResult(completion=response.choices[0]['message']['content'])


class GPT2Model(GenerativeModel):

    @property
    def settings(self) -> dict:
        return {key: value for key, value in self._settings.items() if key != 'api_key'}

    def send_message(self, message: str, max_tokens: int = None, top_p: float = None,
                     temperature: float = None, *args, **kwargs) -> 'CompletionResult':
        """
        sends a single message (prompt) to a model and returns its completion as a CompletionResult
        :param message: a prompt that is given to a model
        :param max_tokens: the limit of tokens within a model's completion
        :param top_p: a number from 0 to 1, in range which should be the sum of max probable generated tokens
        :param temperature: a number from 0 to 2 which makes probability distribution more or less peaked (creativity)
        :param args: any additional args
        :param kwargs: any additional kwargs
        :return: CompletionResult instance
        """
        openai.api_key = self._settings['api_key']
        try:
            response = openai.Completion.create(engine=self.settings['model'],
                                                prompt=message,
                                                max_tokens=self._get_setting('max_tokens', max_tokens),
                                                top_p=self._get_setting('top_p', top_p),
                                                temperature=self._get_setting('temperature', temperature))
        except openai.OpenAIError as openai_error:
            return CompletionResult(False, error=openai_error)
        except Exception as error:
            return CompletionResult(False, error=error)
        return CompletionResult(completion=response.choices[0].text)


# additional classes


class CompletionResult:
    def __init__(self, success: bool = True, completion: str = '', error: Exception = None):
        self.success = success
        self.completion = completion
        self.error = error

# service methods


generative_models = GenerativeModelFactory
generative_models.register_model(GPT35, GPT35Model)
generative_models.register_model(GPT2, GPT2Model)
