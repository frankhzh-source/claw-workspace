import re

with open('_doc_full_content.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# V4 strategy: Remove ALL <col> width attributes and let Feishu auto-size.
# 
# Root cause of remaining wrapping: Feishu overrides <col width> values.
# T12 had [50,330,240] sent but Feishu stored [50,480,110] - overriding the "说明" col to 110px
# This causes "创建图像节点" (84px) to wrap at 68px usable.
#
# Solution: Remove col widths entirely. Feishu's auto-layout is smart enough
# to balance columns properly, and won't compress short-text columns.
# 
# Additional improvement: For header cells (th), set background-color to 
# differentiate from data cells for better readability.

table_pattern = re.compile(r'(<table.*?</table>)', re.DOTALL)

def beautify_table(table_html, config_idx):
    # Remove all col width attributes - let Feishu auto-size
    # Replace <col width="xxx"/> with plain <col/>
    table_html = re.sub(r'<col[^>]*/>', '<col/>', table_html)
    
    # Add light gray background to header row for visual hierarchy
    # <th background-color="light-gray">
    table_html = table_html.replace('<th ', '<th background-color="light-gray" ')
    
    return table_html

tables = table_pattern.findall(content)
result = content

for i, old_table in enumerate(tables):
    new_table = beautify_table(old_table, i)
    result = result.replace(old_table, new_table, 1)
    print(f'Table {i}: processed')

with open('_doc_v4.txt', 'w', encoding='utf-8') as f:
    f.write(result)

print(f'\nDone: {len(content)} -> {len(result)} chars')
