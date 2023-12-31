#!/usr/bin/env python3
"""Migrates a notion.so export to obsidian.md format.
"""
# fix links in notion.so export
#
# Copyright (C) 2023 Robert Wallis, All Rights Reserved.

from typing import TextIO
import csv
import os
import re
import sys


MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^\]]+)\)')
URL_MD5_PATTERN = re.compile(r'%20[a-fA-F0-9]{32}')
MD5_PATTERN = re.compile(r'\s*[a-fA-F0-9]{32}')


def main(argv=sys.argv):
    """CLI for notion2obsidian.py

    >>> main(['notion2obsidian.py', 'test_data/export.zip'])
    ziptest/Zip Table.md
    ziptest/Zip Example.md
    >>> delete_path('ziptest')

    >>> main(['notion2obsidian.py', 'test_data'])
    test_data/export/Table.md
    test_data/export/Example.md
    >>> delete_path('test_data/export')

    >>> main(['notion2obsidian.py'])
    """
    if len(argv) == 2:
        option = argv[1]
        if os.path.isfile(option):
            if '.zip' == option[-4:]:
                notion_zip(option)
                return
        elif os.path.isdir(option):
            walk_files(option)
            return

    print(f"Usage: {sys.argv[0]} <notion_export.zip>|<notion_export_folder>", file=sys.stderr)


def delete_path(rootpath: str):
    """Recrusively delete a folder.
    >>> import tempfile
    >>> tdir = tempfile.TemporaryDirectory()
    >>> os.mkdir(os.path.join(tdir.name, 'testdir'))
    >>> open(os.path.join(tdir.name, 'testdir/test.txt'), 'w').close()
    >>> os.path.exists(tdir.name)
    True
    >>> delete_path(tdir.name)
    >>> os.path.exists(tdir.name)
    False
    """
    if os.path.exists(rootpath):
        for (rootpath, dirs, files) in os.walk(rootpath):
            for filename in files:
                fullpath = os.path.join(rootpath, filename)
                os.remove(fullpath)
            for dirname in dirs:
                fullpath = os.path.join(rootpath, dirname)
                delete_path(fullpath)
        os.rmdir(rootpath)


def walk_files(rootpath: str):
    """Recrusively go through folder looking for files to convert, and convert them.
    >>> delete_path('test_data/export')
    >>> walk_files('test_data/export aabbccddeeff00112233445566778899')
    test_data/export/Table.md
    test_data/export/Example.md
    >>> os.listdir('test_data/export')
    ['Example.md', 'Table.md']
    >>> delete_path('test_data/export')
    """
    # delete everything in the directory rootpath
    for (rootpath, dirs, files) in os.walk(rootpath):
        for filename in files:
            fullpath = os.path.join(rootpath, filename)
            if '__MACOSX' in fullpath:
                # these files are some binary Apple provenance file with a .md extension
                continue
            elif '.md' == fullpath[-3:]:
                outfile = remove_md5_from_filename(fullpath)
                clean_and_make_dir_for_filename(outfile)
                print(outfile)
                process_markdown(open(fullpath, mode='r'), open(outfile, mode='w'))
            elif '.csv' == fullpath[-4:]:
                outfile = remove_md5_from_filename(fullpath)
                outfile = outfile.replace('.csv', '.md')
                clean_and_make_dir_for_filename(outfile)
                print(outfile)
                # skip the BOM by opening as a utf-8-sig
                process_csv(open(fullpath, mode='r', encoding='utf-8-sig'), open(outfile, mode='w'))
        for dirname in dirs:
            walk_files(dirname)


def notion_zip(zip_filename: str):
    """Unzips a notion.so export, and converts the files.
    >>> old_dir = os.path.abspath('.')
    >>> delete_path('test_data/ziptest')
    >>> os.mkdir('test_data/ziptest')
    >>> os.chdir('test_data/ziptest')
    >>> notion_zip('../export.zip')
    ziptest/Zip Table.md
    ziptest/Zip Example.md
    >>> os.listdir('ziptest')
    ['Zip Table.md', 'Zip Example.md']
    >>> os.chdir(old_dir)
    >>> delete_path('test_data/ziptest')
    """
    import zipfile
    rootpath = os.path.dirname(".")
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        for filename in zip_ref.namelist():
            outfile = os.path.join(rootpath, filename)
            if '__MACOSX' in outfile:
                # these files are some binary Apple provenance file with a .md extension
                continue
            elif '.md' == outfile[-3:]:
                outfile = remove_md5_from_filename(outfile)
                clean_and_make_dir_for_filename(outfile)
                in_file = zip_ref.open(filename)
                import io
                in_file = io.TextIOWrapper(io.BytesIO(zip_ref.read(filename)), encoding='utf-8-sig')
                print(outfile)
                process_markdown(in_file, open(outfile, mode='w'))
            elif '.csv' == outfile[-4:]:
                outfile = remove_md5_from_filename(outfile)
                outfile = outfile.replace('.csv', '.md')
                clean_and_make_dir_for_filename(outfile)
                import io
                in_file = io.TextIOWrapper(io.BytesIO(zip_ref.read(filename)), encoding='utf-8-sig')
                print(outfile)
                process_csv(in_file, open(outfile, mode='w'))


def clean_and_make_dir_for_filename(filename: str):
    """Makes a folder if it doesn't exist.
    >>> old_path = os.path.abspath('.')
    >>> import tempfile
    >>> tdir = tempfile.TemporaryDirectory()
    >>> os.chdir(tdir.name)
    >>> clean_and_make_dir_for_filename('test.md')
    >>> empty_dir = os.listdir('.')
    >>> clean_and_make_dir_for_filename('folder/test.md')
    >>> one_folder = os.listdir('.')
    >>> os.chdir(old_path) # cleanup before testing result
    >>> empty_dir
    []
    >>> one_folder
    ['folder']
    """
    dirname = os.path.dirname(filename)
    if len(dirname) == 0 or dirname == '.' or dirname == '/':
        return
    cleaned = remove_md5_from_filename(dirname)
    if not os.path.exists(cleaned):
        os.makedirs(cleaned, exist_ok=True)


def process_markdown(in_file: TextIO, out_file: TextIO):
    """When a markdown file is found, fix the links and file name
    >>> import io
    >>> in_file = io.StringIO('# Test\\n[link](https://example.com/123%20aAbBcCdDeEfF00112233445566778899.md)')
    >>> out_file = io.StringIO()
    >>> process_markdown(in_file, out_file)
    >>> print(out_file.getvalue()) # doctest: +NORMALIZE_WHITESPACE
    # Test
    [link](https://example.com/123.md)
    """
    for line in in_file:
        matches = MARKDOWN_LINK_PATTERN.findall(line)
        for _title, url in matches:
            url2 = remove_md5_from_url(url)
            if len(url2) and url != url2:
                line = line.replace(url, url2)
        out_file.write(line)


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


def process_csv(csv_file: TextIO, kanban_file: TextIO):
    """Migrates a notion.so table to an obsidian kanban file.
    >>> import io
    >>> csv_file = io.StringIO('\ufeffName,Status,Tags\\nWork on CSV Exporter,Doing,notion\\nWrite doctests,Doing,\\n')
    >>> kanban_file = io.StringIO()
    >>> process_csv(csv_file, kanban_file)
    >>> print(kanban_file.getvalue()) # doctest: +NORMALIZE_WHITESPACE
    ---
    kanban-plugin: basic
    ---
    ## Doing
    - [ ] Work on CSV Exporter #notion
    - [ ] Write doctests


    Empty CSV File
    >>> csv_file = io.StringIO('\ufeffName,Status,Tags\\n')
    >>> kanban_file = io.StringIO()
    >>> process_csv(csv_file, kanban_file)

    """
    # open the csv
    records = records_from_csv(csv_file)
    if len(records) == 0:
        return
    first_record = records[0]
    statuses = statuses_from_csv(records)
    status_records = records_grouped_by_status(records)
    keys = list(first_record.keys())
    title_key = keys[0] if keys else 'Name'
    unknown_params = unknown_record_params(first_record, [title_key, 'Status', 'Tags'])

    # write the kanban file
    kanban_write_header(kanban_file)

    for status in statuses:
        kanban_write_column(kanban_file, status)

        for record in status_records[status]:
            tags = [record['Tags']] if 'Tags' in record and record['Tags'] else []
            params = {p:record[p] for p in unknown_params if p in record}
            kanban_write_card(kanban_file, status, record[title_key], tags, params)
        kanban_file.write('\n\n')


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
    >>> kanban_write_card(kanban_file, 'Done', 'Write doctests', ['notion', ''], {})
    >>> kanban_write_card(kanban_file, 'Done', 'Test params', ['notion', ''], {'unknown': 'param', 'other': '', '': 'Empty Param'})
    >>> print(kanban_file.getvalue())
    - [ ] Work on CSV Exporter
    - [x] Write doctests #notion
    - [x] Test params unknown:param Empty Param #notion
    <BLANKLINE>
    """
    line = '- '
    if status == 'Done':
        line += f'[x] {title}'
    else:
        line += f'[ ] {title}'

    for key, value in unknown_params.items():
        if len(key) and len(value):
            line += f' {key}:{value}'
        elif len(value):
            line += f' {value}'

    if len(tags):
        for tag in tags:
            if len(tag):
                line += f' #{tag}'
    kanban_file.write(line)
    kanban_file.write('\n')

def records_from_csv(csv_file: TextIO):
    """Reads a csv file, and returns an array of dicts.
    >>> import io
    >>> csv_file = io.StringIO('Name,Status,Tags\\nWork on CSV Exporter,Doing,notion\\n')
    >>> records_from_csv(csv_file)
    [{'Name': 'Work on CSV Exporter', 'Status': 'Doing', 'Tags': 'notion'}]
    """
    records = []
    for row in csv.DictReader(csv_file):
        records.append(row)
    return records


def statuses_from_csv(csv_data: list[dict], default_status=''):
    """Returns a list of unique statuses from a csv file.
    csv_data is a list of dicts, each dict is a row in the csv file.
    >>> statuses_from_csv([{'Status': ''}, {'Status': 'Doing'}, {'Status': 'Done'}])
    ['', 'Doing', 'Done']

    >>> statuses_from_csv([{}, {}, {}])
    ['']
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

    >>> unknown_record_params({'Name': 'Work on CSV Exporter', 'Priority': '2'}, ['Name', 'Status', 'Tags'])
    ['Priority']
    """
    result = []
    for key in record.keys():
        if key not in known_params:
            result.append(key)
    return result


if __name__ == '__main__':
    main()

