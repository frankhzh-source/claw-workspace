"""
生成异常报告 CSV
从 02_metadata_with_anomaly.csv 中提取所有带异常标记的行
输出到 03_anomaly_report.csv
"""
import csv
import os

meta_csv = r'E:\AI电商工作创建\LORA训练数据集\02_metadata_with_anomaly.csv'
out_csv = r'E:\AI电商工作创建\LORA训练数据集\03_anomaly_report.csv'
src_prefix = r'E:\工作进度\产品图片\原始工作图片库'

with open(meta_csv, 'r', encoding='utf-8-sig') as fin, \
     open(out_csv, 'w', newline='', encoding='utf-8-sig') as fout:
    reader = csv.DictReader(fin)
    fieldnames = ['file_path', 'file_name', 'ext', 'size_bytes',
                  'width', 'height', 'color_mode', 'anomaly', 'source_dir']
    writer = csv.DictWriter(fout, fieldnames=fieldnames)
    writer.writeheader()

    count = 0
    for row in reader:
        a = row.get('anomaly', '').strip()
        if not a:
            continue
        fp = row['file_path']
        # 提取源目录（根目录下一级）
        rel = fp.replace(src_prefix, '').lstrip('\\').lstrip('/')
        parts = rel.split(os.sep)
        source_dir = parts[0] if parts else ''

        writer.writerow({
            'file_path': fp,
            'file_name': row['file_name'],
            'ext': row['ext'],
            'size_bytes': row['size_bytes'],
            'width': row.get('width', ''),
            'height': row.get('height', ''),
            'color_mode': row.get('color_mode', ''),
            'anomaly': a,
            'source_dir': source_dir,
        })
        count += 1

print(f'✅ 异常报告已生成: {count} 条记录 → {out_csv}')
