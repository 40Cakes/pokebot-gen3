# Note: This file will get replaced when run in GitHub actions.
# In that case, the tagged version will be placed in here instead.
#
# So this file is only for development, or when someone just fetches
# the Git repository.
#
# It will try to get the current commit hash and use it as the
# version number, prefixed by `dev-` (e.g. `dev-a1b2c3d`.)

import os
from modules.runtime import get_base_path

pokebot_name = "PokéBot"
pokebot_version = "dev"

try:
    # If someone managed to get a copy of the repository without actually having
    # Git installed, this should still be able to get the commit hash of the current
    # HEAD.
    # It's probably not the _best_ way to do this... but it works.
    git_dir = get_base_path() / ".git"
    if git_dir.is_dir():
        with open(git_dir / "HEAD", "r") as head_file:
            head = head_file.read().strip()
            if head.startswith("ref: "):
                # If the head of a branch is checked out
                full_path = git_dir.as_posix() + "/" + head[5:]
                with open(full_path, "r") as ref_file:
                    head = ref_file.read().strip()

            if len(head) == 40:
                # If a tag is checked out
                for tag_path in (git_dir / "refs" / "tags").iterdir():
                    if tag_path.is_file():
                        with open(tag_path, "r") as tag_file:
                            tag = tag_file.read().strip()
                            if tag == head:
                                pokebot_version = tag_path.name
                                break

                # If some regular non-head commit is checked out
                if pokebot_version == "dev":
                    pokebot_version = f"dev-{head[0:7]}"
except:
    # If any issue occurred while trying to figure out the current commit hash,
    # just default to showing 'dev' for the version.
    pass
