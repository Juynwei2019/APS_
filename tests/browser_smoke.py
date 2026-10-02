"""Optional: python tests/browser_smoke.py (requires Playwright and Chromium)."""
import os
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from playwright.sync_api import sync_playwright

with tempfile.TemporaryDirectory() as folder:
    app.DB = Path(folder) / 'data' / 'aps.db'
    app.initialize()
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('APS_CHROMIUM', '/usr/bin/chromium'), headless=True)
            page = browser.new_page(viewport={'width':1440, 'height':1000})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.get_by_role('button', name='產生排程 →').click()
            page.locator('#results').wait_for(state='visible')
            assert page.locator('#operations tbody tr').count() == 4
            assert page.locator('.bar').count() == 4
            page.get_by_role('button', name='生產訂單', exact=True).click()
            page.locator('[data-key="quantity"]').first.fill('0')
            page.get_by_role('button', name='儲存資料', exact=True).click()
            page.wait_for_function("document.querySelector('#message').classList.contains('error')")
            assert '數量' in page.locator('#message').inner_text()
            page.locator('[data-key="quantity"]').first.fill('3')
            page.get_by_role('button', name='儲存資料', exact=True).click()
            page.wait_for_function("document.querySelector('#message').textContent.includes('已儲存')")
            page.reload()
            page.get_by_role('button', name='生產訂單', exact=True).click()
            assert page.locator('[data-key="quantity"]').first.input_value() == '3'
            page.get_by_role('button', name='產生排程 →').click()
            page.locator('#results').wait_for(state='visible')
            page.screenshot(path='/tmp/aps-desktop.png', full_page=True)
            page.set_viewport_size({'width':390, 'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors, errors
            browser.close()
            print('PASS: schedule, Gantt, validation, save/reload, mobile layout, no JS errors')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
