#!/usr/bin/env python3
"""Migrates a notion.so export to obsidian.md format.
"""
# fix links in notion.so export
#
# Copyright (C) 2023 Robert Wallis, All Rights Reserved.

import csv
import os
import re


MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^\]]+)\)')
URL_MD5_PATTERN = re.compile(r'%20[a-fA-F0-9]{32}')
MD5_PATTERN = re.compile(r'\s*[a-fA-F0-9]{32}')


def main():
    walk_files('.')


def walk_files(rootpath: str):
    """Recrusively go through folder looking for files to convert, and convert them.
    """
    for (rootpath, dirs, files) in os.walk(rootpath):
        for filename in files:
            if '.md' == filename[-3:]:
                process_markdown(rootpath, filename)
            if '.csv' == filename[-4:]:
                process_csv(rootpath, filename)
        for dirname in dirs:
            walk_files(dirname)


def process_markdown(rootpath: str, filename: str):
    """When a markdown file is found, fix the links and file name
    """
    filename = os.path.join(rootpath, filename)
    cleaned = remove_md5_from_filename(filename)
    filename_out = f"{cleaned}.out"
    if filename == cleaned:
        print(filename)
    else:
        cleaned_path = remove_md5_from_filename(rootpath)
        if cleaned_path != rootpath:
            print(f"mkdir {cleaned_path}")
            os.makedirs(cleaned_path, exist_ok=True)

    with open(filename) as file, open(filename_out, mode='w') as file_out:
        for line in file:
            matches = MARKDOWN_LINK_PATTERN.findall(line)
            for title, url in matches:
                url2 = remove_md5_from_url(url)
                if len(url2) and url != url2:
                    print(f" title: {title}")
                    print(f"    url1: {url}")
                    print(f"    url2: {url2}")
                    line = line.replace(url, url2)
            file_out.write(line)

    os.rename(filename_out, cleaned)


def remove_md5_from_url(url: str):
    """Removes the md5 hash from a url.
    >>> remove_md5_from_url('https://example.com/123%20aAbBcCdDeEfF00112233445566778899.md')
    'https://example.com/123.md'
    """
    matches = URL_MD5_PATTERN.findall(url)
    for match in matches:
        url = url.replace(match, '')
    return url


def remove_md5_from_filename(filename: str):
    """Removes the md5 hash from a filename.
    >>> remove_md5_from_filename('123 aAbBcCdDeEfF00112233445566778899.md')
    '123.md'
    """
    for match in MD5_PATTERN.findall(filename):
        filename = filename.replace(match, '')
    return filename


def process_csv(rootpath: str, filename: str):
    """When a csv file is found, convert it to a kanban.
    >>> import tempfile
    >>> tdir = tempfile.TemporaryDirectory()
    >>> csv_filename = 'test aAbBcCdDeEfF00112233445566778899.csv'
    >>> with open(os.path.join(tdir.name, csv_filename), mode='w') as temp_file:
    ...     temp_file.write('\ufeffName,Status,Tags\\nWork on CSV Exporter,Doing,notion\\n')
    52
    >>> process_csv(tdir.name, csv_filename)
    >>> print(os.listdir(tdir.name))
    ['test aAbBcCdDeEfF00112233445566778899.csv', 'test.md']
    """
    csv_filename = os.path.join(rootpath, filename)
    kanban_filename = remove_md5_from_filename(csv_filename)
    if kanban_filename != csv_filename:
        cleaned_path = remove_md5_from_filename(rootpath)
        if cleaned_path != rootpath:
            print(f"mkdir {cleaned_path}")
            os.makedirs(cleaned_path, exist_ok=True)
    kanban_filename = kanban_filename.replace('.csv', '.md')
    migrate_notion_table_to_obsidian_kanban(csv_filename, kanban_filename)


def migrate_notion_table_to_obsidian_kanban(csv_filename: str, kanban_filename: str):
    """Migrates a notion.so table to an obsidian kanban file.
    >>> import tempfile
    >>> csv_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    >>> csv_file.write('\ufeffName,Status,Tags\\nWork on CSV Exporter,Doing,notion\\n')
    52
    >>> csv_file.close()
    >>> kanban_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    >>> migrate_notion_table_to_obsidian_kanban(csv_file.name, kanban_file.name)
    >>> print(open(kanban_file.name, mode='r').read()) # doctest: +NORMALIZE_WHITESPACE
    ---
    kanban-plugin: basic
    ---
    ## Doing
    - [ ] Work on CSV Exporter #notion
    >>> os.remove(csv_file.name)
    """
    # open the csv
    records = records_from_csv(csv_filename)
    if len(records) == 0:
        return
    first_record = records[0]
    statuses = statuses_from_csv(records)
    status_records = records_grouped_by_status(records)
    keys = list(first_record.keys())
    title_key = keys[0] if keys else 'Name'
    unknown_params = unknown_record_params(first_record, [title_key, 'Status', 'Tags'])

    # write the kanban file
    with open(kanban_filename, mode='w') as kanban:
        kanban_write_header(kanban)

        for status in statuses:
            kanban_write_column(kanban, status)
            if status in status_records:
                for record in status_records[status]:
                    tags = [record['Tags']] if 'Tags' in record else []
                    params = {p:record[p] for p in unknown_params if p in record}
                    kanban_write_card(kanban, status, record[title_key], tags, params)
            kanban.write('\n\n')


def kanban_write_header(kanban_file):
    """Write a header in the style of the basic kanban plugin for Obsidian.md
    >>> import io
    >>> kanban_file = io.StringIO()
    >>> kanban_write_header(kanban_file)
    >>> print(kanban_file.getvalue())
    ---
    <BLANKLINE>
    kanban-plugin: basic
    <BLANKLINE>
    ---
    <BLANKLINE>
    <BLANKLINE>
    """
    # this is the markdown header for the kanban
    kanban_file.write('---\n')
    kanban_file.write('\n')
    kanban_file.write('kanban-plugin: basic\n')
    kanban_file.write('\n')
    kanban_file.write('---\n')
    kanban_file.write('\n')


def kanban_write_column(kanban_file, column_name):
    """Write a kanban column.
    >>> import io
    >>> kanban_file = io.StringIO()
    >>> kanban_write_column(kanban_file, 'Done')
    >>> print(kanban_file.getvalue())
    ## Done
    <BLANKLINE>
    <BLANKLINE>
    """
    kanban_file.write(f'## {column_name}\n\n')


def kanban_write_card(kanban_file, status:str, title:str, tags:list[str], unknown_params:dict[str, str]):
    """Write a kanban card.
    >>> import io
    >>> kanban_file = io.StringIO()
    >>> kanban_write_card(kanban_file, 'Doing', 'Work on CSV Exporter', [], {})
    >>> kanban_write_card(kanban_file, 'Done', 'Write doctests', ['notion'], {'unknown': 'param'})
    >>> print(kanban_file.getvalue())
    - [ ] Work on CSV Exporter
    - [x] Write doctests unknown:param #notion
    <BLANKLINE>
    """
    line = '- '
    if status == 'Done':
        line += f'[x] {title}'
    else:
        line += f'[ ] {title}'

    for key, value in unknown_params.items():
        line += f' {key}:{value}'

    if len(tags):
        for tag in tags:
            line += f' #{tag}'
    kanban_file.write(line)
    kanban_file.write('\n')

def records_from_csv(filename: str):
    """Reads a csv file, and returns an array of dicts.
    >>> import tempfile
    >>> file_data = '\ufeffName,Status,Tags\\nWork on CSV Exporter,Doing,notion\\n'
    >>> temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    >>> temp_file.write(file_data)
    52
    >>> temp_file.close()
    >>> records_from_csv(temp_file.name)
    [{'Name': 'Work on CSV Exporter', 'Status': 'Doing', 'Tags': 'notion'}]
    """
    records = []
    # encoding='utf-8-sig' avoids the bom unicode header
    with open(filename, encoding='utf-8-sig') as csvfile:
        for row in csv.DictReader(csvfile):
            records.append(row)
    return records


def statuses_from_csv(csv_data: list[dict], default_status='TODO'):
    """Returns a list of unique statuses from a csv file.
    csv_data is a list of dicts, each dict is a row in the csv file.
    >>> statuses_from_csv([{'Status': ''}, {'Status': 'Doing'}, {'Status': 'Done'}])
    ['', 'Doing', 'Done']
    """
    statuses = []
    for row in csv_data:
        if 'Status' in row and row['Status'] not in statuses:
            statuses.append(row['Status'])
    if len(statuses) == 0:
        statuses.append(default_status)
    return statuses


def records_grouped_by_status(csv_data: list[dict], default_status=''):
    """Returns a dict of lists of records grouped by status.
    csv_data is a list of dicts, each dict is a row in the csv file.
    >>> records_grouped_by_status([{'Status': ''}, {'Status': 'Doing'}, {'Status': 'Done'}])
    {'': [{'Status': ''}], 'Doing': [{'Status': 'Doing'}], 'Done': [{'Status': 'Done'}]}
    """
    result = {}
    for row in csv_data:
        status = row['Status'] if 'Status' in row else default_status
        result.setdefault(status, []).append(row)
    return result


def unknown_record_params(record: dict, known_params: list[str]):
    """Returns a list of unknown parameters from a record.
    record is a dict, each key is a column in the csv file.
    >>> unknown_record_params({'Name': 'Work on CSV Exporter', 'Status': 'Doing', 'Tags': 'notion'}, ['Name', 'Status', 'Tags'])
    []
    """
    result = []
    for key in record.keys():
        if key not in known_params:
            result.append(key)
    return result


if __name__ == '__main__':
    main()

