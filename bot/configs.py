import logging
import os
from typing import Union

import yaml
from addict import Dict

logger = logging.getLogger(__name__)

__all__ = [
    "Bot",
    "Log",
    "Colors",
    "Emojis",
    "Reactions",
    "HelpMessages",
    "Events",
    "Fun",
    "Tasks",
]


def _env_var_constructor(loader, node) -> Union[str, list[str]]:
    default = None

    # 為純量，獲取單一環境變數
    if node.id == "scalar":
        key = loader.construct_scalar(node)
        value = os.getenv(key, default)

        return value
    # 為序列，獲取多個環境變數
    else:
        keys = loader.construct_sequence(node)
        values = [os.getenv(key) for key in keys]

        return values


def _join_var_constructor(loader, node) -> str:
    fields = loader.construct_sequence(node)
    return "".join(str(x) for x in fields)


yaml.SafeLoader.add_constructor("!ENV", _env_var_constructor)
yaml.SafeLoader.add_constructor("!JOIN", _join_var_constructor)

with open("configs.yml", "r", encoding="UTF-8") as f:
    _CONFIG_YAML = yaml.safe_load(f)
    _CONFIG_DICT = Dict(_CONFIG_YAML)

Bot: Dict = _CONFIG_DICT.bot

Log: Dict = _CONFIG_DICT.log

Colors: Dict = _CONFIG_DICT.styles.colors

Emojis: Dict = _CONFIG_DICT.styles.emojis

Reactions: Dict = _CONFIG_DICT.styles.reactions

HelpMessages: Dict = _CONFIG_DICT.help_messages

Events: Dict = _CONFIG_DICT.events

Fun: Dict = _CONFIG_DICT.fun

Tasks: Dict = _CONFIG_DICT.tasks
