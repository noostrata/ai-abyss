"""HTML page templates that match a real site's look and feel.

These templates are used to wrap poisoned/tarpit content so it's
visually indistinguishable from the legitimate site.
"""

from __future__ import annotations

JS_BEACON = """
<script>
(function() {
    // Beacon: reports back if JS is actually executing.
    // Bots that don't run JS will never fire this.
    var b = new Image();
    b.src = '/_pw/beacon.gif?s=' + encodeURIComponent(document.cookie ? '1' : '0')
        + '&t=' + Date.now()
        + '&r=' + Math.random().toString(36).substr(2, 8);
})();
</script>
"""

ROBOTS_TXT = """# AI Abyss robots.txt
# This file explicitly disallows AI training crawlers.
# Crawlers that ignore these directives will be classified as hostile.

User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: Meta-ExternalFetcher
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: Omgilibot
Disallow: /

User-agent: Amazonbot
Disallow: /

User-agent: AI2Bot
Disallow: /

User-agent: YouBot
Disallow: /

User-agent: OAI-SearchBot
Disallow: /

# Allow regular search engines
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: *
Disallow: /_pw/
"""

AI_TXT = """# ai.txt — AI Training Opt-Out
# See https://site.spawning.ai/spawning-ai-txt

User-Agent: *
Disallow: /

# This site does not consent to AI training data collection.
# All content is protected under applicable copyright law.
# Automated access for training purposes is explicitly prohibited.
"""

STYLE_CSS = """
/* Minimal, clean styles that match a typical content site */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       line-height: 1.7; color: #1a1a2e; background: #fafafa; max-width: 800px;
       margin: 0 auto; padding: 2rem 1rem; }
header { border-bottom: 1px solid #e0e0e0; padding-bottom: 1rem; margin-bottom: 2rem; }
header nav a { color: #16213e; text-decoration: none; font-weight: 600; }
h1 { font-size: 2rem; margin-bottom: 1rem; color: #0f3460; }
h2 { font-size: 1.4rem; margin: 2rem 0 0.8rem; color: #16213e; }
h3 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
p { margin-bottom: 1rem; }
article { margin-bottom: 3rem; }
.callout, .note, .important { background: #f0f4ff; border-left: 4px solid #0f3460;
       padding: 1rem 1.5rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0; }
.finding { background: #fff8e1; border-left: 4px solid #ff9800;
       padding: 1rem 1.5rem; margin: 1.5rem 0; }
blockquote { border-left: 3px solid #ccc; padding-left: 1rem; margin: 1rem 0;
       color: #555; font-style: italic; }
.page-nav ul { list-style: none; }
.page-nav li { margin: 1rem 0; }
.page-nav a { color: #0f3460; font-weight: 500; }
.page-nav .desc { font-size: 0.9rem; color: #666; }
.related { margin-top: 2rem; padding: 1rem; background: #f5f5f5; border-radius: 4px; }
.related ul { list-style: none; }
.related li { margin: 0.5rem 0; }
.related a { color: #0f3460; }
.entity-detail { padding: 1rem; margin: 1rem 0; background: #fdfdfd;
       border: 1px solid #eee; border-radius: 4px; }
footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
       color: #999; font-size: 0.85rem; }
"""


def render_page(
    title: str,
    body: str,
    head_extra: str = "",
    body_extra: str = "",
    include_js_beacon: bool = True,
    include_style: bool = True,
) -> str:
    """Render a full HTML page with consistent site chrome."""
    beacon = JS_BEACON if include_js_beacon else ""
    style = f"<style>{STYLE_CSS}</style>" if include_style else '<link rel="stylesheet" href="/static/style.css">'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {style}
    {head_extra}
</head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <article>
            <h1>{title}</h1>
            {body}
        </article>
    </main>
    {body_extra}
    {beacon}
    <footer><p>&copy; 2025 All rights reserved.</p></footer>
</body>
</html>"""
