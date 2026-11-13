"""Anonymous verification of the deployed static site; no login or stored profile."""
import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
URL=sys.argv[1] if len(sys.argv)>1 else 'https://coursejesus-accessbridge.netlify.app'
out=ROOT/'evidence/public'
out.mkdir(parents=True,exist_ok=True)
checks=[]
with sync_playwright() as p:
    chrome=Path(os.environ.get('CHROME_PATH',r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
    browser=p.chromium.launch(executable_path=str(chrome) if chrome.exists() else None,headless=True)
    context=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
    page=context.new_page(); page.set_default_navigation_timeout(90000)
    errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
    assert page.goto(URL,wait_until='load').status==200
    assert page.locator('.lesson-card').count()==3
    page.screenshot(path=str(out/'index.png'))
    checks.append('anonymous_index_three_lessons')
    for slug in ['stack-queue','bfs-dfs','matrix-transform']:
        assert page.goto(URL+'/lessons/'+slug+'.html',wait_until='load').status==200
        assert page.locator('.quiz-question').count()==3
        page.locator('#toggle-language').focus();page.keyboard.press('Enter')
        assert page.locator('html').get_attribute('lang')=='zh-CN'
        page.locator('#toggle-size').focus();page.keyboard.press('Space')
        assert page.locator('#toggle-size').get_attribute('aria-pressed')=='true'
        for field in page.locator('.quiz-question').all():
            answer=field.locator('.quiz-feedback').get_attribute('data-answer')
            field.locator('input[value="'+answer+'"]').check()
            field.locator('button').click()
            assert '正确' in field.locator('.quiz-feedback').inner_text()
        page.locator('section[aria-labelledby="sources"] summary').first.click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/(slug+'-mobile.png')),full_page=True)
        page.set_viewport_size({'width':640,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.add_script_tag(path=str(ROOT/'tests/vendor/axe.min.js'))
        violations=page.evaluate('async()=> (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})).violations')
        assert not violations,[(v['id'],v['impact']) for v in violations]
        with page.expect_download() as info: page.locator('a[download]').click()
        saved=out/(slug+'-download.html');info.value.save_as(saved)
        assert saved.read_bytes()==(ROOT/'app/dist/offline'/(slug+'.html')).read_bytes()
        context.set_offline(True)
        offline=context.new_page();offline.goto(saved.as_uri(),wait_until='load')
        assert offline.locator('.question').count()==3
        offline.locator('.question input').first.check()
        offline.locator('.question button').first.click()
        assert offline.locator('.feedback').first.inner_text()
        offline.close();context.set_offline(False)
        checks.append(slug+': language, large text, keyboard, 3 correct answers, source, 390px, 640px, axe, download, offline file practice')
        page.set_viewport_size({'width':1280,'height':900})
    assert not errors,errors
    browser.close()
(out/'checks.json').write_text(json.dumps({'status':'VERIFIED_LIVE','url':URL,'checks':checks,'page_errors':errors,'axe_violations':0,'authenticated':False},indent=2),encoding='utf-8')
print('VERIFIED_LIVE: anonymous three-lesson flow, actual downloads and disconnected file practice')
