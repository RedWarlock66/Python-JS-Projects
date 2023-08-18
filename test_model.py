import tiktoken
import random
from generative_models import GenerativeModel, CompletionResult


class TestModel(GenerativeModel):
    def __init__(self, context_window: int = 10, request_pause: int = 0, *args, **kwargs):
        self._settings = {'context_window': context_window, 'request_pause': request_pause}
        self._encoding = tiktoken.encoding_for_model('gpt-3.5-turbo-0613')

    @property
    def encoding(self):
        return self._encoding

    def set_context_window(self, value: int):
        self._settings['context_window'] = value

    def set_request_pause(self, value: int):
        self._settings['request_pause'] = value

    def send_message(self, message: str, max_tokens: int = None, top_p: float = None,
                     temperature: float = None, *args, **kwargs) -> 'CompletionResult':
        random_value = kwargs.get('random_value', 4)
        if random_value < 3:
            return CompletionResult(success=False, error=Exception('Test exception'))
        else:
            if 'return_prompt' in kwargs:
                return CompletionResult(completion=message)
            else:
                if 'compress' in kwargs:
                    message = message.replace(kwargs['compress'], '', 1)
                completion_cut = 2 if kwargs.get('cut_completion', False) else 1
                symbols_count = int(kwargs.get('symbols_count', len(message)) / completion_cut)
                completion = message[:symbols_count]
                return CompletionResult(completion=completion)
