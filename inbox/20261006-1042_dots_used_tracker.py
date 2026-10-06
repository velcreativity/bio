#!/usr/bin/env python3
"""중고 매물 검색/재확인 CLI. Python 3.10+, pip install playwright.
python THIS_FILE init | login | run | export | selftest
"""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse, quote, urljoin

LABELS = {'available':'거래가능','reserved':'예약중','sold':'판매완료',
          'out_of_stock':'품절','removed':'삭제/페이지없음','unknown':'미확인'}
EXACT = {'거래가능':'available','판매중':'available','판매 중':'available',
         '예약중':'reserved','예약 중':'reserved','판매완료':'sold','판매 완료':'sold',
         '거래완료':'sold','거래 완료':'sold','판매종료':'sold','판매 종료':'sold',
         '품절':'out_of_stock','일시품절':'out_of_stock','SOLD OUT':'out_of_stock'}
AVAIL = {'InStock':'available','LimitedAvailability':'available',
         'OutOfStock':'out_of_stock','SoldOut':'sold','Discontinued':'sold'}
DEFAULT = {
 'keywords':['검색할 상품명을 입력하세요'], 'exclude_keywords':[],
 'min_price':None, 'max_price':None, 'data_dir':'used_tracker_data',
 'delay_seconds':4, 'timeout_ms':30000, 'render_wait_ms':1800,
 'scroll_rounds':3, 'max_per_search':40, 'recheck_limit':300,
 'headless':True, 'profile_dir':'used_tracker_profile',
 'sources':[
  {'name':'당근','enabled':True,'search_url':'https://www.daangn.com/kr/buy-sell/?search={keyword}&in={region}',
   'region':'', 'item_url_regex':r'/kr/buy-sell/[^/?]+/?$|/articles/\d+',
   'allowed_hosts':['www.daangn.com','daangn.com'], 'status_selector':'','price_selector':''},
  {'name':'번개장터','enabled':True,'search_url':'https://m.bunjang.co.kr/search/products?q={keyword}',
   'item_url_regex':r'/products/\d+', 'allowed_hosts':['m.bunjang.co.kr','bunjang.co.kr'],
   'status_selector':'','price_selector':''},
  {'name':'중고나라','enabled':True,'search_url':'https://web.joongna.com/search/{keyword}',
   'item_url_regex':r'/product/\d+', 'allowed_hosts':['web.joongna.com'],
   'status_selector':'','price_selector':''},
  {'name':'네이버카페','enabled':False,'search_url':'',
   'item_url_regex':r'/[^/]+/\d+|articleid=\d+|/articles/\d+',
   'allowed_hosts':['cafe.naver.com','m.cafe.naver.com'],
   'status_selector':'','price_selector':''},
  {'name':'기타쇼핑몰','enabled':False,'search_url':'','item_url_regex':'',
   'allowed_hosts':[], 'status_selector':'','price_selector':''}
 ]}

# 상태 라벨은 본문 전체에서 찾지 않는다. 명시적 selector 또는 h1 인근의 짧은
# 독립 라벨만 채택. 추천 영역의 판매완료와 본문 인용문이 섞이지 않도록 제한.
EXTRACT = r'''cfg => {
 const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
 const get = (sel) => sel ? [...document.querySelectorAll(sel)].filter(visible).map(e => e.innerText.trim()).filter(Boolean) : [];
 const h = [...document.querySelectorAll('h1')].find(visible);
 let labels = get(cfg.status_selector);
 if (!cfg.status_selector && h) {
   let p=h.parentElement;
   for(let i=0;i<3 && p;i++,p=p.parentElement) {
     if(p.querySelectorAll('h1').length!==1 || p.innerText.length>1500) break;
     for(const e of p.querySelectorAll('span,button,[role="status"]')) {
       if(visible(e) && e.children.length===0 && e.innerText.trim().length<=15) labels.push(e.innerText.trim());
     }
   }
 }
 const structured=[];
 for(const s of document.querySelectorAll('script[type="application/ld+json"]')) {
   try {structured.push(JSON.parse(s.textContent))} catch(e) {}
 }
 const meta = sel => document.querySelector(sel)?.content || '';
 return {title:h?.innerText.trim() || meta('meta[property="og:title"]') || document.title,
   h1:!!h, labels:[...new Set(labels)], structured,
   price_text:get(cfg.price_selector)[0] || '',
   meta_price:meta('meta[property="product:price:amount"]'),
   body:document.body?.innerText.slice(0,100000) || '',
   canonical:document.querySelector('link[rel="canonical"]')?.href || '',
   links:[...document.querySelectorAll('a[href]')].filter(visible).map(a=>({url:a.href,title:a.innerText.trim()}))};
}'''

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(url):
    p=urlparse(url)
    # Cafe articleid is part of identity; keep query to avoid merging different articles.
    q=p.query if 'naver.com' in p.netloc else ''
    return urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/'),'',q,''))

def allowed(url, source):
    p=urlparse(url)
    return p.scheme in ('http','https') and p.hostname in source['allowed_hosts']

def money(s):
    try:
        return int(float(str(s).replace(',','').replace('원','').strip()))
    except (ValueError, TypeError):
        return None

def products(value):
    if isinstance(value,list):
        for v in value: yield from products(v)
    elif isinstance(value,dict):
        t=value.get('@type',[])
        if t=='Product' or isinstance(t,list) and 'Product' in t:
            yield value
        # Only graph nesting: do not collect recommendation/ItemList Products.
        if '@graph' in value: yield from products(value['@graph'])

def classify(data, code, url, source):
    body=data.get('body','')
    # Access errors override any apparent stale status.
    if code in (401,403,429) or code>=500:
        return 'unknown',f'HTTP {code}',None
    if re.search(r'captcha|로봇이 아닙|접근이 제한|비정상적인 접근',body,re.I):
        return 'unknown','접근 제한/인증 화면',None
    if re.search(r'로그인이 필요|로그인 후 이용|멤버만|회원만 열람',body):
        return 'unknown','로그인/카페 권한 필요',None
    if code in (404,410):
        return 'removed',f'HTTP {code} (삭제 또는 경로 변경 가능)',None
    if not allowed(url,source) or not re.search(source['item_url_regex'],url):
        return 'unknown','상품 상세페이지 밖으로 이동',None
    price=money(data.get('price_text') or data.get('meta_price'))
    signals=[]
    # Structured offer must match THIS URL (or the single product title).
    ps=list(products(data.get('structured',[])))
    for p in ps:
        offers=p.get('offers',[])
        if isinstance(offers,dict): offers=[offers]
        for offer in offers if isinstance(offers,list) else []:
            if not isinstance(offer,dict): continue
            target=offer.get('url') or p.get('url')
            matches=canonical(urljoin(url,target))==canonical(url) if target else len(ps)==1 and p.get('name')==data.get('title')
            if not matches: continue
            status=AVAIL.get(str(offer.get('availability','')).split('/')[-1])
            if status: signals.append((status,'JSON-LD availability: '+str(offer['availability'])))
            if price is None: price=money(offer.get('price'))
    for label in data.get('labels',[]):
        if label.strip() in EXACT:
            signals.append((EXACT[label.strip()],'상품 인근 상태 라벨: '+label.strip()))
    states={s for s,_ in signals}
    if len(states)>1: return 'unknown','상태 근거 충돌: '+str(signals),price
    if signals: return signals[0][0],'; '.join(e for _,e in signals),price
    return 'unknown','명시적 상태 근거 없음 (판매가능으로 추정하지 않음)',price

def database(path):
    db=sqlite3.connect(path)
    db.row_factory=sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS items(url TEXT PRIMARY KEY, source TEXT, title TEXT,
      price INTEGER, state TEXT, evidence TEXT, first_seen TEXT, last_checked TEXT,
      last_verified_state TEXT, last_verified_at TEXT);
    CREATE TABLE IF NOT EXISTS queries(url TEXT, keyword TEXT, PRIMARY KEY(url,keyword));
    CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, url TEXT, checked TEXT,
      state TEXT, evidence TEXT, snapshot TEXT, http_code INTEGER);
    CREATE TABLE IF NOT EXISTS changes(id INTEGER PRIMARY KEY,url TEXT,checked TEXT,
      before_state TEXT,after_state TEXT);
    CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, checked TEXT,source TEXT,
      keyword TEXT,url TEXT,found INTEGER,error TEXT);
    ''')
    return db

def record(db,url,source,title,keyword,state,evidence,price,snapshot,code):
    t=now()
    old=db.execute('SELECT * FROM items WHERE url=?',(url,)).fetchone()
    verified=state if state!='unknown' else (old['last_verified_state'] if old else None)
    vt=t if state!='unknown' else (old['last_verified_at'] if old else None)
    db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(url) DO UPDATE SET title=excluded.title,price=COALESCE(excluded.price,items.price),
      state=excluded.state,evidence=excluded.evidence,last_checked=excluded.last_checked,
      last_verified_state=excluded.last_verified_state,last_verified_at=excluded.last_verified_at''',
      (url,source,title or (old['title'] if old else ''),price,state,evidence,
       old['first_seen'] if old else t,t,verified,vt))
    if keyword: db.execute('INSERT OR IGNORE INTO queries VALUES(?,?)',(url,keyword))
    db.execute('INSERT INTO observations(url,checked,state,evidence,snapshot,http_code) VALUES(?,?,?,?,?,?)',
               (url,t,state,evidence,snapshot,code))
    # A temporary access failure does not erase last verified state. Recovery to the
    # same state is not a new trading-state change.
    if old and state!='unknown' and old['last_verified_state'] and old['last_verified_state']!=state:
        db.execute('INSERT INTO changes(url,checked,before_state,after_state) VALUES(?,?,?,?)',
                   (url,t,old['last_verified_state'],state))
    db.commit()

def export(db,out,cfg):
    rows=[dict(r) for r in db.execute('SELECT * FROM items ORDER BY last_checked DESC')]
    for r in rows:
        r['keywords']=' | '.join(x[0] for x in db.execute('SELECT keyword FROM queries WHERE url=?',(r['url'],)))
        r['state_ko']=LABELS[r['state']]
    def selected(r):
        return (not any(x.casefold() in r['title'].casefold() for x in cfg['exclude_keywords'])
          and (cfg['min_price'] is None or r['price'] is not None and r['price']>=cfg['min_price'])
          and (cfg['max_price'] is None or r['price'] is not None and r['price']<=cfg['max_price']))
    def write(name, records):
        fields=list(records[0]) if records else ['url','state','evidence']
        with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fields); w.writeheader(); w.writerows(records)
    write('all_items.csv',rows)
    write('filtered_items.csv',[r for r in rows if selected(r)])
    write('available.csv',[r for r in rows if selected(r) and r['state']=='available'])
    write('changes.csv',[dict(r) for r in db.execute('SELECT * FROM changes ORDER BY id DESC')])
    write('search_runs.csv',[dict(r) for r in db.execute('SELECT * FROM runs ORDER BY id DESC')])
    (out/'all_items.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('내보내기:',out.resolve(), '전체 매물:',len(rows), flush=True)

class Collector:
    def __init__(self, context, cfg, out):
        self.context,self.cfg,self.out=context,cfg,out
    def fetch(self,url,source,scroll=False):
        page=self.context.new_page()
        result=None;code=0
        try:
            response=page.goto(url,wait_until='domcontentloaded',timeout=self.cfg['timeout_ms'])
            code=response.status if response else 0
            page.wait_for_timeout(self.cfg['render_wait_ms'])
            for _ in range(self.cfg['scroll_rounds'] if scroll else 0):
                page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
                page.wait_for_timeout(1000)
            # Naver desktop cafe article content may live in a same-origin iframe.
            frame=page.frame(name='cafe_main')
            target=frame if frame else page
            data=target.evaluate(EXTRACT,source)
            data['final_url']=page.url
            key=hashlib.sha256(url.encode()).hexdigest()[:16]+'_'+str(time.time_ns())
            base=self.out/'snapshots'/key
            base.with_suffix('.html').write_text(target.content(),encoding='utf-8')
            # Full raw source and extracted evidence are retained locally, never uploaded.
            base.with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            result=(data,code,str(base.with_suffix('.json')))
        finally:
            page.close()
            time.sleep(max(1,self.cfg['delay_seconds']))
        return result

def validate(cfg):
    if not cfg.get('keywords') or any(k=='검색할 상품명을 입력하세요' or not k.strip() for k in cfg['keywords']):
        raise ValueError('config.json의 keywords를 실제 상품명으로 바꾸세요.')
    names=set()
    for s in cfg['sources']:
        if not s.get('enabled'): continue
        if s['name'] in names: raise ValueError('source name은 고유해야 합니다.')
        names.add(s['name'])
        if not s['allowed_hosts'] or not s['item_url_regex'] or not s['search_url']:
            raise ValueError(s['name']+': search_url, item_url_regex, allowed_hosts를 설정하세요.')
        re.compile(s['item_url_regex'])
        url=s['search_url'].format(keyword='test',region=quote(s.get('region','')))
        if not allowed(url,s): raise ValueError(s['name']+': 검색 URL의 호스트가 allowed_hosts에 없습니다.')
        if s['name']=='당근' and not s.get('region'):
            print('안내: 당근 지역 미설정. 지역 선택 화면이면 검색 실패로 기록됩니다.',flush=True)

def run(cfg,db,out):
    validate(cfg)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit('먼저 python -m pip install playwright 및 python -m playwright install chromium 실행')
    with sync_playwright() as pw:
        context=pw.chromium.launch_persistent_context(str(Path(cfg['profile_dir']).resolve()),headless=cfg['headless'])
        try:
            collector=Collector(context,cfg,out)
            sources={s['name']:s for s in cfg['sources'] if s.get('enabled')}
            targets={}
            for s in sources.values():
                for kw in cfg['keywords']:
                    search=s['search_url'].format(keyword=quote(kw,safe=''),region=quote(s.get('region',''),safe=''))
                    count=0;err=''
                    try:
                        data,code,_=collector.fetch(search,s,True)
                        if code>=400: raise RuntimeError('HTTP '+str(code))
                        links=data['links']
                        for link in links:
                            u=canonical(link['url'])
                            if allowed(u,s) and re.search(s['item_url_regex'],u):
                                if not any(x in link['title'].casefold() for x in [kw.casefold()]):
                                    # Do not discard empty-text image links; detail title is checked below.
                                    if link['title']: continue
                                targets.setdefault(u,{'source':s,'title':link['title'],'keywords':set()})['keywords'].add(kw)
                                db.execute('INSERT OR IGNORE INTO queries VALUES(?,?)',(u,kw))
                                count+=1
                                if count>=cfg['max_per_search']: break
                        if not count: err='매물 링크 0개: 실제 빈 결과/지역/권한/페이지 구조 확인 필요'
                    except Exception as e: err=str(e)
                    db.execute('INSERT INTO runs(checked,source,keyword,url,found,error) VALUES(?,?,?,?,?,?)',
                               (now(),s['name'],kw,search,count,err));db.commit()
                    print(s['name'],kw, '발견:',count,err,flush=True)
            # Recheck oldest first. Disappearing from search never implies sold/deleted.
            for row in db.execute('SELECT * FROM items ORDER BY last_checked LIMIT ?',(cfg['recheck_limit'],)).fetchall():
                if row['source'] in sources:
                    targets.setdefault(row['url'],{'source':sources[row['source']],'title':row['title'],'keywords':set()})
            for url,item in targets.items():
                s=item['source']; data={};code=0;snapshot=''
                try:
                    data,code,snapshot=collector.fetch(url,s)
                    state,evidence,price=classify(data,code,data['final_url'],s)
                    title=data.get('title') if data.get('h1') else item['title']
                    # Verify discovered image links against title before including.
                    if item['keywords'] and not any(k.casefold() in (title or '').casefold() for k in item['keywords']):
                        evidence='검색어와 상세 제목 불일치; '+evidence
                        state='unknown'
                except Exception as e:
                    state,evidence,price,title='unknown','확인 실패: '+str(e),None,item['title']
                record(db,url,s['name'],title,None,state,evidence,price,snapshot,code)
                print(LABELS[state], title or url,flush=True)
        finally: context.close()
    export(db,out,cfg)

def selftest():
    import tempfile
    import unittest
    class Tests(unittest.TestCase):
        def setUp(self):
            self.s={'allowed_hosts':['shop.test'],'item_url_regex':r'/product/\d+'}
            self.u='https://shop.test/product/1'
        def check(self,d,code=200):return classify(d,code,self.u,self.s)[0]
        def test_access_and_absence(self):
            for code in (403,429,500):self.assertEqual(self.check({'labels':['판매중']},code),'unknown')
            self.assertEqual(self.check({},404),'removed')
            self.assertEqual(self.check({'body':'추천상품 판매완료\n판매완료 아님'}),'unknown')
            self.assertEqual(self.check({'body':'로그인이 필요합니다','labels':['판매중']}),'unknown')
        def test_labels(self):
            for label,status in EXACT.items():self.assertEqual(self.check({'labels':[label]}),status)
            self.assertEqual(self.check({'labels':['판매중','판매완료']}),'unknown')
        def test_structured_identity(self):
            p={'@type':'Product','url':self.u,'offers':{'availability':'https://schema.org/InStock','price':'1000'}}
            self.assertEqual(self.check({'structured':[p]}),'available')
            p['url']='https://shop.test/product/2'
            self.assertEqual(self.check({'structured':[p]}),'unknown')
            self.assertEqual(self.check({'structured':[{'@type':'ItemList','itemListElement':[p]}]}),'unknown')
        def test_recovery_history_and_export(self):
            with tempfile.TemporaryDirectory() as t:
                db=database(Path(t)/'test.db')
                for st in ('available','unknown','available','sold'):
                    record(db,self.u,'test','상품','키워드',st,'evidence',100,'',200)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM changes').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM observations').fetchone()[0],4)
                export(db,Path(t),DEFAULT)
                self.assertTrue((Path(t)/'all_items.csv').exists());db.close()
        def test_cafe_and_host(self):
            self.assertNotEqual(canonical('https://cafe.naver.com/ArticleRead.nhn?articleid=1'),canonical('https://cafe.naver.com/ArticleRead.nhn?articleid=2'))
            self.assertFalse(allowed('https://shop.test.evil/product/1',self.s))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    raise SystemExit(0 if result.wasSuccessful() else 1)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=['init','login','run','export','selftest'])
    ap.add_argument('--config',default='config.json')
    args=ap.parse_args()
    if args.command=='selftest': selftest()
    cp=Path(args.config)
    if args.command=='init':
        if cp.exists(): raise SystemExit('기존 설정 파일을 덮어쓰지 않았습니다: '+str(cp))
        cp.write_text(json.dumps(DEFAULT,ensure_ascii=False,indent=2),encoding='utf-8')
        print('생성:',cp,'— keywords, 당근 region, 카페/쇼핑몰 URL을 수정하세요.');return
    cfg=json.loads(cp.read_text(encoding='utf-8'))
    if args.command=='login':
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(str(Path(cfg['profile_dir']).resolve()),headless=False)
            try:
                for s in cfg['sources']:
                    if s.get('enabled'):
                        ctx.new_page().goto('https://'+s['allowed_hosts'][0],wait_until='domcontentloaded')
                input('열린 브라우저에서 직접 로그인/지역 설정 후 여기서 Enter: ')
            finally: ctx.close()
        return
    out=Path(cfg['data_dir']);out.mkdir(parents=True,exist_ok=True)
    (out/'snapshots').mkdir(exist_ok=True)
    db=database(out/'items.sqlite3')
    try:
        if args.command=='run': run(cfg,db,out)
        else: export(db,out,cfg)
    finally: db.close()

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,json.JSONDecodeError) as e: raise SystemExit('설정 오류: '+str(e))
