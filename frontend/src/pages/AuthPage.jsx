import {
  ArrowRight,
  LineChart,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  WalletCards,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { PasswordInput } from "../components/PasswordInput";
import { ThemeToggle } from "../components/ThemeToggle";
import { useToast } from "../components/ToastProvider";
import { useAuth } from "../context/AuthContext";
import { computePasswordStrength } from "../utils/password";

const REMEMBER_KEY = "budgetflow:remember-username";

const initialLogin = {
  username: "",
  password: "",
};

const initialRegister = {
  username: "",
  first_name: "",
  email: "",
  password: "",
  password_confirm: "",
};

const REGISTER_FIELDS = ["username", "first_name", "email", "password", "password_confirm"];
const LOGIN_FIELDS = ["username", "password"];

const PREVIEW_ROWS = [
  { name: "Groceries", fill: 71, amount: "$284 / $400", color: "#059669" },
  { name: "Rent", fill: 95, amount: "$1,140 / $1,200", color: "#4f46e5" },
  { name: "Fun money", fill: 35, amount: "$52 / $150", color: "#10b981" },
];

const HERO_STATS = [
  { value: "4.9★", label: "Average rating" },
  { value: "12K+", label: "Households planning" },
  { value: "$240M", label: "Tracked this year" },
];

const TRUST_ITEMS = [
  { icon: ShieldCheck, label: "Bank-level encryption" },
  { icon: Sparkles, label: "No card required" },
  { icon: LockKeyhole, label: "Free forever plan" },
];

function PasswordStrengthMeter({ password }) {
  const { score, label } = computePasswordStrength(password);
  return (
    <div className="password-strength" aria-live="polite">
      <div className="password-strength__track">
        <span
          className={`password-strength__fill password-strength__fill--${score}`}
          style={{ width: `${(score / 4) * 100}%` }}
        />
      </div>
      <small className={`password-strength__label password-strength__label--${score}`}>
        {label}
      </small>
    </div>
  );
}

function extractFieldErrors(data, fields) {
  if (!data || typeof data !== "object") {
    return {};
  }
  const result = {};
  for (const field of fields) {
    const value = data[field];
    if (Array.isArray(value)) {
      result[field] = value.map(String).join(" ");
    } else if (typeof value === "string") {
      result[field] = value;
    }
  }
  return result;
}

export function AuthPage() {
  const { isAuthenticated, login, register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("login");
  const [loginForm, setLoginForm] = useState(initialLogin);
  const [registerForm, setRegisterForm] = useState(initialRegister);
  const [remember, setRemember] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    try {
      const saved = localStorage.getItem(REMEMBER_KEY);
      if (saved) {
        setLoginForm((current) => ({ ...current, username: saved }));
      } else {
        setRemember(false);
      }
    } catch {
      /* ignore storage errors */
    }
  }, []);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const nextPath = location.state?.from?.pathname || "/dashboard";

  function updateLogin(event) {
    const { name, value } = event.target;
    setLoginForm((current) => ({ ...current, [name]: value }));
  }

  function updateRegister(event) {
    const { name, value } = event.target;
    setRegisterForm((current) => ({ ...current, [name]: value }));
  }

  function handleForgotPassword() {
    navigate("/forgot-password");
  }

  async function handleLogin(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!loginForm.username.trim()) {
      nextErrors.username = "Username is required.";
    }
    if (!loginForm.password) {
      nextErrors.password = "Password is required.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      await login({
        username: loginForm.username.trim(),
        password: loginForm.password,
      });
      try {
        if (remember) {
          localStorage.setItem(REMEMBER_KEY, loginForm.username.trim());
        } else {
          localStorage.removeItem(REMEMBER_KEY);
        }
      } catch {
        /* ignore storage errors */
      }
      toast.success("Welcome back!", "Let's see how your money's doing.");
      navigate(nextPath, { replace: true });
    } catch (error) {
      const fieldErrors = extractFieldErrors(error.data, LOGIN_FIELDS);
      if (Object.keys(fieldErrors).length > 0) {
        setErrors((current) => ({ ...current, ...fieldErrors }));
      }
      toast.error("Login failed", error.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!registerForm.username.trim()) {
      nextErrors.username = "Username is required.";
    }
    if (!registerForm.email.trim()) {
      nextErrors.email = "Email is required.";
    }
    if (!registerForm.password) {
      nextErrors.password = "Choose a password.";
    }
    if (registerForm.password !== registerForm.password_confirm) {
      nextErrors.password_confirm = "Passwords must match.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      await register({
        ...registerForm,
        username: registerForm.username.trim(),
        email: registerForm.email.trim(),
        first_name: registerForm.first_name.trim(),
      });
      toast.success("You're in!", "We added a few starter categories to get you going.");
      navigate("/dashboard", { replace: true });
    } catch (error) {
      const fieldErrors = extractFieldErrors(error.data, REGISTER_FIELDS);
      if (Object.keys(fieldErrors).length > 0) {
        setErrors((current) => ({ ...current, ...fieldErrors }));
      }
      toast.error("Registration failed", error.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel auth-panel--hero">
        <div className="brand-mark brand-mark--hero">
          <span className="brand-mark__badge">
            <WalletCards size={20} />
          </span>
          <div>
            <strong>BudgetFlow</strong>
            <p>Beautiful budgeting for real life.</p>
          </div>
        </div>

        <div className="auth-copy">
          <span className="eyebrow">Money, made friendly</span>
          <h1>Build a healthier budget rhythm — no spreadsheets required.</h1>
          <p>
            Organize your envelopes, move money in a tap, and see exactly where your spending
            goes on a calm, friendly dashboard.
          </p>
        </div>

        <div className="hero-stats">
          {HERO_STATS.map((stat) => (
            <div className="hero-stats__item" key={stat.label}>
              <span className="hero-stats__value">{stat.value}</span>
              <span className="hero-stats__label">{stat.label}</span>
            </div>
          ))}
        </div>

        <div className="hero-preview">
          <article className="hero-preview__card">
            <div className="hero-preview__header">
              <span className="hero-preview__title">
                <LineChart size={18} /> May envelopes
              </span>
              <span className="hero-preview__pill">Live preview</span>
            </div>
            <div className="hero-preview__rows">
              {PREVIEW_ROWS.map((row) => (
                <div className="hero-preview__row" key={row.name}>
                  <div className="hero-preview__row-top">
                    <span className="hero-preview__row-name">
                      <span
                        className="hero-preview__dot"
                        style={{ "--dot": row.color }}
                      />
                      {row.name}
                    </span>
                    <span className="hero-preview__row-amount">{row.amount}</span>
                  </div>
                  <div className="hero-preview__bar">
                    <span
                      className="hero-preview__bar-fill"
                      style={{ "--fill": `${row.fill}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <div className="trust-strip">
            {TRUST_ITEMS.map(({ icon: Icon, label }) => (
              <div className="trust-strip__item" key={label}>
                <Icon size={16} />
                {label}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="auth-panel auth-panel--form">
        <div className="auth-panel__topbar">
          <ThemeToggle />
        </div>
        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === "login" ? "auth-tab--active" : ""}`}
            onClick={() => {
              setMode("login");
              setErrors({});
            }}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === "register" ? "auth-tab--active" : ""}`}
            onClick={() => {
              setMode("register");
              setErrors({});
            }}
          >
            Create account
          </button>
        </div>

        {mode === "login" ? (
          <form className="auth-form" onSubmit={handleLogin}>
            <div className="auth-heading">
              <h2>Welcome back</h2>
              <p>Pick up where you left off and keep your plan moving.</p>
            </div>

            <label className="field">
              <span>Username</span>
              <input
                name="username"
                value={loginForm.username}
                onChange={updateLogin}
                placeholder="Enter your username"
                autoComplete="username"
              />
              {errors.username ? <small>{errors.username}</small> : null}
            </label>

            <label className="field">
              <span>Password</span>
              <PasswordInput
                name="password"
                value={loginForm.password}
                onChange={updateLogin}
                placeholder="Enter your password"
                autoComplete="current-password"
              />
              {errors.password ? <small>{errors.password}</small> : null}
            </label>

            <div className="auth-form__row-between">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                />
                Remember me
              </label>
              <button type="button" className="link-button" onClick={handleForgotPassword}>
                Forgot password?
              </button>
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
              <LockKeyhole size={16} />
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleRegister}>
            <div className="auth-heading">
              <h2>Let's get you set up</h2>
              <p>We'll add a few starter categories so you can jump right in.</p>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>Username</span>
                <input
                  name="username"
                  value={registerForm.username}
                  onChange={updateRegister}
                  placeholder="Choose a username"
                  autoComplete="username"
                />
                {errors.username ? <small>{errors.username}</small> : null}
              </label>

              <label className="field">
                <span>Display name</span>
                <input
                  name="first_name"
                  value={registerForm.first_name}
                  onChange={updateRegister}
                  placeholder="How should we greet you?"
                  autoComplete="given-name"
                />
              </label>

              <label className="field field--full">
                <span>Email</span>
                <input
                  type="email"
                  name="email"
                  value={registerForm.email}
                  onChange={updateRegister}
                  placeholder="you@example.com"
                  autoComplete="email"
                />
                {errors.email ? <small>{errors.email}</small> : null}
              </label>

              <label className="field">
                <span>Password</span>
                <PasswordInput
                  name="password"
                  value={registerForm.password}
                  onChange={updateRegister}
                  placeholder="Create a password"
                  autoComplete="new-password"
                />
                {errors.password ? <small>{errors.password}</small> : null}
                {registerForm.password ? (
                  <PasswordStrengthMeter password={registerForm.password} />
                ) : null}
              </label>

              <label className="field">
                <span>Confirm password</span>
                <PasswordInput
                  name="password_confirm"
                  value={registerForm.password_confirm}
                  onChange={updateRegister}
                  placeholder="Repeat your password"
                  autoComplete="new-password"
                />
                {errors.password_confirm ? <small>{errors.password_confirm}</small> : null}
              </label>
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
              <ArrowRight size={16} />
              {submitting ? "Creating account..." : "Create account"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
