import logging
from io import BytesIO

import requests
from celery import shared_task
from celery.decorators import task
from telegram_handler.formatters import HtmlFormatter

logger = logging.getLogger(__name__)
logger.setLevel(logging.NOTSET)
logger.propagate = False

__all__ = ['TelegramHandler']


MAX_MESSAGE_LEN = 4096


class TelegramHandler(logging.Handler):
    API_ENDPOINT = 'https://api.telegram.org'
    last_response = None

    def __init__(self, token, chat_id=None, level=logging.NOTSET, timeout=2, disable_notification=False,
                 disable_web_page_preview=False, proxies=None):
        self.token = token
        self.disable_web_page_preview = disable_web_page_preview
        self.disable_notification = disable_notification
        self.timeout = timeout
        self.proxies = proxies
        self.chat_id = chat_id or self.get_chat_id()
        if not self.chat_id:
            level = logging.NOTSET
            logger.error('Did not get chat id. Setting handler logging level to NOTSET.')
        logger.info('Chat id: %s', self.chat_id)

        super(TelegramHandler, self).__init__(level=level)

        self.setFormatter(HtmlFormatter())

    # @classmethod
    # def format_url(cls, token, method):
    #     return '%s/bot%s/%s' % (cls.API_ENDPOINT, token, method)

    def get_chat_id(self):
        response = self.request(method='getUpdates')
        if not response or not response.get('ok', False):
            logger.error('Telegram response is not ok: %s', str(response))
            return
        try:
            return response['result'][-1]['message']['chat']['id']
        except:
            logger.exception('Something went terribly wrong while obtaining chat id')
            logger.debug(response)

    # def request(self, method, **kwargs):
    #     url = self.format_url(self.token, method)

    #     kwargs.setdefault('timeout', self.timeout)
    #     kwargs.setdefault('proxies', self.proxies)
    #     response = None
    #     try:
    #         response = requests.post(url, **kwargs)
    #         self.last_response = response
    #         response.raise_for_status()
    #         return response.json()
    #     except:
    #         logger.exception('Error while making POST to %s', url)
    #         logger.debug(str(kwargs))
    #         if response is not None:
    #             logger.debug(response.content)

    #     return response

    # def send_message(self, text, **kwargs):
    #     data = {'text': text}
    #     data.update(kwargs)
    #     return self.request('sendMessage', json=data)

    # def send_document(self, text, document, **kwargs):
    #     data = {'caption': text}
    #     data.update(kwargs)
    #     return self.request('sendDocument', data=data, files={'document': ('traceback.txt', document, 'text/plain')})

    def emit(self, record):
        text = self.format(record)

        data_from_class = {
            'chat_id': self.chat_id,
            'disable_web_page_preview': self.disable_web_page_preview,
            'disable_notification': self.disable_notification,
            'token': self.token
        }
        send_logs.delay(text,data_list=data_from_class)
        # data = {
        #     'chat_id': self.chat_id,
        #     'disable_web_page_preview': self.disable_web_page_preview,
        #     'disable_notification': self.disable_notification,
        # }

        # if getattr(self.formatter, 'parse_mode', None):
        #     data['parse_mode'] = self.formatter.parse_mode

        # if len(text) < MAX_MESSAGE_LEN:
        #     response = self.send_message(text, **data)
        # else:
        #     response = self.send_document(text[:1000], document=BytesIO(text.encode()), **data)

        # if response and not response.get('ok', False):
        #     logger.warning('Telegram responded with ok=false status! {}'.format(response))


@shared_task(default_retry_delay=10, max_retries=1, time_limit=60)
def send_logs(text,data_list):
    data = {
        'chat_id': data_list.chat_id,
        'disable_web_page_preview': data_list.disable_web_page_preview,
        'disable_notification': data_list.disable_notification,
    }
    if len(text) < MAX_MESSAGE_LEN:
        response = send_message(text,token=data_list.token, **data)
    else:
        response = send_document(text[:1000], token=data_list.token, document=BytesIO(text.encode()), **data)

    if response and not response.get('ok', False):
        logger.warning('Telegram responded with ok=false status! {}'.format(response))

def send_message(text, token, **kwargs):
    data = {'text': text}
    data.update(kwargs)
    return request('sendMessage', token=token  json=data)

def send_document( text, document, token, **kwargs):
    data = {'caption': text}
    data.update(kwargs)
    return request('sendDocument', token=token data=data, files={'document': ('traceback.txt', document, 'text/plain')})

def format_url(cls, token, method):
        return '%s/bot%s/%s' % ("https://api.telegram.org", token, method)

def request(method, token, **kwargs):
        url = format_url(token, method)

        kwargs.setdefault('timeout', 2)
        kwargs.setdefault('proxies', None)
        response = None
        try:
            response = requests.post(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except:
            logger.exception('Error while making POST to %s', url)
            logger.debug(str(kwargs))
            if response is not None:
                logger.debug(response.content)

        return response