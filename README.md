# README

Limited export of the contents of a [Dendron](https://www.dendron.so) vault to a [Logseq](https://logseq.com) graph.


## What does the script do?

The script copies `.md` files and the `assets` directory from a Dendron vault directory to an output directory. It makes the `.md` files Logseq ready by doing the following:

- renames files from Dendrons `category.subcategory.note-title.md` to Logseqs `category___subcategory___note-title.md`
- changes wikilinks from Dendron's `[[catetegory.subcategory.note-title]]` to Logseq's `[[category/subcategory/note-title]]`, it also **removes** aliases and anchors from the wikilinks:
    - `[[alias|note-title]]` -> `[[note-title]]`
    - `[[note-title#heading]]` -> `[[note-title]]`
- Dendron embeds are changed to Logseq embeds, note that **anchors are removed**:
    - `![[a.b.embedded-note]]` -> `{{embed [[a/b/embedded-note]]}}
    - `![[a.b.embedded-note]]` -> `{{embed [[a/b/embedded-note]]}}
    - `![[a.b.embedded-note#^blockref]]` -> `{{embed [[a/b/embedded-note]]}}
    - `![[a.b.embedded-note#start:#end]]` -> `{{embed [[a/b/embedded-note]]}}
- inline images using `![.*](/assets/.*)` are changed to `![.*](../assets/.*)`; you need to put the `assets` folder in the same directory as the `pages/` directory
- Logseq reads `yaml` frontmatter and picks up the title, but titles must be unique, so my frontmatter solution is the following:
    - use the `title:` value as an alias (first node - `alias:: title`)
    - make the rest of the frontmatter a code block
    - title is only included in the frontmatter code block if aliases are not created
- title -> alias can be turned off and it is possible to just remove the frontmatter
- headings are used to infer outline level, the `#` characters are left and the heading and its children are indented according to the number of `#` used by the heading.

Although I have done some basic verification of the functionality, but there might be bugs etc. You need to verify that the results the script produces are what you want. **I take NO responsibility for any loss of data.**

I don't think I am missing anything in my export, but I might discover something at a future date, so I will not be deleting my Dendron vault any time soon. If for no other reason than to use it as the source for some other export to some other system.


## Usage

```
usage: dendron2logseq.py [-h] [--remove-frontmatter] [--alias-title]           
                         [--four-space-indent] [-y] vault_path output_path

positional arguments:
  vault_path
  output_path

options:
  -h, --help            show this help message and exit
  --remove-frontmatter  Remove frontmatter. Frontmatter is kept as a code block 
                        by default
  --alias-title         Add existing title as an alias.
  --four-space-indent   Indent using four spaces. Default: tab
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
- parsing is done line by line, so if you use hard linebreaks in a paragraph, you will get one bullet point for each line
- line base parsing also mean that e.g. wiki links that span over two or more lines will not be changed in any way
- if you have indented code blocks the indentation level will be "reset" (the whole block, not the individual lines")
- any special characters are left untouched in the file name (Logseq urlencodes special characters)


## Backstory

I created this script as Dendron is sadly no longer actively developed. I looked at three possible alternatives to Dendron; [Logseq](https://logseq.com), [Obsidian](https://obsidian.md/) and [Zettlr](https://www.zettlr.com/).

Zettlr looks like a good markdown editor with Pandoc and Zotero integration for academic research and publication, but that is not my main use-case. Obsidian is of course the big player here, and I don't really have any good reason for not choosing it (except perhaps that it is closed source).

Logseq got me interested because I have never really tried to use an outliner style PKM and I liked the keyboard navigation and the way Logseq does tasks.

