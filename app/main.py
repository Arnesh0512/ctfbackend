from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.middleware import OriginGuard
import app.models.admin
import app.models.content
import app.models.game
import app.models.logs
import app.models.progress
import app.models.team
from app.routers.admin import router as admin_router
from app.routers.events import router as events_router
from app.routers.team import router as team_router

SWAGGER_NESTED_ACCORDION_JS = """
<script>
(function() {
  const groupStates = {};

  function setupGroupMinimizer(groupPrefix, groupName) {
    const headers = Array.from(document.querySelectorAll('.opblock-tag'));
    if (!headers.length) return false;

    // Filter headers belonging to this group (data-tag or textContent starting with groupPrefix)
    const matchingHeaders = headers.filter(h => {
      const tag = (h.getAttribute('data-tag') || h.textContent || '').trim();
      return tag.startsWith(groupPrefix);
    });

    if (!matchingHeaders.length) return false;

    // Map each header to its enclosing tag section
    const matchingSections = matchingHeaders.map(h => {
      return h.closest('.opblock-tag-section') || h.closest('span') || h.parentElement;
    }).filter(Boolean);

    const masterId = 'swagger-' + groupName + '-master-header';
    let master = document.getElementById(masterId);
    if (!master && matchingSections.length > 0) {
      if (!(groupName in groupStates)) {
        groupStates[groupName] = false; // false = expanded (not collapsed)
      }

      master = document.createElement('div');
      master.id = masterId;
      master.style.margin = '28px 0 12px 0';
      master.style.padding = '14px 20px';
      master.style.background = '#f1f5f9';
      master.style.border = '1px solid #cbd5e1';
      master.style.borderRadius = '8px';
      master.style.cursor = 'pointer';
      master.style.display = 'flex';
      master.style.justifyContent = 'space-between';
      master.style.alignItems = 'center';
      master.style.userSelect = 'none';

      master.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:22px; font-weight:800; color:#0f172a; letter-spacing:-0.5px;">${groupName}</span>
          <span style="font-size:12px; color:#64748b; background:#e2e8f0; padding:3px 10px; border-radius:12px; font-weight:600;">global minimizer</span>
        </div>
        <div id="swagger-${groupName}-master-arrow" style="font-size:18px; color:#475569; transition:transform 0.25s ease;">&#9660;</div>
      `;

      master.addEventListener('click', () => {
        groupStates[groupName] = !groupStates[groupName];
        const isCollapsed = groupStates[groupName];
        const arrow = document.getElementById(`swagger-${groupName}-master-arrow`);
        if (arrow) arrow.style.transform = isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
        master.style.background = isCollapsed ? '#e2e8f0' : '#f1f5f9';

        matchingSections.forEach(sec => {
          sec.style.display = isCollapsed ? 'none' : '';
        });
      });

      const firstSec = matchingSections[0];
      firstSec.parentNode.insertBefore(master, firstSec);
    }

    // Apply visual indentation and strip prefix from sub-labels
    const isCollapsed = groupStates[groupName] || false;
    matchingHeaders.forEach(h => {
      const label = h.querySelector('a span') || h.querySelector('span') || h;
      if (label && label.childNodes) {
        for (let node of label.childNodes) {
          if (node.nodeType === Node.TEXT_NODE && node.nodeValue.includes(groupPrefix)) {
            node.nodeValue = node.nodeValue.replace(new RegExp('^' + groupPrefix + '\\\\s*'), '').trim();
          }
        }
      }

      const sec = h.closest('.opblock-tag-section') || h.closest('span') || h.parentElement;
      if (sec) {
        sec.style.marginLeft = '20px';
        sec.style.borderLeft = '3px solid #94a3b8';
        sec.style.paddingLeft = '14px';
        if (isCollapsed) {
          sec.style.display = 'none';
        }
      }
    });

    return true;
  }

  function updateAllGroups() {
    setupGroupMinimizer('teams:', 'teams');
    setupGroupMinimizer('admin:', 'admin');
  }

  const timer = setInterval(() => {
    updateAllGroups();
  }, 150);

  setTimeout(() => clearInterval(timer), 8000);

  const observer = new MutationObserver(() => {
    updateAllGroups();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
"""


def create_app() -> FastAPI:
    prefix = settings.api_prefix
    docs = settings.docs_enabled
    app = FastAPI(
        title="MAYASABHA CTF BACKEND",
        docs_url=None,  # Handled via custom endpoint below to inject nested accordion script
        redoc_url=None,
        openapi_url=f"{prefix}/openapi.json" if docs else None,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    if settings.frontend_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.frontend_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["*"],
        )
        app.add_middleware(
            OriginGuard,
            allowed=settings.frontend_origins,
        )

    if docs:
        @app.get(f"{prefix}/docs", include_in_schema=False)
        async def custom_swagger_ui_html() -> HTMLResponse:
            html = get_swagger_ui_html(
                openapi_url=f"{prefix}/openapi.json",
                title=f"{app.title} - Swagger UI",
                swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
                swagger_ui_parameters={"persistAuthorization": True},
            )
            content = html.body.decode("utf-8").replace("</body>", f"{SWAGGER_NESTED_ACCORDION_JS}\n</body>")
            return HTMLResponse(content=content)

    @app.get(f"{prefix}/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "mayasabha-ctf-backend"}

    # Include Participant / Public routers FIRST
    app.include_router(team_router, prefix=prefix)
    app.include_router(events_router, prefix=prefix)

    # Include Admin master router (containing auth, team, game, time, store, file, question, path)
    app.include_router(admin_router, prefix=prefix)

    return app


app = create_app()
