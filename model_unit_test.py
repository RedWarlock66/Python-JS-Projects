import unittest
from parameterized import parameterized
from test_model import TestModel
from generative_models import CompletionResult, GenerativeModel, generative_models as gm_factory
from json import load


def _get_test_samples(key: str):
    with open('test_samples.json', 'r') as file:
        samples = load(file)
    return [tuple(sample) for sample in samples[key]]


class GenerativeModelFactoryTest(unittest.TestCase):
    def test_gm_factory(self):
        self.assertIsInstance(gm_factory.models(), list)
        non_existing_model = ''
        for model in gm_factory.models():
            self.assertTrue(issubclass(type(gm_factory.get_model(model)), GenerativeModel))
            # isn't logically guaranteed, but it should be enough
            if not non_existing_model and model + ('-' * 50) not in gm_factory.models():
                non_existing_model = model + ('-' * 50)
        with self.assertRaises(Exception):
            gm_factory.get_model(non_existing_model)


class BasicGenerativeModelTest(unittest.TestCase):
    """
    tests basic I/O functionality of generative_models.GenerativeModel through test_model.TestModel
    """

    def __init__(self, method_name='runTest'):
        super(BasicGenerativeModelTest, self).__init__(method_name)
        self._model = TestModel()

    @parameterized.expand(_get_test_samples('send_message'))
    def test_send_message(self, message: str, random_value: int, symbols_count: int):
        completion_result = self._model.send_message(message=message,
                                                     random_value=random_value,
                                                     symbols_count=symbols_count)
        self.assertIsInstance(completion_result, CompletionResult)
        if random_value < 3:
            self._assert_error(completion_result)
        else:
            self._assert_success(completion_result)

    @parameterized.expand(_get_test_samples('send_prompt'))
    def test_send_prompt(self, instruction: str, expectation: str, request: str,
                         examples: list[dict]):
        completion_result = self._model.send_prompt(instruction, expectation, request, examples,
                                                    random_value=4, symbols_count=9)
        self._assert_success(completion_result)
        completion_result = self._model.send_prompt(instruction, expectation, request, examples,
                                                    random_value=4, symbols_count=9, return_prompt=True)
        print('-'*50)
        print(f'{instruction = }', f'{expectation = }', f'{request = }')
        if examples is not None:
            examples_string = '\n'.join([str(example) for example in examples])
            print(f'examples:\n{examples_string}')
        print(f'prompt:\n{completion_result.completion}')

    @parameterized.expand(_get_test_samples('send_content_with_overlap'))
    def test_send_content_with_overlap(self, content: str, overlap: int, context_window: int, request_pause: int,
                                       final_instruction: str, cut_completion: bool = False):
        print(f'Sending content with overlap {"in parallel" if request_pause == 0 else "in series"}')
        print(f'{content = } {overlap = } {context_window = } {request_pause = }')
        self._model.set_context_window(context_window)
        self._model.set_request_pause(request_pause)
        content_oversized = (len(self._model.encoding.encode(content)) > context_window)
        # to be explicit
        compressing_instruction = self._model.content_compressing_instruction
        completion_result = self._model.send_content_with_overlap(content=content, overlap=overlap,
                                                                  random_value=4, cut_completion=cut_completion,
                                                                  final_instruction=final_instruction,
                                                                  compress=compressing_instruction)
        if len(self._model._encode(final_instruction)) > self._model.settings['context_window']:
            self._assert_error(completion_result)
            return
        if content_oversized:
            if len(self._model._encode(compressing_instruction)) > self._model.settings['context_window']:
                self._assert_error(completion_result)
                return
            if not cut_completion:
                self._assert_error(completion_result)
                return
        self._assert_success(completion_result)
        print('-' * 50)
        # execute coverage assessment after testing

    def _assert_success(self, result: CompletionResult):
        self.assertIsInstance(result, CompletionResult)
        self.assertTrue(result.success)
        self.assertIsInstance(result.completion, str)
        self.assertTrue(len(result.completion) > 0)
        self.assertIs(result.error, None)
        print(f'success was expected: {result.success = } {result.completion = }')

    def _assert_error(self, result: CompletionResult):
        self.assertIsInstance(result, CompletionResult)
        self.assertFalse(result.success)
        self.assertEqual(result.completion, '')
        self.assertIsInstance(result.error, Exception)
        print(f'error was expected: {result.success = } {result.error = }')


class AsynchronousGenerativeModelTest(unittest.IsolatedAsyncioTestCase):
    def __init__(self, method_name='runTest'):
        super(AsynchronousGenerativeModelTest, self).__init__(method_name)
        self._model = TestModel()

    @parameterized.expand(_get_test_samples('send_message'))
    async def test_send_messages_consequentially(self, message: str, random_value: int, symbols_count: int):
        completion_result = await self._model.asend_message(message=message,
                                                            random_value=random_value,
                                                            symbols_count=symbols_count)
        if random_value < 3:
            self._assert_error(completion_result)
        else:
            self._assert_success(completion_result)

    @parameterized.expand(_get_test_samples('send_prompt'))
    async def test_send_prompt_consequentially(self, instruction: str, expectation: str, request: str,
                                               examples: list[dict]):
        completion_result = await self._model.asend_prompt(instruction, expectation, request, examples,
                                                           random_value=4, symbols_count=9)
        self._assert_success(completion_result)

    @parameterized.expand(_get_test_samples('send_content_with_overlap'))
    async def test_send_content_with_overlap_cons(self, content: str, overlap: int, context_window: int,
                                                  request_pause: int, final_instruction: str,
                                                  cut_completion: bool = False):
        self._model.set_context_window(context_window)
        self._model.set_request_pause(request_pause)
        content_oversized = (len(self._model.encoding.encode(content)) > context_window)
        compressing_instruction = self._model.content_compressing_instruction
        completion_result = await self._model.asend_content_with_overlap(content=content, overlap=overlap,
                                                                         random_value=4, cut_completion=cut_completion,
                                                                         final_instruction=final_instruction,
                                                                         compress=compressing_instruction)
        if len(self._model._encode(final_instruction)) > self._model.settings['context_window']:
            self._assert_error(completion_result)
            return
        if content_oversized:
            if len(self._model._encode(compressing_instruction)) > self._model.settings['context_window']:
                self._assert_error(completion_result)
                return
            if not cut_completion:
                self._assert_error(completion_result)
                return
        self._assert_success(completion_result)

    def _assert_success(self, result: CompletionResult):
        self.assertIsInstance(result, CompletionResult)
        self.assertTrue(result.success)
        self.assertIsInstance(result.completion, str)
        self.assertTrue(len(result.completion) > 0)
        self.assertIs(result.error, None)
        print(f'success was expected: {result.success = } {result.completion = }')

    def _assert_error(self, result: CompletionResult):
        self.assertIsInstance(result, CompletionResult)
        self.assertFalse(result.success)
        self.assertEqual(result.completion, '')
        self.assertIsInstance(result.error, Exception)
        print(f'error was expected: {result.success = } {result.error = }')


if __name__ == '__main__':
    unittest.main()
