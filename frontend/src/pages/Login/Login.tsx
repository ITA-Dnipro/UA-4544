import React, { useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { Loader2, Eye, EyeOff } from "lucide-react";
import styles from "./Login.module.css";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";

interface ILoginForm {
  email: string;
  password: string;
  role: string;
  rememberMe: boolean;
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ILoginForm>({
    mode: "onBlur",
    defaultValues: { role: "startup", rememberMe: false },
  });

  const watchedFields = watch();

  const getFieldClassName = (fieldName: keyof ILoginForm) => {
    let stateClass = styles.inputDefault;

    if (errors[fieldName]) {
      stateClass = styles.inputError;
    } else if (watchedFields[fieldName]) {
      stateClass = styles.inputSuccess;
    }

    return `${styles.inputBase} ${stateClass}`;
  };

  const onSubmit: SubmitHandler<ILoginForm> = async (data) => {
    setIsLoading(true);
    setServerError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      navigate("/");
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : "Server error occurred",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Login to Platform</h1>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          {serverError && (
            <div className={styles.serverError}>{serverError}</div>
          )}

          <div>
            <label htmlFor="email-input" className={styles.label}>
              Email Address
            </label>
            <input
              id="email-input"
              type="email"
              placeholder="Enter your email"
              className={getFieldClassName("email")}
              {...register("email", {
                required: "Email is required",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: "Invalid email format",
                },
              })}
            />
            {errors.email && (
              <p className={styles.errorText}>{errors.email.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password-input" className={styles.label}>
              Password
            </label>
            <div className={styles.passwordWrapper}>
              <input
                id="password-input"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                className={getFieldClassName("password")}
                {...register("password", {
                  required: "Password is required",
                  minLength: {
                    value: 6,
                    message: "Minimum 6 characters required",
                  },
                })}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className={styles.eyeButton}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && (
              <p className={styles.errorText}>{errors.password.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="role-select" className={styles.label}>
              User Role
            </label>
            <div className={styles.passwordWrapper}>
              <select
                id="role-select"
                className={getFieldClassName("role")}
                {...register("role")}
              >
                <option value="startup">Startup</option>
                <option value="investor">Investor</option>
              </select>
            </div>
          </div>
          <div className={styles.optionsRow}>
            <div className={styles.checkboxContainer}>
              <label className={styles.checkboxLabel}>
                <input type="checkbox" {...register("rememberMe")} />
                <span>Remember me</span>
              </label>
            </div>
            <div className={styles.forgotPasswordWrapper}>
              <Link to="/password-reset" className={styles.forgotPasswordLink}>
                Forgot password?
              </Link>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`${styles.submitButton} ${isLoading ? styles.btnDisabled : styles.btnIdle}`}
          >
            {isLoading ? (
              <Loader2 className={styles.spinner} size={18} />
            ) : (
              "Log In"
            )}
          </button>
        </form>
      </div>

      <p className={styles.footerText}>
        New here?{" "}
        <Link to="/register" className={styles.registerLink}>
          Create an account
        </Link>
      </p>
    </div>
  );
};

export default LoginPage;
