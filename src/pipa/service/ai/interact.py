import argparse
import re
import os
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from pipa.common.logger import logger, stream_handler

Msgs: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
Inputs: Dict[str, Dict[str, Any]] = defaultdict(lambda: defaultdict(lambda: ""))
Tools: Dict[str, List[Callable]] = defaultdict(list)


def extract_strings_variables(s: str) -> Optional[List[str]]:
    """Extract inputs from a string

    Args:
        s (str): the string, may contains input like '{input}'

    Returns:
        Optional[List[str]]: Inputs name list
    """
    try:
        s.format()
        return None
    except KeyError:
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        matches = re.findall(pattern, s)
        return matches


def add_msg(
    chat_index: str,
    role: Literal["human", "system", "placeholder", "ai", "agent"],
    input: Optional[str] = None,
    msg: str = "",
) -> None:
    """Add Message to one chat

    Args:
        chat_index (str): In what chat
        role (Literal[&quot;human&quot;, &quot;system&quot;, &quot;placeholder&quot;, &quot;ai&quot;, &quot;agent&quot;]): Specify msg role
        input (Optional[str], optional): Specify msg input. Defaults to None.
        msg (str, optional): Specify msg, use '{xxx}' to indicate a input. Defaults to "".
    """
    match role:
        case "human" | "system" | "placeholder" | "ai":
            Msgs[chat_index].append((role, msg))
            vars = extract_strings_variables(msg)
            if vars is not None:
                for v in vars:
                    if input is not None:
                        Inputs[chat_index][v] = input
        case "agent":
            Msgs[chat_index].append(("placeholder", "{agent_scratchpad}"))


def add_func(chat_index: str, func: Callable) -> None:
    """Add external function call

    Args:
        chat_index (str): In what chat
        func (Callable): Function that may be called to parse outputs (judged by the AI).
    """
    Tools[chat_index].append(tool(func))


class Model:
    """AI Model

    Call Model.setup() first to set the API Key.
    """

    is_enable = True if "OPENAI_API_KEY" in os.environ else False

    def enabled(f):
        def wrap(*args, **kwargs):
            if Model.is_enable:
                return f(*args, **kwargs)
            else:
                return None

        return wrap

    @staticmethod
    def setup(api_key: str) -> None:
        os.environ["OPENAI_API_KEY"] = api_key
        Model.is_enable = True

    @enabled
    def __init__(self) -> None:
        self._model = ChatOpenAI(
            model="qwen-turbo",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self._parser = StrOutputParser()
        self._chain = self._model | self._parser

    @enabled
    def invoke(self, chat_index: str) -> str:
        """Invoke messages without function calls

        Args:
            chat_index (str): In what chat

        Returns:
            str: the output
        """
        msg = Msgs[chat_index]
        input = Inputs[chat_index]
        prompt_v = ChatPromptTemplate.from_messages(msg).invoke(input)
        return self._chain.invoke(prompt_v)

    @enabled
    def agent_invoke(self, chat_index: str) -> Dict[str, Any]:
        """Invoke messages with function calls

        Args:
            chat_index (str): In what chat

        Returns:
            Dict[str, Any]: the output
        """
        msg = Msgs[chat_index]
        tools = Tools[chat_index]
        input = Inputs[chat_index]
        agent = create_tool_calling_agent(self._model, Tools[chat_index], msg)
        agent_exe = AgentExecutor(agent=agent, tools=tools, verbose=True)
        return agent_exe.invoke(input=input)


def main():
    logger.setLevel(level=logging.INFO)
    stream_handler.setLevel(level=logging.INFO)
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-c", "--chat", type=str, default="Test", help="Specify chat name"
    )
    argp.add_argument("--key", type=str, default=None, help="Specify API Key")
    args = argp.parse_args()
    chat = getattr(args, "chat")
    api_key = getattr(args, "key")
    if api_key is None and "OPENAI_API_KEY" not in os.environ:
        logger.error("Not specify api key")
        exit(-1)

    add_msg(
        chat,
        input="bob",
        role="system",
        msg="You are a helpful AI bot. Your name is {name}.",
    )
    add_msg(chat, role="human", msg="Hello, how are you doing?")
    add_msg(chat, role="ai", msg="I'm doing well, thanks!")
    add_msg(chat, input="whats your name", role="human", msg="{question}")
    Model.setup(api_key=api_key)
    model = Model()
    ret = model.invoke(chat)
    logger.info(f"AI response: {ret}")


if __name__ == "__main__":
    main()
