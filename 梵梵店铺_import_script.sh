#!/bin/bash
# 导入梵梵店铺分镜脚本到 LibTV
# 用法: 先 libtv login web 登录，再运行此脚本

# 1. 创建项目
libtv project create -n "梵梵店铺-落英缤纷"

# 2. 导入分镜数据
# 将 JSON 文件中的 rows 写入 script 节点的 rows 属性
libtv script import \
  --project "梵梵店铺-落英缤纷" \
  --file "C:/Users/jt/WorkBuddy/Claw/梵梵店铺_LibTV分镜脚本.json"
