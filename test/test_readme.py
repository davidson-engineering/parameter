"""Run the README examples: pycon blocks as doctests, console blocks against the CLI."""

import doctest
import re
import shlex
from pathlib import Path

import pytest

from parameter.cli import main

README = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
BLOCK = re.compile(r"^```(\w+)\n(.*?)^```", re.MULTILINE | re.DOTALL)
BLOCKS = BLOCK.findall(README)


@pytest.fixture
def readme_files(tmp_path, monkeypatch):
    """Write the README's ``# name.yaml`` blocks to a scratch directory and work there."""
    for language, body in BLOCKS:
        first, _, rest = body.partition("\n")
        if language == "yaml" and first.startswith("# "):
            (tmp_path / first[2:].strip()).write_text(rest, encoding="utf-8")
    monkeypatch.chdir(tmp_path)


def test_python_examples(readme_files):
    examples = "\n".join(body for language, body in BLOCKS if language == "pycon")
    test = doctest.DocTestParser().get_doctest(examples, {}, "README.md", "README.md", 0)
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    runner.run(test)
    assert runner.failures == 0, f"{runner.failures} README example(s) failed, see output above"


def test_command_line_examples(readme_files, capsys):
    blocks = [body for language, body in BLOCKS if language == "console" and "$ parameter" in body]
    assert blocks
    for body in blocks:
        for command, expected in re.findall(r"^\$ (.*)\n((?:(?!\$ ).*\n)*)", body, re.MULTILINE):
            args = shlex.split(command)
            assert args[0] == "parameter"
            output_file = args[args.index(">") + 1] if ">" in args else None
            code = main(args[1 : args.index(">")] if output_file else args[1:])
            out = capsys.readouterr().out
            assert code == 0, command
            if output_file:
                Path(output_file).write_text(out, encoding="utf-8")
            else:
                assert out.strip() == expected.strip(), command
