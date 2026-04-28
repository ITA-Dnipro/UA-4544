import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import styles from "./PasswordReset.module.css";

interface IResetConfirmForm {
  password: string;
  confirmPassword: string;
}

const PasswordResetConfirm: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] =
    useState<boolean>(false);

  const token = searchParams.get("token");
  const uid = searchParams.get("uid");

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid, isSubmitting },
  } = useForm<IResetConfirmForm>({
    mode: "onChange",
  });

  const password = watch("password");

  const onSubmit = async (data: IResetConfirmForm) => {
    setError(null);

    try {
      const res = await fetch("/api/auth/password-reset/confirm/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
          uid,
          password: data.password,
        }),
      });

      if (!res.ok) {
        throw new Error();
      }

      setIsSuccess(true);
    } catch (e) {
      setError("This password reset link is invalid or has expired.");
    }
  };

  if (!token || !uid) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.container}>
          <h1 className={styles.title}>Reset Link Error</h1>
          <hr className={styles.divider} />

          <p className={styles.description}>
            This password reset link is invalid or has expired.
          </p>

          <button
            onClick={() => navigate("/password-reset")}
            className={styles.submitButton}
          >
            Request a New Link
          </button>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.container}>
          <h1 className={styles.title}>Password Changed</h1>
          <hr className={styles.divider} />

          <p className={styles.description}>
            Your password has been successfully updated. You can now log in to
            your account with your new password.
          </p>

          <div className={styles.buttonWrapper}>
            <button
              onClick={() => navigate("/login")}
              className={styles.submitButton}
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.container}>
        <h1 className={styles.title}>Reset Password</h1>
        <hr className={styles.divider} />

        {error && <p className={styles.errorText}>{error}</p>}

        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="password" className={styles.label}>
              New Password
            </label>
            <p className={styles.inputHelpText}>
              Password must be at least 8 characters long and include an
              uppercase letter, a lowercase letter, and a digit.
            </p>

            <div className={styles.passwordInputWrapper}>
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                {...register("password", {
                  required: "Please enter a password",
                  minLength: {
                    value: 8,
                    message: "Minimum 8 characters required",
                  },
                  pattern: {
                    value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/,
                    message: "Password does not meet the requirements",
                  },
                })}
                className={`${styles.input} ${
                  errors.password ? styles.inputError : ""
                }`}
                placeholder="Enter new password"
              />

              <button
                type="button"
                className={styles.eyeButton}
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>

            {errors.password && (
              <span className={styles.errorText}>
                {errors.password.message}
              </span>
            )}
          </div>

          <div className={styles.inputGroup}>
            <label htmlFor="confirmPassword" className={styles.label}>
              Confirm New Password
            </label>

            <div className={styles.passwordInputWrapper}>
              <input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                {...register("confirmPassword", {
                  required: "Please confirm your password",
                  validate: (value) =>
                    value === password ||
                    "Passwords do not match. Please ensure both fields are identical.",
                })}
                className={`${styles.input} ${
                  errors.confirmPassword ? styles.inputError : ""
                }`}
                placeholder="Repeat password"
              />

              <button
                type="button"
                className={styles.eyeButton}
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label={
                  showConfirmPassword
                    ? "Hide confirm password"
                    : "Show confirm password"
                }
                aria-pressed={showConfirmPassword}
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>

            {errors.confirmPassword && (
              <span className={styles.errorText}>
                {errors.confirmPassword.message}
              </span>
            )}
          </div>

          <div className={styles.buttonWrapper}>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={!isValid || isSubmitting}
            >
              {isSubmitting ? "Saving..." : "Save Password"}
            </button>
          </div>
        </form>
      </div>

      <div className={styles.outsideFooter}>
        <Link to="/login" className={styles.backLink}>
          Back to Login
        </Link>
      </div>
    </div>
  );
};

export default PasswordResetConfirm;
