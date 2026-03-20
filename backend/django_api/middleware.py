from backend.core.config import settings


class SimpleCORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://192.168.2.1:5173",
            "http://localhost:3000",
            settings.FRONTEND_BASE_URL.rstrip("/"),
        }

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = self._build_preflight_response()
        else:
            response = self.get_response(request)
        return self._add_cors_headers(request, response)

    def _build_preflight_response(self):
        from django.http import HttpResponse

        response = HttpResponse(status=200)
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-CSRF-Token"
        return response

    def _add_cors_headers(self, request, response):
        origin = request.headers.get("Origin")
        if origin in self.allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Vary"] = "Origin"
        return response
