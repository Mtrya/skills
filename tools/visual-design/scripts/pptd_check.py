#!/usr/bin/env python3
"""pptd 格式与导出支持范围校验器。

用法: python pptd_check.py <pptd目录> [-p 1,3 | 2-5]
检查: YAML 语法、必填字段、类型、取值范围、$主题引用、页面文件、src 资源、bounds 越界、表格比例。
"""
import argparse, os, re, sys

from pptd_support import prepare_deck, prepare_element

try:
    import yaml
except ImportError:
    sys.exit('需要 pyyaml: pip install pyyaml')

ISSUES = []
def issue(kind, path, eid, msg):
    ISSUES.append(f'[{kind}] {path} id="{eid}" {msg}')

def check_number(v, kinds=(int, float)):
    return isinstance(v, kinds) and not isinstance(v, bool)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('deck_dir')
    ap.add_argument('-p', '--pages', default=None)
    a = ap.parse_args()

    root = os.path.abspath(a.deck_dir)
    pptd_files = [f for f in os.listdir(root) if f.endswith('.pptd')]
    if len(pptd_files) != 1:
        sys.exit(f'{root} 必须包含且仅包含一个 .pptd 文件')
    entry = os.path.join(root, sorted(pptd_files)[0])

    try:
        deck = yaml.safe_load(open(entry, encoding='utf-8'))
    except yaml.YAMLError as e:
        sys.exit(f'[YamlParseError] {entry}: {e}')
    try:
        prepare_deck(deck)
    except ValueError as e:
        sys.exit(f'[Unsupported] {entry}: {e}')

    # 主入口必填
    for field in ('size', 'pages'):
        if field not in deck:
            issue('MissingField', entry, '-', f'主入口缺少 {field}')
    size = deck.get('size') or []
    if len(size) != 2 or not all(check_number(v) and v > 0 for v in size):
        issue('OutOfRange', entry, '-', 'size 必须是两个正数 [w, h]')
    colors = set((deck.get('theme') or {}).get('colors') or {})
    styles = set((deck.get('theme') or {}).get('textStyles') or {})

    page_list = deck.get('pages') or []
    # 页码过滤
    sel = set()
    if a.pages:
        for part in a.pages.split(','):
            if '-' in part:
                lo, hi = part.split('-'); sel.update(range(int(lo), int(hi)+1))
            else:
                sel.add(int(part))

    for idx, rel in enumerate(page_list, 1):
        if sel and idx not in sel:
            continue
        ppath = os.path.join(root, rel)
        if not os.path.isfile(ppath):
            issue('PageNotFound', entry, '-', f'页面 {idx}: {rel} 不存在'); continue
        try:
            page = yaml.safe_load(open(ppath, encoding='utf-8'))
        except yaml.YAMLError as e:
            issue('YamlParseError', ppath, '-', str(e)); continue
        if not isinstance(page, dict) or 'elements' not in page:
            issue('MissingField', ppath, '-', '缺少 elements'); continue

        seen_ids = set()
        for el in page.get('elements') or []:
            eid = el.get('elementId', '?')
            try:
                el = prepare_element(el, deck.get('theme') or {})
            except (ValueError, KeyError) as e:
                issue('Unsupported', ppath, eid, str(e)); continue
            if eid in seen_ids:
                issue('OutOfRange', ppath, eid, 'elementId 重复')
            seen_ids.add(eid)
            et = el.get('elementType')
            if et not in ('text','shape','line','image','icon','table','chart'):
                issue('InvalidType', ppath, eid, f'未知 elementType: {et}'); continue
            b = el.get('bounds')
            if not (isinstance(b, list) and len(b) == 4 and all(check_number(v) for v in b)):
                issue('InvalidType', ppath, eid, 'bounds 须为 4 个数字'); continue
            if b[2] <= 0 or b[3] <= 0:
                issue('OutOfRange', ppath, eid, 'bounds 宽高须为正数')
            if size and (b[0] < 0 or b[1] < 0 or b[0]+b[2] > size[0] or b[1]+b[3] > size[1]):
                issue('BoundsOutside', ppath, eid, f'bounds {b} 超出页面 {size}（出血设计可忽略）')

            def check_color_ref(c):
                if isinstance(c, str) and c.startswith('$') and c[1:] not in colors:
                    issue('InvalidTheme', ppath, eid, f'颜色 token {c} 未在 theme.colors 定义')

            if et == 'text':
                c = el.get('content') or {}
                if 'text' not in c:
                    issue('MissingField', ppath, eid, 'text 元素缺少 content.text')
                check_color_ref(c.get('color'))
                ts = c.get('textStyle')
                if isinstance(ts, str) and ts.startswith('$') and ts[1:] not in styles:
                    issue('InvalidTheme', ppath, eid, f'文本样式 {ts} 未定义')
            if et == 'image':
                src = el.get('src','')
                if src and not src.startswith(('http://','https://')):
                    if not os.path.isfile(os.path.join(root, src)):
                        issue('SrcNotFound', ppath, eid, f'图片不存在: {src}')
            if et == 'shape':
                if 'shapeName' not in el:
                    issue('MissingField', ppath, eid, 'shape 缺少 shapeName')
                if el.get('shapeName') == 'custom' and not ('viewBox' in el and 'path' in el):
                    issue('MissingField', ppath, eid, 'custom 形状需要 viewBox 和 path')
            if et == 'table':
                for k in ('columnWidths','rowHeights'):
                    ws = el.get(k)
                    if not ws or not all(check_number(v) for v in ws):
                        issue('InvalidType', ppath, eid, f'{k} 须为数字数组'); continue
                    if abs(sum(ws) - 1) > 0.01:
                        issue('OutOfRange', ppath, eid, f'{k} 之和须为 1（当前 {sum(ws):.3f}）')
                    if any(not (0 <= v <= 1) for v in ws):
                        issue('OutOfRange', ppath, eid, f'{k} 每项须在 [0,1]')
            # fill 里的颜色引用
            fill = el.get('fill')
            if isinstance(fill, dict):
                check_color_ref(fill.get('color'))

    if ISSUES:
        print('\n'.join(ISSUES)); print(f'\n共 {len(ISSUES)} 个问题')
        sys.exit(1)
    print('校验通过，无问题。')

if __name__ == '__main__':
    main()
