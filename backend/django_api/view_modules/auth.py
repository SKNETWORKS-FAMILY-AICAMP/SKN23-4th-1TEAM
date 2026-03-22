from .shared import *  # noqa: F401,F403


@api_view(["POST"])
def auth_signup(request):
    body = json_body(request)
    with db_session() as db:
        try:
            auth_service.signup(db, body["email"], body["password"], body.get("name"))
        except KeyError as exc:
            raise ApiError(f"missing field: {exc.args[0]}", 422) from exc
        except ValueError as exc:
            raise ApiError(str(exc), 400) from exc
    return {"ok": True}


@api_view(["GET"])
def auth_check_email(request):
    email = request.GET.get("email", "")
    with db_session() as db:
        return {"exists": auth_service.check_user_exists(db, email)}


@api_view(["POST"])
def auth_send_signup_email(request):
    body = json_body(request)
    with db_session() as db:
        if auth_service.check_user_exists(db, body["email"]):
            raise ApiError("이미 가입한 이메일입니다.", 400)
    ok, error_msg = auth_service.send_auth_email(body["email"], body["auth_code"])
    if not ok:
        raise ApiError(error_msg, 500)
    return {"message": "인증번호 발송 성공"}


@api_view(["POST"])
def auth_login(request):
    body = json_body(request)
    with db_session() as db:
        try:
            access, refresh, user_id = auth_service.login(
                db,
                body["email"],
                body["password"],
            )
        except ValueError as exc:
            raise ApiError("이메일 또는 비밀번호가 일치하지 않습니다.", 401) from exc
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ApiError("사용자를 찾을 수 없습니다.", 404)
        _ensure_active_user(user)
        csrf = fresh_csrf_token()
        response = json_response(_user_payload(user, access, refresh, csrf))
        issue_cookie_token_response(response, refresh_token=refresh, csrf_token=csrf)
        return response


@api_view(["POST"])
def auth_logout(request):
    require_csrf(request)
    refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    with db_session() as db:
        if refresh_token:
            auth_service.revoke_refresh(db, refresh_token)
    response = json_response({"ok": True})
    clear_auth_cookies(response)
    return response


@api_view(["POST"])
def auth_refresh(request):
    body = json_body(request) if request.body else {}
    refresh_token = body.get("refresh_token") or request.COOKIES.get(
        settings.REFRESH_COOKIE_NAME
    )
    if not refresh_token:
        raise ApiError("유효하지 않은 토큰입니다.", 401)
    if not body.get("refresh_token"):
        require_csrf(request)
    with db_session() as db:
        try:
            new_access, new_refresh = auth_service.rotate_refresh(db, refresh_token)
            user = auth_service.get_user_from_access(db, new_access)
        except Exception as exc:
            raise ApiError("유효하지 않은 토큰입니다.", 401) from exc
        csrf = fresh_csrf_token()
        response = json_response(_user_payload(user, new_access, new_refresh, csrf))
        issue_cookie_token_response(
            response,
            refresh_token=new_refresh,
            csrf_token=csrf,
        )
        return response


@api_view(["GET"])
def auth_me(request):
    with db_session() as db:
        user = get_current_user(request, db)
        return {"id": user.id, "email": user.email, "name": user.name}


@api_view(["GET"])
def auth_verify(request):
    token = get_bearer_token(request)
    if not token:
        raise ApiError("토큰이 없습니다.", 401)
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("sub")
        with db_session() as db:
            user = (
                db.query(User).filter(User.id == int(user_id)).first()
                if user_id
                else None
            )
            if not user:
                raise ApiError("유효하지 않은 인증 정보입니다.", 401)
            return {
                "id": user.id,
                "name": user.name or user.email.split("@")[0],
                "role": getattr(user, "role", "user"),
                "profile_image_url": getattr(user, "profile_image_url", None),
                "email": user.email,
                "tier": getattr(user, "tier", "normal"),
            }
    except ExpiredSignatureError as exc:
        raise ApiError(
            f"{settings.ACCESS_TOKEN_MINUTES}분 동안 활동이 없어 자동 로그아웃 되었습니다.",
            401,
        ) from exc
    except JWTError as exc:
        raise ApiError("유효하지 않은 인증 정보입니다.", 401) from exc


@api_view(["POST"])
def auth_send_reset_email(request):
    body = json_body(request)
    with db_session() as db:
        if not auth_service.check_user_exists(db, body["email"]):
            raise ApiError("가입되지 않은 이메일입니다.", 404)
    ok, error_msg = auth_service.send_auth_email(body["email"], body["auth_code"])
    if not ok:
        raise ApiError(error_msg, 500)
    return {"message": "인증번호 발송 성공"}


@api_view(["POST"])
def auth_reset_password(request):
    body = json_body(request)
    with db_session() as db:
        success, error_msg = auth_service.update_password(
            db,
            body["email"],
            body["new_password"],
        )
        if not success:
            raise ApiError(error_msg, 500)
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


@api_view(["POST"])
def auth_unlock(request):
    body = json_body(request)
    with db_session() as db:
        user = db.query(User).filter(User.email == body["email"]).first()
        if not user:
            raise ApiError("사용자를 찾을 수 없습니다.", 404)
        if getattr(user, "status", "active") != "dormant":
            raise ApiError("휴면 상태의 계정이 아닙니다.", 400)
        user.status = "active"
        db.commit()
    return {"detail": "휴면 해제 완료"}


@api_view(["POST"])
def auth_withdraw(request):
    body = json_body(request)
    with db_session() as db:
        user = db.query(User).filter(User.email == body["email"]).first()
        if not user:
            raise ApiError("사용자를 찾을 수 없습니다.", 404)
        user.status = "withdrawn"
        db.commit()
    return {"detail": "회원 탈퇴가 완료되었습니다."}


@api_view(["POST"])
def auth_profile_image(request):
    file = request.FILES.get("file")
    if not file:
        raise ApiError("file is required", 422)
    with db_session() as db:
        user = get_current_user(request, db)
        upload_dir = os.path.join("static", "profiles")
        os.makedirs(upload_dir, exist_ok=True)
        ext = file.name.split(".")[-1]
        new_filename = f"user_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        file_path = os.path.join(upload_dir, new_filename)
        with open(file_path, "wb") as buffer:
            for chunk in file.chunks():
                buffer.write(chunk)
        image_url = f"{settings.BACKEND_BASE_URL}/static/profiles/{new_filename}"
        user.profile_image_url = image_url
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"profile_image_url": user.profile_image_url}


@api_view(["POST"])
def auth_upgrade(request):
    with db_session() as db:
        user = get_current_user(request, db)
        if getattr(user, "tier", "normal") == "premium":
            return {"detail": "이미 프리미엄 등급입니다.", "tier": "premium"}
        user.tier = "premium"
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"detail": "등급 업그레이드가 완료되었습니다.", "tier": user.tier}


@api_view(["GET"])
def social_kakao_start(request):
    state = _create_oauth_state("kakao")
    params = {
        "response_type": "code",
        "client_id": settings.KAKAO_CLIENT_ID,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "state": state,
        "scope": "account_email profile_nickname profile_image",
    }
    return HttpResponseRedirect(
        "https://kauth.kakao.com/oauth/authorize?" + urlencode(params)
    )


@api_view(["GET"])
def social_kakao_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    _validate_oauth_state(state, "kakao")
    access_token = social_service.kakao_exchange_code_for_token(code)
    provider_user_id, email, name, image_url = social_service.kakao_fetch_profile(
        access_token
    )
    with db_session() as db:
        user = social_service.get_or_create_social_user(
            db,
            provider="kakao",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            profile_image_url=image_url,
        )
        _ensure_active_user(user)
        our_access, our_refresh = auth_service.issue_tokens_for_user_id(db, user.id)
    csrf = fresh_csrf_token()
    frontend_url = (
        f"{settings.FRONTEND_BASE_URL}/?"
        f"{urlencode({'access_token': our_access, 'social': 'kakao'})}"
    )
    response = HttpResponseRedirect(frontend_url)
    issue_cookie_token_response(response, refresh_token=our_refresh, csrf_token=csrf)
    return response


@api_view(["GET"])
def social_google_start(request):
    state = _create_oauth_state("google")
    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return HttpResponseRedirect(
        "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    )


@api_view(["GET"])
def social_google_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    _validate_oauth_state(state, "google")
    access_token = social_service.google_exchange_code_for_token(code)
    provider_user_id, email, name, image_url = social_service.google_fetch_profile(
        access_token
    )
    with db_session() as db:
        user = social_service.get_or_create_social_user(
            db,
            provider="google",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            profile_image_url=image_url,
        )
        _ensure_active_user(user)
        our_access, our_refresh = auth_service.issue_tokens_for_user_id(db, user.id)
    csrf = fresh_csrf_token()
    frontend_url = (
        f"{settings.FRONTEND_BASE_URL}/?"
        f"{urlencode({'access_token': our_access, 'social': 'google'})}"
    )
    response = HttpResponseRedirect(frontend_url)
    issue_cookie_token_response(response, refresh_token=our_refresh, csrf_token=csrf)
    return response


@api_view(["GET"])
def social_naver_start(request):
    state = _create_oauth_state("naver")
    params = {
        "response_type": "code",
        "client_id": settings.NAVER_CLIENT_ID,
        "redirect_uri": settings.NAVER_REDIRECT_URI,
        "state": state,
    }
    return HttpResponseRedirect(
        "https://nid.naver.com/oauth2.0/authorize?" + urlencode(params)
    )


@api_view(["GET"])
def social_naver_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    _validate_oauth_state(state, "naver")
    access_token = social_service.naver_exchange_code_for_token(code, state=state)
    provider_user_id, email, name = social_service.naver_fetch_profile(access_token)
    with db_session() as db:
        user = social_service.get_or_create_social_user(
            db,
            provider="naver",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
        )
        _ensure_active_user(user)
        our_access, our_refresh = auth_service.issue_tokens_for_user_id(db, user.id)
    csrf = fresh_csrf_token()
    frontend_url = (
        f"{settings.FRONTEND_BASE_URL}/?"
        f"{urlencode({'access_token': our_access, 'social': 'naver'})}"
    )
    response = HttpResponseRedirect(frontend_url)
    issue_cookie_token_response(response, refresh_token=our_refresh, csrf_token=csrf)
    return response
