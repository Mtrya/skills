---
name: visual-design
description: 创建和编辑演示文稿及设计资产，包括 PPTX、信息图、海报、社媒配图、简历与产品宣传图。用可编辑的 .pptd 源文件组织页面，校验后导出 PPTX 或渲染为图片；按交付物选择演示文稿或设计资产工作流。
license: 供个人学习使用
---

# Visual Design

共用 `.pptd` 格式、字体规则和导出脚本；按任务选择工作流，只加载当前模式的指导。

| 任务 | 工作流 | 场景参考 |
|---|---|---|
| 演示文稿、PPT、slides、deck | [演示文稿工作流](references/slides.md) | 自主设计时读 [PPT 设计手册](references/design-playbook.md) |
| 海报、信息图、社媒配图、简历、产品宣传图 | [设计资产工作流](references/assets.md) | 按类型读 [设计场景规范](references/profiles.md) |

两种模式的视觉规则各自适用，例如分析型幻灯片的克制配色与海报的质感技法。使用同一品牌或用户设计规范时保持一致。

## 共享格式与工具

生成前读 [pptd 格式与本地支持范围](references/pptd-spec.md)，选择字体时读 [字体体系](references/fonts.md)。超出导出器支持范围的元素先用合适工具制作成素材，再作为图片嵌入；保持可编辑的文字和支持的图形元素。

依赖：`python-pptx`、`matplotlib`、`pyyaml`；视觉检查使用 LibreOffice 和 Poppler。以下 `scripts/` 路径相对于本技能目录，执行时解析为绝对路径：

```bash
python scripts/pptd_check.py <作品目录>
python scripts/pptd_to_pptx.py <作品目录> -o <输出.pptx>
```

导出器遇到不支持的字段或元素会报错并停止，不用占位图形、其他图表类型或丢失元素的文件冒充成功。校验检查格式与支持范围；文字溢出、遮挡、字体替换和版面质量仍需渲染检查。

## 渲染与交付

产物优先放在用户指定位置或项目已有输出目录；临时渲染文件使用独立工作目录。作品保持自包含：一个 `.pptd` 主入口、`pages/` 和 `media/`。

将 PPTX 导出为 PDF，再逐页转图检查，避免把单张 PNG 当作整套幻灯片的预览：

```bash
soffice --headless --convert-to pdf --outdir <预览目录> <输出.pptx>
pdftoppm -png -r 144 <预览目录/输出.pdf> <预览目录/page>
```

图片交付时按目标像素尺寸选择渲染分辨率；导出画布的 `size` 按 96 dpi 转换为 PPTX 尺寸，96 dpi 渲染可得到对应像素大小。检查全部页面后交付 `.pptd` 源文件及用户要求的成品。
