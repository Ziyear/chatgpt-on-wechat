import io
import random
import re
from hashlib import md5

import requests

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from plugins import *


@plugins.register(
    name="MyPicAi",
    desc="自定义ai图片插件",
    version="0.1",
    author="ziyear",
    desire_priority=0,
)
class MyPicAi(Plugin):
  def __init__(self):
    super().__init__()
    try:
      self.config = super().load_config()
      if not self.config:
        self.config = self._load_config_template()
      self.model_url = self.config.get("model_url", '')
      self.authorization = self.config.get("authorization", '')
      self.need_fy = self.config.get("need_fy", True)
      self.fy_appid = self.config.get("fy_appid", '20190717000318722')
      self.fy_appkey = self.config.get("fy_appkey", 'rIicPz8CTERxTScuxjFE')
      self.fy_url = self.config.get("fy_url",
                                    'http://api.fanyi.baidu.com/api/trans/vip/translate')
      logger.info("[MyPicAi] inited")
      self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
    except Exception as e:
      logger.error(f"[MyPicAi]初始化异常：{e}")
      raise "[MyPicAi] init failed, ignore "

  def _load_config_template(self):
    logger.debug(
        "No MyPicAi plugin config.json, use plugins/MyPicAi/config.json.template")
    try:
      plugin_config_path = os.path.join(self.path, "config.json.template")
      if os.path.exists(plugin_config_path):
        with open(plugin_config_path, "r", encoding="utf-8") as f:
          plugin_conf = json.load(f)
          return plugin_conf
    except Exception as e:
      logger.exception(e)

  def on_handle_context(self, e_context: EventContext):
    context = e_context['context'].content
    if not self.starts_with_hua(context):
      return
    if e_context['context'].type != ContextType.TEXT:
      return
    ok, res = self.query(context.replace("请画", "", 1))
    if ok:
      reply = Reply(ReplyType.IMAGE, res)
      e_context["reply"] = reply
      e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

  def starts_with_hua(self, text):
    pattern = '^请画'
    if re.match(pattern, text):
      return True
    else:
      return False

  def query(self, content):
    headers = {
      "Authorization": "Bearer " + self.authorization,
      "Content-Type": "application/json"
    }
    if self.need_fy:
      content = self.fy(content)
    try:
      response = requests.post(self.model_url, headers=headers, json={
        "inputs": content,
      })
      return True, io.BytesIO(response.content)
    except Exception as e:
      logger.error(format(e))
      return False, "画图出现问题，请休息一下再问我吧"

  def fy(self, query):
    salt = random.randint(32768, 65536)
    sign = md5((self.fy_appid + query + str(salt) + self.fy_appkey).encode(
        'utf-8')).hexdigest()
    # Build request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': self.fy_appid, 'q': query, 'from': 'zh', 'to': 'en',
               'salt': salt,
               'sign': sign}
    # Send request
    r = requests.post(self.fy_url, params=payload, headers=headers)
    result = r.json()
    # Show response
    return result['trans_result'][0]['dst']
