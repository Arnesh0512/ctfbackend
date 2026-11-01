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
from app.routers.file import router as file_router
from app.routers.game import router as game_router
from app.routers.path import router as path_router
from app.routers.question import router as question_router
from app.routers.store import router as store_router
from app.routers.teams import router as teams_router
from app.routers.time import router as time_router

SWAGGER_NESTED_ACCORDION_JS = """
<script>
(function() {
  function setupAdminNestedGroups() {
    const sections = Array.from(document.querySelectorAll('.opblock-tag-section'));
    if (!sections.length) return false;
    if (document.getElementById('admin-master-group')) return true;

    // Filter all sections whose tag starts with "admin:"
    const adminSections = sections.filter(sec => {
      const btn = sec.querySelector('h4.opblock-tag');
      const text = btn ? btn.innerText.trim() : '';
      return text.startsWith('admin:');
    });

    if (!adminSections.length) return false;

    // Create the outer admin master accordion container
    const master = document.createElement('div');
    master.id = 'admin-master-group';
    master.className = 'opblock-tag-section is-open';
    master.style.border = '1px solid #cbd5e1';
    master.style.borderRadius = '8px';
    master.style.marginBottom = '20px';
    master.style.backgroundColor = '#f8fafc';
    master.style.overflow = 'hidden';

    // Header
    const header = document.createElement('h4');
    header.className = 'opblock-tag';
    header.style.cursor = 'pointer';
    header.style.margin = '0';
    header.style.padding = '14px 20px';
    header.style.backgroundColor = '#f1f5f9';
    header.style.borderBottom = '1px solid #cbd5e1';
    header.style.display = 'flex';
    header.style.justifyContent = 'space-between';
    header.style.alignItems = 'center';

    header.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:18px; font-weight:700; color:#0f172a; text-transform:none;">admin</span>
      </div>
      <button type="button" class="expand-operation" style="background:none; border:none; cursor:pointer;" title="Expand/Collapse admin">
        <svg width="20" height="20" viewBox="0 0 20 20" style="transition:transform 0.2s ease;">
          <path d="M5 7.5L10 12.5L15 7.5" fill="none" stroke="#475569" stroke-width="2.5" stroke-linecap="round"/>
        </svg>
      </button>
    `;

    // Body containing sub-minimizers
    const body = document.createElement('div');
    body.id = 'admin-master-body';
    body.style.padding = '10px 16px';
    body.style.display = 'block';

    const firstAdmin = adminSections[0];
    firstAdmin.parentNode.insertBefore(master, firstAdmin);
    master.appendChild(header);
    master.appendChild(body);

    let isOpen = true;
    const arrow = header.querySelector('svg');
    header.addEventListener('click', () => {
      isOpen = !isOpen;
      body.style.display = isOpen ? 'block' : 'none';
      header.style.borderBottom = isOpen ? '1px solid #cbd5e1' : 'none';
      arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(-90deg)';
    });

    // Move each admin section into body and rename the visible label
    adminSections.forEach(sec => {
      const label = sec.querySelector('h4.opblock-tag a span, h4.opblock-tag span');
      if (label) {
        const full = label.innerText.trim();
        if (full.startsWith('admin:')) {
          label.innerText = full.replace(/^admin:\s*/, '').trim();
        }
      }
      sec.style.margin = '8px 0';
      sec.style.backgroundColor = '#ffffff';
      sec.style.border = '1px solid #e2e8f0';
      sec.style.borderRadius = '6px';
      body.appendChild(sec);
    });

    return true;
  }

  // Poll until Swagger UI finishes rendering initial DOM
  const timer = setInterval(() => {
    if (setupAdminNestedGroups()) {
      clearInterval(timer);
    }
  }, 100);

  // Watch for DOM changes (search, filter, re-renders)
  const observer = new MutationObserver(() => {
    if (!document.getElementById('admin-master-group')) {
      setupAdminNestedGroups();
    }
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

    # Include Admin, Teams, Events, Game, Time, Store, File, Question, and Path routers
    app.include_router(admin_router, prefix=prefix)
    app.include_router(teams_router, prefix=prefix)
    app.include_router(events_router, prefix=prefix)
    app.include_router(game_router, prefix=prefix)
    app.include_router(time_router, prefix=prefix)
    app.include_router(store_router, prefix=prefix)
    app.include_router(file_router, prefix=prefix)
    app.include_router(question_router, prefix=prefix)
    app.include_router(path_router, prefix=prefix)

    return app


app = create_app()
