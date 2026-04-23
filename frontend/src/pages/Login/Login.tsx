import React, { useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { Loader2, Eye, EyeOff, ChevronDown } from "lucide-react";
import styles from "./Login.module.css";
import { useNavigate } from "react-router-dom";

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
    defaultValues: { role: "user", rememberMe: false },
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
      console.log("Дані форми:", data);
      navigate("/");
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Помилка сервера");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Вхід на платформу</h1>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          {serverError && (
            <div className={styles.serverError}>{serverError}</div>
          )}

          <div>
            <label className={styles.label}>Електронна пошта</label>
            <input
              type="email"
              placeholder="Введіть email"
              className={getFieldClassName("email")}
              {...register("email", {
                required: "Обов'язкове поле",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: "Невірний формат",
                },
              })}
            />
            {errors.email && (
              <p className={styles.errorText}>{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className={styles.label}>Пароль</label>
            <div className={styles.passwordWrapper}>
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Введіть пароль"
                className={getFieldClassName("password")}
                {...register("password", {
                  required: "Пароль обов'язковий",
                  minLength: { value: 6, message: "Мінімум 6 символів" },
                })}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className={styles.eyeButton}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && (
              <p className={styles.errorText}>{errors.password.message}</p>
            )}
          </div>

          <div>
            <label className={styles.label}>Роль користувача</label>
            <div className={styles.passwordWrapper}>
              <select
                className={getFieldClassName("role")}
                {...register("role")}
              >
                <option value="user">Користувач</option>
                <option value="admin">Стартап</option>
                <option value="investor">Інвестор</option>
              </select>
            </div>
          </div>

          <div className={styles.checkboxContainer}>
            <label className={styles.checkboxLabel}>
              <input type="checkbox" {...register("rememberMe")} />
              <span>Запам'ятати мене</span>
            </label>
            <a href="/forgot-password" className={styles.forgotLink}>
              Забули пароль?
            </a>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`${styles.submitButton} ${isLoading ? styles.btnDisabled : styles.btnIdle}`}
          >
            {isLoading ? (
              <Loader2 className="animate-spin mr-2" size={18} />
            ) : (
              "Увійти"
            )}
          </button>
        </form>
      </div>

      <p className={styles.footerText}>
        Вперше тут?{" "}
        <a href="/register" className={styles.registerLink}>
          Зареєструйтесь
        </a>
      </p>
    </div>
  );
};

export default LoginPage;
