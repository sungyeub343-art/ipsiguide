"""Build static region pages, national region lists, SEO head tags and sitemap.xml.

Run from the site root after changing regions.js, all-subregions.js or a *-district.html template:
    python generate-pages.py
"""
import datetime
import hashlib
import html
import json
import re
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_URL = 'https://ipsiguide.kr'
BRAND = 'IPSIGuide'
PHONE = '010-2928-3614'

CATEGORIES = [
    {
        'key': 'consulting', 'template': 'district.html', 'national': 'cities.html',
        'service': '입시 컨설팅', 'short': '입시 컨설팅',
        'national_title': '지역별 입시 컨설팅 | 수시·정시 전략, 면접·제시문 대비 | IPSIGuide',
        'description': '{full} 학생을 위한 수시·정시 지원 전략, 면접, 제시문 대비 입시 컨설팅 안내입니다.',
        'faq': ('언제부터 입시 컨설팅을 받는 것이 좋나요?',
                '고1~고2에 시작하면 내신과 생기부를 함께 설계할 수 있고, 고3은 남은 기간에 맞춰 지원 전략과 면접 준비에 집중합니다.'),
    },
    {
        'key': 'tutoring', 'template': 'tutoring-district.html', 'national': 'tutoring.html',
        'service': '내신대비 과외', 'short': '내신대비 과외',
        'national_title': '내신대비 과외 | 전국 지역별 고등 내신 관리 | IPSIGuide',
        'description': '{full} 고등학생을 위한 국어·영어·수학·사회탐구·과학탐구 내신대비 과외 안내입니다.',
        'faq': ('다니는 학교 시험 범위에 맞춰 수업하나요?',
                '네. {district} 학생이 다니는 학교의 시험 범위와 일정을 확인해 과목별 학습 계획을 세웁니다.'),
    },
    {
        'key': 'jungsi-tutoring', 'template': 'jungsi-tutoring-district.html', 'national': 'jungsi-tutoring.html',
        'service': '정시대비 과외', 'short': '정시대비 과외',
        'national_title': '정시대비 과외 | 전국 지역별 수능 과목 관리 | IPSIGuide',
        'description': '{full} 학생을 위한 수능 국어·수학·영어·탐구 정시대비 과외 안내입니다.',
        'faq': ('모의고사 성적이 낮아도 시작할 수 있나요?',
                '네. 현재 등급과 목표 대학을 기준으로 취약 영역부터 순서대로 관리합니다.'),
    },
    {
        'key': 'essay-tutoring', 'template': 'essay-tutoring-district.html', 'national': 'essay-tutoring.html',
        'service': '논술과외', 'short': '논술과외',
        'national_title': '논술과외 | 전국 지역별 대학 논술 첨삭 | IPSIGuide',
        'description': '{full} 학생을 위한 대학 논술과외, 제시문 분석, 답안 작성과 첨삭 수업 안내입니다.',
        'faq': ('논술 수업은 어떻게 진행되나요?',
                '목표 대학의 기출 유형을 먼저 확인하고, 제시문 분석과 답안 작성, 1:1 첨삭을 반복합니다.'),
    },
    {
        'key': 'record-management', 'template': 'record-management-district.html', 'national': 'record-management.html',
        'service': '생기부 관리', 'short': '생기부 관리',
        'national_title': '생기부 관리 | 전국 지역별 학교생활기록부 컨설팅 | IPSIGuide',
        'description': '{full} 학생을 위한 세특·창체·행특 등 학교생활기록부(생기부) 관리 안내입니다.',
        'faq': ('고3도 생기부 관리를 받을 수 있나요?',
                '네. 남은 학기의 기록 방향을 정리하고, 이미 작성된 기록은 면접 대비와 연결해 활용하는 방법을 안내합니다.'),
    },
    {
        'key': 'interview-coaching', 'template': 'interview-coaching-district.html', 'national': 'interview-coaching.html',
        'service': '면접 코칭', 'short': '면접 코칭',
        'national_title': '면접 코칭 | 전국 지역별 대학 입시 면접 대비 | IPSIGuide',
        'description': '{full} 학생을 위한 학생부 면접, 제시문 면접, 인성 면접 등 대학 입시 면접 코칭 안내입니다.',
        'faq': ('면접 날짜가 얼마 남지 않았는데 준비할 수 있나요?',
                '네. 지원 대학의 면접 방식과 남은 기간에 맞춰 예상 질문 정리와 모의 면접 위주로 집중 준비합니다.'),
    },
]

HOME = {
    'title': '입시컨설팅 | 에듀코 상상코칭 - 수시·정시 전략, 면접·생기부·논술 관리',
    'description': '에듀코 상상코칭 입시컨설팅. 수시·정시 지원 전략, 면접 코칭, 생기부 관리, 논술·내신·정시 과외까지 전국 지역별로 안내합니다. 전화 상담 010-2928-3614',
}

EXTRA_CSS = """
      .local-info { padding: 10px 0 70px; }
      .local-info h2 { margin: 0 0 12px; }
      .local-info .lead { max-width: 820px; color: var(--muted, #5f6b80); }
      .local-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 22px; }
      .local-card { padding: 22px; border: 1px solid var(--line, #dfe7f5); border-radius: 16px; background: #fff; }
      .local-card h3 { margin: 0 0 12px; color: var(--navy, #0f1d3d); font-size: 1.05rem; }
      .local-links { display: flex; flex-wrap: wrap; gap: 7px; }
      .local-links a { padding: 6px 10px; border: 1px solid var(--line, #dfe7f5); border-radius: 9px; color: #43516b; background: #fbfdff; font-size: 13px; }
      .local-links a:hover { border-color: var(--blue, #2f73ff); color: var(--blue, #2f73ff); }
      .subregion-list span { padding: 8px 12px; border: 1px solid var(--line, #dfe7f5); border-radius: 9px; color: var(--navy, #0f1d3d); background: #fff; font-size: 13px; font-weight: 700; }
      .local-faq { margin-top: 22px; }
      .local-faq details { padding: 16px 18px; border: 1px solid var(--line, #dfe7f5); border-radius: 12px; background: #fff; }
      .local-faq details + details { margin-top: 10px; }
      .local-faq summary { cursor: pointer; color: var(--navy, #0f1d3d); font-weight: 800; }
      .local-faq p { margin: 10px 0 0; color: var(--muted, #5f6b80); font-size: 14px; }
      @media (max-width: 720px) { .local-grid { grid-template-columns: 1fr; } }
"""


def load_regions():
    """Evaluate regions.js + all-subregions.js with Node so the data matches what the browser sees."""
    js = (
        "global.window={};const fs=require('fs');"
        "eval(fs.readFileSync('regions.js','utf8'));eval(fs.readFileSync('all-subregions.js','utf8'));"
        "process.stdout.write(JSON.stringify({regions:window.ipsiRegions,subregions:window.ipsiSubregions}));"
    )
    out = subprocess.run(['node', '-e', js], cwd=ROOT, capture_output=True, check=True)
    data = json.loads(out.stdout.decode('utf-8'))
    return data['regions'], data['subregions']


def slug(region, district):
    return f'{region}-{district}'


def page_url(folder, region, district):
    return f'{BASE_URL}/{folder}/{urllib.parse.quote(slug(region, district))}.html'


def josa(word, with_batchim, without_batchim):
    code = ord(word[-1]) - 0xAC00
    has_batchim = 0 <= code <= 11171 and code % 28 != 0
    return word + (with_batchim if has_batchim else without_batchim)


def pick(key, options):
    return options[int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16) % len(options)]


def esc(text):
    return html.escape(text, quote=True)


def set_inner(page, element_id, text):
    pattern = re.compile(r'(<(\w+)[^>]*\bid="' + re.escape(element_id) + r'"[^>]*>)(.*?)(</\2>)', re.S)
    page, count = pattern.subn(lambda m: m.group(1) + text + m.group(4), page, count=1)
    return page


def head_tags(title, description, url, extra_jsonld=None, robots=None):
    tags = [
        f'    <link rel="canonical" href="{esc(url)}" />',
        f'    <meta property="og:type" content="website" />',
        f'    <meta property="og:site_name" content="{BRAND}" />',
        f'    <meta property="og:locale" content="ko_KR" />',
        f'    <meta property="og:title" content="{esc(title)}" />',
        f'    <meta property="og:description" content="{esc(description)}" />',
        f'    <meta property="og:url" content="{esc(url)}" />',
    ]
    if robots:
        tags.insert(0, f'    <meta name="robots" content="{robots}" />')
    for data in extra_jsonld or []:
        tags.append('    <script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>')
    return '\n'.join(tags)


def replace_seo_block(page, block):
    marked = f'    <!--seo-->\n{block}\n    <!--/seo-->\n'
    if '<!--seo-->' in page:
        return re.sub(r'    <!--seo-->\n.*?    <!--/seo-->\n', lambda _: marked, page, count=1, flags=re.S)
    return page.replace('  </head>', marked + '  </head>', 1)


def set_title_and_description(page, title, description):
    page = re.sub(r'<title>.*?</title>', lambda _: f'<title>{esc(title)}</title>', page, count=1, flags=re.S)
    page = re.sub(r'<meta\s+name="description"\s+content="[^"]*"\s*/>',
                  lambda _: f'<meta name="description" content="{esc(description)}" />', page, count=1)
    return page


def breadcrumb(items):
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': name, 'item': url}
            for i, (name, url) in enumerate(items)
        ],
    }


def build_region_page(cat, template, region, district, districts, subregions):
    full = f'{region} {district}'
    service = cat['service']
    title = f'{full} {service} | {BRAND}'
    sample = subregions[:3]
    description = cat['description'].format(full=full)
    if sample:
        description += f' {"·".join(sample)} 등 {district} 전 지역 상담 가능.'
    url = page_url(cat['key'], region, district)

    page = template
    page = re.sub(r'    <!--legacy-redirect-->.*?<!--/legacy-redirect-->\n', '', page, flags=re.S)
    page = re.sub(r'\s*<script[^>]*>.*?</script>', '', page, flags=re.S)
    page = set_title_and_description(page, title, description)

    page = set_inner(page, 'region-label', esc(region))
    page = set_inner(page, 'district-title', esc(district if cat['key'] == 'consulting' else full))
    for element_id in ('district-copy', 'subject-region', 'guide-region', 'footer-region', 'subregion-heading'):
        page = set_inner(page, element_id, esc(full))
    page = set_inner(page, 'service-heading', esc(f'{full} 학생에게 필요한 컨설팅'))

    if subregions:
        page = set_inner(page, 'subregion-list', ''.join(f'<span>{esc(name)}</span>' for name in subregions))
        page = page.replace('동·읍·면 선택</h2>', '동·읍·면 안내</h2>', 1)
        page = re.sub(r'(<div id="subregion-section"[^>]*><div class="section-head">.*?</h2>)<p>.*?</p>',
                      lambda m: m.group(1) + f'<p>아래 {esc(district)} 모든 동·읍·면 학생이 상담할 수 있습니다.</p>',
                      page, count=1, flags=re.S)
    else:
        page = re.sub(r'<div id="subregion-section"', '<div id="subregion-section" hidden', page, count=1)

    # Pages live one folder down, so site-relative links need ../
    page = re.sub(r'\b(href|src)="(?!https?:|#|/|tel:|mailto:|\.\./)([^"]*)"', r'\1="../\2"', page)

    count = len(subregions)
    names = ', '.join(sample)
    service_obj = josa(service, '을', '를')
    lead = pick(full + cat['key'], [
        f'{full}에는 {count}개의 동·읍·면이 있습니다. {BRAND}는 {names} 등 {district} 전 지역 학생을 대상으로 {service_obj} 안내합니다.',
        f'{names} 등 {full} {count}개 동·읍·면 어디에 살고 있어도 {service} 상담을 받을 수 있습니다.',
        f'{full} 학생과 학부모님을 위한 {service} 안내 페이지입니다. {names} 등 {count}개 동·읍·면 학생이 상담할 수 있습니다.',
    ]) if subregions else f'{full} 학생과 학부모님을 위한 {service} 안내 페이지입니다.'

    index = districts.index(district)
    nearby = [d for d in districts[max(0, index - 6):index + 7] if d != district][:10]
    nearby_links = ''.join(
        f'<a href="{esc(slug(region, d))}.html">{esc(d)} {esc(service)}</a>' for d in nearby)
    other_links = ''.join(
        f'<a href="../{other["key"]}/{esc(slug(region, district))}.html">{esc(district)} {esc(other["short"])}</a>'
        for other in CATEGORIES if other is not cat)

    first_dongs = ', '.join(subregions[:5]) if subregions else district
    faqs = [
        (f'{district} 어느 동에 살아도 상담받을 수 있나요?',
         f'네. {first_dongs} 등 {full} 전 지역 학생 모두 상담할 수 있습니다. {PHONE}로 연락주시면 학생 상황에 맞춰 안내드립니다.'),
        (f'{service}는 어떻게 시작하나요?',
         f'전화 상담에서 학년, 현재 성적, 목표를 확인한 뒤 학생에게 맞는 진행 방향과 일정을 안내드립니다.'),
        (cat['faq'][0], cat['faq'][1].format(district=district, full=full)),
    ]
    faq_html = ''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faqs)

    section = (
        f'<section class="local-info"><div class="container">'
        f'<h2>{esc(full)} {esc(service)} 안내</h2><p class="lead">{esc(lead)}</p>'
        f'<div class="local-grid">'
        f'<article class="local-card"><h3>{esc(region)} 다른 지역 {esc(service)}</h3><div class="local-links">{nearby_links}'
        f'<a href="../{cat["national"]}">전체 지역 보기</a></div></article>'
        f'<article class="local-card"><h3>{esc(district)} 다른 수업 안내</h3><div class="local-links">{other_links}</div></article>'
        f'</div>'
        f'<div class="local-faq"><h2>자주 묻는 질문</h2>{faq_html}</div>'
        f'</div></section>'
    )
    page = page.replace('</main>', section + '</main>', 1)
    page = page.replace('    </style>', EXTRA_CSS.rstrip('\n') + '\n    </style>', 1)

    jsonld = [breadcrumb([
        ('홈', f'{BASE_URL}/'),
        (service, f'{BASE_URL}/{cat["national"]}'),
        (full, url),
    ])]
    page = replace_seo_block(page, head_tags(title, description, url, jsonld))
    return page


def build_region_grid(cat, regions):
    cards = []
    for region, districts in regions.items():
        links = ''.join(
            f'<a href="{cat["key"]}/{esc(slug(region, d))}.html">{esc(d)}</a>' for d in districts)
        cards.append(
            f'<article class="region-card"><h3>{esc(region)}</h3>'
            f'<span class="region-count">{len(districts)}개 지역 안내</span>'
            f'<div class="district-list">{links}</div></article>')
    return ''.join(cards)


def update_page(name, transform):
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    new = transform(text)
    if new != text:
        path.write_text(new, encoding='utf-8', newline='')


def main():
    regions, subregion_map = load_regions()
    today = datetime.date.today().isoformat()
    sitemap = [(f'{BASE_URL}/', '1.0')]

    org = {
        '@context': 'https://schema.org',
        '@type': 'EducationalOrganization',
        'name': '에듀코 상상코칭 입시컨설팅',
        'alternateName': BRAND,
        'url': f'{BASE_URL}/',
        'telephone': '+82-10-2928-3614',
        'areaServed': {'@type': 'Country', 'name': '대한민국'},
        'description': HOME['description'],
    }
    def home(p):
        # Open Graph tags now come from the generated SEO block.
        p = re.sub(r'\n\s*<meta\s+property="og:(title|description|type)"\s+content="[^"]*"\s*/>', '', p)
        p = set_title_and_description(p, HOME['title'], HOME['description'])
        return replace_seo_block(p, head_tags(HOME['title'], HOME['description'], f'{BASE_URL}/', [org]))
    update_page('index.html', home)

    # Phone page is thin; keep it out of search results.
    update_page('form.html', lambda p: replace_seo_block(
        p, head_tags('전화 상담 | IPSIGuide', '전화 상담 안내', f'{BASE_URL}/form.html', robots='noindex, follow')))

    total = 0
    for cat in CATEGORIES:
        template = (ROOT / cat['template']).read_text(encoding='utf-8')
        folder = ROOT / cat['key']
        folder.mkdir(exist_ok=True)
        expected = set()
        for region, districts in regions.items():
            for district in districts:
                subs = subregion_map.get(f'{region} {district}') or subregion_map.get(district) or []
                name = f'{slug(region, district)}.html'
                expected.add(name)
                (folder / name).write_text(
                    build_region_page(cat, template, region, district, districts, subs),
                    encoding='utf-8', newline='\n')
                sitemap.append((page_url(cat['key'], region, district), '0.6'))
                total += 1
        for stale in folder.glob('*.html'):
            if stale.name not in expected:
                stale.unlink()

        national_url = f'{BASE_URL}/{cat["national"]}'
        sitemap.insert(1, (national_url, '0.8'))

        def national(p, cat=cat, national_url=national_url):
            p = re.sub(r'<!--regions-->.*?<!--/regions-->',
                       lambda _: '<!--regions-->' + build_region_grid(cat, regions) + '<!--/regions-->', p, count=1, flags=re.S)
            desc = re.search(r'<meta name="description" content="([^"]*)"', p).group(1)
            p = set_title_and_description(p, cat['national_title'], html.unescape(desc))
            jsonld = [breadcrumb([('홈', f'{BASE_URL}/'), (cat['service'], national_url)])]
            return replace_seo_block(p, head_tags(cat['national_title'], html.unescape(desc), national_url, jsonld))
        update_page(cat['national'], national)

    body = '\n'.join(
        f'  <url>\n    <loc>{esc(url)}</loc>\n    <lastmod>{today}</lastmod>\n    <priority>{priority}</priority>\n  </url>'
        for url, priority in sitemap)
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '\n</urlset>\n',
        encoding='utf-8', newline='\n')
    print(f'Generated {total} region pages and sitemap.xml with {len(sitemap)} URLs.')


if __name__ == '__main__':
    main()
