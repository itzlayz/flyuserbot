# Fly-telegram UserBot
# this code is licensed by cc-by-nc (https://creativecommons.org/share-your-work/cclicenses)

import importlib
import inspect
import shutil
import ast
import sys
import os

from typing import Set

from pyrogram import Client, filters
from pyrogram.types import Message

from .misc import Builder, modules_help
from database.types import account

MODULES_DIR = "modules"
DRAGON_MODULES_DIR = "dragon_modules"
loaded_modules = []


class Filters:
    def owner_filter(_, __, message: Message) -> bool:
        return bool(
            message.from_user.id in account.get("owners") or message.from_user.is_self
        )


owner = filters.create(Filters.owner_filter)


class CodeAnalysis:
    def __init__(self):
        self.functions = (
            "eval",
            "exec",
            "DeleteAccount",
        )
        self.items = []

    def analyze(self, path: str) -> Set[str]:
        with open(path, "r") as file:
            code = file.read()

        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):

                if isinstance(node.func, ast.Attribute):
                    if (
                        isinstance(node.func.value, ast.Call)
                        and isinstance(node.func.value.func, ast.Name)
                        and node.func.value.func.id == "__import__"
                    ):
                        module_name = node.func.value.args[0].s
                        if module_name in self.allowed:
                            self.items.append(module_name)

                elif isinstance(node.func, ast.Name) and node.func.id in self.functions:
                    self.items.append(node.func.id)

        return self.items


class Loader:
    def __init__(self):
        self.help_manager = Builder()

        self.core_modules = (
            "help",
            "loader",
            "core",
            "executor",
        )

    async def unload(self, name: str, client: Client, remove: bool = True) -> bool:
        """Unload a module"""
        if name not in os.listdir(MODULES_DIR):
            raise NameError(f"Module '{name}' is not found!")
        if name in self.core_modules:
            raise PermissionError("Cannot unload system modules!")

        module = importlib.import_module(f"modules.{name}.sources.main")  # load module

        for obj_name, obj in vars(module).items():
            handlers = getattr(obj, "handlers", [])
            if not isinstance(handlers, list):
                continue

            for handler, group in handlers:
                client.remove_handler(handler, group)  # remove handler

        self.help_manager.remove_module(name)  # remove from help

        if name in sys.modules:
            del sys.modules[name]  # remove from sys modules

        if module in loaded_modules:
            loaded_modules.remove(module)

        if remove:
            shutil.rmtree(os.path.join(MODULES_DIR, name))

        return True

    async def load(self, name: str, client: Client,
    check_code: bool = True) -> bool:
        """Load a module"""
        path = os.path.join(MODULES_DIR, name)

        if name not in os.listdir(MODULES_DIR):
            raise NameError(f"Module '{name}' is not found!")
        elif "module.json" not in os.listdir(path):
            raise ValueError(
                f"Module '{name}' is out of date or does not have a module information file."
            )

        if check_code:
            for file in os.listdir(path):
                if file.endswith(".py"):
                    path = os.path.join(MODULES_DIR, name, file)
                    founded_items = CodeAnalysis().analyze(path)
                    if founded_items:
                        raise Exception(
                            f"Malicious code was found in '{name}' module: ",
                            ",".join(founded_items),
                        )

        module = importlib.import_module(f"modules.{name}.sources.main")  # load module
        loaded_modules.append(module)

        # add to help
        commands = [
            func[:-4]
            for func, _ in inspect.getmembers(module, inspect.isfunction)
            if func.endswith("_cmd")
        ]
        self.help_manager.add_module(name, commands)

        for obj_name, obj in vars(module).items():
            handlers = getattr(obj, "handlers", [])
            if not isinstance(handlers, list):
                continue

            for handler, group in handlers:
                client.add_handler(handler, group)  # add handler

        return True

    async def load_dragon(self, name: str, client: Client,
    check_code: bool = True) -> bool:
        """Load dragon module"""
        path = os.path.join(DRAGON_MODULES_DIR, f"{name}.py")
        if not os.path.exists(path):
            raise NameError(f"Dragon module '{name}' is not found!")
            
        if check_code:
            founded_items = CodeAnalysis().analyze(path)
            if founded_items:
                raise Exception(
                    f"Malicious code was found in '{name}' dragon module: ",
                    ",".join(founded_items),
                )

        module = importlib.import_module(f"dragon_modules.{name}")
        loaded_modules.append(module)

        # convert "modules_help" to "modules"
        for module_name, commands in modules_help.items():
            self.help_manager.add_module(
                module_name, [command.split()[0] for command in commands.keys()], True
            )

        for obj_name, obj in vars(module).items():
            handlers = getattr(obj, "handlers", [])
            if not isinstance(handlers, list):
                continue

            for handler, group in handlers:
                client.add_handler(handler, group)  # add handler

        return True

    async def unload_dragon(
        self, name: str, client: Client, remove: bool = True
    ) -> bool:
        """Unload dragon modules"""
        path = os.path.join(DRAGON_MODULES_DIR, f"{name}.py")
        if not os.path.exists(path):
            raise NameError(f"Dragon module '{name}' is not found!")

        module = importlib.import_module(f"dragon_modules.{name}")
        self.help_manager.remove_module(name)

        if name in sys.modules:
            del sys.modules[name]

        if module in loaded_modules:
            loaded_modules.remove(module)

        if remove:
            os.remove(path)

        return True
