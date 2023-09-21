import os
from jsonschema import validate
from ruamel.yaml import YAML
from modules.Console import console
from ruamel.yaml import YAML

yaml = YAML()

block_schema = """
type: object
properties:
    block_list:
        type: array
        uniqueItems: true"""

file = "stats\CatchBlockList.yml"

def GetBlockList():
    try:
        if not os.path.isfile(file):
            # BlockList file doesn't exist, create it
            BlockListFile = open(file, 'w')
            BlockListFile.write("# CatchBlockList\n# example list in comment below\n\n#block_list: \n#- Bulbasaur\n#- Charmander\n#- Squirtle\n\nblock_list: \n- FakePokemonName ")
            BlockListFile.close()
    except Exception:
        console.print_exception()

    try:
        with open(file, mode='r', encoding='utf-8') as f:
            blockListFile = yaml.load(f)
            validate(blockListFile, yaml.load(block_schema))
            blockList = blockListFile
            return blockList
    except Exception:
        console.print_exception()
        console.print('[bold red]CatchBlockList is invalid![/]')
        return None

