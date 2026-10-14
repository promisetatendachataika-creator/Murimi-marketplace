/* Set the colour theme before the page paints, so it never flashes.
   (An outside file, not inline, so the page can forbid inline scripts: see core/security.py.) */
try { var t = localStorage.getItem("murimi-theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
