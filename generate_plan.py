import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\jt\WorkBuddy\Claw\full_records.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

def generate_plan(record):
    name = record['产品名称']
    detail = record['产品详情']
    theme = record['产品主题画面内容']
    detail_scene = record['产品细节画面']
    category = record['商品名称']

    # 提取主题画面中的场景数量
    scenes = []
    if '主图' in theme or '场景' in theme or '画面' in theme:
        # 按数字或项目符号分割
        import re
        scene_splits = re.split(r'(?:\n\s*\d+[\.、]\s*|\n\s*[-•*]\s*|\n\s*【[^】]+】|\n\s*画面\s*\d+)', theme)
        scenes = [s.strip() for s in scene_splits if len(s.strip()) > 20]

    # 拍摄计划
    plan_parts = []
    plan_parts.append(f"【{name}】拍摄计划")
    plan_parts.append("")
    plan_parts.append("一、前期准备")
    plan_parts.append(f"1. 产品类别：{category}")
    plan_parts.append("2. 核心卖点梳理：" + detail.replace('\n', ' ')[:100] + "...")
    plan_parts.append("3. 道具清单：按主题画面需求准备背景板、灯光、辅助道具")
    plan_parts.append("4. 设备：相机/手机+三脚架+补光灯+反光板")
    plan_parts.append("")
    plan_parts.append("二、拍摄执行")
    if len(scenes) >= 2:
        for i, scene in enumerate(scenes[:5], 1):
            first_line = scene.split('\n')[0][:50]
            plan_parts.append(f"场景{i}：{first_line}...")
    else:
        plan_parts.append("场景1：主视觉拍摄（首图）")
        plan_parts.append("场景2：产品卖点特写")
        plan_parts.append("场景3：使用场景还原")
        plan_parts.append("场景4：细节工艺展示")
        plan_parts.append("场景5：包装/售后展示")
    plan_parts.append("")
    plan_parts.append("三、后期要求")
    plan_parts.append("1. 调色：保持品牌色调一致性")
    plan_parts.append("2. 修图：去除瑕疵，突出质感")
    plan_parts.append("3. 文案嵌入：按主题画面文案排版")
    plan_parts.append("4. 格式输出：主图800x800px，详情页宽750px")

    # 思考过程
    think_parts = []
    think_parts.append(f"【{name}】创作思考")
    think_parts.append("")
    think_parts.append("一、目标人群分析")
    if '办公' in detail or '通勤' in detail:
        think_parts.append("- 核心人群：25-35岁都市白领/上班族")
    elif '学生' in detail or '学习' in detail:
        think_parts.append("- 核心人群：18-25岁学生群体")
    elif '母婴' in detail or '宝宝' in detail or '儿童' in detail:
        think_parts.append("- 核心人群：25-40岁年轻父母")
    elif '户外' in detail or '运动' in detail or '健身' in detail:
        think_parts.append("- 核心人群：20-35岁运动爱好者")
    elif '礼品' in detail or '送礼' in detail:
        think_parts.append("- 核心人群：25-45岁有送礼需求的消费者")
    else:
        think_parts.append("- 核心人群：18-40岁大众消费者")

    think_parts.append("")
    think_parts.append("二、视觉策略")
    if '国潮' in name or '中式' in detail or '古典' in detail:
        think_parts.append("- 风格定位：国潮/新中式美学")
        think_parts.append("- 色彩方案：故宫红、墨黑、鎏金等传统配色")
    elif '极简' in detail or '简约' in detail or '北欧' in detail:
        think_parts.append("- 风格定位：极简/北欧现代风")
        think_parts.append("- 色彩方案：低饱和莫兰迪色系+大面积留白")
    elif '轻奢' in detail or '高端' in detail or '品质' in detail:
        think_parts.append("- 风格定位：轻奢/高端质感")
        think_parts.append("- 色彩方案：黑金/白金高级配色")
    elif '可爱' in name or '萌' in name or '治愈' in detail:
        think_parts.append("- 风格定位：萌趣/治愈系")
        think_parts.append("- 色彩方案：马卡龙色系+柔和光影")
    else:
        think_parts.append("- 风格定位：根据产品调性匹配对应视觉风格")
        think_parts.append("- 色彩方案：以产品主色调为基础延展")

    think_parts.append("")
    think_parts.append("三、转化逻辑")
    think_parts.append("1. 首图：3秒抓住注意力，突出最大差异化卖点")
    think_parts.append("2. 卖点图：痛点→解决方案→效果验证")
    think_parts.append("3. 场景图：代入使用场景，降低决策门槛")
    think_parts.append("4. 信任图：证书/背书/评价，消除购买顾虑")
    think_parts.append("5. 促销图：价格锚点+紧迫感，促成下单")

    # 输出结果
    output_parts = []
    output_parts.append(f"【{name}】交付物清单")
    output_parts.append("")
    output_parts.append("一、主图（5张）")
    output_parts.append("1. 首图：核心卖点可视化主视觉")
    output_parts.append("2. 卖点图：关键功能/材质特写")
    output_parts.append("3. 场景图：使用场景还原")
    output_parts.append("4. 对比图：与竞品/使用前后对比")
    output_parts.append("5. 促销图：价格+活动信息")
    output_parts.append("")
    output_parts.append("二、详情页长图（1套）")
    output_parts.append("- 海报头图→卖点展开→场景展示→细节工艺→信任背书→促销收尾")
    output_parts.append("")
    output_parts.append("三、细节图（4-6张）")
    detail_lines = [l.strip() for l in detail_scene.split('\n') if len(l.strip()) > 5][:6]
    for i, line in enumerate(detail_lines, 1):
        short = line[:60] + "..." if len(line) > 60 else line
        output_parts.append(f"{i}. {short}")
    output_parts.append("")
    output_parts.append("四、视频素材（如有）")
    output_parts.append("- 主图视频：15秒动态展示")
    output_parts.append("- 使用教程：30秒场景演示")

    return {
        'record_id': record['record_id'],
        '产品名称': name,
        '拍摄计划': '\n'.join(plan_parts),
        '思考过程': '\n'.join(think_parts),
        '输出结果': '\n'.join(output_parts),
    }

results = []
for rec in records:
    result = generate_plan(rec)
    results.append(result)

with open(r'C:\Users\jt\WorkBuddy\Claw\generated_plans.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"已为 {len(results)} 条记录生成拍摄计划/思考过程/输出结果")
print(f"首条记录产品名称: {results[0]['产品名称']}")
print(f"拍摄计划字数: {len(results[0]['拍摄计划'])}")
print(f"思考过程字数: {len(results[0]['思考过程'])}")
print(f"输出结果字数: {len(results[0]['输出结果'])}")
