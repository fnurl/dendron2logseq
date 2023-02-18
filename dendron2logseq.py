#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path
from shutil import copytree

# Default globals
INDENT = '\t'

# compiled regular expressions
heading_re = re.compile(r"(#+) ")
inline_code_re = re.compile(r"`.*?`")
embed_token_re = re.compile(r"!\[\[.+?\]\]")
embed_token_with_anchor_re = re.compile(r"!\[\[(.+?)(#.*)?\]\]")
wiki_link_token_re = re.compile(r"\[\[.+?\]\]")
wiki_link_token_with_internals_re = re.compile(r"\[\[(.*?|)?(.+?)(#.*)?\]\]")
image_assets_re = re.compile(r"(!\[.*?\]\()(/assets/)(.*?\))")


def ask_for_confirmation(msg, default=None):
    """Promt msg to user, return answer: 'y' (True), 'n' (False).

    If no answer use default if provided.
    """
    yes = 'Y' if default == 'y' else 'y'
    no = 'N' if default == 'n' else 'n'
    while True:
        answer = input(f"{msg} [{yes}/{no}] ").lower()
        if answer == '' and default:
            answer = default
        if answer == 'y':
            return True
        elif answer == 'n':
            return False


def get_duplicate_titles(vault_path):
    """Return any duplicate titles, {title: [filepath, filepath], ...}."""
    # {title: [filepath1, filpath2, ...], ...}
    titles = {}
    # collect titles
    for childpath in vault_path.iterdir():
        if childpath.is_file() and childpath.suffix == '.md':
            title = get_title(childpath)
            if title:
                titles.setdefault(title, []).append(childpath.name)

    # collect duplicate titles
    duplicates = {}
    for title, filepaths in titles.items():
        if len(filepaths) > 1:
            duplicates[title] = filepaths
    return duplicates


def get_title(md_filepath):
    """Return title of markdown file at md_filepath. Return None if not found."""
    title = None
    with open(md_filepath) as md_file:
        for line_num, line in enumerate(md_file):
            # first line - no frontmatter?
            if line_num == 0:
                if not line.startswith('---'):
                    break
                continue
            # frontmatter - title found
            elif line.startswith('title:'):
                title = line[6:].strip()
                # strip initial and ending quotes
                if title[0] in ['"', "'"] and title[-1] == title[0]:
                    title = title[1:-1]
                    break
            # end of frontmatter
            elif line.rstrip().startswith('---'):
                break
    return title


def vault2graph(vault_path, output_path, remove_frontmatter, alias_title):
    """Save assets dir and processed markdown files to output_path."""
    print(f"\nProcessing Dendron vault at {vault_path.resolve()} [{remove_frontmatter=}, {alias_title=}]")

    # process directory items
    assets_path = None
    for childpath in vault_path.iterdir():
        if childpath.name[0] == "." or childpath.suffix == ".yml":
            print(f"IGNORED: {childpath.name}")
            continue
        elif childpath.is_dir() and childpath.name == "assets":
            assets_path = childpath
        elif childpath.suffix == ".md":
            new_name = f"{childpath.stem.replace('.', '___')}.md"
            print(f"{childpath.name} -> {new_name}")
            process_and_save_file(childpath, output_path, new_name,
                                  remove_frontmatter, alias_title)
        else:
            print(f"WARNING: File not handled, {childpath.name!r}")

    if assets_path:
        print(f"Assets directory found, copying {assets_path.resolve()} -> {(output_path / 'assets').resolve()}")
        copytree(assets_path, output_path / "assets", dirs_exist_ok=True)


def process_and_save_file(source_path, output_path, new_name,
                          remove_frontmatter, alias_title):
    output = []
    with open(source_path, 'r') as source_file:
        first_line_checked = False
        in_frontmatter = False
        in_code_block = False
        frontmatter_handled = False
        outline_level = 0

        for line in source_file:
            # first line, check if frontmatter exists
            if not first_line_checked:
                if not line.rstrip().startswith('---'):
                    frontmatter_handled = True
                first_line_checked = True

            #### PROCESS FRONTMATTER ####
            if not frontmatter_handled:
                #print(f"FRONTMATTER: {line!r}")
                # start/end of frontmatter found
                if line.rstrip().startswith('---'):
                    # start
                    if not in_frontmatter:
                        in_frontmatter = True
                        # keep frontmatter - begin code block
                        if not remove_frontmatter:
                            # frontmatter will be added as a code block
                            output.append('- ```\n')
                            output.append(f"  {line}")
                    # end
                    else:
                        # keep frontmatter - end code block
                        if not remove_frontmatter:
                            output.append(f"  {line}")
                            output.append('  ```\n')
                        in_frontmatter = False
                        frontmatter_handled = True
                    # start/end handled, go to next line
                    continue

                # frontmatter not handled, line is not '---' -> in frontmatter
                # use title as alias?
                elif line.startswith('title:'):
                    if alias_title:
                        output.insert(0, f"alias:: {line[6:].lstrip()}")
                    elif not remove_frontmatter:
                        output.append(f"  {line}")
                # add key to code block
                elif not remove_frontmatter:
                    output.append(f"  {line}")

                # next line (no need for else below)
                continue

            #### PROCESS DOCUMENT BODY ####
            #print(f"BODY: {line!r}")

            # code block start/end
            # LIMITATION: Does not handle indented code blocks. Will remove any
            # indentation before '```'
            if line.lstrip().startswith("```"):
                #print(f"CODE: {line!r}")
                line = line.lstrip()
                # start
                if not in_code_block:
                    line = f"{INDENT*outline_level}- {line}"
                # end
                else:
                    line = f"{INDENT*outline_level}  {line}"
                in_code_block = not in_code_block
                output.append(line)
                continue

            # In code block, do not change line, just indent
            if in_code_block:
                #print(f"CODE: {line!r}")
                line = f"{INDENT*outline_level}  {line}"
                output.append(line)
                continue

            # Outside of code block - use headings to determine outline
            # hierarchy and process internal links and embeds
            if line[0] == '#':
                #print(f"HEADING: {line!r}")
                match = heading_re.match(line)
                if match:
                    outline_level = len(match[1])
                    # indent heading
                    line = f"{INDENT*(outline_level-1)}- {line}"
                    line = convert_internal_links(line)
                    output.append(line)
                    continue

            # Indent empty lines
            if line.lstrip() == '':
                line = f"{INDENT*outline_level}-{line}"
            # Indent bullet points
            elif line.lstrip()[0] == '-':
                line = f"{INDENT*outline_level}{line}"
            # Indent line ordinary lines
            else:
                line = f"{INDENT*outline_level}- {line}"

            #print(f"OUTLINE: {line!r}")
            # take care of embeds, ![[title]] before internal links, [[title]]
            # so that we don't have to worry about accidentally mistaking an
            # embed for a internal link
            line = convert_embeds(line)
            line = convert_internal_links(line)

            # fix image path from /assets/ to ./assets/
            if 'assets' in line:
                #print(f"before: {line}")
                line = image_assets_re.sub(r"\1../assets/\3", line)
                #print(f"after: {line}")

            output.append(line)

        # write output
        #pprint(output)
        with open(output_path / new_name, 'w') as output_file:
            output_file.write("".join(output))


def convert_embeds(line):
    """Convert embeds, ![[a.b.note-name]] -> {{embed [[a/b/note-name]]}}."""
    #print(f"convert embeds: {line!r}")
    # line is split into splits (with possible embeds to be converted)
    # by inline code separators (to be kept as they are)
    non_code_splits = inline_code_re.split(line)  # parts not in ``
    code_separators = inline_code_re.findall(line)

    #print(f"{non_code_splits=}, {code_separators=}")

    # for each non_code_split, replace '.' -> '/' in embed tokens and replace
    # dendron embed tokens with logseq embed tokens
    nc_i = 0
    while nc_i < len(non_code_splits):
        #print(f"{non_code_splits[nc_i]=}")
        # a non_code split (possibly containing an embed) is split into splits
        # without embeds using embed token regex as separators.
        # embed tokens (separators) should be modified: Replace . -> /
        non_embed_splits = embed_token_re.split(non_code_splits[nc_i])
        embed_token_separators = embed_token_re.findall(non_code_splits[nc_i])

        # replace . -> / in embed tokens
        embed_token_index = 0
        while embed_token_index < len(embed_token_separators):
            embed_token_separators[embed_token_index] = embed_token_separators[embed_token_index].replace('.', '/')
            #print(f"{embed_token_separators[embed_token_index]=}")
            embed_token_index += 1

        # recombine non_embed_splits with embed_token_separators if needed
        # and put back into the correct non_code_split
        if len(non_embed_splits) > 1:
            non_code_splits[nc_i] = recombine_splits_separators(non_embed_splits, embed_token_separators)

        # replace the all dendron embed tokens in non_code_split with logseq
        # embed tokens and remove any anchor (block reference)
        non_code_splits[nc_i] = embed_token_with_anchor_re.sub(r"{{embed [[\1]]}}", non_code_splits[nc_i])
        nc_i += 1

    return recombine_splits_separators(non_code_splits, code_separators)


def convert_internal_links(line):
    """Convert internal links, [[a.b.c.note-title]] -> [[a/b/c/note-title]]."""
    # line is split into splits (with possible embeds to be converted)
    # by inline code separators (to be kept as they are)
    non_code_splits = inline_code_re.split(line)  # parts not in ``
    code_separators = inline_code_re.findall(line)

    #print(f"convert line: {non_code_splits=}, {code_separators=}")

    # for each non_code_split, replace '.' -> '/' in link tokens and remove
    # anchors from link tokens
    nc_i = 0
    while nc_i < len(non_code_splits):
        #print(f"{non_code_splits[nc_i]=}")
        # a non_code split (possibly containing a link) is split into splits
        # without links using link token regex as separators.
        # link tokens (separators) should be modified: Replace . -> /
        non_link_splits = wiki_link_token_re.split(non_code_splits[nc_i])
        link_token_separators = wiki_link_token_re.findall(non_code_splits[nc_i])

        # replace . -> / in link tokens
        link_token_index = 0
        while link_token_index < len(link_token_separators):
            link_token_separators[link_token_index] = link_token_separators[link_token_index].replace('.', '/')
            #print(f"{link_token_separators[link_token_index]=}")
            link_token_index += 1

        # recombine non_link_splits with link_token_separators if needed
        # and put back into the correct non_code_split
        if len(non_link_splits) > 1:
            non_code_splits[nc_i] = recombine_splits_separators(non_link_splits, link_token_separators)

        # replace the all dendron link tokens in non_code_split with link tokens
        # without anchors
        #print(f"before: {non_code_splits[nc_i]=}")
        non_code_splits[nc_i] = wiki_link_token_with_internals_re.sub(r"[[\2]]", non_code_splits[nc_i])
        #print(f"after: {non_code_splits[nc_i]=}")
        nc_i += 1

    return recombine_splits_separators(non_code_splits, code_separators)


    # line is split into splits (with possible internal links to be converted)
    # by inline code separators (to be kept as they are)
    converted_ilink_splits = inline_code_re.split(line)
    code_separators = inline_code_re.findall(line)

    return recombine_splits_separators(converted_ilink_splits, code_separators)


def recombine_splits_separators(splits, separators):
    #print(f"recombine: {splits=}, {separators=}")
    # combine changed elements with unchanged elements if necessary
    if len(splits) > 1:
        recombined = []
        for index, separator in enumerate(separators):
            recombined.append(f"{splits[index]}")
            recombined.append(f"{separator}")
        recombined.append(f"{splits[index+1]}")
        return ''.join(recombined)
    else:
        return splits[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('vault_path')
    parser.add_argument('output_path')
    parser.add_argument('--remove-frontmatter',
                        help="Remove frontmatter. Frontmatter is kept as a code block by default",
                        action='store_true')
    parser.add_argument('--alias-title', help="Add existing title as an alias.",
                        action='store_true')
    parser.add_argument('--four-space-indent', help="Indent using four spaces. Default: tab",
                        action='store_true')
    parser.add_argument('-y', '--yes', help="Answer yes to all prompts.",
                        action='store_true')
    args = parser.parse_args()
    print(args)

    # Indent sequence
    if args.four_space_indent:
        INDENT = '    '

    # check vault
    vault_path = Path(args.vault_path)
    if not vault_path.is_dir():
        print(f"{vault_path} does not exist.")
        sys.exit(1)

    # check output path
    output_path = Path(args.output_path)
    if not output_path.is_dir():
        print(f"{output_path.resolve()} does not exist, creating it")
        output_path.mkdir(parents=True)
    else:
        dir_contents = [c for c in output_path.iterdir()]
        print(f"Destination {output_path.resolve()} contains {len(dir_contents)} items.")
        print("Nothing will be deleted, but files might be overwritten.")
        if not args.yes and not ask_for_confirmation("Continue?", default='n'):
            print("Aborting.")
            sys.exit(1)

    duplicates = get_duplicate_titles(vault_path)
    if duplicates:
        print("The following duplicate titles were found:")
        for title, filepaths in duplicates.items():
            print(f"  * Title: {title!r} in files {', '.join(filepaths)}")
        print()
        if not args.yes and not ask_for_confirmation("Continue?", default='y'):
            print("Aborting")
            sys.exit(1)

    vault2graph(vault_path, output_path,
                remove_frontmatter=args.remove_frontmatter,
                alias_title=args.alias_title)