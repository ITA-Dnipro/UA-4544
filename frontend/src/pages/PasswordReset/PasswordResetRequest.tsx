import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import styles from "./PasswordReset.module.css";

interface IResetRequestForm {
  email: string;
}

const PasswordResetRequest: React.FC = () => {
  const [isSent, setIsSent] = useState<boolean>(false);
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
  } = useForm<IResetRequestForm>({ mode: "onChange" });

  const onSubmit = async (data: IResetRequestForm): Promise<void> => {
    try {
      await fetch("/api/auth/password-reset/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: data.email }),
      });
    } catch {
    } finally {
      setIsSent(true);
    }
  };

  if (isSent) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.container}>
          <h1 className={styles.title}>Check your email</h1>
          <hr className={styles.divider} />

          <p className={styles.description}>
            We have sent password reset instructions to your email address.
            Please check your inbox and follow the link provided.
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
        <h1 className={styles.title}>Forgot Password?</h1>
        <hr className={styles.divider} />

        <p className={styles.description}>
          Enter the email address associated with your account and we'll send
          you a link to reset your password.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="email" className={styles.label}>
              Email Address
            </label>

            <input
              id="email"
              type="email"
              {...register("email", {
                required: "Email is required",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: "Invalid email format",
                },
              })}
              className={`${styles.input} ${
                errors.email ? styles.inputError : ""
              }`}
              placeholder="Enter your email"
            />

            {errors.email && (
              <span className={styles.errorText}>{errors.email.message}</span>
            )}
          </div>

          <button
            type="submit"
            className={styles.submitButton}
            disabled={!isValid || isSubmitting}
          >
            {isSubmitting ? "Sending..." : "Reset Password"}
          </button>
        </form>
      </div>

      <div className={styles.outsideFooter}>
        <Link to="/login" className={styles.backLink}>
          I remember my password. <strong>Back to login</strong>
        </Link>
      </div>
    </div>
  );
};

export default PasswordResetRequest;
