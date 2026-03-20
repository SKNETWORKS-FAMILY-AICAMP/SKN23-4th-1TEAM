import { useState } from "react";
import { createPortal } from "react-dom";
import { authApi } from "../../api/authApi";
import { X } from "lucide-react";
import "./SignUpForm.scss";

const TERMS_AIWORK = `
제 1 장 총칙

제 1 조 (목적)
본 약관은 AIWORK가 운영하는 AI 모의면접 서비스(이하 "당 사이트")에서 제공하는 모든 서비스(이하 "서비스")의 이용조건 및 절차, 이용자와 당 사이트의 권리, 의무, 책임사항과 기타 필요한 사항을 규정함을 목적으로 합니다.

제 2 조 (약관의 효력과 변경)
① 당 사이트는 이용자가 본 약관 내용에 동의하는 것을 조건으로 이용자에게 서비스를 제공하며, 당 사이트의 서비스 제공 행위 및 이용자의 서비스 사용 행위에는 본 약관을 우선적으로 적용하겠습니다.
② 당 사이트는 본 약관을 사전 고지 없이 변경할 수 있으며, 변경된 약관은 당 사이트 내에 공지함으로써 이용자가 직접 확인하도록 할 것입니다. 이용자가 변경된 약관에 동의하지 아니하는 경우 본인의 회원등록을 취소(회원탈퇴)할 수 있으며, 계속 사용할 경우에는 약관 변경에 대한 암묵적 동의로 간주됩니다. 변경된 약관은 공지와 동시에 그 효력을 발휘합니다.

제 3 조 (약관 외 준칙)
본 약관에 명시되지 않은 사항은 전기통신기본법, 전기통신사업법, 정보통신망 이용촉진 및 정보보호 등에 관한 법률 및 기타 관련 법령의 규정에 의합니다.

제 4 조 (용어의 정의)
① 본 약관에서 사용하는 용어의 정의는 다음과 같습니다.
 1. 이용자 : 본 약관에 따라 당 사이트가 제공하는 서비스를 받는 자
 2. 가 입 : 당 사이트가 제공하는 신청서 양식에 해당 정보를 기입하고, 본 약관에 동의하여 서비스 이용계약을 완료시키는 행위
 3. 회 원 : 당 사이트에 필요한 개인 정보를 제공하여 회원 등록을 한 자로서, 당 사이트의 정보 및 서비스를 이용할 수 있는 자
 4. 아이디 : 이용고객의 식별과 이용자가 서비스 이용을 위하여 이용자가 정한 문자와 숫자의 조합
 5. 비밀번호 : 아이디에 대한 본인 여부를 확인하기 위하여 사용되는 문자, 숫자, 특수문자 등의 조합
 6. 탈퇴 : 서비스 또는 회원이 이용계약을 종료하는 행위
② 본 약관에서 정의하지 않은 용어는 개별서비스에 대한 별도 약관 및 이용규정에서 정의합니다.

제 2 장 서비스 제공 및 이용

제 5 조 (이용 계약의 성립)
① 이용계약은 이용자가 온라인으로 당 사이트에서 제공하는 이용계약 신청서를 작성하여 가입을 완료하는 것으로 성립됩니다.
② 당 사이트는 다음 각 호에 해당하는 경우에 가입을 취소할 수 있습니다.
 1. 다른 사람의 명의를 사용하여 신청하였을 때
 2. 이용 계약 신청서의 내용을 허위로 기재하였거나 신청하였을 때
 3. 사회의 안녕 질서 혹은 미풍양속을 저해할 목적으로 신청하였을 때
 4. 다른 사람의 당 사이트 서비스 이용을 방해하거나 그 정보를 도용하는 등의 행위를 하였을 때
 5. 당 사이트를 이용하여 법령과 본 약관이 금지하는 행위를 하는 경우
 6. 기타 당 사이트가 정한 이용신청요건이 미비 되었을 때
③ 당 사이트는 다음 각 호에 해당하는 경우 그 사유가 소멸될 때까지 이용계약 성립을 유보할 수 있습니다.
 1. 서비스 관련 제반 용량이 부족한 경우
 2. 기술상 장애 사유가 있는 경우
④ 당 사이트가 제공하는 서비스는 자체 개발하거나 다른 기관과의 협의 등을 통해 제공하는 일체의 서비스를 말하는 것이며, 그 내용을 변경할 경우에는 이용자에게 공지한 후 변경하여 제공할 수 있습니다.

제 6 조 (회원정보 사용에 대한 동의)
① 회원의 개인정보는 공공기관의 개인정보보호법에 의해 보호되며 당 사이트의 개인정보처리방침이 적용됩니다.
② 당 사이트의 회원 정보는 다음과 같이 수집, 사용, 관리, 보호됩니다.
 1. 개인정보의 수집 : 당 사이트는 회원 가입시 회원이 제공하는 정보를 수집합니다.
 2. 개인정보의 사용 : 당 사이트는 서비스 제공과 관련해서 수집된 회원정보를 본인의 승낙 없이 제3자에게 누설, 배포하지 않습니다. 단, 전기통신기본법 등 법률의 규정에 의해 국가기관의 요구가 있는 경우, 범죄에 대한 수사상의 목적이 있거나 방송통신심의위원회의 요청이 있는 경우 또는 기타 관계법령에서 정한 절차에 따른 요청이 있는 경우, 회원이 당 사이트에 제공한 개인정보를 스스로 공개한 경우에는 그러하지 않습니다.
 3. 개인정보의 관리 : 회원은 개인정보의 보호 및 관리를 위하여 서비스의 개인정보관리에서 수시로 회원의 개인정보를 수정/삭제할 수 있습니다. 수신되는 정보 중 불필요하다고 생각되는 부분도 변경/조정할 수 있습니다. 개인정보의 이용기간은 이용자가 가입을 완료하고 개인정보관리에서 회원가입을 탈퇴하는 시점이며 보호기간도 동일합니다.
 4. 개인정보의 보호 : 회원의 개인정보는 오직 회원만이 열람/수정/삭제 할 수 있으며, 이는 전적으로 회원의 아이디와 비밀번호에 의해 관리되고 있습니다. 따라서 타인에게 본인의 아이디와 비밀번호를 알려주어서는 아니 되며, 작업 종료 시에는 반드시 로그아웃 해주시고, 웹 브라우저의 창을 닫아주시기 바랍니다.

제 7 조 (회원의 정보 보안)
① 가입 신청자가 당 사이트 서비스 가입 절차를 완료하는 순간부터 회원은 입력한 정보의 비밀을 유지할 책임이 있으며, 회원의 아이디와 비밀번호를 타인에게 제공하여 발생하는 모든 결과에 대한 책임은 회원 본인에게 있습니다.
② 아이디와 비밀번호에 관한 모든 관리의 책임은 회원에게 있으며, 회원의 아이디나 비밀번호가 부정하게 사용되었다는 사실을 발견한 경우에는 즉시 당 사이트에 신고하여야 합니다. 신고를 하지 않음으로 인한 모든 책임은 회원 본인에게 있습니다.
③ 회원은 당 사이트 서비스의 사용 종료 시마다 정확히 접속을 종료하도록 해야 하며, 정확히 종료하지 아니함으로써 제3자가 이용자 또는 회원에 관한 정보를 이용하게 되는 등의 결과로 인해 발생하는 손해 및 손실에 대하여 당 사이트는 책임을 부담하지 아니합니다.

제 8 조 (서비스 이용시간)
① 서비스 이용시간은 당 사이트의 업무상 또는 기술상 특별한 지장이 없는 한 연중무휴, 1일 24시간을 원칙으로 합니다.
② 제1항의 이용시간은 정기점검 등의 필요로 인하여 당 사이트가 정한 날 또는 시간 및 예기치 않은 사건사고로 인한 시간은 예외로 합니다.

제 9 조 (서비스의 중지 및 정보의 저장과 사용)
① 당 사이트 서비스에 보관되거나 전송된 메시지 및 기타 통신 메시지 등의 내용이 국가의 비상사태, 정전, 당 사이트의 관리 범위 외의 서비스 설비 장애 및 기타 불가항력에 의하여 보관되지 못하였거나 삭제된 경우, 전송되지 못한 경우 및 기타 통신 데이터의 손실이 있을 경우에 당 사이트는 관련 책임을 부담하지 아니합니다.
② 당 사이트가 정상적인 서비스 제공의 어려움으로 인하여 일시적으로 서비스를 중지하여야 할 경우에는 서비스 중지 1주일 전의 고지 후 서비스를 중지할 수 있으며, 이 기간 동안 이용자가 고지내용을 인지하지 못한 데 대하여 당 사이트는 책임을 부담하지 아니합니다. 부득이한 사정이 있을 경우 위 사전 고지기간은 감축되거나 생략될 수 있습니다. 
③ 당 사이트의 사정으로 서비스를 영구적으로 중단하여야 할 경우 제2항에 의거합니다. 다만, 이 경우 사전 고지기간은 1개월로 합니다.
④ 당 사이트는 사전 고지 후 서비스를 일시적으로 수정, 변경 및 중단할 수 있으며, 이에 대하여 이용자 또는 제3자에게 어떠한 책임도 부담하지 아니합니다.
⑤ 당 사이트는 이용자가 본 약관의 내용에 위배되는 행동을 한 경우, 임의로 서비스 사용을 제한 및 중지할 수 있습니다. 이 경우 당 사이트는 위 이용자의 접속을 금지할 수 있습니다.
⑥ 장기간 휴면 회원인 경우 안내 메일 또는 공지사항 발표 후 1주일간의 통지 기간을 거쳐 서비스 사용을 중지할 수 있습니다.

제 10 조 (서비스의 변경 및 해지)
① 당 사이트는 이용자가 서비스를 이용하여 얻은 자료로 인한 손해에 관하여 책임을 지지 않으며, 회원이 본 서비스에 게재한 정보, 자료, 사실의 신뢰도, 정확성 등 내용에 관하여는 책임을 지지 않습니다.
② 당 사이트는 서비스 이용과 관련하여 가입자에게 발생한 손해 중 가입자의 고의, 과실에 의한 손해에 대하여 책임을 부담하지 아니합니다.
③ 회원을 탈퇴하고자 하는 경우에는 당 사이트 로그인 후 회원탈퇴 절차에 따라 해지할 수 있습니다.

제 11 조 (정보 제공 및 홍보물 게재)
① 당 사이트는 서비스를 운영함에 있어서 각종 정보를 서비스에 게재하는 방법 등으로 회원에게 제공할 수 있습니다.
② 당 사이트는 서비스에 적절하다고 판단되거나 활용 가능성 있는 홍보물을 게재할 수 있습니다.

제 12 조 (게시물의 저작권)
① 이용자가 게시한 게시물의 내용에 대한 권리는 이용자에게 있습니다.
② 당 사이트는 게시된 내용을 사전 통지 없이 편집, 이동할 수 있는 권리를 보유하며, 사전 통지 없이 삭제할 수 있습니다.

제 13 조 (이용자의 행동규범 및 서비스 이용제한)
① 이용자가 제공하는 정보의 내용이 허위인 것으로 판명되거나, 그러하다고 의심할 만한 합리적인 사유가 발생할 경우 당 사이트는 이용자의 본 서비스 사용을 일부 또는 전부 중지할 수 있으며, 이로 인해 발생하는 불이익에 대해 책임을 부담하지 아니합니다.
② 이용자가 당 사이트 서비스를 통하여 게시, 전송, 입수하였거나 전자메일 기타 다른 수단에 의하여 게시, 전송 또는 입수한 모든 형태의 정보에 대하여는 이용자가 모든 책임을 부담하며 당 사이트는 어떠한 책임도 부담하지 아니합니다.

제 3 장 의무 및 책임

제 14 조 (당 사이트의 의무)
① 당 사이트는 법령과 본 약관이 금지하거나 미풍양속에 반하는 행위를 하지 않으며, 지속적이고 안정적으로 서비스를 제공하기 위해 노력할 의무가 있습니다.
② 당 사이트는 회원의 개인 신상 정보를 본인의 승낙 없이 타인에게 누설, 배포하지 않습니다.
③ 당 사이트는 이용자가 안전하게 당 사이트 서비스를 이용할 수 있도록 보안시스템을 갖추어야 합니다.
④ 당 사이트는 이용자의 귀책사유로 인한 서비스 이용 장애에 대하여 책임을 지지 않습니다.

제 15 조 (회원의 의무)
① 회원 가입시에 요구되는 정보는 정확하게 기입하여야 합니다.
② 회원은 당 사이트의 사전 승낙 없이 서비스를 이용하여 어떠한 영리행위도 할 수 없습니다.

제 4 장 기 타

제 16 조 (당 사이트의 소유권)
① 당 사이트가 제공하는 서비스, 지적재산권 및 기타 권리는 당 사이트에 소유권이 있습니다.

제 17 조 (양도금지)
회원이 서비스의 이용권한, 기타 이용계약 상 지위를 타인에게 양도, 증여할 수 없으며, 이를 담보로 제공할 수 없습니다.

제 18 조 (손해배상)
당 사이트는 무료로 제공되는 서비스와 관련하여 회원에게 어떠한 손해가 발생하더라도 당 사이트가 고의로 행한 범죄행위를 제외하고 이에 대하여 책임을 부담하지 아니합니다.

제 19 조 (면책조항)
① 당 사이트는 서비스에 표출된 어떠한 의견이나 정보에 대해 확신이나 대표할 의무가 없으며 회원이나 제3자에 의해 표출된 의견을 승인하거나 반대하거나 수정하지 않습니다.

제 20 조 (관할법원)
본 서비스 이용과 관련하여 발생한 분쟁에 대해 소송이 제기될 경우 대전지방법원을 전속적 관할 법원으로 합니다.

부 칙
(시행일) 본 약관은 2026년 3월 25일부터 시행됩니다.
`;

const TERMS_PRIVACY = `
1. 개인정보의 수집항목 및 수집방법 
AIWORK에서는 기본적인 회원 서비스 제공을 위한 필수정보로 실명인증정보와 가입정보로 구분하여 다음의 정보를 수집하고 있습니다. 필수정보를 입력해주셔야 회원 서비스 이용이 가능합니다.

가. 수집하는 개인정보의 항목 
* 수집하는 필수항목
- 실명인증정보 : 이름, 이메일 인증
- 가입정보 : 아이디, 비밀번호, 성명, 이메일

[컴퓨터에 의해 자동으로 수집되는 정보]
인터넷 서비스 이용과정에서 아래 개인정보 항목이 자동으로 생성되어 수집될 수 있습니다. 
- IP주소, 서비스 이용기록, 방문기록 등

나. 개인정보 수집방법
홈페이지 회원가입을 통한 수집 

2. 개인정보의 수집/이용 목적 및 보유/이용 기간
AIWORK에서는 정보주체의 회원 가입일로부터 서비스를 제공하는 기간 동안에 한하여 AIWORK 서비스를 이용하기 위한 최소한의 개인정보를 보유 및 이용 하게 됩니다. 회원가입 등을 통해 개인정보의 수집·이용, 제공 등에 대해 동의하신 내용은 언제든지 철회하실 수 있습니다. 회원 탈퇴를 요청하거나 수집/이용목적을 달성하거나 보유/이용기간이 종료한 경우, 사업 폐지 등의 사유발생시 개인 정보를 지체 없이 파기합니다.

* 실명인증정보
- 개인정보 수집항목 : 이름, 이메일 인증
- 개인정보의 수집·이용목적 : 홈페이지 이용에 따른 본인 식별/인증절차에 이용
- 개인정보의 보유 및 이용기간 : 별도로 저장하지 않으며 실명인증용으로만 이용

* 가입정보
- 개인정보 수집항목 : 아이디, 비밀번호, 성명, 이메일
- 개인정보의 수집·이용목적 : 홈페이지 서비스 이용 및 회원관리, 불량회원의 부정 이용방지, 민원신청 및 처리 등
- 개인정보의 보유 및 이용기간 : 1년 또는 회원탈퇴시

정보주체는 개인정보의 수집·이용목적에 대한 동의를 거부할 수 있으며, 동의 거부시 AIWORK에 회원가입이 되지 않으며, AIWORK에서 제공하는 서비스를 이용할 수 없습니다.

3. 수집한 개인정보 제3자 제공
AIWORK에서는 정보주체의 동의, 법률의 특별한 규정 등 개인정보 보호법 제17조 및 제18조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.
        
4. 개인정보 처리업무 안내
AIWORK에서는 개인정보의 취급위탁은 하지 않고 있으며, 원활한 서비스 제공을 위해 아래의 기관을 통한 실명인증 및 공공 I-PIN, GPKI 인증을 하고 있습니다. 

* 수탁업체
- 사자개, SKN23-4th-1TEAM 
`;

interface SignUpFormProps {
  onSwitchMode: (mode: "login" | "signup" | "find") => void;
}

export const SignUpForm = ({ onSwitchMode }: SignUpFormProps) => {
  const [email, setEmail] = useState("");
  const [isEmailChecked, setIsEmailChecked] = useState(false);
  const [isEmailAvailable, setIsEmailAvailable] = useState<boolean | null>(
    null,
  );

  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [authCode, setAuthCode] = useState("");
  const [inputCode, setInputCode] = useState("");
  const [isCodeSent, setIsCodeSent] = useState(false);
  const [isVerified, setIsVerified] = useState(false);

  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [agreeTerms, setAgreeTerms] = useState(false);
  const [agreePrivacy, setAgreePrivacy] = useState(false);

  const [showTermsModal, setShowTermsModal] = useState<{
    title: string;
    content: string;
  } | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [globalError, setGlobalError] = useState("");

  const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
  const namePattern = /^[가-힣a-zA-Z\s]+$/;
  const pwPattern = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[\W_]).{8,}$/;

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value);
    setIsEmailChecked(false);
    setIsEmailAvailable(null);
    setIsVerified(false);
    setIsCodeSent(false);
  };

  const handleCheckEmail = async () => {
    if (!email || !emailPattern.test(email)) {
      setIsEmailAvailable(false);
      return;
    }
    setIsLoading(true);
    try {
      const data = await authApi.checkEmail(email);
      setIsEmailAvailable(!data.exists);
      setIsEmailChecked(true);
    } catch (err) {
      setIsEmailAvailable(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendCode = async () => {
    setIsLoading(true);
    try {
      const generatedCode = Math.floor(
        100000 + Math.random() * 900000,
      ).toString();
      await authApi.sendSignupEmail({ email, auth_code: generatedCode });
      setAuthCode(generatedCode);
      setIsCodeSent(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || "발송 실패");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = () => {
    if (inputCode === authCode) {
      setIsVerified(true);
      setShowVerifyModal(false);
    } else {
      alert("인증번호가 일치하지 않습니다.");
    }
  };

  const handleToggleAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked;
    setAgreeTerms(checked);
    setAgreePrivacy(checked);
  };

  const handleSubmit = async () => {
    setGlobalError("");

    if (!isVerified) return setGlobalError("이메일 인증을 먼저 진행해주세요.");
    if (!name || !namePattern.test(name))
      return setGlobalError("이름 형식을 확인해주세요.");
    if (!password || !pwPattern.test(password))
      return setGlobalError("비밀번호 형식을 확인해주세요.");
    if (password !== confirmPassword)
      return setGlobalError("비밀번호가 일치하지 않습니다.");
    if (!agreeTerms || !agreePrivacy)
      return setGlobalError("필수 약관에 모두 동의해주세요.");

    setIsLoading(true);
    try {
      await authApi.register({ email, password, name });
      setShowSuccessModal(true);
      setTimeout(() => onSwitchMode("login"), 3000);
    } catch (err: any) {
      setGlobalError(err.response?.data?.detail || "회원가입에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="signup-form-container">
      <div className="login-logo">회원가입</div>

      <div className="input-row">
        <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
          <input
            type="text"
            value={email}
            onChange={handleEmailChange}
            placeholder="아이디 (이메일)"
            disabled={isVerified}
          />
        </div>
        <button
          type="button"
          className="check-btn"
          onClick={handleCheckEmail}
          disabled={!email || isVerified || isLoading}
        >
          중복 확인
        </button>
      </div>

      {isEmailChecked && isEmailAvailable === true && (
        <div className="field-msg text-success">사용 가능한 아이디입니다.</div>
      )}
      {isEmailChecked && isEmailAvailable === false && (
        <div className="field-msg text-error">
          이미 가입되거나 유효하지 않은 아이디입니다.
        </div>
      )}

      {!isVerified ? (
        <button
          type="button"
          className="verify-trigger-btn"
          onClick={() => {
            if (isEmailChecked && isEmailAvailable) setShowVerifyModal(true);
            else alert("먼저 중복 확인을 진행해주세요.");
          }}
        >
          인증하기
        </button>
      ) : (
        <button type="button" className="verify-trigger-btn disabled" disabled>
          인증 완료
        </button>
      )}

      <hr className="divider" />

      <div className="input-group">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="이름 (한글 또는 영문)"
        />
        {name &&
          (namePattern.test(name) ? (
            <div className="field-msg text-success">
              올바른 이름 형식입니다.
            </div>
          ) : (
            <div className="field-msg text-error">
              한글과 영어만 입력 가능합니다.
            </div>
          ))}
      </div>

      <div className="input-group">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="비밀번호 (영문, 숫자, 특수문자 포함 8자 이상)"
        />
        {password &&
          (pwPattern.test(password) ? (
            <div className="field-msg text-success">안전한 비밀번호입니다.</div>
          ) : (
            <div className="field-msg text-error">
              형식에 맞게 입력해주세요.
            </div>
          ))}
      </div>

      <div className="input-group">
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="비밀번호 확인"
        />
        {confirmPassword &&
          (password === confirmPassword ? (
            <div className="field-msg text-success">비밀번호가 일치합니다.</div>
          ) : (
            <div className="field-msg text-error">
              비밀번호가 일치하지 않습니다.
            </div>
          ))}
      </div>

      <div className="terms-box">
        <label className="term-row all-agree">
          <input
            type="checkbox"
            checked={agreeTerms && agreePrivacy}
            onChange={handleToggleAll}
          />
          <span>
            <strong>전체 동의하기</strong>
          </span>
        </label>
        <div className="term-desc">
          필수 이용약관 및 개인정보 수집/이용 동의를 포함합니다.
        </div>
        <hr />
        <div className="term-row">
          <label>
            <input
              type="checkbox"
              checked={agreeTerms}
              onChange={(e) => setAgreeTerms(e.target.checked)}
            />
            <span>
              <strong>(필수)</strong> <strong>AIWORK</strong> 이용약관
            </span>
          </label>
          <button
            type="button"
            onClick={() =>
              setShowTermsModal({
                title: "AIWORK 이용약관",
                content: TERMS_AIWORK,
              })
            }
          >
            보기
          </button>
        </div>
        <div className="term-row">
          <label>
            <input
              type="checkbox"
              checked={agreePrivacy}
              onChange={(e) => setAgreePrivacy(e.target.checked)}
            />
            <span>
              <strong>(필수)</strong> 개인정보 수집/이용 동의
            </span>
          </label>
          <button
            type="button"
            onClick={() =>
              setShowTermsModal({
                title: "개인정보 수집/이용 동의",
                content: TERMS_PRIVACY,
              })
            }
          >
            보기
          </button>
        </div>
      </div>

      {globalError && (
        <div className="status-msg text-error">{globalError}</div>
      )}

      <button
        type="button"
        className="submit-btn"
        onClick={handleSubmit}
        disabled={isLoading}
      >
        {isLoading ? "저장 중..." : "가입하기"}
      </button>

      <div className="helper-links">
        <button
          type="button"
          className="text-btn"
          onClick={() => onSwitchMode("login")}
        >
          이미 계정이 있으신가요? 로그인
        </button>
      </div>

      {showVerifyModal &&
        createPortal(
          <div className="custom-modal-overlay">
            <div className="custom-modal">
              <div className="modal-header">
                <h3>이메일 인증</h3>
                <button type="button" onClick={() => setShowVerifyModal(false)}>
                  <X size={20} />
                </button>
              </div>
              <div className="modal-body">
                <p>
                  본인 확인을 진행합니다.
                  <br />
                  가입하실 이메일 주소로 인증번호를 발송합니다.
                </p>
                <input
                  type="text"
                  value={email}
                  disabled
                  className="disabled-input"
                />
                <button
                  type="button"
                  className="action-btn"
                  onClick={handleSendCode}
                  disabled={isLoading}
                >
                  {isCodeSent ? "인증번호 재발송" : "인증번호 발송"}
                </button>

                {isCodeSent && (
                  <>
                    <hr
                      style={{ margin: "20px 0", borderTop: "1px solid #eee" }}
                    />
                    <input
                      type="text"
                      value={inputCode}
                      onChange={(e) => setInputCode(e.target.value)}
                      placeholder="인증번호 6자리"
                    />
                    <button
                      type="button"
                      className="action-btn primary"
                      onClick={handleVerifyCode}
                    >
                      인증 확인
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>,
          document.body,
        )}

      {showTermsModal &&
        createPortal(
          <div className="custom-modal-overlay">
            <div className="custom-modal large">
              <div className="modal-header">
                <h3>{showTermsModal.title}</h3>
                <button type="button" onClick={() => setShowTermsModal(null)}>
                  <X size={20} />
                </button>
              </div>
              <div className="modal-body terms-content">
                {showTermsModal.content}
              </div>
              <button
                type="button"
                className="action-btn primary"
                style={{ margin: "20px 20px", width: "calc(100% - 40px)" }}
                onClick={() => setShowTermsModal(null)}
              >
                확인
              </button>
            </div>
          </div>,
          document.body,
        )}

      {showSuccessModal &&
        createPortal(
          <div className="custom-modal-overlay">
            <div className="custom-modal text-center">
              <div
                className="icon"
                style={{ fontSize: "50px", marginBottom: "10px" }}
              >
                👾
              </div>
              <h2 style={{ color: "#0176f7", margin: "0 0 15px 0" }}>
                환영합니다!
              </h2>
              <p>
                <b>{name}</b>님,
                <br />
                회원가입이 성공적으로 완료되었습니다.
              </p>
              <p style={{ fontSize: "13px", color: "#888", marginTop: "20px" }}>
                3초 후 로그인 페이지로 자동 이동합니다...
              </p>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};
