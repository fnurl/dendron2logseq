# README

Limited export of the contents of a [Dendron](https://www.dendron.so) vault to a [Logseq](https://logseq.com) graph.


## What does the script do?

The script copies `.md` files and the `assets` directory from a Dendron vault directory to an output directory. It makes the `.md` files Logseq ready by doing the following:

- **renames files** from Dendrons `category.subcategory.note-title.md` to Logseqs `category___subcategory___note-title.md`
- **changes wikilinks** from Dendron's `[[catetegory.subcategory.note-title]]` to Logseq's `[[category/subcategory/note-title]]`, it also **removes** aliases and anchors from the wikilinks:
    - `[[alias|note-title]]` -> `[[note-title]]`
    - `[[note-title#heading]]` -> `[[note-title]]`
- **changes embeds** from Dendron's syntax to Logseq' syntax, note that **anchors are removed**:
    - `![[a.b.embedded-note]]` -> `{{embed [[a/b/embedded-note]]}}
    - `![[a.b.embedded-note]]` -> `{{embed [[a/b/embedded-note]]}}
    - `![[a.b.embedded-note#^blockref]]` -> `{{embed [[a/b/embedded-note]]}}
    - `![[a.b.embedded-note#start:#end]]` -> `{{embed [[a/b/embedded-note]]}}
- **changes inline images** from `![.*](/assets/.*)` to `![.*](../assets/.*)`; you need to put the `assets` folder in the same directory as the `pages/` directory
- **yaml frontmatter -> code block**: the yaml frontmatter is converted to a code block at the top of the page
    - Logseq reads `yaml` frontmatter and picks up the title, but titles must be unique, I had a lot of pages with the same name but in different hierarchies, so this was my solution
        - frontmatter can be excluded entirely using `--remove-frontmatter`
        - `title:` value can be used as an alias (first node - `alias:: title`) using `--alias-title`
        - title is only included in the frontmatter code block if aliases are not created
- **infer outline level using headings**: headings are used to infer outline level, the `#` characters are left and the heading and its children are indented according to the number of `#` used by the heading.
- **convert paragraphs to bullets**: every paragraph separated by one or more blank lines is made into a bullet; i.e. no "free" paragraphs exist in the output
- ~~**convert lines to bullets**: every line is made into a bullet; i.e. no "free" paragraphs exist in the output~~


### Added 2023-02-21

- **multiline** paragraphs and blockquotes are kept in the same outline bullet
- **use `title:` as `title::` property**; will abort if duplicate titles are found
- **converts indented code blocks** (using tab or four spaces as prefix) to fenced code blocks
- **added option for how to handle empty lines**, `--remove-empty-lines {none, all, trim}`, default: `trim`:
    - `none`: don't remove empty lines
    - `all`: remove all empty lines
    - `trim`: remove empty lines in the beginning of the body and after headings, keep a maximum of one empty line in the rest of the body
- **handles fenced code blocks in lists**
- **handles blockquotes in lists**


## Data loss

Although I have done some basic verification of the functionality, but there might be bugs etc. You need to verify that the results the script produces are what you want. **I take NO responsibility for any loss of data.**

I don't think I am missing anything in my export, but I might discover something at a future date, so I will not be deleting my Dendron vault any time soon. If for no other reason than to use it as the source for some other export to some other system.


## Usage

```
usage: dendron2logseq.py [-h] [--remove-frontmatter]
                         [--alias-title | --use-title] [--four-space-indent] 
                         [--remove-empty-lines {none,all,trim}] [-y]
                         vault_path output_path

positional arguments:
  vault_path
  output_path

options:
  -h, --help            show this help message and exit
  --remove-frontmatter  Remove frontmatter. Frontmatter is kept as a code block 
                        by default
  --alias-title         Add existing title as an alias.
  --use-title           Use title from frontmatter as title:: property value. 
                        Requires that no duplicate titles exist.
  --four-space-indent   Indent using four spaces. Default: tab
  --remove-empty-lines {none,all,trim}
                        Remove empty lines. none: Don't remove any empty lines, 
                        all: Remove all empty lines, trim: Remove empty lines 
                        after headings and
                        in beginning, keep maximum of one empty line in rest of 
                        document. Default: trim
  -y, --yes             Answer yes to all prompts.
```

I recommend that you output to a temporary directory and copy the contents to your Logsec `pages/` directory. E.g. if you want to convert the vault `~/Dendron/work/vault1` and output to `~/output` you would run

```
$ ./dendron2logseq.py ~/Dendron/work/vault1 ~/output
```

The script will create `~/output` if necessary. If there are files there they may be overwritten, but nothing is explicitly deleted. You will get a warning if there are files in `~/output`.

The `--four-space-indent` is used to use four spaces to indent each level instead of `\t` which is the default for Logseq. You can change the global config for this in your `~/.logseq/config.edn`:

```edn
{
  :export/bullet-indentation :four-spaces
}
```


## Limitations of the script

My use of Dendron has been quite limited feature-wise, which I am sort of happy for now, as this made creating a script for my needs easier. If you have a different or more advanced setup you might find this script lacking. Here are the limitations I can think of:

- incorrect/unexpected markdown syntax may procduce unexpected results
- line based parsing of links and embeds: links/embeds that span over two or more lines will not be changed in any way
- any special characters are left untouched in the file name (Logseq urlencodes special characters)
- does not parse headings created with `---` or `===` following a line of text
- does not handle ordered lists


### Fixed

- ~~if you have fenced code blocks in a nested list item the indentation level will be "reset" (the whole block, not the lines within the code block)~~ *Fixed: 2023-02-22*
- ~~parsing is done line by line, so if you use hard linebreaks in a paragraph, you will get one bullet point for each line~~ *Fixed 2023-02-22*


## Backstory

I created this script as Dendron is sadly no longer actively developed. I looked at three possible alternatives to Dendron; [Logseq](https://logseq.com), [Obsidian](https://obsidian.md/) and [Zettlr](https://www.zettlr.com/).

Zettlr looks like a good markdown editor with Pandoc and Zotero integration for academic research and publication, but that is not my main use-case. Obsidian is of course the big player here, and I don't really have any good reason for not choosing it (except perhaps that it is closed source).

Logseq got me interested because I have never really tried to use an outliner style PKM and I liked the keyboard navigation and the way Logseq does tasks.

