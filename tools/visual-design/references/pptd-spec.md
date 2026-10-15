# pptd 格式规范（精简完整版）

YAML 1.2 语法。设计目标：每页自包含、所见即所得、人可直接读写。

## 本地导出支持范围

下文保留格式说明与示例，格式能描述的能力不等于本地导出器全部实现。校验器与导出器共用支持规则；不支持的字段和类型会报错，不能以其他元素代替。

- `size` 与 `bounds` 按 96 dpi 的像素换算，保留源画布尺寸和比例；`fontSize` 与边框宽度以 pt 计。
- text：纯文本及 `p/strong/em/u` 标签、字号、字体名、颜色、粗斜体、对齐与倍数行距；支持 `theme.textStyles`，局部字段优先。其他标签、LaTeX、字距和固定像素行距需先处理。
- shape：支持脚本 `SHAPES` 中的常用预置形状、纯色填充与实线边框；自定义 path、调整参数、渐变/图片填充需制作成素材。
- line：支持两个端点的实线；折线可拆成多个 line 元素。
- image：支持本地文件或 URL，以及 `fit: {mode: fill}`；按目标宽高比预处理素材。crop、cover/contain、cropShape 和图片边框尚未实现。
- table：支持行列比例、纯文本、字号、颜色、粗体、水平对齐、纯色填充及单元格合并；其他单元格样式会报错。
- chart：支持 bar、line、area、pie，渲染为图片嵌入；支持类别轴、数值轴、轴标题、图标题与图例。暂不支持多个 bar 系列、混合 pie 系列及其他图表类型，需外部绘制后嵌入。
- icon、元素 opacity/rotation/flip、动画与备注暂不支持。字体须预先安装；`customFonts` 不会自动加载，声明会报错。字体准备见 [fonts.md](fonts.md)。

## 文件结构

```
项目目录/
├── deck.pptd        # 主入口：版本、尺寸、主题、页面清单、自定义字体
├── pages/
│   ├── page-1.page  # 每页一个文件，元素平铺
│   └── ...
└── media/           # 图片资源，页面里用相对路径 ./media/xx.png 引用
```

## 主入口 .pptd

```yaml
version: v2
size: [960, 540]        # PPT 16:9；海报可用 [1280,720]/[720,1280]/[960,1280]/[1080,1080]
theme:
  colors:               # 自定义色板，元素里用 $名字 引用
    primary: "#16324F"
    accent: "#2B5C8A"
  textStyles:           # 命名文本样式，用 $名字 引用
    body: {fontSize: 16, color: "$primary"}
pages:
  - pages/page-1.page
  - pages/page-2.page
```

## 页面 .page

```yaml
elements:
  - elementId: title
    elementType: text
    bounds: [60, 40, 840, 80]   # [x, y, w, h]，页面左上角原点，单位 px
    content: {text: "页面标题", fontSize: 32, bold: true}
```

所有元素共有字段：`elementId`（唯一）、`elementType`、`bounds`；可选 `opacity [0,1]`、`rotation`（顺时针角度）、`flip: [水平, 垂直]`。

## 元素一：text

```yaml
- elementId: t1
  elementType: text
  bounds: [60, 140, 840, 200]
  content:
    text: |                # 支持富文本标签
      <p>段落一，<strong>加粗</strong>、<em>斜体</em>、<u>下划线</u></p>
      <ul><li>列表项</li></ul>
      <p>公式：\(E=mc^2\)，上标 x<sup>2</sup></p>
    fontSize: 18
    fontFamily: "MiSans"   # 先在渲染环境中安装，再使用准确的 family 名
    color: "#333333"
    align: {horizontal: left, vertical: top}   # horizontal: left/center/right/justify
    lineHeight: 1.6        # 倍数；或 lineHeightPx 固定值
    letterSpacing: 1
    textStyle: "$body"     # 引用 theme.textStyles，局部字段优先
```

富文本标签：`p / span / strong / em / u / s / sup / sub / a / ul / ol / li`；LaTeX 用 `\(...\)`（行内）与 `\[...\]`（独立）。

## 元素二：shape

```yaml
- elementId: s1
  elementType: shape
  bounds: [60, 300, 200, 100]
  shapeName: rect          # 177 种预置：rect, roundRect, ellipse, triangle, arrow, star5...
  adjustments: [15000]     # 形状调节参数（如圆角半径），省略有默认值
  fill: {type: solid, color: "$primary"}    # 也支持 gradient、image
  border: {color: "#000", width: 1}
```

自定义形状：`shapeName: custom` + `viewBox: [w, h]` + `path: "M..."`（SVG path 语法）。
**形状不内嵌文字**——文字叠一个 text 元素。

## 元素三：line

```yaml
- elementId: l1
  elementType: line
  bounds: [60, 250, 840, 2]
  points: [[0, 0], [840, 0]]    # 相对 bounds 的折线点
  border: {color: "$primary", width: 2, style: solid}   # style: solid/dash/dot
```

## 元素四：image

```yaml
- elementId: img1
  elementType: image
  bounds: [60, 100, 400, 300]
  src: "./media/photo.png"
  crop: {top: 0.1, bottom: 0.1}     # 第一步：比例裁剪（正值内切，负值外扩）
  fit: {mode: cover}                 # 第二步：cover 填满裁边 / contain 完整留白 / fill 拉伸
  cropShape: {shapeName: ellipse}   # 第三步：按形状轮廓裁剪显示区
  border: {color: "#000", width: 1}
```

渲染顺序固定：**crop → fit → cropShape**。

## 元素五：icon

```yaml
- elementId: ic1
  elementType: icon
  bounds: [60, 100, 48, 48]
  iconName: "fas:lightbulb"   # Font Awesome free：fas（solid）/far（regular）/fab（brands）
  fill: {type: solid, color: "$primary"}
```

图标查询：https://fontawesome.com/search?ic=free-collection

## 元素六：table

```yaml
- elementId: tb1
  elementType: table
  bounds: [60, 120, 840, 300]
  columnWidths: [0.3, 0.4, 0.3]    # 比例，总和必须为 1
  rowHeights: [0.2, 0.4, 0.4]      # 同上
  rows:
    - - text: "表头1"
        fill: {type: solid, color: "$primary"}
        color: "#fff"
        bold: true
        colSpan: 2                 # 合并：被覆盖的格子在数组中直接省略
      - text: "表头3"
    - - text: "A"
      - text: "右对齐数字"
        align: {horizontal: right}
    - - text: "B"
      - text: "C"
      - text: "D"
```

单元格字段：`text`（支持富文本）、`textStyle`、`color/fontSize/fontFamily/bold/italic`、`fill`、`align`、`rowSpan/colSpan`。合并区覆盖的单元格不写占位。

## 元素七：chart

仿 ECharts 思路：顶层**没有** type 字段，每个 series 自带 type。13 种：`bar / line / area / scatter / bubble / candlestick / pie / radar / waterfall / heatmap / treemap / sunburst / sankey`。

```yaml
- elementId: c1
  elementType: chart
  bounds: [60, 100, 500, 320]
  xAxis: {type: category, data: ["Q1","Q2","Q3","Q4"]}
  yAxis: {type: value, name: "亿元"}
  series:
    - type: bar
      name: 收入
      data: [12, 18, 25, 31]
      color: "$primary"
    - type: line
      name: 增速
      data: [0, 50, 39, 24]
  legend: {show: true}
  title: {text: "季度收入"}
```

饼图等无坐标轴类型省略 xAxis/yAxis，series 内给 `data: [{name, value}, ...]`。

## 内置 10 色板

`#1783FE #00C9C9 #7B61FF #FF7A45 #FFC53D #25B864 #F759AB #8C8C8C #FA541C #13A8A8`

## 校验要点（脚本检查项）

脚本检查 YAML、页面尺寸与文件、元素 bounds、主题引用、图片路径、表格比例以及本地导出支持范围。文字溢出、欠填充、遮挡、字体替换和漂移通过逐页渲染检查。

## 设计资产补充

- **自由尺寸**：常用 16:9 `[1280,720]`、9:16 `[720,1280]`、4:3 `[1280,960]`、3:4 `[960,1280]`、1:1 `[1080,1080]`；信息图默认宽 1080，高按内容定。
- **出血允许**：刻意超出画布的元素可按设计保留；BoundsOutside 提醒需要判断，导出能力错误必须修正。
- **质感素材**：颗粒纹理、渐变叠层等先用合适工具制作成素材存入 media/，再以 image 嵌入。
- **重复元素**：平铺纹理、等距点阵可用 Python 计算坐标批量生成 element 列表。
