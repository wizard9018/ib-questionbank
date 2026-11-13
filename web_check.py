"""用浏览器打开生成的网页，截图并检查渲染是否正常（公式/图片/评分标准）。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = Path(r"C:/Users/wizar/Downloads/RV-IB-Math-Web/index.html").as_uri()
OUT = Path("web/_check")


def main():
    OUT.mkdir(exist_ok=True)
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("console", lambda m: errors.append(f"[console.{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

        page.goto(PAGE, wait_until="load", timeout=60000)
        page.wait_for_timeout(2500)

        # 1) 首屏
        page.screenshot(path=str(OUT / "01-first.png"), full_page=False)

        stats = page.evaluate("""() => ({
            qref: document.querySelector('.qref')?.textContent,
            position: document.querySelector('.position')?.textContent,
            katexCount: document.querySelectorAll('.katex').length,
            imgCount: document.querySelectorAll('#content img').length,
            imgBroken: [...document.querySelectorAll('#content img')].filter(i => !i.complete || i.naturalWidth === 0).length,
            sidebarLinks: document.querySelectorAll('.qlist a').length,
            bodyLen: document.querySelector('#content')?.innerText.length,
            katexErr: document.querySelectorAll('.katex-err').length,
        })""")
        print("首屏:", stats)

        # 2) 展开评分标准
        page.click("#toggleMS")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "02-markscheme.png"), full_page=False)
        ms = page.evaluate("""() => ({
            visible: document.getElementById('markSchemeCard').classList.contains('visible'),
            len: document.querySelector('#markSchemeCard .md')?.innerText.length,
            imgs: document.querySelectorAll('#markSchemeCard img').length,
            broken: [...document.querySelectorAll('#markSchemeCard img')].filter(i => !i.complete || i.naturalWidth === 0).length,
        })""")
        print("评分标准:", ms)

        # 3) 跳到带公式/多小问的题，再截一张
        page.evaluate("""() => {
            const links = [...document.querySelectorAll('.qlist a')];
            const target = links.find(a => a.textContent.trim() === 'AA1332') || links[5];
            target.click();
        }""")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "03-another.png"), full_page=False)
        print("第二题:", page.evaluate("() => document.querySelector('.qref')?.textContent"))

        # 4) 走一遍所有题，检查有没有崩的
        bad = page.evaluate("""() => {
            const links = [...document.querySelectorAll('.qlist a')];
            const problems = [];
            for (const a of links) {
                a.click();
                const q = document.querySelector('.qref')?.textContent;
                if (!q) problems.push(a.textContent);
            }
            return {checked: links.length, problems: problems.slice(0, 5)};
        }""")
        print("遍历当前科目:", bad)

        browser.close()

    if errors:
        print("\n控制台错误:")
        for e in errors[:10]:
            print("  ", e)
    else:
        print("\n无控制台错误")
    print(f"截图: {OUT.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
