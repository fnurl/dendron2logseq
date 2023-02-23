#!/usr/bin/env python3
"""Script for converting Dendron vaults to Logseq graphs.

- Dendron: https://www.dendron.so
- Logseq: https://logseq.com

Author: Jody Foo, February 2023.
"""
import argparse
import re
import sys
from pathlib import Path
from shutil import copytree

# Default globals
INDENT = '\t'

# Compiled regular expressions
heading_re = re.compile(r"(#+) ")
tab_indents_re = re.compile(r"(\t+)")
inline_code_re = re.compile(r"`.*?`")
indent_level_re = re.compile(r"(    )+")
bullet_re = re.compile(r"^( *)([-*+])(.*)")
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
    with open(md_filepath, encoding="utf-8") as md_file:
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


def get_indent_level(line):
    m = indent_level_re.match(line)
    if m:
        return len(m[0]) // 4
    return 0


def push_to_stack_no_repeat(stack, value):
    if not stack or stack[-1] != value:
        stack.append(value)


def vault2graph(vault_path, output_path, remove_frontmatter, alias_title,
                use_title, remove_empty_lines):
    """Save assets dir and processed markdown files to output_path."""
    print(f"\nProcessing Dendron vault at {vault_path.resolve()}")
    msg = "Options: {rm_fm}, {alias}, {title}, {rm_lines}\n"
    print(msg.format(rm_fm=f"{remove_frontmatter=}", alias=f"{alias_title=}",
                     title=f"{use_title=}", rm_lines=f"{remove_empty_lines=}"))

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
                                  remove_frontmatter, alias_title, use_title,
                                  remove_empty_lines)
        else:
            print(f"WARNING: File not handled, {childpath.name!r}")

    if assets_path:
        msg = "Assets directory found, copying {src} -> {dest}"
        print(msg.format(src=assets_path.resolve(),
              dest=(output_path / 'assets').resolve()))
        copytree(assets_path, output_path / "assets", dirs_exist_ok=True)


def process_and_save_file(source_path, output_path, new_name,
                          remove_frontmatter, alias_title, use_title,
                          remove_empty_lines):
    output = []
    with open(source_path, 'r', encoding="utf-8") as source_file:
        first_line_checked = False
        in_frontmatter = False
        in_body = False
        frontmatter_handled = False
        heading_level = 0
        indent_level = 0
        content_stack = []
        previous_line = None

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
                    elif use_title:
                        output.insert(0, f"title:: {line[6:].lstrip()}")
                    elif not remove_frontmatter:
                        output.append(f"  {line}")
                # add key to code block
                elif not remove_frontmatter:
                    output.append(f"  {line}")

                # next line (no need for else below)
                continue

            # keep unprocessed line (except for \t replacement) to save as
            # previous_line
            unprocessed_line = line

            #### BETWEEN FRONTMATTER AND BODY ####

            if not in_body:
                if line.strip() == '':
                    previous_line = unprocessed_line
                    if remove_empty_lines in ['all', 'trim']:
                        continue
                    elif remove_empty_lines == 'none':
                        output.append("-\n")
                else:
                    in_body = True

            #### PROCESS DOCUMENT BODY ####
            #print(f"BODY: {line!r}")

            # content_stack is used to keep track of the current block context
            # content_stack is [] in the beginning
            #
            # possible items on the stack:
            #  - "fenced code block"
            #  - "indented code block"
            #  - "heading"
            #  - "ul" (unordered list)
            #  - "paragraph"
            #
            # changes to content_stack
            #   - an empty line clears the stack unless the top item is
            #     "heading"
            #   - headings clears the stack
            #   - indented code blocks are only valid outside if the stack is
            #     empty or if directly after "heading"
            #   - fenced code blocks are valid everywhere
            #   - list clears content stack if the current top item is not
            #     "list"
            #   - if top of stack is heading and any content is encountered,
            #     stack is cleared
            #

            # replace initial tabs with four spaces
            if line[0] == '\t':
                match = tab_indents_re.match(line)
                if match:
                    num_tabs = len(match[1])
                    line = f"{'    '*num_tabs}{line[num_tabs:]}"

            ######## CODE BLOCKS ########

            # ``` code block start/end
            # LIMITATION: Does not handle indented code blocks (in outline).
            # Will remove any indentation before '```'
            if line.lstrip().startswith("```"):
                #print(f"```: {line=}, {content_stack=}")
                #print(f"CODE: {line!r}")
                #line = line.lstrip()
                # start
                if content_stack[-1:] != ["fenced code block"]:
                    # fenced code block clears stack if added after heading
                    if content_stack[-1:] == ["heading"]:
                        indent_level = 0
                        content_stack.clear()

                    # start of code block part of list
                    if 'list' in content_stack:
                        block_indent = get_indent_level(line)
                        # start at same or greater indent level -> part of same
                        # list item
                        if block_indent >= indent_level:
                            # assume indent is correct
                            line = f"{INDENT*heading_level}{line}"
                        # outdented level -> new fenced code block in list
                        else:
                            indent_level = block_indent
                            line = f"{INDENT*heading_level}{INDENT*block_indent}- {line.lstrip()}"
                    # start of code block outside list
                    else:
                        # fenced code block is part of paragraph, align with
                        # paragraph bullet
                        if content_stack[-1:] == ['paragraph']:
                            line = f"{INDENT*heading_level}  {line}"
                        # fenced code block is not in list or part of paragraph
                        # -> new bullet
                        else:
                            # clears content_stack
                            indent_level = 0
                            content_stack.clear()
                            line = f"{INDENT*heading_level}- {line}"
                    push_to_stack_no_repeat(content_stack, "fenced code block")
                # end
                else:
                    # code block part of list, assume indent good
                    if 'list' in content_stack:
                        line = f"{INDENT*heading_level}{line}"
                    # otherwise align with paragraph bullet
                    else:
                        line = f"{INDENT*heading_level}  {line}"
                    content_stack.pop()
                output.append(line)
                previous_line = unprocessed_line
                continue

            # In fenced code block, do not change line, just indent
            # assume line is originally correctly indented
            if content_stack[-1:] == ["fenced code block"]:
                #print(f"CODE: {line!r}")
                # code block part of list, assume indent good
                if 'list' in content_stack:
                    line = f"{INDENT*heading_level}{line}"
                # otherwise align with paragraph bullet
                else:
                    line = f"{INDENT*heading_level}  {line}"
                output.append(line)
                previous_line = unprocessed_line
                continue

            # possible indented code block starts with '    '
            if line.startswith('    '):
                # start of indented code block?
                # only start if content_stack is empty or after heading and
                # not already in indented code block
                #print(f"{line=}, {content_stack=}")
                if ((not content_stack or content_stack[-1:] == ["heading"])
                        and content_stack[-1:] != ["indented code block"]):
                    #print("START OF INDENTED CODE BLOCK")
                    # indented code block clears stack if added after heading
                    if content_stack[-1:] == ["heading"]:
                        indent_level = 0
                        content_stack.clear()
                    output.append(f"{INDENT*heading_level}- ```\n")
                    push_to_stack_no_repeat(content_stack, "indented code block")

                # in indented code block
                if content_stack[-1:] == ["indented code block"]:
                    # add code line to code block
                    line = f"{INDENT*heading_level}  {line[4:]}"
                    output.append(line)
                    previous_line = unprocessed_line
                    continue
            # end of indented code block
            elif content_stack[-1:] == ["indented code block"]:
                # add ending ```
                output.append(f"{INDENT*heading_level}  ```\n")
                # no longer in indented code block
                content_stack.pop()

            ######## NON-CODE BLOCKS ########
            # Outside of code block and frontmatter

            # Handle empty lines: keep all, remove all, trim
            if line.strip() == '':
                #print(f"EMPTY LINE a: {previous_line=}, {content_stack=}")
                # empty line clears stack if top of stack is not "heading"
                if content_stack[-1:] != ["heading"]:
                    indent_level = 0
                    content_stack.clear()
                #print(f"EMPTY LINE b: {previous_line=}, {content_stack=}")

                # keep empty lines
                if remove_empty_lines == 'none':
                    line = f"{INDENT*heading_level}- {line}"
                    output.append(line)
                # remove all empty lines
                elif remove_empty_lines == 'all':
                    pass
                # trim empty lines
                elif remove_empty_lines == 'trim':
                    #print(f"TRIM: {previous_line=}, {content_stack=}")
                    # remove empty lines after headings
                    if content_stack[-1:] == ["heading"]:
                        pass
                    # keep one empty line
                    elif previous_line.strip() != '':
                        line = f"{INDENT*heading_level}- {line}"
                        output.append(line)
                previous_line = unprocessed_line
                continue

            ######## NON-EMPTY, NON-CODE BLOCK LINES ########

            # horizontal rules
            if line.strip() in ['---', '***']:
                line = f"{INDENT*heading_level}- {line.lstrip()}"
                output.append(line)
                previous_line = unprocessed_line
                continue

            # Headings - Use headings to determine outline hierarchy
            if line[0] == '#':
                #print(f"HEADING: {line!r}")
                match = heading_re.match(line)
                if match:
                    heading_level = len(match[1])

                    # heading clears content_stack
                    indent_level = 0
                    content_stack.clear()

                    # indent heading
                    line = f"{INDENT*(heading_level-1)}- {line}"
                    line = convert_internal_links(line)
                    output.append(line)
                    push_to_stack_no_repeat(content_stack, "heading")
                    previous_line = unprocessed_line
                    continue

            # Blockquotes
            if line.lstrip()[0] == '>':
                #print(f">: {line=}, {block_indent=}, {indent_level=}, {content_stack=}")
                # block quotes in lists
                if 'list' in content_stack:
                    block_indent = get_indent_level(line)
                    # same or greater indent level -> part of same list item
                    if block_indent >= indent_level:
                        # assume indent is correct
                        line = f"{INDENT*heading_level}{line}"
                    # outdented level -> new blockquote block in list
                    else:
                        indent_level = block_indent
                        line = f"{INDENT*heading_level}{INDENT*block_indent}- {line.lstrip()}"
                # outside list
                else:
                    # continuation of block quote outside list
                    if content_stack[-1:] == ['blockquote']:
                        line = f"{INDENT*heading_level}  {line}"
                    # new blockquote outside list
                    else:
                        # resets content_stack
                        indent_level = 0
                        content_stack.clear()
                        line = f"{INDENT*heading_level}- {line}"
                line = convert_internal_links(line)
                output.append(line)
                push_to_stack_no_repeat(content_stack, 'blockquote')
                previous_line = unprocessed_line
                continue

            ############ BULLET OR PARAGRAPH ############

            # bullets (unordered list)
            if line.lstrip()[:2] in ['- ', '* ', '+ ']:
                # new bullet -> new indent_level
                indent_level = get_indent_level(line)

                # normalize bullet to '- '
                line = bullet_re.sub(r"\1-\3", line)
                line = f"{INDENT*heading_level}{line}"

                # push context
                push_to_stack_no_repeat(content_stack, "list")

            # line without block prefix {-, >}
            else:
                block_indent = get_indent_level(line)

                # no linebreak, and same indent level -> line belongs to the
                # previous paragraph/bullet/blockquote
                if (previous_line and previous_line.strip() != ''
                        and block_indent >= indent_level):
                    line = f"{INDENT*heading_level}  {line}"
                # new paragraph
                else:
                    # clears content_stack
                    indent_level = 0
                    content_stack.clear()
                    line = f"{INDENT*heading_level}- {line}"
                    push_to_stack_no_repeat(content_stack, "paragraph")

            #print(f"OUTLINE: {line!r}")

            ############ CONVERT EMBEDS AND INTERNAL LINKS ############

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
            previous_line = unprocessed_line
            #print(f"{previous_line=}")

        # write output
        #pprint(output)
        with open(output_path / new_name, 'w', encoding="utf-8") as output_file:
            output_file.write("".join(output))


def convert_embeds(line):
    """Convert embeds, ![[a.b.note-name]] -> {{embed [[a/b/note-name]]}}.

    Anchors are removed, i.e. both ![[note#^ref]] and ![[note#start:#end]] are
    changed to {{embed [[note]]}}
    """
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
    title_options = parser.add_mutually_exclusive_group()
    title_options.add_argument('--alias-title',
                               help="Add existing title as an alias.",
                               action='store_true')
    title_options.add_argument('--use-title',
                               help="Use title from frontmatter as title:: property value. Requires that no duplicate titles exist.",
                               action='store_true')
    parser.add_argument('--four-space-indent',
                        help="Indent using four spaces. Default: tab",
                        action='store_true')
    parser.add_argument('--remove-empty-lines',
                        help="Remove empty lines. none: Don't remove any empty lines, all: Remove all empty lines, trim: Remove empty lines after headings and in beginning, keep maximum of one empty line in rest of document. Default: trim",
                        choices=['none', 'all', 'trim'],
                        default='trim')
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
        if args.use_title:
            print("No duplicate titles allowed with --use-titles. Please resolve and re-run command.")
            sys.exit(1)
        if not args.yes and not ask_for_confirmation("Continue?", default='y'):
            print("Aborting")
            sys.exit(1)

    vault2graph(vault_path, output_path,
                remove_frontmatter=args.remove_frontmatter,
                alias_title=args.alias_title, use_title=args.use_title,
                remove_empty_lines=args.remove_empty_lines)
