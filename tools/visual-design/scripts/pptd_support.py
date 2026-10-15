"""Export support shared by the validator and PPTX exporter."""

import re

SHAPE_TYPES = {
    'rect': 'RECTANGLE', 'roundRect': 'ROUNDED_RECTANGLE',
    'ellipse': 'OVAL', 'triangle': 'ISOSCELES_TRIANGLE',
    'rtTriangle': 'RIGHT_TRIANGLE', 'diamond': 'DIAMOND',
    'pentagon': 'PENTAGON', 'hexagon': 'HEXAGON',
    'star5': 'STAR_5_POINT', 'rightArrow': 'RIGHT_ARROW',
    'leftArrow': 'LEFT_ARROW', 'upArrow': 'UP_ARROW',
    'downArrow': 'DOWN_ARROW', 'chevron': 'CHEVRON',
    'parallelogram': 'PARALLELOGRAM', 'trapezoid': 'TRAPEZOID',
    'donut': 'DONUT', 'blockArc': 'BLOCK_ARC',
    'foldedCorner': 'FOLDED_CORNER', 'smileyFace': 'SMILEY_FACE',
    'heart': 'HEART', 'lightningBolt': 'LIGHTNING_BOLT',
    'sun': 'SUN', 'moon': 'MOON', 'cloud': 'CLOUD',
    'cross': 'CROSS', 'pie': 'PIE', 'arc': 'ARC',
}


def fields(value, allowed, label):
    unknown = set(value) - set(allowed.split())
    if unknown:
        raise ValueError(f'{label}: unsupported fields: {", ".join(sorted(unknown))}')


def fill_border(element):
    fill = element.get('fill') or {}
    fields(fill, 'type color', 'fill')
    if fill and fill.get('type') != 'solid':
        raise ValueError('Only solid fills are supported; render other fills as image assets')
    border = element.get('border') or {}
    fields(border, 'color width style', 'border')
    if border.get('style', 'solid') != 'solid':
        raise ValueError('Only solid borders are supported')


def prepare_deck(deck):
    fields(deck, 'version size theme pages', 'deck')
    if deck.get('version', 'v2') != 'v2':
        raise ValueError('Only pptd version v2 is supported')
    theme = deck.get('theme') or {}
    fields(theme, 'colors textStyles', 'theme')


def prepare_text(content, theme):
    content = dict(content)
    style = content.pop('textStyle', None)
    if style:
        if not isinstance(style, str) or not style.startswith('$'):
            raise ValueError('textStyle must reference a theme style using $name')
        content = {**theme['textStyles'][style[1:]], **content}
    fields(content, 'text fontSize fontFamily color bold italic align lineHeight', 'text')
    align = content.get('align') or {}
    fields(align, 'horizontal vertical', 'text alignment')
    if align.get('horizontal', 'left') not in ('left', 'center', 'right', 'justify'):
        raise ValueError('Unsupported horizontal alignment')
    if align.get('vertical', 'top') not in ('top', 'middle', 'bottom'):
        raise ValueError('Unsupported vertical alignment')
    text_blocks(content.get('text', ''))
    return content


def text_blocks(raw):
    if '\\(' in raw or '\\[' in raw:
        raise ValueError('LaTeX is unsupported; render equations as image assets')
    stack = []
    for token in re.findall(r'<[^>]+>', raw):
        match = re.fullmatch(r'<(/?)(p|strong|em|u)>', token)
        if not match:
            raise ValueError(f'Unsupported rich-text tag: {token}')
        closing, tag = match.groups()
        if closing:
            if not stack or stack.pop() != tag:
                raise ValueError('Unbalanced rich-text tags')
        else:
            if tag == 'p' and stack:
                raise ValueError('Paragraphs cannot be nested')
            stack.append(tag)
    if stack:
        raise ValueError('Unbalanced rich-text tags')
    if '<p>' in raw:
        if re.sub(r'<p>.*?</p>', '', raw, flags=re.S).strip():
            raise ValueError('Text outside paragraph tags would be lost; put it in a paragraph')
        return re.findall(r'<p>(.*?)</p>', raw, flags=re.S)
    return [raw]


def prepare_element(element, theme):
    element = dict(element)
    kind = element.get('elementType')
    allowed = {
        'text': 'content',
        'shape': 'shapeName fill border',
        'line': 'points border',
        'image': 'src fit',
        'table': 'columnWidths rowHeights rows',
        'chart': 'series xAxis yAxis legend title',
    }
    if kind not in allowed:
        raise ValueError(f'Unsupported elementType: {kind}; render it as an image asset')
    fields(element, 'elementId elementType bounds ' + allowed[kind], kind)
    if kind == 'text':
        element['content'] = prepare_text(element.get('content') or {}, theme)
    elif kind == 'shape':
        if element.get('shapeName') not in SHAPE_TYPES:
            raise ValueError(f'Unsupported shapeName: {element.get("shapeName")}')
        fill_border(element)
    elif kind == 'line':
        if 'points' in element and len(element['points']) != 2:
            raise ValueError('Only two-point lines are supported; split polylines into segments')
        fill_border(element)
    elif kind == 'image':
        fit = element.get('fit') or {}
        fields(fit, 'mode', 'image fit')
        if fit.get('mode', 'fill') != 'fill':
            raise ValueError('Only image fit=fill is supported; prepare the image at its target aspect ratio')
    elif kind == 'table':
        for row in element.get('rows') or []:
            for cell in row:
                fields(cell, 'text fontSize color bold align fill rowSpan colSpan', 'table cell')
                if re.search(r'<[^>]+>', cell.get('text', '')):
                    raise ValueError('Table cells support plain text only')
                fill_border(cell)
                align = cell.get('align') or {}
                fields(align, 'horizontal', 'cell alignment')
                if align.get('horizontal', 'left') not in ('left', 'center', 'right'):
                    raise ValueError('Unsupported table alignment')
    elif kind == 'chart':
        series = element.get('series') or []
        for item in series:
            fields(item, 'type data name color', 'chart series')
            if item.get('type') not in ('bar', 'line', 'area', 'pie'):
                raise ValueError(f'Unsupported chart type: {item.get("type")}')
            if item.get('type') == 'pie' and len(series) != 1:
                raise ValueError('Pie charts require exactly one series')
            if item.get('type') == 'pie' and item.get('color'):
                raise ValueError('Per-series pie colors are unsupported')
        if sum(item.get('type') == 'bar' for item in series) > 1:
            raise ValueError('Multiple bar series are unsupported; render the chart separately')
        for axis, expected in (('xAxis', 'category'), ('yAxis', 'value')):
            spec = element.get(axis) or {}
            fields(spec, 'type data name' if axis == 'xAxis' else 'type name', axis)
            if spec.get('type', expected) != expected:
                raise ValueError(f'Unsupported {axis} type: {spec.get("type")}')
        fields(element.get('legend') or {}, 'show', 'legend')
        fields(element.get('title') or {}, 'text', 'chart title')
    return element
