#!/usr/bin/env python3
"""Generate KIWI diary cover image from SVG template."""

from xml.etree import ElementTree as ET
import re
import io
import os

# Read the SVG template
svg_path = r"C:\Users\jt\WorkBuddy\Claw\KIWI日记封面模板_v2.svg"
with open(svg_path, "r", encoding="utf-8") as f:
    svg_content = f.read()

# Customize for Day 172
day_number = "172"
title = "FORCE大会没说的"
subtitle = "那个问题：谁算得清ROI？"
subtitle_line2 = "当AI写出90%的代码，生产率只高了60%"
author = "海风 · 2026"

# Replace placeholder values
svg_content = re.sub(r'>Day<', '>Day<', svg_content)  # Keep
svg_content = re.sub(r'>XXX<', f'>{day_number}<', svg_content)
svg_content = re.sub(r'>这里是文章核心标题<', f'>{title}<', svg_content)
svg_content = re.sub(r'>副标题或补充说明<', f'>{subtitle}<', svg_content)
svg_content = re.sub(r'>可延伸第二行<', f'>{subtitle_line2}<', svg_content)

# Save the customized SVG
output_svg = r"C:\Users\jt\WorkBuddy\Claw\_cover_day172.svg"
with open(output_svg, "w", encoding="utf-8") as f:
    f.write(svg_content)

print(f"SVG cover saved: {output_svg}")
print("Done! Now convert to PNG for WeChat upload.")
