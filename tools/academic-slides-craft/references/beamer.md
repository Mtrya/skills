# Beamer 实操

示例取自一份真实编译交付的论文汇报稿（XeLaTeX + `ctexbeamer`）：中文 Noto Sans CJK SC（粗体映射 Medium），西文 Fira Sans，数学 Fira Math。以下代码可直接抄改，颜色与宏名在各段保持一致。

## 导言区：字体、颜色与版式

```latex
\documentclass[aspectratio=169,12pt,fontset=none,t]{ctexbeamer}
\usepackage{amsmath,booktabs,colortbl,siunitx}
\usepackage{tikz}
\usepackage{unicode-math}
\usetikzlibrary{arrows.meta}

\setCJKmainfont{Noto Sans CJK SC}
\setCJKsansfont[BoldFont={Noto Sans CJK SC Medium}]{Noto Sans CJK SC}
\setsansfont[BoldFont=FiraSans-SemiBold.otf,ItalicFont=FiraSans-Italic.otf,
  BoldItalicFont=FiraSans-BoldItalic.otf]{FiraSans-Regular.otf}
\setmathfont{FiraMath-Regular.otf}

\definecolor{Canvas}{HTML}{F9FAFB}   \definecolor{Ink}{HTML}{1E293B}
\definecolor{Blue}{HTML}{003B70}     \definecolor{Teal}{HTML}{0F766E}
\definecolor{Muted}{HTML}{606B7A}    \definecolor{Line}{HTML}{D5DFEA}
\definecolor{BlueWash}{HTML}{EFF5FC} \definecolor{BlueLine}{HTML}{BFD4EE}
\definecolor{TealWash}{HTML}{EDF7F4} \definecolor{TealLine}{HTML}{B6DDD2}

\setbeamercolor{background canvas}{bg=Canvas}
\setbeamercolor{normal text}{fg=Ink,bg=Canvas}
\setbeamercolor{structure}{fg=Blue}
\setbeamersize{text margin left=9mm,text margin right=9mm}

\newcommand{\keytext}[1]{\textcolor{Blue}{\textbf{#1}}}
\newcommand{\softtext}[1]{\textcolor{Teal}{#1}}
\newcommand{\sectionrule}{\par\vskip.5em{\color{Line}\hrule height .45pt}\vskip.55em}
```

- `fontset=none` 关掉 ctex 默认字体集后显式声明；中文粗体映射到 Medium，避免默认伪粗在投影上糊开。
- 类选项 `t` 让正文顶部对齐，两栏与图文页不因垂直居中错位；封面单独用 `[plain,c]`。
- 颜色只留主色、强调色与中性灰；两条语义支路固定用 Blue/Teal 一对，全稿与图内一致。

## 接入机构主题

- 主题以本地路径接入（如 `\usepackage{theme/beamerthemefudan}`），仓库内保留主题副本与 LICENSE。先编译主题示例，核对版面比例、标题页、页脚、标识与中文字体；微调用 `\patchcmd`，不整段复制主题模板：

```latex
% 标题页换用机构横版标识，并收紧上下间距
\expandafter\patchcmd\csname beamer@@tmpl@title page\endcsname
  {logo-titlepage.pdf}{fudan-cover.pdf}{}{}
\expandafter\patchcmd\csname beamer@@tmpl@title page\endcsname
  {\vskip3em}{\vskip1.6em}{}{}
```

- 页脚固定三栏：短标题、本页出处、页码。出处用 `\source{...}` 按页写入，比集中到文献页更利于台上指认：

```latex
\newcommand{\framesource}{}
\AtBeginEnvironment{frame}{\gdef\framesource{}}
\newcommand{\source}[1]{\gdef\framesource{#1}}
\setbeamercolor{framesource}{fg=Muted,bg=Canvas}
\setbeamertemplate{footline}{%
  \leavevmode\vbox{%
  \hbox to \paperwidth{\hskip9mm{\color{Line}\rule{\dimexpr\paperwidth-18mm\relax}{.4pt}}\hfil}%
  \nointerlineskip
  \hbox{%
    \begin{beamercolorbox}[wd=.27\paperwidth,ht=2.6ex,dp=1.7ex,leftskip=9mm]{framesource}
      \scriptsize\insertshorttitle
    \end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.60\paperwidth,ht=2.6ex,dp=1.7ex,center]{framesource}
      \scriptsize\framesource
    \end{beamercolorbox}%
    \begin{beamercolorbox}[wd=.13\paperwidth,ht=2.6ex,dp=1.7ex,right,rightskip=9mm]{framesource}
      \scriptsize\insertframenumber/\inserttotalframenumber
    \end{beamercolorbox}%
  }}}
```

- 每页用 `\note{...}` 写预计用时与口头过渡，`\setbeameroption{hide notes}` 控制导出是否带备注页。

## 公式、图与数据表

- 变量斜体；操作符与单位用正体：`unicode-math` 下写 `\symup{CE}`、`$[-1,1]\,\symup{m/s}$`，比 `\mathrm` 更贴合所用数学字体。
- 架构图共享一套节点样式；同一张图拆到相邻页时复用坐标与语义色，只让新增部分变色：

```latex
\tikzset{
  flow/.style={-{Stealth[length=2.2mm,width=1.55mm]},line width=.95pt,draw=Muted},
  stage/.style={fill=white,draw=Line,line width=.55pt,text=Ink,rounded corners=2.2pt,
    minimum height=9.5mm,align=center,inner xsep=2mm,font=\small},
  velocity stage/.style={fill=BlueWash,draw=BlueLine,text=Blue},
  response stage/.style={fill=TealWash,draw=TealLine,text=Teal},
}
```

- 白底照片加 0.5 pt 细描边，图宽扣除边线，避免融进画布；两栏并排时先核对照片上缘与首行文字：

```latex
\newcommand{\framedphoto}[1]{%
  \begingroup
  \setlength{\fboxsep}{0pt}\setlength{\fboxrule}{.5pt}%
  \fcolorbox{Line}{white}{\includegraphics[width=\dimexpr\linewidth-2\fboxrule\relax]{#1}}%
  \endgroup
}
```

- 数据表用 `booktabs` 三线表；数值列用 `siunitx` 的 `S` 列对齐小数点，最优值按指标方向上色，比例条代替整列数字对比（零点与满刻度全表统一）：

```latex
% \stairsbar{数值}{颜色}：以 176.5 为满刻度的比例条
\newcommand{\stairsbar}[2]{%
  \begin{tikzpicture}[baseline=-.47ex]
    \path[use as bounding box] (0,-.11) rectangle (2.6,.11);
    \draw[Muted!22,line width=.5pt] (0,0) -- (2.6,0);
    \draw[#2,line width=1.65pt] (0,0) -- ({2.6*#1/176.5},0);
  \end{tikzpicture}}

{\renewcommand{\arraystretch}{1.32}
\begin{tabular}{p{3.2cm}rS[table-format=3.2,table-column-width=1.64cm,table-number-alignment=right,mode=text,detect-weight=true]l}
  \toprule
  Actor 输入 & 踩空恢复 & \multicolumn{2}{c}{连续爬楼平均级数} \\
  \midrule
  \rowcolor{BlueWash}
  \keytext{完整方法} & \keytext{20/20} & \color{Blue}\bfseries 176.5 & \stairsbar{176.5}{Blue} \\
  速度估计置零 & 18/20 & 51.45 & \stairsbar{51.45}{Muted} \\
  隐向量置零 & 1/20 & 13.3 & \stairsbar{13.3}{Muted} \\
  \bottomrule
\end{tabular}}
```

## 从实际导出件核对

在项目要求的工作目录编译，临时文件单独放置，核对完成后即清理；用户需要留档时，先把 PDF 复制到交付位置再删目录。以下命令以 `slides.tex` 为例。

```bash
slides_build_dir=$(mktemp -d)
trap 'rm -rf "$slides_build_dir"' EXIT   # 需保留产物时先 cp 再退出
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir="$slides_build_dir" slides.tex
pdfinfo "$slides_build_dir/slides.pdf"
pdftoppm -r 140 -png "$slides_build_dir/slides.pdf" "$slides_build_dir/page"
```

- 看日志中的溢出版面和缺字提示。看整套缩略图判断节奏，再以投影尺寸看改过和受全局样式影响的页面。用 `pdftotext -layout` 抽查公式周围的文字、数据标签、页序与文献出处。
- Beamer 可能把紧接在 `\begin{frame}{标题}` 后面的裸花括号组当成副标题。若首个内容块在 PDF 中消失，在它之前显式进入正文，例如用 `\noindent` 引出分组。重新检查该块是否出现。
- 把全局内容对齐改为顶部以后，重点检查含大照片、图注和两栏的页面。以最终 PDF 里的边界为准，必要时收紧页眉的段间距或缩小图幅。提交前核对总时长、封面、最后一页，以及用户明确要求增删的页。
