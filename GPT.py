from pathlib import Path
from json import load, dump
from datetime import datetime
import openai

class ConversationAPI:

    _settings_file = settings = Path(__file__).resolve().parent / 'settings/openai_settings.json'

    def __init__(self):
        self._settings = self._read_settings()
        self._conversation = []
        self._log_file = self._generate_log_file_name()

    @property
    def conversation(self):
        return self._conversation

    @property
    def openai_key(self):
        return self._settings['key']

    @openai_key.setter
    def openai_key(self, value:str):
        #here must be a transaction
        self._settings['key'] = value
        self._write_settings()

    def send_message(self, role:str, content:str) -> dict['success':bool, 'result':(dict)]:
        openai.api_key = self._settings['key']
        self._add_message({"role": role, "content": content})
        try:
            response = openai.ChatCompletion.create(model=self._settings['model'],
                                                    messages=self._conversation)
        except openai.OpenAIError as error:
            return {'success':False,
                    'result':{'error_type':'OpenAI API error', 'description':str(error)}}
        except Exception as error:
            return {'success': False,
                    'result': {'error_type': 'Other error', 'description': str(error)}}
        response_message = response.choices[0]['message']
        self._add_message(response_message, response['usage']['total_tokens'])
        return {"success":True,
                "result":{'role':response_message['role'], 'content':response_message['content']}
                }

    def clear_conversation(self):
        self._save_conversation()
        self._log_file = self._generate_log_file_name()
        self._conversation.clear()

    def _generate_log_file_name(self) -> str:
        return Path(__file__).resolve().parent / f'log/log {datetime.now().strftime("%Y%m%d%H%M%S")}.json'

    def _read_settings(self) -> dict:
        with open(self._settings_file, 'r') as openai_setting:
            settigns_dict = load(openai_setting)
        return settigns_dict

    def _write_settings(self):
        with open(self._settings_file, 'w') as openai_settings:
            dump(self._settings, openai_settings)

    def _add_message(self, message, total_tokens:int = None):
        self._conversation.append(message)
        #here we should use a separate thread
        self._save_conversation()
        self._cut_converstaion(total_tokens)

    def _cut_converstaion(self, total_tokens:int = None):
        if total_tokens is not None and total_tokens >= self._settings['max_tokens']:
            #this solution doesn't consider all the nuances but it's good enough in most cases
            messages_to_remove = round(len(self._conversation) * self._settings['conversation_cut_percentage'] / 100)
            self._conversation = self._conversation[messages_to_remove:]
            self._log_file = self._generate_log_file_name()

    def _save_conversation(self):
        with open(self._log_file, 'w') as log_file:
            dump(self._conversation, log_file)