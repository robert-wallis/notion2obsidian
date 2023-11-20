# Notion to Obsidian

This project will convert a notion.so export of MD files into Obsidian's format.

Specifcally:
* removing md5 hashes in filenames and links
* converting tables into Obsidian kanban basic boards

# Setting up Dev Environment

If you'd like to hack on notion2obsidian these commands will help you get started.

```
make test

pip3 install coverage
make coverage
```
