from backend.db.session import SessionLocal
from backend.services import auth_service
from backend.models.user import User

def create_admin_account():
    db = SessionLocal()
    try:
        # 1. admin 계정이 있는지 확인
        user = db.query(User).filter(User.email == "admin").first()
        
        if not user:
            # 2. 계정이 없으면 일반 회원가입 로직으로 먼저 생성 (비밀번호 자동 암호화)
            auth_service.signup(db, email="admin", password="1234", name="관리자")
            user = db.query(User).filter(User.email == "admin").first()
            
        # 3. 관리자 권한 및 프리미엄 등급 강제 부여
        user.role = "admin"
        user.tier = "premium"
        user.status = "active"
        
        db.commit()
        print("관리자(admin) 계정 셋팅이 완료되었습니다.")
        
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_account()