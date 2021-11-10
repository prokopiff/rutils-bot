import logging
import logging.config
import os
import requests
import urllib.parse as urlparse
from telegram import Update
from telegram.ext import Updater, MessageHandler, CallbackContext

token = os.getenv('RECRUIT_BOT_TOKEN')
default_headers = {'User-Agent': 'recruit-utils-bot'}


def log_setup():
  logging.config.fileConfig('logging.conf')
  logger = logging.getLogger('main')
  return logger


def handler(update: Update, context: CallbackContext) -> None:
  logger.info('Got a message: %s', update.message.text)
  response = get_email(update.message.text)
  logger.info('Response: %s', response)
  update.message.reply_text(response)


def get_email(input) -> str:
  try:
    if is_url(input):
      logger.debug('Message is a URL')
      return get_email(extract_username(input))
    else:
      return extract_email(input)
  except Exception as e:
    logger.error(e)
    return 'Invalid input'


def is_url(s: str) -> bool:
  return s.find('github.com') > -1


def extract_username(url: str) -> str:
  return urlparse.urlsplit(url)[2].split('/')[1]


def extract_email(user_name: str) -> str:
  repos = get_repos(user_name)
  repo_name = ''
  for repo in repos:
    if not repo['fork']:
      repo_name = repo['name']
      break

  if not repo_name:
    return 'No repositories found'
  else:
    return get_email_from_repo(user_name, repo_name)


def get_repos(username: str):
  logger.debug('Getting repos for %s', username)
  resp = requests.get('https://api.github.com/users/{}/repos'.format(username),
                      headers=default_headers)

  json = sorted(resp.json(), key=lambda repo: repo['updated_at'], reverse=True)
  logger.debug('Got %d repos', len(json))
  return json


def get_email_from_repo(user_name, repo_name) -> str:
  logger.debug('Getting commits for %s/%s', user_name, repo_name)
  commits = requests.get('https://api.github.com/repos/{}/{}/commits'.format(user_name, repo_name)).json()
  commits = sorted(commits, key=lambda c: c['commit']['author']['date'], reverse=True)
  logger.debug('Got %d commits', len(commits))
  msg = 'No commits found'
  for commit in commits:
    if commit['author']['login'] == user_name:
      msg = commit['commit']['author']['email']
      break
  return msg


logger = log_setup()

logger.info('Starting bot')
updater = Updater(token)

updater.dispatcher.add_handler(MessageHandler(filters=None,callback=handler))

updater.start_polling()
logger.info('Started')
updater.idle()
