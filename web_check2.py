"""验证打包好的题库网页：六科切换、公式、图片、答案标记、控制台错误。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = Path(r"C:/Users/wizar/Downloads/RV-Questionbank-Web/index.html").as_uri()
OUT = Path("web/_check2")


def main():
    OUT.mkdir(exist_ok=True)
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

        page.goto(PAGE, wait_until="load", timeout=120000)
        page.wait_for_timeout(4000)

        subs = page.evaluate("() => [...document.querySelectorAll('#subjects button')].map(b => b.textContent)")
        print("科目按钮:", subs)

        total = page.evaluate("() => document.querySelector('.position')?.textContent")
        print("初始位置:", total)

        for idx, name in enumerate(subs):
            page.evaluate(f"() => document.querySelectorAll('#subjects button')[{idx}].click()")
            page.wait_for_timeout(1500)

            info = page.evaluate("""() => {
                const links = [...document.querySelectorAll('.qlist a')];
                const first = links[0];
                if (first) first.click();
                return {links: links.length};
            }""")
            page.wait_for_timeout(800)

            detail = page.evaluate("""() => {
                const imgs = [...document.querySelectorAll('#content img')];
                return {
                    ref: document.querySelector('.qref')?.textContent,
                    position: document.querySelector('.position')?.textContent,
                    katex: document.querySelectorAll('.katex').length,
                    katexErr: document.querySelectorAll('.katex-err').length,
                    imgs: imgs.length,
                    broken: imgs.filter(i => !i.complete || i.naturalWidth === 0).length,
                    bodyLen: document.querySelector('#questionCard .md')?.innerText.length || 0,
                };
            }""")

            # 展开答案
            page.click("#toggleMS")
            page.wait_for_timeout(700)
            ms = page.evaluate("""() => ({
                len: document.querySelector('#markSchemeCard .md')?.innerText.length || 0,
                imgs: document.querySelectorAll('#markSchemeCard img').length,
                broken: [...document.querySelectorAll('#markSchemeCard img')]
                          .filter(i => !i.complete || i.naturalWidth === 0).length,
            })""")
            page.click("#toggleMS")
            page.wait_for_timeout(300)

            status = "OK"
            if detail["katexErr"] or detail["broken"] or ms["broken"]:
                status = "!! 检查"
            print(f"  {name:<14} 题号 {str(detail['ref']):<8} {str(detail['position']):<12} "
                  f"公式 {detail['katex']:>3} 图 {detail['imgs']:>2}/{detail['broken']} "
                  f"答案 {ms['len']:>5}字 {ms['imgs']:>2}/{ms['broken']}  {status}")

            if idx == 3:
                page.screenshot(path=str(OUT / f"subject{idx}.png"))

        # 物理科目截一张（有选择题答案标记）
        for idx, name in enumerate(subs):
            if "Physics" in name:
                page.evaluate(f"() => document.querySelectorAll('#subjects button')[{idx}].click()")
                page.wait_for_timeout(1200)
                page.evaluate("() => document.querySelectorAll('.qlist a')[0].click()")
                page.wait_for_timeout(1000)
                page.click("#toggleMS")
                page.wait_for_timeout(1200)
                page.screenshot(path=str(OUT / "physics.png"), full_page=False)
                ans = page.evaluate("""() => {
                    const t = document.querySelector('#markSchemeCard .md')?.innerText || '';
                    const m = t.match(/答案[:：]\\s*[A-D]/g);
                    return m ? m.slice(0, 3) : [];
                }""")
                print("  物理答案标记样例:", ans)
                break

        browser.close()

    print("\n控制台错误:", errors[:5] if errors else "无")
    print("截图:", OUT.resolve())
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
