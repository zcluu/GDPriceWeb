import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import { api } from "../api/endpoints";
import { useAuthStore } from "../store";

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const signIn = useAuthStore((state) => state.signIn);
  const redirect = searchParams.get("redirect") || "/dashboard";
  const mutation = useMutation({
    mutationFn: () => api.login(password),
    onSuccess: (data) => {
      signIn(data.access_token);
      navigate(redirect, { replace: true });
    }
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-crest">
          <ShieldCheck size={28} />
        </div>
        <h1>金价守望</h1>
        <p>输入系统密码后进入个人积存金监控台。</p>
        <form onSubmit={submit}>
          <label>系统密码</label>
          <div className="input-with-icon">
            <LockKeyhole size={18} />
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoFocus
              placeholder="请输入密码"
            />
          </div>
          {mutation.error && <div className="form-error">{mutation.error.message}</div>}
          <button className="primary-button full" disabled={!password || mutation.isPending}>
            {mutation.isPending ? "正在校验" : "进入系统"}
          </button>
        </form>
      </div>
    </div>
  );
}
