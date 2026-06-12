/*
 * Skincare AI Agent — embeddable chat widget for ANY website.
 *
 * Works on regular (non-Shopify) websites: plain HTML sites, WordPress,
 * Wix, Webflow, custom domains, etc. It injects a floating launcher button
 * that opens the AI advisor in an iframe, so there are no CORS issues and no
 * build step required on the host site.
 *
 * USAGE — paste this single line before </body>, replacing the data values:
 *
 *   <script
 *     src="https://skincare-frontend-z72h.onrender.com/widget/chat-widget.js"
 *     data-store-id="4"
 *     data-app-url="https://skincare-frontend-z72h.onrender.com"
 *     data-accent="#ec4899"
 *     data-title="Beauty Advisor"
 *     defer
 *   ></script>
 *
 * data-store-id  (required) the site ID from your AI dashboard
 * data-app-url   (optional) base URL of the AI app; defaults to the script origin
 * data-accent    (optional) launcher button color (default #ec4899)
 * data-title     (optional) iframe accessibility title
 * data-position  (optional) "right" (default) or "left"
 */
(function () {
  'use strict';

  if (window.__skincareAiWidgetLoaded) return;
  window.__skincareAiWidgetLoaded = true;

  var script = document.currentScript;
  if (!script) {
    var scripts = document.getElementsByTagName('script');
    script = scripts[scripts.length - 1];
  }

  var storeId = script.getAttribute('data-store-id') || '1';
  var appUrl = (script.getAttribute('data-app-url') || new URL(script.src).origin).replace(/\/$/, '');
  var accent = script.getAttribute('data-accent') || '#ec4899';
  var title = script.getAttribute('data-title') || 'Beauty AI advisor';
  var side = script.getAttribute('data-position') === 'left' ? 'left' : 'right';

  function build() {
    var root = document.createElement('div');
    root.id = 'skincare-ai-chat-root';
    root.setAttribute('aria-live', 'polite');

    var launcher = document.createElement('button');
    launcher.id = 'skincare-ai-chat-launcher';
    launcher.type = 'button';
    launcher.setAttribute('aria-label', 'Open beauty advisor chat');
    launcher.setAttribute('aria-expanded', 'false');
    launcher.textContent = '\u2726';
    launcher.style.cssText =
      'position:fixed;' + side + ':20px;bottom:20px;z-index:99998;width:56px;height:56px;' +
      'border:none;border-radius:9999px;background:' + accent + ';color:#fff;font-size:24px;' +
      'line-height:1;cursor:pointer;box-shadow:0 12px 30px rgba(15,23,42,0.35);';

    var panel = document.createElement('div');
    panel.id = 'skincare-ai-chat-panel';
    panel.hidden = true;
    panel.style.cssText =
      'position:fixed;' + side + ':20px;bottom:88px;z-index:99999;' +
      'width:min(400px,calc(100vw - 32px));height:min(620px,calc(100vh - 120px));' +
      'border-radius:20px;overflow:hidden;box-shadow:0 20px 50px rgba(15,23,42,0.35);background:#0f172a;';

    var frame = document.createElement('iframe');
    frame.id = 'skincare-ai-chat-frame';
    frame.title = title;
    frame.src = appUrl + '/embed/chat?store_id=' + encodeURIComponent(storeId);
    frame.setAttribute('loading', 'lazy');
    frame.style.cssText = 'width:100%;height:100%;border:none;';

    panel.appendChild(frame);
    root.appendChild(launcher);
    root.appendChild(panel);
    document.body.appendChild(root);

    function setOpen(open) {
      panel.hidden = !open;
      launcher.setAttribute('aria-expanded', open ? 'true' : 'false');
      launcher.textContent = open ? '\u00d7' : '\u2726';
    }

    launcher.addEventListener('click', function () {
      setOpen(panel.hidden);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !panel.hidden) setOpen(false);
    });
  }

  if (document.body) {
    build();
  } else {
    document.addEventListener('DOMContentLoaded', build);
  }
})();
