import io

def test_simple_card_kanban():
    from notion2obsidian import process_csv
    # GIVEN a csv file with just a Title column
    csv_file = io.StringIO("Title\nCard 1\nCard 2\nCard 3\n")

    # WHEN we convert it to Obsidian kanbans
    obsidian_file = io.StringIO()
    process_csv(csv_file, obsidian_file)

    # THEN we should get a file with just the titles
    assert obsidian_file.getvalue() == """---

kanban-plugin: basic

---

## 

- [ ] Card 1
- [ ] Card 2
- [ ] Card 3


"""
