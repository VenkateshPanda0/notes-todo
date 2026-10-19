from starlette.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """Static files with a fallback to index.html for client-side routes.

    Reloading or deep-linking to a route like /notes has no matching file, so serve the app shell
    and let React Router handle it. API paths are excluded so a mistyped endpoint still returns 404.
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise
