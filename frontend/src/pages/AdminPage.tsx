import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { adminApi, type AdminUser } from "../api/adminApi";
import { createPortal } from "react-dom";
import { useAuthStore } from "../store/authStore";
import { ROUTES } from "../constants/routes";
import { authApi } from "../api/authApi";
import "./AdminPage.scss";

export const AdminPage = () => {
  const navigate = useNavigate();
  const { user, clearAuth } = useAuthStore();

  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [activeMenu, setActiveMenu] = useState("회원 관리");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedTierUser, setSelectedTierUser] = useState<string>("");
  const [selectedTier, setSelectedTier] = useState<string>("normal");
  const [selectedStatusUser, setSelectedStatusUser] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("active");
  const [selectedRoleUser, setSelectedRoleUser] = useState<string>("");

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getUsers();
      if (Array.isArray(data)) {
        setUsers(data);
        if (data.length > 0) {
          const firstUserId = String(data[0].id);
          setSelectedTierUser(firstUserId);
          setSelectedStatusUser(firstUserId);
          setSelectedRoleUser(firstUserId);
        }
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role !== "admin") {
      alert("관리자 권한이 없습니다.");
      navigate(ROUTES.HOME);
      return;
    }
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleUpdate = async (type: string) => {
    try {
      let sql = "";
      let args: any[] = [];

      if (type === "tier") {
        sql = "UPDATE users SET tier = %s WHERE id = %s";
        args = [selectedTier, parseInt(selectedTierUser)];
      } else if (type === "status") {
        sql = "UPDATE users SET status = %s WHERE id = %s";
        args = [selectedStatus, parseInt(selectedStatusUser)];
      } else if (type === "grant_admin") {
        sql = "UPDATE users SET role = 'admin' WHERE id = %s";
        args = [parseInt(selectedRoleUser)];
      } else if (type === "revoke_admin") {
        sql = "UPDATE users SET role = 'user' WHERE id = %s";
        args = [parseInt(selectedRoleUser)];
      }

      const res = await adminApi.updateUser(sql, args);
      if (res.result === "SUCCESS") {
        alert("성공적으로 변경되었습니다.");
        fetchUsers();
      } else {
        alert(`변경 실패: ${res.result}`);
      }
    } catch (error) {
      console.error(error);
      alert("서버 통신 오류가 발생했습니다.");
    }
  };

  const activeUsers = users.filter(
    (u) => u.status !== "withdrawn" && u.status !== "dormant",
  ).length;
  const plusUsers = users.filter((u) => u.tier === "premium").length;

  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const executeLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error(error);
    } finally {
      setShowLogoutModal(false);
      clearAuth();
      navigate(ROUTES.AUTH);
    }
  };

  return (
    <div className="admin-layout">
      <header className="admin-header">
        <div className="logo-area" onClick={() => navigate(ROUTES.HOME)}>
          <span className="logo-text">
            AI<span>WORK</span>
          </span>
          <span className="logo-sub">관리자 대시보드</span>
        </div>
        <div className="user-area">
          <span>{user?.name || "admin"} 님 </span>
          <button className="btn-admin-logout" onClick={handleLogoutClick}>
            로그아웃
          </button>
        </div>
      </header>

      <div className="admin-container">
        <aside className="admin-sidebar">
          <div className="menu-label">메뉴</div>
          <button
            className={`menu-btn ${activeMenu === "회원 관리" ? "active" : ""}`}
            onClick={() => setActiveMenu("회원 관리")}
          >
            회원 관리
          </button>
          <button
            className={`menu-btn ${activeMenu === "서비스 설정" ? "active" : ""}`}
            onClick={() => setActiveMenu("서비스 설정")}
          >
            서비스 설정
          </button>
        </aside>

        <main className="admin-main">
          {activeMenu === "회원 관리" ? (
            <>
              <div className="page-header">
                <h2>회원 관리</h2>
                <p>AIWORK 서비스 사용자 목록을 확인하고 관리합니다.</p>
              </div>

              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-label">전체 회원</span>
                  <div className="stat-value">
                    {users.length} <span className="unit">명</span>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-label">활성 회원</span>
                  <div className="stat-value active">
                    {activeUsers} <span className="unit">명</span>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-label">PREMIUM 회원</span>
                  <div className="stat-value plus">
                    {plusUsers} <span className="unit">명</span>
                  </div>
                </div>
              </div>

              <div className="admin-section">
                <div className="section-header">
                  <h3>전체 사용자 목록</h3>
                  <button className="btn-refresh" onClick={fetchUsers}>
                    새로고침
                  </button>
                </div>
                <div className="table-wrapper">
                  {loading ? (
                    <div className="loading">데이터를 불러오는 중입니다...</div>
                  ) : (
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>id</th>
                          <th>status</th>
                          <th>email</th>
                          <th>name</th>
                          <th>password</th>
                          <th>role</th>
                          <th>tier</th>
                          <th>provider</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((u) => (
                          <tr key={u.id}>
                            <td>{u.id}</td>
                            <td>{u.status}</td>
                            <td>{u.email}</td>
                            <td>{u.name}</td>
                            <td className="masked">
                              {u.password ? "********" : "None"}
                            </td>
                            <td>{u.role}</td>
                            <td>{u.tier}</td>
                            <td>{u.provider || "None"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              <div className="admin-section control-panel">
                <h3>회원 정보 수정</h3>
                <div className="control-grid">
                  <div className="control-box">
                    <h4>회원 등급 변경</h4>
                    <select
                      value={selectedTierUser}
                      onChange={(e) => setSelectedTierUser(e.target.value)}
                    >
                      {users.map((u) => (
                        <option key={`t-${u.id}`} value={u.id}>
                          {u.id}: {u.name || u.email}
                        </option>
                      ))}
                    </select>
                    <select
                      value={selectedTier}
                      onChange={(e) => setSelectedTier(e.target.value)}
                    >
                      <option value="normal">normal</option>
                      <option value="premium">premium</option>
                    </select>
                    <button
                      className="btn-primary full"
                      onClick={() => handleUpdate("tier")}
                    >
                      등급 변경 적용
                    </button>
                  </div>

                  <div className="control-box">
                    <h4>계정 상태 관리</h4>
                    <select
                      value={selectedStatusUser}
                      onChange={(e) => setSelectedStatusUser(e.target.value)}
                    >
                      {users.map((u) => (
                        <option key={`s-${u.id}`} value={u.id}>
                          {u.id}: {u.name || u.email}
                        </option>
                      ))}
                    </select>
                    <select
                      value={selectedStatus}
                      onChange={(e) => setSelectedStatus(e.target.value)}
                    >
                      <option value="active">정상 (active)</option>
                      <option value="dormant">휴면 계정 (dormant)</option>
                      <option value="withdrawn">탈퇴 처리 (withdrawn)</option>
                    </select>
                    <button
                      className="btn-primary full"
                      onClick={() => handleUpdate("status")}
                    >
                      상태 변경 적용
                    </button>
                  </div>
                </div>

                <div className="divider" />

                <div className="admin-role-box">
                  <h4>관리자 권한 관리</h4>
                  <p className="current-admins">
                    현재 관리자:{" "}
                    <strong>
                      {users
                        .filter((u) => u.role === "admin")
                        .map((u) => u.name || u.email)
                        .join(", ")}
                    </strong>
                  </p>
                  <div className="role-actions">
                    <select
                      value={selectedRoleUser}
                      onChange={(e) => setSelectedRoleUser(e.target.value)}
                    >
                      {users.map((u) => (
                        <option key={`r-${u.id}`} value={u.id}>
                          {u.id}: {u.name || u.email} [{u.role}]
                        </option>
                      ))}
                    </select>
                    <button
                      className="btn-primary"
                      onClick={() => handleUpdate("grant_admin")}
                    >
                      관리자 부여
                    </button>
                    <button
                      className="btn-outline"
                      onClick={() => handleUpdate("revoke_admin")}
                    >
                      권한 해제
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <h2>서비스 설정</h2>
              <p>준비 중인 기능입니다.</p>
            </div>
          )}
        </main>
      </div>

      {showLogoutModal &&
        createPortal(
          <div
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15,23,42,0.6)",
              backdropFilter: "blur(4px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 9999,
            }}
          >
            <div
              style={{
                background: "#ffffff",
                padding: "32px",
                borderRadius: "20px",
                width: "90%",
                maxWidth: "360px",
                textAlign: "center",
                boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)",
              }}
            >
              <h3
                style={{
                  margin: "0 0 12px 0",
                  fontSize: "20px",
                  fontWeight: "800",
                  color: "#1e293b",
                }}
              >
                로그아웃 하시겠습니까?
              </h3>
              <p
                style={{
                  margin: "0 0 24px 0",
                  fontSize: "14px",
                  color: "#64748b",
                }}
              >
                관리자 세션이 종료되며
                <br />
                로그인 화면으로 이동합니다.
              </p>
              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  onClick={() => setShowLogoutModal(false)}
                  style={{
                    flex: 1,
                    padding: "12px",
                    borderRadius: "12px",
                    border: "1px solid #e2e8f0",
                    background: "#ffffff",
                    color: "#475569",
                    fontWeight: "700",
                    cursor: "pointer",
                  }}
                >
                  취소
                </button>
                <button
                  onClick={executeLogout}
                  style={{
                    flex: 1,
                    padding: "12px",
                    borderRadius: "12px",
                    border: "none",
                    background: "#0176f7",
                    color: "#ffffff",
                    fontWeight: "700",
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(1, 118, 247, 0.3)",
                  }}
                >
                  확인
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};
